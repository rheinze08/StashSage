"""
discord_flask.py · Discord-bot + Flask API for StashSage
────────────────────────────────────────────────────────────────────────────
Key design notes
────────────────────────────────────────────────────────────────────────────
• Production Flask server via Waitress (no dev-server banner)
• Background scraper loop reads POE client logs
• Discord bot runs in its own event loop & thread
• Hot-reload on token / user-ID change
• Anti-spam: one DM per (buyer,item) per 10 min
• FIXES:
  – Clean coroutine shutdown (no RuntimeWarning)
  – Guard so the bot is spawned only once (no duplicate logins)
"""

from __future__ import annotations

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

# ── matplotlib headless ────────────────────────────────────────────────
matplotlib.use("Agg")
rcParams["font.family"] = ["Microsoft YaHei", "DejaVu Sans"]

# ── constants ──────────────────────────────────────────────────────────
CYCLE_MINUTES            = 5
DM_POLL_SECONDS          = max(30, CYCLE_MINUTES * 60 // 2)
SCRAPE_HISTORY_WEEKS     = 3
DM_NOTIFY_WINDOW_MINUTES = 10
TIME_WINDOW_MARGIN       = 1
IMG_W, IMG_H             = 9, 5

print(
    f"[cfg] scrape every {CYCLE_MINUTES} min | DM every {DM_POLL_SECONDS} s | "
    f"history {SCRAPE_HISTORY_WEEKS} w | notify cool-down ≤{DM_NOTIFY_WINDOW_MINUTES} min",
    flush=True,
)

# ── Flask singleton ────────────────────────────────────────────────────
app = Flask(__name__)
_API_URL = "http://127.0.0.1:5000"

# ══════════════════════════════════════════════════════════════════════
#  Helper: build a fresh Discord.Client wired to a ServiceManager
# ══════════════════════════════════════════════════════════════════════
def _make_client(manager: "ServiceManager") -> discord.Client:
    intents = discord.Intents.default()
    intents.messages = intents.message_content = intents.dm_messages = True
    cl = discord.Client(intents=intents)

    @cl.event
    async def on_ready():
        print(f"✅ Logged in as {cl.user}", flush=True)
        try:
            await cl.change_presence(activity=discord.Game("activated and listening"))
            if manager.user_id:
                owner = await cl.fetch_user(manager.user_id)
                await owner.send("🤖 StashSage bot activated and listening.")
        except Exception as e:
            print("Startup presence/DM error:", e, flush=True)

        cl.loop.create_task(_dm_poll_loop(manager, cl))

    return cl


async def _dm_poll_loop(manager: "ServiceManager", client: discord.Client):
    """Poll `/latest-trades` and DM the owner."""
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
                tid = f"{t['timestamp']}_{t['buyer']}_{t['item_name']}_{t['amount']}_{t['currency']}"
                if tid in manager._seen_ids_set:
                    continue

                ts = datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S")
                if ts < datetime.now() - timedelta(minutes=DM_NOTIFY_WINDOW_MINUTES):
                    continue

                if not manager._should_send_ping(t["buyer"], t["item_name"]):
                    continue

                try:
                    await user.send(
                        f"📊 **New Trade (poll): {t['item_name']}**\n"
                        f"{t['amount']} {t['currency']} from {t['buyer']}"
                    )
                except Exception as e:
                    print("DM send error (poll):", e, flush=True)

                manager._seen_ids_set.add(tid)
                manager._seen_ids_q.append(tid)

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
        self.trade_history: deque = deque(maxlen=50_000)
        self._seen_ids_set: set[str] = set()
        self._seen_ids_q:   deque    = deque(maxlen=10_000)
        self._recent_ping: dict[str, datetime] = {}

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
            p = cfg.get(key, "").strip()
            if p:
                out.append(p)
        return out

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
    #  Anti-spam helper
    # ------------------------------------------------------------------
    def _should_send_ping(self, buyer: str, item: str) -> bool:
        key = f"{buyer}|{item}".lower()
        now = datetime.now()
        last = self._recent_ping.get(key)
        if last and (now - last) < timedelta(minutes=DM_NOTIFY_WINDOW_MINUTES):
            return False
        self._recent_ping[key] = now
        cutoff = now - timedelta(minutes=DM_NOTIFY_WINDOW_MINUTES * 2)
        self._recent_ping = {k: ts for k, ts in self._recent_ping.items() if ts >= cutoff}
        return True

    # ------------------------------------------------------------------
    #  Scraper
    # ------------------------------------------------------------------
    def _notify_new_trades(self, trades: list[dict]) -> None:
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
            tid = f"{t['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}_{t['buyer']}_{t['item_name']}_{t['amount']}_{t['currency']}"
            if t["timestamp"] < cutoff or tid in self._seen_ids_set:
                continue
            if not self._should_send_ping(t["buyer"], t["item_name"]):
                continue

            self._seen_ids_set.add(tid)
            self._seen_ids_q.append(tid)
            if len(self._seen_ids_q) == self._seen_ids_q.maxlen:
                self._seen_ids_set.discard(self._seen_ids_q.popleft())

            asyncio.run_coroutine_threadsafe(_send_one(t), self._client_loop)

    def _scrape_once(self) -> None:
        new_trades = read_all_log_trades(self.LOG_FILES, SCRAPE_HISTORY_WEEKS)
        if not new_trades:
            return
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
        print(df.tail(3)[["timestamp", "buyer", "amount", "currency"]].to_string(index=False), flush=True)
        self._notify_new_trades(new_trades)

    def _scrape_loop(self) -> None:
        while True:
            self._scrape_once()
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


# ───────── module-level helpers (used by GUI) ──────────────────────────
_manager = ServiceManager()
def start_services(cfg):  _manager.start(cfg)
def update_config(cfg):   _manager.update_config(cfg)

# ───────── Flask routes (unchanged) ────────────────────────────────────
@app.route("/get-api-url")
def _route_api_url():
    ip = socket.gethostbyname(socket.gethostname()) or "127.0.0.1"
    return jsonify({"localhost": _API_URL, "lan": f"http://{ip}:5000"})

@app.route("/latest-trades")
def _route_latest_trades():
    cutoff = datetime.now() - timedelta(minutes=CYCLE_MINUTES + TIME_WINDOW_MARGIN)
    recent = [t for t in _manager.trade_history
              if datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S") >= cutoff]
    return jsonify(recent or {"status": "no_new_trades"})

@app.route("/generate-price-chart/<item_name>")
def _route_price_chart(item_name):
    if not _manager.trade_history:
        return jsonify({"status": "no_data_for_item"})
    df = pd.DataFrame(_manager.trade_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    buf = generate_price_chart_for_item(item_name, df)
    return jsonify({"status": "no_data_for_item"}) if buf is None else send_file(
        buf, mimetype="image/png", as_attachment=True, download_name=f"{item_name}_price_chart.png"
    )

@app.route("/generate-offers-chart/<item_name>")
def _route_offers_chart(item_name):
    if not _manager.trade_history:
        return jsonify({"status": "no_data_for_item"})
    df = pd.DataFrame(_manager.trade_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    buf = generate_offers_table_chart(item_name, df)
    return jsonify({"status": "no_data_for_item"}) if buf is None else send_file(
        buf, mimetype="image/png", as_attachment=True, download_name=f"{item_name}_offers_chart.png"
    )
