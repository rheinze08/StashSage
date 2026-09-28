"""
poe2trade.app.config_manager
─────────────────────────────────────────────────────────────────────
Read / write per-user configuration for StashSage.

• v1.4 – 2025-06-04
  – Adds “price_mirror_filter” (float, in Exalts) to DEFAULT_CONFIG.
  – Keeps backward-compatibility: any missing keys are injected on load.
"""

from __future__ import annotations
import json, logging, os, shutil, sys
from pathlib import Path
from tkinter import messagebox
from uuid import uuid4

APP_NAME    = "StashSage"
CONFIG_FILE = "config.json"
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Defaults – change them in ONE place only
# ──────────────────────────────────────────────────────────────────────
_default_appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
_default_prediction_log = str(_default_appdata / APP_NAME / "prediction_log.json")
# Default scrape output to a personal, writable folder (Documents) so users
# don't land on a protected location like Program Files ([WinError 5]).
_default_stash_scrape_dir = str(Path.home() / "Documents" / APP_NAME)

DEFAULT_CONFIG: dict = {
    # Native in-game hotkey used to copy the selected item's description.
    "copy_hotkey":          "ctrl+c",
    # Counterfactual explicit-mod value analysis for rare items.
    "stash_scrape_hotkey": "ctrl+3",
    "craft_potential_hotkey": "ctrl+4",
    # NEW ► minimum/maximum price for the Price-Mirror / K-NN overlay
    "price_mirror_filter":  "1e",
    "price_mirror_max_filter": "100d",
    # Max nearest items shown for KNN overlays (Ctrl+1/Ctrl+2)
    "knn_filtered_k": 10,
    # Minimum parsed rows required before training category models.
    "min_training_rows": 30,
    # Window close action: keep price-check hotkeys available in the tray by
    # default, or exit the application completely.
    "close_behavior": "tray",
    "custom_hotkey":       "ctrl+1",
    # Prediction history log file (optional)
    "prediction_log_dir":  _default_prediction_log,
    # Auction Price Tool
    "auction_hotkey":        "-",  # single hotkey: copy, adjust, paste
    "auction_cut_rule":      "5-", # "5-" flat or "10%" percent
    # Stash Scrape defaults
    "stash_scrape_username": "",
    "stash_scrape_save_dir": _default_stash_scrape_dir,
    "stash_scrape_search_wait": 120,
    "stash_scrape_listing_type": "merchant",
    "stash_scrape_selected_categories": [],
    # Price list set to use for scraping: "default", "early", "late"
    "price_list_key": "default",
    # Which model set predictions are scored with. "default" is whatever the
    # updater syncs; other values name a directory under generated/model_sets/.
    "active_model_set": "default",
    # Denomination predictions are displayed in: "auto" keeps exalts until they
    # stop being readable and then switches to divine; the rest always win.
    # One of: auto, exalted, divine, chaos.
    "price_display": "auto",
    # In-app updater. The manifest is published with the GitHub Pages download
    # site and points to verified GitHub release assets.
    "auto_update": True,
    "update_manifest_url": "https://rheinze08.github.io/StashSage/update-manifest.json",
    "update_channel": "stable",
    "declined_update_version": "",
    # Optional client telemetry for verified app update downloads. Blank by
    # default so normal desktop usage does not call a server unless configured.
    "metrics_api_base": "",
    "metrics_api_key": "",
    "installation_id": "",
}
# --------------------------------------------------------------------

# Manifest URLs used by older dev/release builds. Existing per-user configs
# keep their saved value forever unless we migrate them explicitly, so a moved
# endpoint would otherwise leave users checking a permanent 404.
LEGACY_UPDATE_MANIFEST_URLS = frozenset(
    {
        "https://rheinze08.github.io/StashSage/assets/update/stable.json",
    }
)

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


def _show_config_error(message: str) -> None:
    """Best-effort config error dialog.

    Config loading can happen during module import, before a Tk root exists.
    A dialog failure must not turn a recoverable config problem into startup
    failure.
    """
    try:
        messagebox.showerror("StashSage Config Error", message)
    except Exception:
        log.warning("StashSage Config Error: %s", message)


