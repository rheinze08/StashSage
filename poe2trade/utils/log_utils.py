"""
log_utils.py · v3
────────────────────────────────────────────────────────────────────────────
• read_all_log_trades(log_files, history_weeks=3, *, dedupe_by_buyer=True)
    → returns only trades whose timestamp ≥ now‑history_weeks
    → keeps **one** (newest) trade per buyer when dedupe_by_buyer is True
      (default).
• Fast reverse scan: reads each log from the end backwards in ~8 KiB blocks,
  stopping as soon as a line’s timestamp is older than the cutoff.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import List, Dict

# ────────────────────────── helpers ──────────────────────────────────────
_TRADE_RE = re.compile(
    r'(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'@From\s(?P<buyer>.*?): Hi, I would like to buy your '
    r'(?P<item>.*?) listed for (?P<amount>\d+)\s(?P<cur>\w+)',
    re.DOTALL,
)

def _parse_trade_line(line: str) -> Dict | None:
    m = _TRADE_RE.search(line)
    if not m:
        return None
    return {
        "timestamp": datetime.strptime(m.group("ts"), "%Y/%m/%d %H:%M:%S"),
        "buyer":      m.group("buyer"),
        "item_name":  m.group("item"),
        "amount":     int(m.group("amount")),
        "currency":   m.group("cur"),
    }

# ────────────────────────── public API ───────────────────────────────────
def read_all_log_trades(
    log_files: List[str],
    history_weeks: int = 3,
    *,                              # force keyword for new flag
    dedupe_by_buyer: bool = True,   # --- NEW
) -> List[Dict]:
    """
    Return *deduplicated* trade records not older than *history_weeks*.

    Deduplication happens on two levels, in this order:
      1. Identical raw log lines (across multiple files) – hash‑based.
      2. (NEW) Multiple trades from the same **buyer** – keeps the *newest*
         trade per buyer when ``dedupe_by_buyer`` is True.

    Keeps order newest→oldest (chronological desc).
    """
    cutoff = datetime.now() - timedelta(weeks=history_weeks)
    seen_lines: set[int] = set()              # hash(line) – avoids dupes across files
    seen_buyers: set[str] = set()             # --- NEW
    trades: List[Dict] = []

    for path in log_files:
        if not os.path.isfile(path):
            continue

        # read 8 KiB chunks from the end backwards
        with open(path, "rb") as fh:
            buf = b""
            fh.seek(0, os.SEEK_END)
            file_pos = fh.tell()

            while file_pos > 0:
                read_size = min(8192, file_pos)
                file_pos -= read_size
                fh.seek(file_pos)
                buf = fh.read(read_size) + buf

                # split into lines; keep last part as carry‑over
                *lines, buf = buf.split(b"\n")
                for raw in reversed(lines):   # newest first
                    try:
                        line = raw.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        continue
                    if not line:
                        continue
                    if hash(line) in seen_lines:
                        continue
                    seen_lines.add(hash(line))

                    tinfo = _parse_trade_line(line)
                    if not tinfo:
                        continue
                    if tinfo["timestamp"] < cutoff:
                        # older than history window: bail out of *this* file
                        file_pos = 0
                        break

                    # -------- NEW buyer‑level deduplication --------
                    if dedupe_by_buyer and tinfo["buyer"] in seen_buyers:
                        continue
                    seen_buyers.add(tinfo["buyer"])
                    # ------------------------------------------------

                    trades.append(tinfo)

            # finish any residual carry‑over line
            if buf:
                try:
                    line = buf.decode("utf-8", errors="ignore").strip()
                    if line and hash(line) not in seen_lines:
                        tinfo = _parse_trade_line(line)
                        if tinfo and tinfo["timestamp"] >= cutoff:
                            if not (dedupe_by_buyer and tinfo["buyer"] in seen_buyers):  # --- NEW
                                seen_buyers.add(tinfo["buyer"])                         # --- NEW
                                trades.append(tinfo)
                except Exception:
                    pass

    # newest → oldest already, but make absolutely sure
    trades.sort(key=lambda r: r["timestamp"], reverse=True)   # keep desc order
    return trades
