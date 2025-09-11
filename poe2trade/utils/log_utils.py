# poe2trade/utils/log_utils.py
"""
log_utils.py · v8 — NFKC-normalize buyer & item; robust player-name validation
───────────────────────────────────────────────────────────────────────────────
• read_all_log_trades(log_files, history_weeks=3, *, dedupe_by_buyer=True)
    → returns newest→oldest trades within cutoff
    → keeps only the most-recent (max timestamp) entry per
      (buyer, item_name, amount, currency)
• Fast reverse scan: reads each log from the end in ~8 KiB blocks,
  stopping once any parsed trade is older than the cutoff.
• Buyer names are NFKC-normalized and validated for Unicode letters/numbers.
• Item names are NFC-normalized.
"""

from __future__ import annotations
import os
import re
import unicodedata
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

import regex  # better Unicode regex support

# parse any Unicode in buyer or item; DOTALL so '.' matches newlines
_TRADE_RE = re.compile(
    r'(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'@From\s(?P<buyer>[^:]+?):\sHi, I would like to buy your '
    r'(?P<item>.*?) listed for (?P<amount>\d+)\s(?P<cur>\w+)',
    re.DOTALL | re.UNICODE,
)

# Allow Unicode letters/numbers across all scripts, plus _, -, space
_VALID_NAME = regex.compile(r"^[\p{L}\p{N}_\- ]{3,16}$", flags=regex.UNICODE)


def _normalize_player_name(name: str) -> str:
    """
    Normalize and validate a player name.

    - Use NFKC normalization to unify similar-looking codepoints
      (Cyrillic vs Latin homoglyphs, etc.)
    - Strip whitespace
    - Validate against allowed characters (letters/numbers, _, -, space)
    """
    cleaned = unicodedata.normalize("NFKC", name.strip())
    if not _VALID_NAME.match(cleaned):
        # Soft fallback: return cleaned even if not valid
        # (avoids dropping trades with weird buyer names)
        return cleaned
    return cleaned


def _parse_trade_line(line: str) -> Dict | None:
    """
    Parse a single log line into its trade components.
    Returns None if the line doesn’t match the trade pattern.
    Buyer names are NFKC-normalized and validated;
    item names are NFC-normalized.
    """
    m = _TRADE_RE.search(line)
    if not m:
        return None

    buyer = _normalize_player_name(m.group("buyer"))
    item = unicodedata.normalize("NFC", m.group("item").strip())

    return {
        "timestamp": datetime.strptime(m.group("ts"), "%Y/%m/%d %H:%M:%S"),
        "buyer": buyer,
        "item_name": item,
        "amount": int(m.group("amount")),
        "currency": m.group("cur").lower(),
    }


def _offer_key(rec: Dict) -> Tuple[str, str, int, str]:
    return (
        rec["buyer"].strip().lower(),
        rec["item_name"].strip().lower(),
        int(rec["amount"]),
        rec["currency"].strip().lower(),
    )


def read_all_log_trades(
    log_files: List[str],
    history_weeks: int = 3,
    *, dedupe_by_buyer: bool = True
) -> List[Dict]:
    """
    Return newest→oldest trades not older than history_weeks.

    Dedupe behavior:
      - If dedupe_by_buyer is True (default), only the latest (max timestamp)
        record for each (buyer, item_name, amount, currency) is kept.
      - Exact duplicate lines across files are naturally collapsed by keying.

    The reverse scan stops early per-file once an older-than-cutoff timestamp is seen.
    """
    cutoff = datetime.now() - timedelta(weeks=history_weeks)

    # store the max timestamp entry for each key
    best: dict[Tuple[str, str, int, str], Dict] = {}

    for path in log_files:
        if not os.path.isfile(path):
            continue

        with open(path, "rb") as fh:
            buf = b""
            fh.seek(0, os.SEEK_END)
            pos = fh.tell()

            while pos > 0:
                chunk = min(8192, pos)
                pos -= chunk
                fh.seek(pos)
                buf = fh.read(chunk) + buf

                *lines, buf = buf.split(b"\n")
                for raw in reversed(lines):  # newest first
                    try:
                        line = raw.decode("utf-8", "ignore").strip()
                    except Exception:
                        continue
                    if not line:
                        continue

                    t = _parse_trade_line(line)
                    if not t:
                        continue
                    if t["timestamp"] < cutoff:
                        # Once we encounter older-than-cutoff, stop this file
                        pos = 0
                        break

                    key = _offer_key(t)
                    if (key not in best) or (t["timestamp"] > best[key]["timestamp"]):
                        best[key] = t

            # leftover partial line
            if buf:
                try:
                    line = buf.decode("utf-8", "ignore").strip()
                    if line:
                        t = _parse_trade_line(line)
                        if t and t["timestamp"] >= cutoff:
                            key = _offer_key(t)
                            if (key not in best) or (t["timestamp"] > best[key]["timestamp"]):
                                best[key] = t
                except Exception:
                    pass

    trades = list(best.values())
    trades.sort(key=lambda r: r["timestamp"], reverse=True)
    return trades
