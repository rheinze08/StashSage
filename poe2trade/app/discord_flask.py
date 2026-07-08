# poe2trade/app/discord_flask.py
"""
discord_flask.py · Discord-bot + Flask API for StashSage
────────────────────────────────────────────────────────
• Production Flask server via Waitress
• Background scraper loop reads PoE client logs
• Discord bot runs in its own event loop & thread
• Hot-reload on token / user-ID change
• No repeat pings for the same (buyer, item, amount, currency)

Change summary (centralized credential checks):
- The Discord bot only starts when BOTH discord_bot_token AND discord_user_id are present.
- start_services(...) can always be called; it'll spin up Flask + scraper regardless,
  and only bring up the bot if creds are valid.
- Hot-reload respects the same rule: credentials change triggers a restart only when both are present;
  otherwise the bot is stopped/kept stopped.
"""

from __future__ import annotations

import sys
import asyncio, io, socket, threading, time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp, discord, matplotlib
import pandas as pd
from flask import Flask, jsonify, send_file, request
from matplotlib import rcParams
from requests.utils import quote
from waitress import serve

from poe2trade.utils.chart_utils import (
    generate_offers_table_chart,
    generate_price_chart_for_item,
)
from poe2trade.utils.log_utils import read_all_log_trades
from poe2trade.utils.gui_utils import (
    parse_copied_item_text,
    process_all_mods,
    _deflate_quality_type_modifiers,
    deflator_and_normaliser,
    cleanup_unused_features,
    flatten_all_mod_patterns,
    drop_raw_mod_slots,
    detect_category_segment,
    build_feature_dataframe,
)
from poe2trade.utils.ml_super_utils import call_ml as call_ml_super
from poe2trade.utils.ml_unsuper_utils import call_ml as call_ml_unsuper, set_knn_runtime_k
from poe2trade import (
    __version__ as STASHSAGE_VERSION,
    __build_date__ as STASHSAGE_BUILD_DATE,
    chaos_exalt,
    divine_exalt,
    annul_exalt,
    poe2trade_root,
)
from statistics import mean as _mean, median as _median

# ── matplotlib headless ───────────────────────────────────────────────
matplotlib.use("Agg")
rcParams["font.family"] = ["Microsoft YaHei", "DejaVu Sans"]

# ── API / server configuration (single source of truth) ───────────────
API_HOST = "0.0.0.0"         # bind to all interfaces
API_PORT = 5005              # << fixed port here
# Local loopback URL used by internal clients (Discord poller, chart fetch)
_API_URL = f"http://127.0.0.1:{API_PORT}"

