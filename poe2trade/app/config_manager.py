# poe2trade/app/config_manager.py
import json
import os
import sys
from pathlib import Path
from tkinter import messagebox

APP_NAME   = "StashSage"
CONFIG_FILE = "config.json"

# ────────────────────────────────────────────────────────────────────────
# Default values – change them here once only
# ────────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "client_type":          "steam",   # "steam" or "ggg"
    "poe_account":          "",
    "steam_client_log_dir": r"C:\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\client.txt",
    "ggg_client_log_dir":   r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\client.txt",
    "discord_user_id":      "",
    "discord_bot_token":    "",
}
# -----------------------------------------------------------------------


def _user_config_dir() -> Path:
    """Return %APPDATA%\StashSage or ~/.StashSage on non‑Windows."""
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home()
    return base / APP_NAME


def _config_path() -> Path:
    """Full path to config.json in the per‑user dir (creates dir if needed)."""
    cfg_dir = _user_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / CONFIG_FILE


def load_config() -> dict:
    """Load existing config, or create it with defaults on first run."""
    cfg_path = _config_path()

    if cfg_path.exists():
        try:
            with cfg_path.open("r", encoding="utf‑8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("Config error", "Config file is corrupt and will be reset.")
            data = DEFAULT_CONFIG.copy()
    else:
        data = DEFAULT_CONFIG.copy()

    # ensure any new keys are added
    updated = False
    for k, v in DEFAULT_CONFIG.items():
        if k not in data:
            data[k] = v
            updated = True
    if updated:
        save_config(data)

    return data


def save_config(config: dict) -> None:
    """Write config dict to disk (user directory)."""
    cfg_path = _config_path()
    with cfg_path.open("w", encoding="utf‑8") as f:
        json.dump(config, f, indent=4)
    print(f"💾  Config saved → {cfg_path}")
