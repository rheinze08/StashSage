"""
poe2trade.app.config_manager
─────────────────────────────────────────────────────────────────────
Read / write per-user configuration for StashSage.

• v1.4 – 2025-06-04
  – Adds “price_mirror_filter” (float, in Exalts) to DEFAULT_CONFIG.
  – Keeps backward-compatibility: any missing keys are injected on load.
"""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from tkinter import messagebox

APP_NAME    = "StashSage"
CONFIG_FILE = "config.json"

# ──────────────────────────────────────────────────────────────────────
# Defaults – change them in ONE place only
# ──────────────────────────────────────────────────────────────────────
_default_appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
_default_prediction_log = str(_default_appdata / APP_NAME / "prediction_log.json")

DEFAULT_CONFIG: dict = {
    "client_type":          "steam",   # "steam" or "ggg"
    "poe_account":          "",
    "steam_client_log_dir": r"C:\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\client.txt",
    "ggg_client_log_dir":   r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\client.txt",
    "discord_user_id":      "",
    "discord_bot_token":    "",
    # Hotkey to trigger Discord API JSON prediction DM
    "discord_api_hotkey":   "ctrl+4",
    # Hotkey to open prediction log overlay
    "prediction_log_hotkey": "ctrl+3",
    # NEW ► maximum price (Exalts) for the Price-Mirror / K-NN overlay
    "price_mirror_filter":  "1e",
    # Max nearest items shown for KNN overlays (Ctrl+1/Ctrl+2)
    "knn_filtered_k": 10,
    # Show XGB visuals (bucket + distributions + feature importance)
    "show_viz_param": False,
    "custom_hotkey":       "ctrl+1",
    # Prediction history log file (optional)
    "prediction_log_dir":  _default_prediction_log,
    # Auction Price Tool
    "auction_hotkey":        "-",  # single hotkey: copy, adjust, paste
    "auction_cut_rule":      "5-", # "5-" flat or "10%" percent
    # Stash Scrape defaults
    "stash_scrape_username": "",
    "stash_scrape_save_dir": "",
    "stash_scrape_search_wait": 120,
}
# --------------------------------------------------------------------

# ──────────────────────────────────────────────────────────────────────
# internal helpers
# ──────────────────────────────────────────────────────────────────────
def _user_config_dir() -> Path:
    r"""Return %APPDATA%\StashSage (on Windows) or ~/.StashSage otherwise."""
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home()
    return base / APP_NAME


def _config_path() -> Path:
    """Full path to config.json (creates the folder if it does not exist)."""
    cfg_dir = _user_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / CONFIG_FILE


# ──────────────────────────────────────────────────────────────────────
# public API
# ──────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    """
    Load the per-user configuration.

    • If the file does not exist → write defaults and return them.
    • If it exists but is malformed → show a dialog, reset to defaults.
    • If it is missing *new* keys introduced in a later version
      (like “price_mirror_filter”) they are injected and the file is
      rewrit­ten in-place.
    """
    cfg_path = _config_path()

    if cfg_path.is_file():
        try:
            with cfg_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError:
            messagebox.showerror(
                "StashSage Config Error",
                "Your config file is corrupt and will be reset."
            )
            data = DEFAULT_CONFIG.copy()
    else:
        data = DEFAULT_CONFIG.copy()

    changed = False
    # migrate renamed keys
    if "prediction_history_hotkey" in data and "prediction_log_hotkey" not in data:
        data["prediction_log_hotkey"] = data.get("prediction_history_hotkey", "")
        changed = True
    if "prediction_history_hotkey" in data:
        del data["prediction_history_hotkey"]
        changed = True

    # inject any new default keys on upgrade
    for k, v in DEFAULT_CONFIG.items():
        if k not in data:
            data[k] = v
            changed = True
    if changed:
        save_config(data)          # silently rewrite with missing keys

    return data


def save_config(cfg: dict) -> None:
    """Persist *cfg* to disk (pretty-printed JSON)."""
    cfg_path = _config_path()
    with cfg_path.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=4)
    print(f"💾  Config saved → {cfg_path}")
