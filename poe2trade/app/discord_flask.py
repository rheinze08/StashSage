# poe2trade/app/discord_flask.py
"""
discord_flask.py · Discord-bot + Flask API for StashSage
────────────────────────────────────────────────────────
• Production Flask server via Waitress
• Background scraper loop reads PoE client logs
• Discord bot runs in its own event loop & thread
• Hot-reload on token / user-ID change
• No repeat pings for the same (buyer, item, amount, currency)
"""

from __future__ import annotations

import sys
import asyncio, io, socket, threading, time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp, discord, matplotlib
import pandas as pd
from flask import Flask, jsonify, send_file
from matplotlib import rcParams
from requests.utils import quote
from waitress import serve

from poe2trade.utils.chart_utils import (
    generate_offers_table_chart,
    generate_price_chart_for_item,
)
from poe2trade.utils.log_utils import read_all_log_trades

# ── matplotlib headless ───────────────────────────────────────────────
matplotlib.use("Agg")
rcParams["font.family"] = ["Microsoft YaHei", "DejaVu Sans"]

# ── constants ─────────────────────────────────────────────────────────
CYCLE_MINUTES            = 5
DM_POLL_SECONDS          = max(30, CYCLE_MINUTES * 60 // 2)
SCRAPE_HISTORY_WEEKS     = 3
DM_NOTIFY_WINDOW_MINUTES = 10
TIME_WINDOW_MARGIN       = 1

print(
    f"[cfg] scrape every {CYCLE_MINUTES} min | DM poll {DM_POLL_SECONDS}s | "
    f"history {SCRAPE_HISTORY_WEEKS}w | dm window ≤{DM_NOTIFY_WINDOW_MINUTES}min",
    flush=True,
)

# ── Flask singleton ───────────────────────────────────────────────────
app = Flask(__name__)
_API_URL = "http://127.0.0.1:5000"

def _offer_key(buyer: str, item_name: str, amount: int | str, currency: str) -> str:
    return f"{str(buyer).strip().lower()}|{str(item_name).strip().lower()}|{int(amount)}|{str(currency).strip().lower()}"

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
    #  Config hot-reload
    # ------------------------------------------------------------------
    def update_config(self, new_cfg: dict[str, Any]) -> None:
        with self._lock:
            old_token, old_uid = self._token, self._USER_ID
            self.cfg = new_cfg or {}
            self._USER_ID = int(self.cfg.get("discord_user_id", "0") or 0) or None
            self._token   = (self.cfg.get("discord_bot_token", "") or "").strip()
            self.LOG_FILES = self._build_log_list(self.cfg)
            print("LOG_FILES →", self.LOG_FILES, flush=True)

            if (self._token != old_token) or (self._USER_ID != old_uid):
                print("[discord_flask] credentials changed – restarting bot", flush=True)
                if self._token:
                    self._restart_discord_bot()
                else:
                    print("Discord bot disabled – missing token.", flush=True)
                    self._stop_bot_sync()

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
        while True:
            try:
                self._scrape_once()
            except Exception as e:
                print("Scrape loop error:", e, flush=True)
            time.sleep(CYCLE_MINUTES * 60)

    # ------------------------------------------------------------------
    #  Public start/stop
    # ------------------------------------------------------------------
    def start(self, cfg: dict[str, Any]) -> None:
        with self._lock:
            if self._started:
                print("[discord_flask] already running – pushing new config.", flush=True)
                self.update_config(cfg)
                return
            self._started = True
            self.update_config(cfg)

        # Flask (Waitress)
        threading.Thread(
            target=serve,
            kwargs={"app": app, "host": "0.0.0.0", "port": 5000},
            daemon=True,
            name="FlaskWaitress",
        ).start()

        # Scraper loop
        self._scraper_thread = threading.Thread(
            target=self._scrape_loop, daemon=True, name="ScraperThread"
        )
        self._scraper_thread.start()

        # Discord bot — only if update_config() hasn’t already started it
        if self._token and self._discord_thread is None:
            self._restart_discord_bot()
        elif not self._token:
            print("Discord bot disabled – missing token.", flush=True)

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
    """Entry-point used by both the Tk GUI and the CLI launcher."""
    _manager.start(cfg)

def update_config(cfg: dict) -> None:
    """Hot-reload running services with a new config dict."""
    _manager.update_config(cfg)

# ───────── Flask routes ────────────────────────────────────────────────
@app.route("/get-api-url")
def _route_api_url():
    ip = socket.gethostbyname(socket.gethostname()) or "127.0.0.1"
    return jsonify({"localhost": _API_URL, "lan": f"http://{ip}:5000"})

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
