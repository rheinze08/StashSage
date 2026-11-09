"""Desktop lifecycle for StashWatch's timer and optional loopback listener."""
from __future__ import annotations

import logging
from pathlib import Path
import secrets
import threading

from werkzeug.serving import make_server

from poe2trade.app import config_manager
from poe2trade.app.stash_watch import WatchManager, WatchStore
from poe2trade.app.stash_watch_api import create_app
from poe2trade.app.stash_watch_trade import TradeCollector


class WatchRuntime:
    def __init__(self, config, *, path: Path | None = None, collector=None):
        self.config = config
        self.collector = collector if collector is not None else TradeCollector()
        self.manager = WatchManager(WatchStore(path or config_manager._user_config_dir() / "stashwatch.sqlite3"), self.collector)
        self.server = None
        self.server_thread = None
        self.api_error = None

    def start(self):
        self.manager.run_scheduler()
        if self.config.get("stash_watch_api_enabled") and self.server is None:
            try:
                self.enable_api(True)
            except (ValueError, OSError) as exc:
                self.api_error = str(exc)
                logging.warning("StashWatch API could not start: %s", exc)

    def enable_api(self, enabled):
        if enabled and self.server is not None:
            return
        updated = dict(self.config)
        updated["stash_watch_api_enabled"] = bool(enabled)
        if enabled:
            port = updated.get("stash_watch_api_port", 5006)
            if type(port) is not int or not 1 <= port <= 65535:
                raise ValueError("API port must be an integer from 1 to 65535")
            token = updated.get("stash_watch_api_token") or secrets.token_urlsafe(32)
            updated["stash_watch_api_token"] = token
            try:
                server = make_server("127.0.0.1", port, create_app(self.manager, token), threaded=True)
            except SystemExit as exc:
                raise ValueError(f"Could not listen on localhost port {port}; choose another port") from exc
            try:
                config_manager.save_config(updated)
            except Exception:
                server.server_close()
                raise
            self.server = server
            self.server_thread = threading.Thread(target=server.serve_forever, name="StashWatch HTTP", daemon=True)
            self.server_thread.start()
        else:
            config_manager.save_config(updated)
            self._stop_api()
        self.config.update(updated)
        self.api_error = None

    def _stop_api(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join(2)
            self.server = None

    def close(self):
        self._stop_api()
        stopped = self.manager.close()
        if stopped and hasattr(self.collector, "close"):
            self.collector.close()


_runtime = None


def get_runtime(config=None):
    global _runtime
    if _runtime is None:
        _runtime = WatchRuntime(config if config is not None else config_manager.load_config())
        _runtime.start()
    return _runtime


def close_runtime():
    global _runtime
    runtime, _runtime = _runtime, None
    if runtime:
        runtime.close()