def _backup_corrupt_config(cfg_path: Path) -> None:
    """Preserve an unreadable config as ``config.json.bak`` before resetting it.

    Resetting to defaults silently discards a user's settings; keeping a backup
    lets them (or us) recover what was there.
    """
    try:
        if cfg_path.is_file():
            backup = cfg_path.with_name(cfg_path.name + ".bak")
            shutil.copy2(cfg_path, backup)
            log.warning("Backed up unreadable config to %s", backup)
    except OSError as exc:
        log.warning("Could not back up corrupt config %s: %s", cfg_path, exc)


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
    try:
        cfg_path = _config_path()
    except OSError as exc:
        log.warning("Could not access config directory; using defaults: %s", exc)
        return DEFAULT_CONFIG.copy()

    needs_rewrite = False
    if cfg_path.is_file():
        try:
            with cfg_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not load config from %s; using defaults: %s", cfg_path, exc)
            _backup_corrupt_config(cfg_path)
            _show_config_error("Your config file is corrupt or unreadable and will be reset.")
            data = DEFAULT_CONFIG.copy()
            needs_rewrite = True
    else:
        data = DEFAULT_CONFIG.copy()
        needs_rewrite = True

    if not isinstance(data, dict):
        log.warning("Config file %s did not contain a JSON object; using defaults", cfg_path)
        _backup_corrupt_config(cfg_path)
        _show_config_error("Your config file has an invalid format and will be reset.")
        data = DEFAULT_CONFIG.copy()
        needs_rewrite = True

    changed = needs_rewrite
    # migrate renamed keys
    # Prediction history now lives in the main application. Retire its former
    # global Ctrl+3 binding instead of migrating it under a new config key.
    for retired_key in ("prediction_history_hotkey", "prediction_log_hotkey"):
        if retired_key in data:
            del data[retired_key]
            changed = True
    # Ctrl+3/Ctrl+4 were reserved for the two auxiliary workspaces. Existing
    # configurations that still have the old Craft default are migrated.
    if "stash_scrape_hotkey" not in data:
        data["stash_scrape_hotkey"] = DEFAULT_CONFIG["stash_scrape_hotkey"]
        changed = True
    if str(data.get("craft_potential_hotkey") or "").strip().lower() == "ctrl+3":
        data["craft_potential_hotkey"] = DEFAULT_CONFIG["craft_potential_hotkey"]
        changed = True
    # Price checks are always standalone overlays; discard the retired
    # workspace-routing preference from older config files.
    if "results_display" in data:
        del data["results_display"]
        changed = True
    update_url = str(data.get("update_manifest_url") or "").strip()
    if update_url in LEGACY_UPDATE_MANIFEST_URLS:
        data["update_manifest_url"] = DEFAULT_CONFIG["update_manifest_url"]
        changed = True
    # An unrecognised denomination would silently format every prediction as
    # exalts; fall back to the default rather than to an arbitrary unit.
    if str(data.get("price_display") or "").strip().lower() not in {
        "auto", "exalted", "divine", "chaos"
    }:
        data["price_display"] = DEFAULT_CONFIG["price_display"]
        changed = True

    # inject any new default keys on upgrade
    for k, v in DEFAULT_CONFIG.items():
        if k not in data:
            data[k] = v
            changed = True
    if not str(data.get("installation_id") or "").strip():
        data["installation_id"] = str(uuid4())
        changed = True
    if changed:
        try:
            save_config(data)          # silently rewrite with missing keys
        except OSError as exc:
            log.warning("Could not rewrite config defaults to %s: %s", cfg_path, exc)

    return data


def save_config(cfg: dict) -> None:
    """Persist *cfg* to disk (pretty-printed JSON).

    Written atomically via a temp file + ``os.replace`` so a crash mid-write can
    never leave a truncated, unreadable config behind.
    """
    cfg_path = _config_path()
    tmp = cfg_path.with_name(f"{cfg_path.name}.tmp-{os.getpid()}-{uuid4().hex}")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=4)
        os.replace(tmp, cfg_path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
    print(f"Config saved -> {cfg_path}")