# ── constants ─────────────────────────────────────────────────────────
CYCLE_MINUTES            = 5
DM_POLL_SECONDS          = max(30, CYCLE_MINUTES * 60 // 2)
SCRAPE_HISTORY_WEEKS     = 3
DM_NOTIFY_WINDOW_MINUTES = 10
TIME_WINDOW_MARGIN       = 1

print(
    f"[cfg] API {API_HOST}:{API_PORT} | scrape every {CYCLE_MINUTES} min | "
    f"DM poll {DM_POLL_SECONDS}s | history {SCRAPE_HISTORY_WEEKS}w | "
    f"dm window ≤{DM_NOTIFY_WINDOW_MINUTES}min",
    flush=True,
)

# ── Flask singleton ───────────────────────────────────────────────────
app = Flask(__name__)

def _offer_key(buyer: str, item_name: str, amount: int | str, currency: str) -> str:
    return f"{str(buyer).strip().lower()}|{str(item_name).strip().lower()}|{int(amount)}|{str(currency).strip().lower()}"


def _best_item_name_from_text_and_parsed(text: str, parsed: dict) -> str:
    """Best-effort display name from parsed fields, with raw-text fallback.

    Priority:
    1) parsed["Item Name"] if non-empty
    2) first header line after "Rarity:" in raw text (up to divider/metadata)
    3) parsed["Base Type"] if present
    4) fallback "(Unknown item)"
    """
    try:
        name_raw = (parsed.get("Item Name") or "").strip()
        if name_raw:
            return name_raw

        # Raw-text fallback: capture lines immediately after the Rarity line
        lines = [l.strip() for l in str(text).splitlines()]
        # find first rarity line
        start = None
        for i, ln in enumerate(lines):
            if ln.lower().startswith("rarity:"):
                start = i + 1
                break
        if start is not None:
            candidates: list[str] = []
            for ln in lines[start: start + 5]:  # only scan a few lines below
                if not ln or ln.startswith("--------"):
                    break
                if any(ln.lower().startswith(pfx) for pfx in (
                    "quality:", "armour:", "evasion", "energy shield",
                    "requires", "sockets:", "item level", "item class:",
                )):
                    break
                candidates.append(ln)
            # For Rare/Unique/Magic, the first non-empty line is the name
            if candidates:
                return candidates[0].strip()

        base_type_raw = (parsed.get("Base Type") or "").strip()
        if base_type_raw:
            return base_type_raw
    except Exception:
        pass
    return "(Unknown item)"


def _extract_name_and_base_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    """Return (name_line, base_type_line) parsed directly from raw text.

    Looks for the first "Rarity:" line and then captures up to two
    subsequent non-metadata, non-divider lines as the item name and
    base type. Returns (None, None) if not determinable.
    """
    try:
        lines = [l.strip() for l in str(text).splitlines()]
        start = None
        for i, ln in enumerate(lines):
            if ln.lower().startswith("rarity:"):
                start = i + 1
                break
        if start is None:
            return None, None

        candidates: list[str] = []
        for ln in lines[start: start + 6]:
            if not ln or ln.startswith("--------"):
                break
            if any(ln.lower().startswith(pfx) for pfx in (
                "quality:", "armour:", "evasion", "energy shield",
                "requires", "sockets:", "item level", "item class:",
            )):
                break
            candidates.append(ln)
        name = candidates[0].strip() if len(candidates) > 0 else None
        base = candidates[1].strip() if len(candidates) > 1 else None
        return name or None, base or None
    except Exception:
        return None, None

# ══════════════════════════════════════════════════════════════════════
#  Helper: build a fresh Discord.Client wired to a ServiceManager
# ══════════════════════════════════════════════════════════════════════
def _make_client(manager: "ServiceManager") -> discord.Client:
    intents = discord.Intents.default()
    intents.messages = intents.message_content = intents.dm_messages = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Logged in as {client.user}", flush=True)
        try:
            await client.change_presence(activity=discord.Game("activated and listening"))
            if manager.user_id:
                owner = await client.fetch_user(manager.user_id)
                await owner.send("🤖 StashSage bot activated and listening.")
        except Exception as e:
            print("Startup presence/DM error:", e, flush=True)

        client.loop.create_task(_dm_poll_loop(manager, client))

    return client


async def _dm_poll_loop(manager: "ServiceManager", client: discord.Client):
    """Poll `/latest-trades` and DM the owner for unseen offer-keys."""
    if manager.user_id is None:
        return

    try:
        user = await client.fetch_user(manager.user_id)
    except Exception as e:
        print("fetch_user error:", e, flush=True)
        return

    async with aiohttp.ClientSession() as sess:
        while not client.is_closed():
            try:
                async with sess.get(f"{_API_URL}/latest-trades") as r:
                    data = await r.json()
            except Exception as e:
                print("DM poll error:", e, flush=True)
                await asyncio.sleep(DM_POLL_SECONDS)
                continue

            if isinstance(data, dict) and data.get("status") == "no_new_trades":
                await asyncio.sleep(DM_POLL_SECONDS)
                continue

            for t in data:
                # Unified offer key (no repeats)
                ok = _offer_key(t["buyer"], t["item_name"], t["amount"], t["currency"])
                if manager.has_dm_for_key(ok):
                    continue

                ts = datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S")
                if ts < datetime.now() - timedelta(minutes=DM_NOTIFY_WINDOW_MINUTES):
                    # stale relative to polling window
                    continue

                if not manager._within_cooldown(ok):
                    continue

                try:
                    await user.send(
                        f"📊 **New Trade (poll): {t['item_name']}**\n"
                        f"{t['amount']} {t['currency']} from {t['buyer']}"
                    )
                except Exception as e:
                    print("DM send error (poll):", e, flush=True)

                manager.mark_dm_sent(ok)

            await asyncio.sleep(DM_POLL_SECONDS)

# ══════════════════════════════════════════════════════════════════════
#  ServiceManager
# ══════════════════════════════════════════════════════════════════════
class ServiceManager:
    """Owns scraper state + Discord bot. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._started = False

        # live config
        self.cfg: dict[str, Any] = {}
        self._token:   Optional[str] = None
        self._USER_ID: Optional[int] = None

        # runtime data
        self.LOG_FILES: list[str] = []
        self.trade_history: deque = deque(maxlen=50_000)   # raw dicts (string timestamp)
        self._dm_seen_keys: set[str] = set()               # (buyer|item|amount|currency)
        self._cooldown_last: dict[str, datetime] = {}      # last DM time per offer-key

        # worker threads
        self._scraper_thread: Optional[threading.Thread] = None
        self._scraper_stop: Optional[threading.Event] = None
        self._discord_thread: Optional[threading.Thread] = None

        # discord client & its loop
        self._client: Optional[discord.Client] = None
        self._client_loop: Optional[asyncio.AbstractEventLoop] = None

    # ───────── helpers ────────────────────────────────────────────────
    @staticmethod
    def _build_log_list(cfg: dict[str, Any]) -> list[str]:
        out = []
        for key in ("steam_client_log_dir", "ggg_client_log_dir"):
            p = (cfg.get(key) or "").strip()
            if p:
                out.append(p)
        return out

    @staticmethod
    def _has_discord_creds(token: Optional[str], user_id: Optional[int]) -> bool:
        token_ok = bool((token or "").strip())
        uid_ok = bool(user_id)
        return token_ok and uid_ok

    def _scanning_enabled(self) -> bool:
        """Return True if log scanning should run (Discord creds + any log file)."""
        return self._has_discord_creds(self._token, self._USER_ID) and bool(self.LOG_FILES)

    # ------------------------------------------------------------------
    #  DM dedupe / cooldown
    # ------------------------------------------------------------------
    def has_dm_for_key(self, offer_key: str) -> bool:
        return offer_key in self._dm_seen_keys

    def mark_dm_sent(self, offer_key: str) -> None:
        self._dm_seen_keys.add(offer_key)
        self._cooldown_last[offer_key] = datetime.now()
        # cap dict size to avoid unbounded growth (lax cap)
        if len(self._dm_seen_keys) > 200_000:
            # drop oldest ~25%
            drop = int(len(self._dm_seen_keys) * 0.25)
            for k in list(self._dm_seen_keys)[:drop]:
                self._dm_seen_keys.discard(k)
                self._cooldown_last.pop(k, None)

    def _within_cooldown(self, offer_key: str) -> bool:
        """Simple 10-min cooldown guard per offer-key (amount+currency included)."""
        last = self._cooldown_last.get(offer_key)
        if not last:
            return True
        return (datetime.now() - last) >= timedelta(minutes=DM_NOTIFY_WINDOW_MINUTES)

    # ------------------------------------------------------------------
    #  Discord-bot lifecycle
    # ------------------------------------------------------------------
    def _run_bot(self) -> None:
        loop = asyncio.new_event_loop()
        self._client_loop = loop
        asyncio.set_event_loop(loop)
        self._client = _make_client(self)
        loop.create_task(self._client.start(self._token))
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def _stop_bot_sync(self, timeout: float = 15.0) -> None:
        if not (self._client and self._client_loop and self._discord_thread):
            return
        if self._client_loop.is_closed():
            return

        async def _shutdown():
            await self._client.close()
            self._client_loop.stop()

        self._client_loop.call_soon_threadsafe(lambda: asyncio.create_task(_shutdown()))
        self._discord_thread.join(timeout=timeout)

        self._client = self._client_loop = self._discord_thread = None

    def _restart_discord_bot(self) -> None:
        self._stop_bot_sync()
        self._discord_thread = threading.Thread(
            target=self._run_bot, daemon=True, name="DiscordBotThread"
        )
        self._discord_thread.start()

    # ------------------------------------------------------------------
    #  Prediction: compute + (optionally) DM as JSON
    # ------------------------------------------------------------------
    def _compute_prediction_payload(self, text: str) -> dict:
        """Compute supervised prediction payload from a raw PoE item dump.

        Returns a small JSON-safe dict with item_name/category/segment and
        the supervised model summary under key 'ml_super'.
        """
        try:
            parsed = parse_copied_item_text(text)
            # Preserve a human-friendly snapshot of the raw parsed item
            raw_preview: dict[str, Any] = {}
            try:
                base_keys = [
                    "Item Category", "Item Name", "Quality", "Armour",
                    "Evasion Rating", "Energy Shield", "Corrupted",
                    "socket_count", "Quality_Type", "Quality_Type_Pct",
                ]
                for k in base_keys:
                    if k in parsed:
                        raw_preview[k] = parsed[k]
                for prefix, max_i in (("implicit", 3), ("enchant", 3), ("rune", 6), ("explicit", 10)):
                    for i in range(1, max_i + 1):
                        k = f"{prefix}_mod_{i}"
                        if k in parsed and parsed[k]:
                            raw_preview[k] = parsed[k]
            except Exception:
                raw_preview = {}
            if not parsed.get("Item Category"):
                parsed["Item Category"] = "default_model"

            parsed = process_all_mods(parsed)

            # Belt charm-slot fix: derive total from any matching patterns
            if (parsed.get("Item Category", "").strip().lower() == "belt"):
                total = 1
                for prefix, max_i in (("implicit", 3), ("enchant", 3), ("rune", 6), ("explicit", 10)):
                    for i in range(1, max_i + 1):
                        pat = str(parsed.get(f"{prefix}_mod_{i}_pattern", "")).lower()
                        val = parsed.get(f"{prefix}_mod_{i}_value", 0) or 0
                        if "charm slot" in pat:
                            try:
                                total = max(total, int(val))
                            except Exception:
                                pass
                parsed["socket_count"] = total
                parsed["has # charm slots"] = total
                # Reflect computed sockets in the raw preview as well
                try:
                    raw_preview["socket_count"] = total
                except Exception:
                    pass

            parsed = _deflate_quality_type_modifiers(parsed)
            parsed = deflator_and_normaliser(parsed)
            parsed = cleanup_unused_features(parsed)
            flatten_all_mod_patterns(parsed)
            drop_raw_mod_slots(parsed)

            cat, seg = detect_category_segment(parsed)
            if cat in ("ring", "amulet", "belt"):
                seg = None

            X = build_feature_dataframe(parsed)

            ml = call_ml_super(cat, seg, X)
            item_display_name = _best_item_name_from_text_and_parsed(text, parsed)
            _, base_from_text = _extract_name_and_base_from_text(text)
            base_type_name = (parsed.get("Base Type") or base_from_text or "").strip()

            # Unsupervised neighbours -> mean/median price (in exalts)
            ml_unsuper_block = None
            try:
                df_knn = call_ml_unsuper(cat, seg, X)
                vals: list[float] = []
                if hasattr(df_knn, "iterrows"):
                    for _, r in df_knn.iterrows():
                        e_val = None
                        # Prefer lower-case fields; fall back to title-case
                        if {"price", "currency"}.issubset(r.index) and pd.notna(r.get("price")):
                            cur = str(r.get("currency")).lower()
                            try:
                                p = float(r.get("price") or 0)
                            except Exception:
                                p = None
                        elif {"Price", "Currency"}.issubset(r.index) and pd.notna(r.get("Price")):
                            cur = str(r.get("Currency")).lower()
                            try:
                                p = float(r.get("Price") or 0)
                            except Exception:
                                p = None
                        elif "Price_in_Exalts" in r and pd.notna(r.get("Price_in_Exalts")):
                            try:
                                e_val = float(r.get("Price_in_Exalts"))
                            except Exception:
                                e_val = None
                            cur = None
                            p = None
                        else:
                            cur = None
                            p = None

                        if e_val is None and p is not None:
                            if cur in {"e", "exa", "exalt", "exalts"}:
                                e_val = float(p)
                            elif cur in {"c", "chaos"}:
                                e_val = float(p) * float(chaos_exalt)
                            elif cur in {"d", "div", "divine"}:
                                e_val = float(p) * float(divine_exalt)
                            elif cur in {
                                "a",
                                "ann",
                                "annul",
                                "annulment",
                                "annul orb",
                                "annulment orb",
                                "annulment_orb",
                                "annulment orbs",
                            }:
                                e_val = float(p) * float(annul_exalt)
                        if isinstance(e_val, (int, float)):
                            vals.append(float(e_val))
                if vals:
                    ml_unsuper_block = {
                        "mean": float(_mean(vals)),
                        "median": float(_median(vals)),
                    }
            except Exception:
                ml_unsuper_block = None

            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "app_version": STASHSAGE_VERSION,
                "build_date": STASHSAGE_BUILD_DATE,
                "item_name": item_display_name,
                "base_type": base_type_name or None,
                "category": cat,
                "segment": seg,
                "ml_super": ml,
                "ml_unsuper": ml_unsuper_block,
                "parsed_item": raw_preview or None,
            }
            return {"status": "ok", "payload": payload}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _dm_prediction_json_async(self, payload: dict) -> dict:
        """Send the given payload as a JSON code block to the configured owner."""
        if self._USER_ID is None or not self._client:
            return {"dm_sent": False, "reason": "discord_not_ready"}
        try:
            user = await self._client.fetch_user(self._USER_ID)
        except Exception as e:
            return {"dm_sent": False, "reason": f"fetch_user_failed: {e}"}

        import json as _json
        item = (payload.get("item_name") or "Item").strip()
        base = (payload.get("base_type") or "").strip()
        try:
            text = _json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception:
            text = str(payload)

        title = (
            f"StashSage Prediction JSON for {item} {base}".strip()
            if base else f"StashSage Prediction JSON for {item}"
        )
        msg = f"{title}\n```json\n{text}\n```"

        # Attach the target item's icon PNG if available (same icon used by KNN overlay)
        files: list[discord.File] = []
        try:
            from pathlib import Path

            def _sanitize(name: str) -> str:
                return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).rstrip()

            cat_norm = str(payload.get("category") or "").strip().lower()
            base_name = (payload.get("base_type") or payload.get("item_name") or "").strip()
            base_safe = _sanitize(base_name) if base_name else ""

            folder_map = {
                "body_armour": "Body_Armour",
                "helmet": "Helmet",
                "boots": "Boots",
                "gloves": "Gloves",
                "foci": "Focus",
                "focus": "Focus",  # alias for backward-compat
                "shield": "Shield",
                "buckler": "Buckler",
                "ring": "Ring",
                "amulet": "Amulet",
                "belt": "Belt",
                # weapons/simple
                "wand": "Wand",
                "sceptre": "Sceptre",
                "scepter": "Sceptre",
                # jewels/simple
                "sapphire": "sapphire",
                "emerald": "emerald",
                "ruby": "ruby",
                # quiver
                "quiver": "Quiver",
            }
            root_dir = Path(poe2trade_root) / "db" / "base_icons"

            candidates: list[Path] = []
            folder = folder_map.get(cat_norm)
            if folder:
                if base_safe:
                    candidates.append(root_dir / folder / f"{base_safe}.png")
                candidates.append(root_dir / folder / "default.png")
            else:
                # fallback across categories
                for f in folder_map.values():
                    if base_safe:
                        candidates.append(root_dir / f / f"{base_safe}.png")
                    candidates.append(root_dir / f / "default.png")

            for p in candidates:
                if p.is_file():
                    fh = p.open("rb")
                    files.append(discord.File(fh, filename=p.name))
                    break
        except Exception:
            files = []

        try:
            if files:
                # Send the icon first with the title line, then the JSON block separately
                await user.send(content=title, files=files)
                await user.send(f"```json\n{text}\n```")
            else:
                await user.send(msg)
            return {"dm_sent": True}
        except Exception as e:
            return {"dm_sent": False, "reason": f"dm_send_failed: {e}"}

    def dm_item_prediction_json(self, text: str) -> dict:
        """Compute prediction JSON from item text and DM it to the owner.

        Returns a dict including 'status', 'payload' and 'dm' result.
        """
        result = self._compute_prediction_payload(text)
        if result.get("status") != "ok":
            return result

        dm_result = {"dm_sent": False, "reason": "discord_not_ready"}
        if self._client_loop and self._client and self._client.is_ready():
            fut = asyncio.run_coroutine_threadsafe(
                self._dm_prediction_json_async(result["payload"]), self._client_loop
            )
            try:
                dm_result = fut.result(timeout=15)
            except Exception as e:
                dm_result = {"dm_sent": False, "reason": f"dm_future_error: {e}"}
        return {**result, "dm": dm_result}

    # ------------------------------------------------------------------
    #  Config hot-reload
    # ------------------------------------------------------------------
    def update_config(self, new_cfg: dict[str, Any]) -> None:
        """Apply new config and (re)start/stop the bot based on credentials."""
        with self._lock:
            old_token, old_uid = self._token, self._USER_ID

            self.cfg = new_cfg or {}
            self._USER_ID = int(self.cfg.get("discord_user_id", "0") or 0) or None
            self._token   = (self.cfg.get("discord_bot_token", "") or "").strip()
            self.LOG_FILES = self._build_log_list(self.cfg)
            print("LOG_FILES →", self.LOG_FILES, flush=True)
            try:
                set_knn_runtime_k(self.cfg.get("knn_filtered_k"))
            except Exception:
                pass

            # Only (re)start the Discord bot when BOTH credentials are present.
            have_creds = self._has_discord_creds(self._token, self._USER_ID)
            creds_changed = (self._token != old_token) or (self._USER_ID != old_uid)

            if creds_changed:
                if have_creds:
                    print("[discord_flask] credentials valid – restarting bot", flush=True)
                    self._restart_discord_bot()
                else:
                    print("[discord_flask] missing discord_bot_token and/or discord_user_id – stopping/keeping bot stopped", flush=True)
                    self._stop_bot_sync()

            # Start/stop scraper thread based on scanning enablement
            if self._scanning_enabled():
                if self._scraper_thread is None or not self._scraper_thread.is_alive():
                    self._start_scraper_thread()
            else:
                self._stop_scraper_thread()

    # ------------------------------------------------------------------
    #  Scraper
    # ------------------------------------------------------------------
    def _notify_new_trades(self, trades: list[dict]) -> None:
        """Send DMs for unseen offer-keys only."""
        if not trades or self._USER_ID is None or not self._client_loop:
            return
        if not self._client or not self._client.is_ready():
            return

        cutoff = datetime.now() - timedelta(minutes=DM_NOTIFY_WINDOW_MINUTES)

        async def _send_one(tr: dict):
            try:
                user = await self._client.fetch_user(self._USER_ID)
                await user.send(
                    f"📊 **New Trade: {tr['item_name']}**\n"
                    f"{tr['amount']} {tr['currency']} from {tr['buyer']}"
                )
                # Attach charts (fire-and-forget)
                for path, label in (("price", "price_chart"), ("offers", "offers_chart")):
                    url = f"{_API_URL}/generate-{path}-chart/{quote(tr['item_name'])}"
                    async with aiohttp.ClientSession() as sess:
                        async with sess.get(url) as r:
                            if r.status == 200:
                                buf = io.BytesIO(await r.read())
                                buf.seek(0)
                                await user.send(file=discord.File(buf, filename=f"{tr['item_name']}_{label}.png"))
            except Exception as e:
                print("DM send error:", e, flush=True)

        for t in trades:
            ok = _offer_key(t["buyer"], t["item_name"], t["amount"], t["currency"])
            if self.has_dm_for_key(ok):
                continue
            if t["timestamp"] < cutoff:
                continue
            if not self._within_cooldown(ok):
                continue

            self.mark_dm_sent(ok)
            asyncio.run_coroutine_threadsafe(_send_one(t), self._client_loop)

    def _scrape_once(self) -> None:
        # Do nothing unless scanning is enabled
        if not self._scanning_enabled():
            return
        # Deduping is handled by read_all_log_trades() now
        new_trades = read_all_log_trades(self.LOG_FILES, SCRAPE_HISTORY_WEEKS, dedupe_by_buyer=True)
        if not new_trades:
            return

        # Push to trade_history (string timestamps). We allow duplicates here;
        # charts and API route do their own latest-per-offer dedupe.
        for t in new_trades:
            self.trade_history.append(
                {
                    "timestamp": t["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    "buyer":     t["buyer"],
                    "item_name": t["item_name"],
                    "amount":    t["amount"],
                    "currency":  t["currency"],
                }
            )

        df = pd.DataFrame(new_trades)
        print("\n📊 New Trades (latest 3):", flush=True)
        print(df.tail(3)[["timestamp", "buyer", "item_name", "amount", "currency"]].to_string(index=False),
              flush=True)

        self._notify_new_trades(new_trades)

    def _scrape_loop(self) -> None:
        stop = self._scraper_stop
        while stop is not None and not stop.is_set():
            try:
                self._scrape_once()
            except Exception as e:
                print("Scrape loop error:", e, flush=True)
            # Wait with wakeup-on-stop semantics
            if stop is None:
                break
            stop.wait(CYCLE_MINUTES * 60)

    def _start_scraper_thread(self) -> None:
        if self._scraper_thread is not None and self._scraper_thread.is_alive():
            return
        self._scraper_stop = threading.Event()
        self._scraper_thread = threading.Thread(
            target=self._scrape_loop, daemon=True, name="ScraperThread"
        )
        self._scraper_thread.start()

    def _stop_scraper_thread(self, timeout: float = 5.0) -> None:
        if self._scraper_thread is None:
            return
        if self._scraper_stop is not None:
            self._scraper_stop.set()
        try:
            self._scraper_thread.join(timeout=timeout)
        except Exception:
            pass
        self._scraper_thread = None
        self._scraper_stop = None

    # ------------------------------------------------------------------
    #  Public start/stop
    # ------------------------------------------------------------------
    def start(self, cfg: dict[str, Any]) -> None:
        """Start Flask; enable log scanning and bot only when Discord is configured."""
        with self._lock:
            if self._started:
                print("[discord_flask] already running – pushing new config.", flush=True)
                # Will (re)start/stop the bot as needed based on creds:
                self.update_config(cfg)
                return
            self._started = True

        # Apply config (this may start/stop the bot and scraper based on creds)
        self.update_config(cfg)

        # Flask (Waitress)
        threading.Thread(
            target=serve,
            kwargs={"app": app, "host": API_HOST, "port": API_PORT},
            daemon=True,
            name="FlaskWaitress",
        ).start()

        # Scraper loop only if scanning is enabled
        if self._scanning_enabled():
            self._start_scraper_thread()

        # Bring up Discord bot only if both creds are present and it's not already running
        if self._has_discord_creds(self._token, self._USER_ID):
            if self._discord_thread is None:
                self._restart_discord_bot()
        else:
            print("Discord bot disabled – missing token and/or user id.", flush=True)

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            self._started = False
        self._stop_bot_sync()

    # ------------------------------------------------------------------
    #  Exposed props
    # ------------------------------------------------------------------
    @property
    def user_id(self) -> Optional[int]:
        return self._USER_ID

    @property
    def token(self) -> Optional[str]:
        return self._token


# ───────── module-level helpers (imported by GUI/CLI) ──────────────────
_manager = ServiceManager()

def start_services(cfg: dict) -> None:
    """Entry-point used by both the Tk GUI and the CLI launcher.
    Safe to call even if Discord creds are missing.
    """
    _manager.start(cfg)

def update_config(cfg: dict) -> None:
    """Hot-reload running services with a new config dict."""
    _manager.update_config(cfg)

# ───────── Flask routes ────────────────────────────────────────────────
@app.route("/get-api-url")
def _route_api_url():
    ip = socket.gethostbyname(socket.gethostname()) or "127.0.0.1"
    return jsonify({"localhost": _API_URL, "lan": f"http://{ip}:{API_PORT}"})

@app.route("/latest-trades")
def _route_latest_trades():
    """Return deduped latest trades within a short time window for DM polling."""
    if not _manager.trade_history:
        return jsonify({"status": "no_new_trades"})
    cutoff = datetime.now() - timedelta(minutes=CYCLE_MINUTES + TIME_WINDOW_MARGIN)
    df = pd.DataFrame(_manager.trade_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df[df["timestamp"] >= cutoff]
    if df.empty:
        return jsonify({"status": "no_new_trades"})
    # Keep latest per (buyer, item, amount, currency)
    df["cur_l"] = df["currency"].astype(str).str.lower()
    df.sort_values("timestamp", inplace=True)
    df = df.drop_duplicates(subset=["buyer","item_name","amount","cur_l"], keep="last")
    df = df.sort_values("timestamp")  # oldest→newest for polling order
    out = [
        {
            "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "buyer": r["buyer"],
            "item_name": r["item_name"],
            "amount": int(r["amount"]),
            "currency": r["currency"],
        }
        for _, r in df.iterrows()
    ]
    return jsonify(out)

@app.route("/generate-price-chart/<item_name>")
def _route_price_chart(item_name):
    if not _manager.trade_history:
        return jsonify({"status": "no_data_for_item"})
    df = pd.DataFrame(_manager.trade_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    buf = generate_price_chart_for_item(item_name, df)
    return (
        jsonify({"status": "no_data_for_item"})
        if buf is None
        else send_file(buf, mimetype="image/png", as_attachment=True,
                       download_name=f"{item_name}_price_chart.png")
    )

@app.route("/generate-offers-chart/<item_name>")
def _route_offers_chart(item_name):
    if not _manager.trade_history:
        return jsonify({"status": "no_data_for_item"})
    df = pd.DataFrame(_manager.trade_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    buf = generate_offers_table_chart(item_name, df)
    return (
        jsonify({"status": "no_data_for_item"})
        if buf is None
        else send_file(buf, mimetype="image/png", as_attachment=True,
                       download_name=f"{item_name}_offers_chart.png")
    )


@app.route("/dm-item-prediction-json", methods=["POST"])
def _route_dm_item_prediction_json():
    """POST a PoE item clipboard dump and DM the owner a JSON prediction.

    Body: { "item_text": "..." }  or form-data with key 'item_text'/'text'.
    Returns: { status, payload?, dm: { dm_sent, reason? } }
    """
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("item_text") or data.get("text") or request.form.get("item_text") or request.form.get("text")
    if not text or not str(text).strip():
        return jsonify({"status": "error", "error": "missing item_text"}), 400

    res = _manager.dm_item_prediction_json(str(text))
    return jsonify(res)
