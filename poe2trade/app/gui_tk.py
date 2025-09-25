# gui_tk.py — Tk/CTk front-end for StashSage
# FULL SOURCE • 24 Jun 2025 • rev N (2025-09-07)
#
#  Ctrl-1 ? supervised overlay  (“Offer History & Price Aura”)
# ---------------------------------------------------------------------

"""
CustomTkinter front-end for StashSage.

This module wires together three main pieces of functionality:
- Supervised price predictions ("Price Aura" + bucket/confidence)
- Unsupervised nearest-neighbour comparisons ("Price Mirror")
- A settings window that controls paths, hotkeys, and filters

Refactor goals:
- Preserve existing behaviour and hotkeys
- Reduce duplication by centralising repeated logic
- Improve docstrings/comments to explain how parts fit together
"""

from __future__ import annotations
import datetime
import importlib
import io, logging, os, re, subprocess, sys, threading
import requests
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Mapping, Tuple, Callable
import json
import pkgutil

# force single-process joblib
os.environ["JOBLIB_MULTIPROCESSING"] = "0"
os.environ["JOBLIB_START_METHOD"] = "threading"

# - third-party -------------------------------------------
import keyboard, numpy as np, pandas as pd, pyperclip, pystray
import customtkinter as ctk
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

# - project -----------------------------------------------
from poe2trade.app import config_manager
from poe2trade.app.discord_flask import start_services, update_config
from poe2trade.utils.chart_utils import (
    generate_bucket_confidence_plot,
    generate_predicted_overlay_with_marker,
)
from poe2trade.utils.gui_utils import (
    main as gui_utils_main,
    parse_copied_item_text,
    process_all_mods,
    _deflate_quality_type_modifiers,
    deflator_and_normaliser,
    cleanup_unused_features,
    flatten_all_mod_patterns,
    drop_raw_mod_slots,
    build_feature_dataframe,
)

# import defence pattern skips so we can hide them in the UI list as well
from poe2trade.utils.gui_utils import (
    PCT_DEFENCE_PATTERNS,
    FLAT_DEFENCE_PATTERNS,
    detect_category_segment,
)
from poe2trade.utils.log_utils import read_all_log_trades
from poe2trade.utils import ml_unsuper_utils  # live price-filter tweak

# chaos/divine ? exalt conversion constants
from poe2trade import (
    poe2trade_root,
    chaos_exalt,
    divine_exalt,
    knn_k,
    __version__,
    __build_date__,
    quantile_splitters,
    jewel_list,
)

from poe2trade.app.gui import constants as gui_constants
from poe2trade.app.gui.state import state as GUI_STATE
from poe2trade.app.gui.ui_helpers import (
    add_png,
    icon_label,
    is_positiveish,
    is_zeroish,
    load_base_image_map as _load_base_image_map,
    find_local_image as _find_local_image,
    mod_sort_bucket as helper_mod_sort_bucket,
    price_simple as helper_price_simple,
    price_string as helper_price_string,
    scaled_png as helper_scaled_png,
    scaled_png_percent as helper_scaled_png_percent,
    textbox as helper_textbox,
    triple as helper_triple,
    price_to_exalt as helper_price_to_exalt,
)

state = GUI_STATE

# - look & feel / logging ---------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# - globals / constants -----------------------------------
DEBUG = False
IMG_W, IMG_H = 12, 9
root: Optional[ctk.CTk] = None
overlay: Optional[ctk.CTkToplevel] = None

steam_entry = ggg_entry = steam_browse_btn = ggg_browse_btn = None
discord_id_entry = discord_token_entry = price_filter_entry = custom_hotkey_entry = filtered_hotkey_entry = discord_api_hotkey_entry = None
client_choice = None

gui_cfg: dict = state.config
LOG_FILES: List[str] = []
SERVICES_STARTED = False
client_day_filter = 30

_FILTER_ENTRY_MEMORY: dict[str, list[str]] = {}

MIN_WINDOW_WIDTH = 560
MIN_WINDOW_HEIGHT = 240


@dataclass(frozen=True)
class DisplayContext:
    """Normalized prediction and bucket metadata for downstream overlays."""

    value: Optional[float]
    value_source: Optional[str]
    bucket_label: Optional[str]
    bucket_low: Optional[float]
    bucket_high: Optional[float]
    intervals: dict[str, tuple[Optional[float], Optional[float]]]
    percentile_values: Optional[tuple[Optional[float], Optional[float]]]


@dataclass(frozen=True)
class BucketMeta:
    """Resolved bucket information with sensible fallbacks for rendering."""

    label: Optional[str]
    low: Optional[float]
    high: Optional[float]
    median: Optional[float]
    intervals: dict[str, tuple[Optional[float], Optional[float]]]


def _auto_resize_root() -> None:
    if root is None:
        return
    try:
        root.update_idletasks()
        width = max(MIN_WINDOW_WIDTH, root.winfo_reqwidth())
        height = max(MIN_WINDOW_HEIGHT, root.winfo_reqheight())
        root.geometry(f"{width}x{height}")
    except Exception:
        pass


def _resolve_build_date(raw_date: str) -> str:
    if raw_date and raw_date != "dev":
        return raw_date

    try:
        meta = importlib.import_module("poe2trade._build_meta")
        resolved = getattr(meta, "__build_date__", None)
        if resolved:
            return str(resolved)
    except Exception:
        pass

    try:
        data = pkgutil.get_data("poe2trade", "_build_meta.py")
        if data:
            scope: dict[str, str] = {}
            exec(data.decode("utf-8", "ignore"), {}, scope)
            resolved = scope.get("__build_date__")
            if resolved:
                return str(resolved)
    except Exception:
        pass

    if getattr(sys, "frozen", False):
        try:
            ts = Path(sys.executable).stat().st_mtime
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            pass

    return raw_date


BUILD_DATE = _resolve_build_date(__build_date__)

DEFAULT_STEAM = gui_constants.DEFAULT_STEAM_LOG_PATH
DEFAULT_GGG = gui_constants.DEFAULT_GGG_LOG_PATH
DEFAULT_PRICE_FILTER = gui_constants.DEFAULT_PRICE_FILTER
DEFAULT_OVERLAY_HOTKEY = gui_constants.DEFAULT_OVERLAY_HOTKEY
DEFAULT_FILTERED_OVERLAY_HOTKEY = gui_constants.DEFAULT_FILTERED_OVERLAY_HOTKEY
DEFAULT_DISCORD_API_HOTKEY = gui_constants.DEFAULT_DISCORD_API_HOTKEY
_overlay_hotkey_handle = None  # track overlay hotkey binding
_filtered_overlay_hotkey_handle = None  # track filtered overlay hotkey binding
_discord_api_hotkey_handle = None  # track discord API hotkey binding

# Bucket colours for text accents
# Bucket colours for accents
_BUCKET_COLOURS = gui_constants.BUCKET_COLOURS
# Neutral bar colour to match KNN UI greys
_BAR_COLOUR = gui_constants.BAR_COLOUR
# Fixed height for the two horizontal bars so they are equal and fit two lines
# Fixed height for the two horizontal bars so they are equal and fit two lines
_BAR_HEIGHT_PX = gui_constants.BAR_HEIGHT_PX
# Fixed name-row height (single line) to keep KNN rows aligned
_NAME_ROW_H = gui_constants.NAME_ROW_HEIGHT
"""
KNN overlay cell height scaling.
Multiply computed cell heights by this factor. For a slight reduction,
use values below 1.0 (e.g., 0.9 = 90%).

Increased slightly from 0.85 ? 0.92 to make cells a bit taller
in both left and right columns without affecting width.
"""
_KNN_CELL_HEIGHT_FACTOR = gui_constants.KNN_CELL_HEIGHT_FACTOR

# ---------- scoring JSON hot-path cache ----------
_SCORING_JSON_CACHE: dict[str, pd.DataFrame] = {}
_SCORING_JSON_MTIME: dict[str, float] = {}


def _load_scoring_json_once(json_path: Path) -> Optional[pd.DataFrame]:
    """Fast, mtime-aware loader for scoring sidecar JSON (orient='records')."""
    try:
        mt = json_path.stat().st_mtime
        key = str(json_path)
        if key in _SCORING_JSON_CACHE and _SCORING_JSON_MTIME.get(key) == mt:
            return _SCORING_JSON_CACHE[key]

        # Robust load: tolerate either a list[dict] or a dict-like
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame.from_records(data)  # fallback

        _SCORING_JSON_CACHE[key] = df
        _SCORING_JSON_MTIME[key] = mt
        return df
    except Exception as exc:
        logging.warning("Failed to load scoring JSON %s: %s", json_path.name, exc)
        return None


# --------------------------------------------------------------
# ------------   BUCKET BADGE HELPER (restored!)   -------------
# --------------------------------------------------------------
def _bucket_badge(
    parent,
    label,
    median,
    lo,
    hi,
    pred_median: float | None = None,
    nearest_mean: float | None = None,
    nearest_median: float | None = None,
    combined_prices_line: str | None = None,
    mode: str = "both",  # 'both' | 'dataset' | 'nearest'
    category_title: str | None = None,
    dataset_pred_value: float | None = None,
):
    """Render a compact horizontal price band with contextual text.

    Two modes are supported:
    - mode="dataset": shows the supervised model's prediction and bucket label
    - mode="nearest": shows quick stats derived from nearest items

    The shape (two lines) is kept consistent between both bars to
    visually align with the KNN section below.
    """
    # Always use a neutral grey bar colour to match KNN cells
    fr = ctk.CTkFrame(parent, fg_color=_BAR_COLOUR, corner_radius=8)
    fr.configure(height=_BAR_HEIGHT_PX)
    fr.pack(fill="x", padx=4, pady=(0, 4))
    try:
        fr.pack_propagate(False)
    except Exception:
        pass
    # Center content vertically using grid spacers for reliability
    try:
        fr.grid_rowconfigure(0, weight=1)
        fr.grid_rowconfigure(2, weight=1)
        fr.grid_columnconfigure(0, weight=1)
    except Exception:
        pass
    content = ctk.CTkFrame(fr, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew")

    sep = " -- "
    show_line1 = True
    show_line2 = True

    # Line 1 – Price Prediction #1: "Price Prediction #1 - <model> - <Xe>"
    if show_line1:
        val = (
            dataset_pred_value
            if isinstance(dataset_pred_value, (int, float))
            else pred_median
        )
        # Ensure nearest bar shows a value even when dataset value is missing
        if mode == "nearest" and not isinstance(val, (int, float)):
            if isinstance(nearest_median, (int, float)):
                val = nearest_median
            elif isinstance(nearest_mean, (int, float)):
                val = nearest_mean
        xe = None
        if isinstance(val, (int, float)):
            try:
                xe = f"{int(round(float(val)))}e"
            except Exception:
                xe = f"{val:.0f}e"
        num = "1" if mode == "dataset" else "2"
        # For the nearest-items bar, include both mean and median in the first line
        if mode == "nearest":
            mean_txt = med_txt = None
            if isinstance(nearest_mean, (int, float)):
                try:
                    mean_txt = f"{int(round(float(nearest_mean)))}e"
                except Exception:
                    mean_txt = f"{nearest_mean:.0f}e"
            if isinstance(nearest_median, (int, float)):
                try:
                    med_txt = f"{int(round(float(nearest_median)))}e"
                except Exception:
                    med_txt = f"{nearest_median:.0f}e"
            parts = []
            if mean_txt:
                parts.append(f"{mean_txt} (mean)")
            if med_txt:
                parts.append(f"{med_txt} (median)")
            suffix = ", ".join(parts) if parts else (xe or "")
            line1 = f"Price Prediction #2 - {suffix}".rstrip()
        else:
            line1 = f"Price Prediction #{num} - {xe or ''}".rstrip()
        ctk.CTkLabel(
            content, text=line1, font=("Helvetica", 28, "bold"), text_color="white"
        ).pack(padx=8, pady=(4, 2))

        # Line 1b – Relative <bucket> Value within {Category}
        # Build as three labels to colour only the bucket word
        if mode == "dataset" and show_line2:
            cat_txt = (category_title or "").strip() or "Category"
            row_ds = ctk.CTkFrame(content, fg_color="transparent")
            row_ds.pack(padx=8, pady=(0, 4))
            ctk.CTkLabel(
                row_ds, text="Relative ", font=("Helvetica", 20), text_color="#EEEEEE"
            ).pack(side="left")
            bucket = (label or "").capitalize()
            bcol = _BUCKET_COLOURS.get(bucket.lower(), "#EEEEEE")
            ctk.CTkLabel(
                row_ds, text=bucket, font=("Helvetica", 20, "bold"), text_color=bcol
            ).pack(side="left")
            ctk.CTkLabel(
                row_ds,
                text=f" Value within {cat_txt}",
                font=("Helvetica", 20),
                text_color="#EEEEEE",
            ).pack(side="left")

    # Line 2 – nearest items (prefer explicit list of prices)
    if show_line2 and mode == "nearest" and combined_prices_line:
        # Keep same font/size as dataset second line for consistency
        ctk.CTkLabel(
            content,
            text=combined_prices_line,
            font=("Helvetica", 20),
            text_color="#EEEEEE",
        ).pack(padx=8, pady=(0, 4))
        return

    # Line 2 — Price Prediction #2 (nearest items), only exalts
    if (
        show_line2
        and mode == "nearest"
        and isinstance(nearest_mean, (int, float))
        and isinstance(nearest_median, (int, float))
    ):
        # Mean/Median are now shown in line 1 to match requested format; avoid duplicating here.
        pass

    # Line 3 — Combined prices list (optional, smaller, not bold)
    # omit third line to keep both bars at two lines


# --------------------------------------------------------------
# ------------- stat / mod helpers ------------------------------
# Map core norm columns ? pretty labels


def _coerce_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(f):
        return None
    return f


def _normalise_bucket_intervals(
    raw_intervals: Any,
) -> dict[str, tuple[float | None, float | None]]:
    intervals: dict[str, tuple[float | None, float | None]] = {}
    if isinstance(raw_intervals, Mapping):
        items = raw_intervals.items()
    else:
        return intervals
    for key, pair in items:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        lo_raw, hi_raw = pair
        lo = _coerce_float(lo_raw) if lo_raw is not None else None
        hi = _coerce_float(hi_raw) if hi_raw is not None else None
        intervals[str(key).lower()] = (lo, hi)
    return intervals


def _resolve_percentile_splitters() -> Tuple[int, int]:
    default = (70, 90)
    try:
        qs = list(quantile_splitters or default)
    except Exception:
        return default
    if len(qs) != 2:
        return default
    try:
        a, b = float(qs[0]), float(qs[1])
    except Exception:
        return default
    if not (0 <= a < b <= 100):
        return default
    return int(round(a)), int(round(b))


@lru_cache(maxsize=64)
def _load_scoring_dataframe(
    cat_norm: str | None, seg_norm: str | None
) -> Optional[pd.DataFrame]:
    cat_key = (cat_norm or "").strip().lower()
    seg_key = (seg_norm or "").strip().lower()
    if not cat_key:
        return None

    model_dir = Path(poe2trade_root) / "db" / "super_models"
    json_candidates: list[Path] = []
    xlsx_candidates: list[Path] = []

    if seg_key:
        json_candidates.append(model_dir / f"{cat_key}_{seg_key}_scoring.json")
        xlsx_candidates.append(model_dir / f"{cat_key}_{seg_key}_scoring.xlsx")
        if cat_key == "body_armour":
            json_candidates.append(model_dir / f"body_armor_{seg_key}_scoring.json")
            xlsx_candidates.append(model_dir / f"body_armor_{seg_key}_scoring.xlsx")
    else:
        json_candidates.append(model_dir / f"{cat_key}_scoring.json")
        xlsx_candidates.append(model_dir / f"{cat_key}_scoring.xlsx")
        for kind in ("ring", "amulet", "belt"):
            json_candidates.append(model_dir / f"{cat_key}_{kind}_scoring.json")
            xlsx_candidates.append(model_dir / f"{cat_key}_{kind}_scoring.xlsx")

    for candidate in json_candidates:
        if candidate.is_file():
            try:
                df = _load_scoring_json_once(candidate)
            except Exception:
                df = None
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df

    for candidate in xlsx_candidates:
        if candidate.is_file():
            try:
                df = pd.read_excel(candidate)
            except Exception:
                continue
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df

    return None


def _derive_bucket_from_value(
    value: float | None,
    *,
    intervals: Mapping[str, tuple[float | None, float | None]],
    percentile_values,
    fallback_label: Any,
    fallback_low: float | None,
    fallback_high: float | None,
) -> tuple[Optional[str], Optional[float], Optional[float]]:
    label: Optional[str] = None
    low = high = None

    low_cut = high_cut = None
    if percentile_values:
        seq = percentile_values
        if not isinstance(seq, (list, tuple)):
            try:
                seq = list(seq)
            except TypeError:
                seq = None
        if seq:
            if len(seq) > 0:
                low_cut = _coerce_float(seq[0])
            if len(seq) > 1:
                high_cut = _coerce_float(seq[1])

    if value is not None and (low_cut is not None or high_cut is not None):
        if low_cut is not None and value <= low_cut:
            label = "Low"
        elif high_cut is not None and value > high_cut:
            label = "High"
        elif low_cut is not None or high_cut is not None:
            label = "Medium"
        if label:
            bucket_key = label.lower()
            if intervals:
                low, high = intervals.get(bucket_key, (None, None))
            if bucket_key == "low":
                if low is None:
                    low = fallback_low
                if high is None:
                    high = low_cut if low_cut is not None else fallback_high
            elif bucket_key == "high":
                if low is None:
                    low = high_cut if high_cut is not None else fallback_low
                if high is None:
                    high = fallback_high
            elif label == "Medium":
                if low is None:
                    low = low_cut
                if high is None:
                    high = high_cut

    if label is None and value is not None and intervals:
        matches = []
        for key, (lo, hi) in intervals.items():
            if (lo is None or value >= lo) and (hi is None or value <= hi):
                matches.append(key.lower())
        if matches:
            if "high" in matches:
                label = "High"
                low, high = intervals.get("high", (None, None))
            elif "medium" in matches:
                label = "Medium"
                low, high = intervals.get("medium", (None, None))
            elif "low" in matches:
                label = "Low"
                low, high = intervals.get("low", (None, None))
        if label is None:
            low_hi = intervals.get("low", (None, None))[1]
            high_lo = intervals.get("high", (None, None))[0]
            if low_hi is not None and value <= low_hi:
                label = "Low"
                low, high = intervals.get("low", (None, None))
            elif high_lo is not None and value >= high_lo:
                label = "High"
                low, high = intervals.get("high", (None, None))
            elif "medium" in intervals:
                label = "Medium"
                low, high = intervals.get("medium", (None, None))

    if label is None:
        if isinstance(fallback_label, str) and fallback_label.strip():
            label = fallback_label.strip().capitalize()
        else:
            label = None
        if low is None:
            low = fallback_low
        if high is None:
            high = fallback_high

    return label, low, high


def _compute_display_context(
    ml_super: Mapping[str, Any],
    *,
    cat_norm: str | None = None,
    seg_norm: str | None = None,
) -> DisplayContext:
    """Normalize ML predictions into a structure overlays can consume safely."""

    if not isinstance(ml_super, Mapping):
        return DisplayContext(
            value=None,
            value_source=None,
            bucket_label=None,
            bucket_low=None,
            bucket_high=None,
            intervals={},
            percentile_values=None,
        )

    predictions = ml_super.get("predictions")
    if not isinstance(predictions, Mapping):
        predictions = {}

    display_value = None
    display_source = None
    for source, candidate in (
        ("xgb", predictions.get("xgb")),
        ("median", ml_super.get("median")),
        ("pred_median", predictions.get("pred_median")),
        ("mean", ml_super.get("mean")),
        ("pred_mean", predictions.get("mean")),
    ):
        display_value = _coerce_float(candidate)
        if display_value is not None:
            display_source = source
            break

    intervals = _normalise_bucket_intervals(ml_super.get("bucket_intervals", {}))

    def _normalize_percentiles(raw_vals: Any) -> Optional[tuple[Optional[float], Optional[float]]]:
        if isinstance(raw_vals, (list, tuple)) and raw_vals:
            low = _coerce_float(raw_vals[0]) if len(raw_vals) > 0 else None
            high = _coerce_float(raw_vals[1]) if len(raw_vals) > 1 else None
            if low is not None or high is not None:
                return (low, high)
        return None

    percentile_values = _normalize_percentiles(ml_super.get("percentile_values"))
    if percentile_values is None:
        cuts = ml_super.get("cuts")
        if isinstance(cuts, Mapping):
            percentile_values = _normalize_percentiles(cuts.get("percentile_values"))

    if percentile_values is None:
        cat_key = (cat_norm or "").strip().lower()
        seg_key = (seg_norm or "").strip().lower()
        df_scored = _load_scoring_dataframe(cat_key, seg_key)
        if isinstance(df_scored, pd.DataFrame) and "pred_median" in df_scored:
            vals = (
                pd.to_numeric(df_scored["pred_median"], errors="coerce")
                .dropna()
                .to_numpy()
            )
            if vals.size:
                low_p, high_p = _resolve_percentile_splitters()
                try:
                    v_low, v_high = np.percentile(vals, [low_p, high_p])
                    percentile_values = (float(v_low), float(v_high))
                except Exception:
                    percentile_values = None

    bucket_label, bucket_low, bucket_high = _derive_bucket_from_value(
        display_value,
        intervals=intervals,
        percentile_values=percentile_values,
        fallback_label=ml_super.get("bucket"),
        fallback_low=_coerce_float(ml_super.get("bucket_low")),
        fallback_high=_coerce_float(ml_super.get("bucket_high")),
    )

    return DisplayContext(
        value=display_value,
        value_source=display_source,
        bucket_label=bucket_label,
        bucket_low=bucket_low,
        bucket_high=bucket_high,
        intervals=intervals,
        percentile_values=percentile_values,
    )


def _extract_supervised_values(
    ml_super: Mapping[str, Any],
    *,
    cat_norm: Optional[str],
    seg_norm: Optional[str],
) -> tuple[
    Optional[float],  # display_value
    Optional[str],    # bucket_label (capitalised)
    Optional[float],  # bucket_low
    Optional[float],  # bucket_high
    Optional[float],  # bucket_median_val
    Mapping[str, tuple[Optional[float], Optional[float]]],  # intervals
    Optional[io.BytesIO],  # conf_buf
]:
    """Centralise supervised values + confidence plot generation.

    Returns a tuple of (display_value, bucket_label, bucket_low, bucket_high,
    bucket_median_val, intervals, conf_buf).
    """
    display_ctx = _compute_display_context(ml_super, cat_norm=cat_norm, seg_norm=seg_norm)

    display_value = display_ctx.value
    if display_value is None and isinstance(ml_super, dict):
        display_value = _coerce_float(ml_super.get("median")) or _coerce_float(
            ml_super.get("mean")
        )

    bucket_label = display_ctx.bucket_label
    if not bucket_label and isinstance(ml_super, dict):
        bucket_label = ml_super.get("bucket")
    if isinstance(bucket_label, str):
        bucket_label = bucket_label.strip().capitalize() or None

    bucket_low = display_ctx.bucket_low
    if bucket_low is None and isinstance(ml_super, dict):
        bucket_low = _coerce_float(ml_super.get("bucket_low"))

    bucket_high = display_ctx.bucket_high
    if bucket_high is None and isinstance(ml_super, dict):
        bucket_high = _coerce_float(ml_super.get("bucket_high"))

    bucket_median_val = display_value
    if bucket_median_val is None and isinstance(ml_super, dict):
        bucket_median_val = _coerce_float(ml_super.get("bucket_median"))

    intervals = display_ctx.intervals
    if not intervals and isinstance(ml_super, dict):
        intervals = ml_super.get("bucket_intervals", {})

    conf_buf: Optional[io.BytesIO] = None
    if intervals and bucket_label:
        try:
            conf_buf = generate_bucket_confidence_plot(
                pred_median=(display_value if isinstance(display_value, (int, float)) else 0.0),
                intervals=intervals,
                bucket_label=bucket_label or "Unknown",
                width=IMG_W,
                height=IMG_H * 0.9,
            )
        except Exception:
            conf_buf = None

    return (
        display_value,
        bucket_label,
        bucket_low,
        bucket_high,
        bucket_median_val,
        intervals,
        conf_buf,
    )
_CORE_KEYS = {"ar_norm": "Armour", "ev_norm": "Evasion", "es_norm": "Energy Shield"}
# Hide these from the modifiers list; handled by *_NORM already
_HIDE_DEF_PATTERNS = PCT_DEFENCE_PATTERNS | FLAT_DEFENCE_PATTERNS

# +---------------- HOT-KEY THROTTLING --------------------+
_hotkey_busy = {
    "super": threading.Lock(),  # Ctrl+1 / Ctrl+0 consolidated
    "filtered": threading.Lock(),  # Filtered overlay flow
    "discord_api": threading.Lock(),  # Discord API JSON DM
}


def _run_with_lock(lock: threading.Lock, fn, *a, **kw):
    if not lock.acquire(blocking=False):
        return
    try:
        fn(*a, **kw)
    finally:
        lock.release()


def _prepare_filtered_context(text: str) -> dict | None:
    try:
        parsed = parse_copied_item_text(text)
    except Exception:
        logging.exception("Failed to parse clipboard for filtered overlay")
        return None

    if not parsed.get("Item Category"):
        parsed["Item Category"] = "default_model"

    try:
        parsed = process_all_mods(parsed)

        if parsed.get("Item Category", "").lower() == "belt":
            total = 1
            for prefix, max_i in (("implicit", 3), ("enchant", 3), ("rune", 6), ("explicit", 10)):
                for i in range(1, max_i + 1):
                    pat = parsed.get(f"{prefix}_mod_{i}_pattern", "").lower()
                    val = parsed.get(f"{prefix}_mod_{i}_value", 0) or 0
                    if "charm slot" in pat:
                        try:
                            total = max(total, int(val))
                        except ValueError:
                            pass
            parsed["socket_count"] = total
            parsed["has # charm slots"] = total

        parsed = _deflate_quality_type_modifiers(parsed)
        parsed = deflator_and_normaliser(parsed)
        name_raw = (parsed.get("Item Name") or "").strip()
        base_type_raw = (parsed.get("Base Type") or "").strip()
        item_display_name = name_raw or base_type_raw or "(Unknown item)"
        icon_name = base_type_raw or name_raw
        if not icon_name:
            icon_name = item_display_name

        parsed = cleanup_unused_features(parsed)
        flatten_all_mod_patterns(parsed)
        drop_raw_mod_slots(parsed)

        cat, seg = detect_category_segment(parsed)
        if cat in ("ring", "amulet", "belt"):
            seg = None

        base_X = build_feature_dataframe(parsed)
        item_name = item_display_name

        return {
            "text": text,
            "parsed": parsed,
            "category": cat,
            "segment": seg,
            "base_X": base_X,
            "item_name": item_name,
            "icon_name": icon_name,
        }
    except Exception:
        logging.exception("Failed to prepare filtered overlay context")
        return None


def _build_filter_rows(base_X: pd.DataFrame, category: str | None) -> list[dict]:
    """Build a list of rows for the filtered-overlay UI.

    Each row is a dict with fields: key, label, raw, display, group.
    Core rows (AR/EV/ES) are emitted first, then modifier rows, with
    jewellery hiding defence-derived fields that are already encoded in *_NORM.
    """
    if base_X is None or base_X.empty:
        return []

    base_series = base_X.iloc[0]
    rows: list[dict] = []

    cat_l = (category or "").strip().lower()
    is_jewellery = cat_l in {"ring", "amulet", "belt"}

    skip = {"price", "currency"}
    if not is_jewellery:
        skip.update(
            {
                "armour",
                "evasion",
                "evasion rating",
                "energy shield",
                "ar",
                "ev",
                "es",
            }
        )
        skip.update(s.lower() for s in _HIDE_DEF_PATTERNS)
    skip_lc = {s.lower() for s in skip}

    def _numeric(series, key: str) -> float:
        try:
            return float(series.get(key, 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    def _disp(value: float) -> float:
        return round(value)

    def _fmt_disp(value: float) -> str:
        return f"{int(value)}" if float(value).is_integer() else f"{value:g}"

    for key in _CORE_KEYS.keys():
        val = _numeric(base_series, key)
        if val == 0:
            continue
        rows.append(
            {
                "key": key,
                "label": _CORE_KEYS.get(key, key),
                "raw": float(val),
                "display": _fmt_disp(_disp(val)),
                "group": "core",
            }
        )

    seen_core = set(_CORE_KEYS.keys())
    for key in sorted(str(k) for k in base_series.index if str(k) not in seen_core):
        key_l = key.lower()
        if key_l in skip_lc:
            continue
        val = _numeric(base_series, key)
        if val == 0:
            continue
        rows.append(
            {
                "key": key,
                "label": key,
                "raw": float(val),
                "display": _fmt_disp(_disp(val)),
                "group": "mods",
            }
        )

    return rows


def _parse_filter_input(raw: str, base_value: float) -> tuple[str, object]:
    """Parse a user-provided filter expression for a mod.

    Supports the following shorthand:
    - "35"  -> (">=", 35)
    - "35+" -> (">=", 35)
    - "35=" -> ("==", 35)
    - "10%" -> ("between", (rounded_lo, rounded_hi)) around the base value
    """
    value = raw.strip()
    if not value:
        raise ValueError("Empty filter value")

    # Percentage => symmetric range around base value, rounded to integers
    if value.endswith('%'):
        num = value[:-1].strip()
        if not num:
            raise ValueError("Percentage filter requires a number, e.g. 10%")
        try:
            pct = float(num) / 100.0
        except ValueError as exc:
            raise ValueError(f"Invalid percentage: {raw}") from exc
        span = abs(float(base_value)) * pct
        lo = float(base_value) - span
        hi = float(base_value) + span
        # Round range bounds for filtering to keep behaviour intuitive
        lo_r = float(round(lo))
        hi_r = float(round(hi))
        lo_r, hi_r = (lo_r, hi_r) if lo_r <= hi_r else (hi_r, lo_r)
        return ('between', (lo_r, hi_r))

    # Accept trailing '+' (>=) or '=' (exact)
    if value.endswith(('+', '=')):
        op_char = value[-1]
        num = value[:-1].strip()
        if not num:
            raise ValueError(f"Invalid filter: {raw}")
        try:
            numeric = float(num)
        except ValueError as exc:
            raise ValueError(f"Invalid numeric value: {raw}") from exc
        if op_char == '+':
            return ('>=', numeric)
        else:
            return ('==', numeric)

    # Plain number => minimum (>=)
    try:
        numeric = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value: {raw}") from exc
    return ('>=', numeric)


def _show_filtered_filter_popup(ctx: dict) -> None:
    """Pop up the filtered-overlay dialog to capture mod constraints."""
    if not (root and root.winfo_exists()):
        return

    rows = _build_filter_rows(ctx.get('base_X'), ctx.get('category'))
    if not rows:
        messagebox.showwarning('StashSage', 'No comparable modifiers found for filtered overlay input.')
        return

    popup = ctk.CTkToplevel(root)
    popup.title('Filtered Mods for Nearest Items')
    try:
        popup.iconbitmap(str(Path(__file__).with_name('stashsage_logo.ico')))
    except Exception:
        pass
    popup.grab_set()

    frame = ctk.CTkFrame(popup)
    frame.pack(fill='both', expand=True, padx=16, pady=16)

    item_key = (ctx.get('item_name') or '').strip().lower()
    prev_snapshot = _FILTER_ENTRY_MEMORY.get(item_key) if item_key else None

    header = ctk.CTkFrame(frame, fg_color='transparent')
    header.pack(fill='x', pady=(0, 12))
    try:
        header.grid_columnconfigure(1, weight=1)
    except Exception:
        pass

    icon_label = _icon_label(
        header,
        ctx.get('icon_name') or ctx.get('item_name', '(Unknown item)'),
        target_w=48,
        target_h=max(_NAME_ROW_H, 48),
    )
    if icon_label:
        icon_label.grid(row=0, column=0, rowspan=2, sticky='nw', padx=(0, 12))

    ctk.CTkLabel(
        header,
        text='Your Item',
        font=('Consolas', 14),
    ).grid(row=0, column=1, sticky='w')

    ctk.CTkLabel(
        header,
        text=ctx.get('item_name', '(Unknown item)'),
        font=('Consolas', 18, 'bold'),
    ).grid(row=1, column=1, sticky='w')

    ctk.CTkLabel(
        frame,
        text='Enter mod filter patterns: 35+ (>=35), 35= (=35), or 35% (+/-35%).',
        wraplength=520,
        justify='left',
        ).pack(anchor='w')

    scroll = ctk.CTkScrollableFrame(frame, height=360, width=540)
    scroll.pack(fill='both', expand=True, pady=12)

    entries: list[tuple[dict, ctk.CTkEntry]] = []

    for idx, row in enumerate(rows):
        row_frame = ctk.CTkFrame(scroll, fg_color='transparent')
        row_frame.pack(fill='x', pady=4)

        label_txt = f"{row['label']}: {row['display']}"
        ctk.CTkLabel(row_frame, text=label_txt, anchor='w').pack(side='left', padx=(0, 12))

        entry = ctk.CTkEntry(row_frame, width=120)
        entry.pack(side='right')
        if prev_snapshot and idx < len(prev_snapshot):
            restored = (prev_snapshot[idx] or '').strip()
            if restored:
                entry.insert(0, restored)
        entries.append((row, entry))

    btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
    btn_frame.pack(fill='x', pady=(8, 0))

    def _apply_filters() -> None:
        filters: dict[str, tuple[str, object]] = {}
        snapshot: list[str] = []
        for row, entry in entries:
            raw_val = entry.get().strip()
            snapshot.append(raw_val)
            if not raw_val:
                continue
            try:
                op, val = _parse_filter_input(raw_val, row['raw'])
            except ValueError as exc:
                messagebox.showerror('Invalid filter', str(exc), parent=popup)
                return
            filters[row['key']] = (op, val)

        popup.destroy()
        if item_key:
            _FILTER_ENTRY_MEMORY[item_key] = snapshot
        _start_filtered_overlay_with_filters(ctx, filters)

    def _cancel() -> None:
        popup.destroy()

    ctk.CTkButton(btn_frame, text='Apply Filter', command=_apply_filters).pack(side='left', expand=True, fill='x', padx=(0, 6))
    ctk.CTkButton(btn_frame, text='Cancel', command=_cancel).pack(side='left', expand=True, fill='x')


def _start_filtered_overlay_async(text: str) -> None:
    """Async entry-point for filtered overlay flow (parsing off UI thread)."""
    def work() -> None:
        ctx = _prepare_filtered_context(text)

        def show() -> None:
            if ctx is None:
                messagebox.showerror('StashSage', 'Could not prepare filtered overlay for this item.')
                return
            _show_filtered_filter_popup(ctx)

        root.after(0, show)

    threading.Thread(target=work, daemon=True).start()


def _start_filtered_overlay_with_filters(ctx: dict, filters: dict[str, tuple[str, object]]) -> None:
    """Resolve neighbours with filters off the UI thread, then render overlay."""
    def work() -> None:
        try:
            # If no filters were provided, fall back to the standard unfiltered KNN
            if not filters:
                uns = gui_utils_main(ctx.get('text', ''), key='unsuper')
                if uns:
                    _X, nbrs = uns
                else:
                    nbrs = None
            else:
                nbrs = ml_unsuper_utils.call_ml(
                    ctx.get('category', 'default_model'),
                    ctx.get('segment'),
                    ctx.get('base_X'),
                    where=filters,
                )
        except Exception:
            logging.exception('Filtered overlay lookup failed')
            nbrs = None

        def finish() -> None:
            if nbrs is None or (hasattr(nbrs, 'empty') and getattr(nbrs, 'empty')):
                messagebox.showwarning('StashSage', 'No neighbours matched the filtered criteria.')
                return
            ctx_out = dict(ctx)
            ctx_out['filtered_neighbors'] = nbrs
            ctx_out['filters'] = filters
            _show_filtered_overlay_result(ctx_out)

        root.after(0, finish)

    threading.Thread(target=work, daemon=True).start()


def _show_filtered_overlay_result(ctx: dict) -> None:
    """Present the filtered overlay result as the consolidated dashboard."""
    if not (root and root.winfo_exists()):
        return

    base_X = ctx.get('base_X')
    nbrs = ctx.get('filtered_neighbors')
    raw_text = ctx.get('text') or ''

    if not isinstance(base_X, pd.DataFrame) or base_X.empty or nbrs is None:
        messagebox.showwarning('StashSage', 'Filtered overlay is unavailable for this item.')
        return

    try:
        root.after(0, lambda: root.configure(cursor='watch'))
    except Exception:
        pass

    def work() -> None:
        try:
            ml_super = gui_utils_main(raw_text, key='super') or {}
            parsed = parse_copied_item_text(raw_text)

            raw_cat = str(parsed.get('Item Category', ctx.get('category', 'default_model'))).lower().replace(' ', '_')
            raw_cat = {'boot': 'boots', 'glove': 'gloves'}.get(raw_cat, raw_cat)
            cat_norm = ctx.get('category') or raw_cat or 'default_model'
            # For Jewels, switch category to the concrete subtype so scoring JSON resolves
            if cat_norm == 'jewel':
                try:
                    raw_lc = (raw_text or '').lower()
                    jt = next((j for j in (jewel_list or []) if re.search(rf"\b{re.escape(j)}\b", raw_lc, flags=re.I)), None)
                    if jt:
                        cat_norm = jt
                except Exception:
                    pass

            seg_norm = ctx.get('segment')
            if isinstance(ml_super, dict):
                seg_norm = ml_super.get('segment') or seg_norm
            if seg_norm is None:
                try:
                    _c, _s = detect_category_segment(parsed)
                    seg_norm = _s
                except Exception:
                    seg_norm = None

            (
                display_value,
                bucket_label,
                bucket_low,
                bucket_high,
                bucket_median_val,
                intervals,
                conf_buf,
            ) = _extract_supervised_values(ml_super, cat_norm=cat_norm, seg_norm=seg_norm)

            unsuper_item_name = parsed.get('Item Name', '(Unknown)')
            try:
                if str(parsed.get('Item Category','')).strip().lower() == 'jewel':
                    raw = (raw_text or '').lower()
                    jt = next((j for j in (jewel_list or []) if re.search(rf"\b{re.escape(j)}\b", raw, flags=re.I)), None)
                    if jt and jt.title() not in unsuper_item_name:
                        unsuper_item_name = (unsuper_item_name + (" " if unsuper_item_name else "") + jt.title()).strip()
            except Exception:
                pass
            item_name = (ml_super.get('item_name') if isinstance(ml_super, dict) else None) or ctx.get('item_name') or unsuper_item_name
            category_title = (cat_norm or '').replace('_', ' ').title()

            def finish() -> None:
                try:
                    root.configure(cursor='')
                except Exception:
                    pass
                _show_dashboard_overlay(
                    item_name,
                    None,
                    None,
                    conf_buf,
                    bucket_label,
                    bucket_median_val,
                    bucket_low,
                    bucket_high,
                    display_value,
                    category_title,
                    cat_norm,
                    seg_norm,
                    base_X,
                    nbrs,
                    unsuper_item_name,
                    filters=ctx.get('filters'),
                )

            root.after(0, finish)
        except Exception:
            logging.exception('Filtered overlay presentation failed')

            def fail() -> None:
                try:
                    root.configure(cursor='')
                except Exception:
                    pass
                messagebox.showerror('StashSage', 'Failed to build filtered overlay.')

            root.after(0, fail)

    threading.Thread(target=work, daemon=True).start()


# +--------------------------------------------------------+

# ------------- price-filter helpers ----------------------
PRICE_FILTER_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[ecd]?\s*$", re.I)


def _apply_price_filter(cfg: dict) -> None:
    raw = str(cfg.get("price_mirror_filter", DEFAULT_PRICE_FILTER)).strip()
    try:
        ml_unsuper_utils.set_price_filter(raw)
        logging.info("KNN price filter set to %r", raw)
    except Exception as exc:
        logging.warning("Invalid price filter %r – defaulting to 1e (%s)", raw, exc)
        ml_unsuper_utils.set_price_filter("1e")


# ------------- tiny UI helpers ----------------------------
def _textbox(parent, lines, yellow, colours, row, col, height: int | None = None, filter_tags: dict[int, str] | None = None):
    return helper_textbox(
        parent,
        lines,
        yellow,
        colours,
        row,
        col,
        height=height,
        filter_tags=filter_tags,
    )



def _parse_item(text: str) -> str | None:
    """
    Fallback name-extractor if gui_utils_main fails.
    After seeing 'Rarity: Rare', collects all subsequent non-empty,
    non-separator lines and joins them into the full item name.
    """
    lines = text.splitlines()
    item_lines: list[str] = []
    grab = False

    for ln in lines:
        if not grab:
            if ln.lower().startswith("rarity:") and "rare" in ln.lower():
                grab = True
            continue
        # once grabbing, stop at blank or '--------'
        if not ln.strip() or ln.startswith("--------"):
            break
        item_lines.append(ln.strip())

    if item_lines:
        # join e.g. ["Mind Mantle", "Ornate Plate"] ? "Mind Mantle Ornate Plate"
        return " ".join(item_lines)
    return None


def _destroy_overlay():
    global overlay
    overlay = state.overlay
    if overlay and overlay.winfo_exists():
        overlay.destroy()
    state.reset_overlay()
    overlay = None


# --- put this right next to _destroy_overlay -----------
def _scaled_png(parent: ctk.CTkFrame, buf: io.BytesIO, target_w: int) -> ctk.CTkLabel:
    return helper_scaled_png(parent, buf, target_w, state.overlay)


# Scale a PNG to a percentage of its native width
def _scaled_png_percent(parent: ctk.CTkFrame, buf: io.BytesIO, pct: float) -> ctk.CTkLabel:
    return helper_scaled_png_percent(parent, buf, pct, state.overlay)


# ---------------- tiny UI helpers ----------------
def _add_png_to_ctklabel(parent: ctk.CTkFrame, buf: io.BytesIO) -> ctk.CTkLabel:
    return add_png(parent, buf, state.overlay)


# ------------- currency helpers --------------------------
def _price_to_exalt(price: float, cur: str | None) -> float:
    return helper_price_to_exalt(price, cur)


def _price_string(row: pd.Series) -> tuple[str, float] | None:
    return helper_price_string(row)


# simple price like "10e" or "50c" or "2d" for header tags
def _price_simple(row: pd.Series) -> Optional[str]:
    return helper_price_simple(row)


def _triple(e_val: float) -> str:
    return helper_triple(e_val)


# ------------- log-scraper (for supervised) -------------
def _scrape_logs() -> pd.DataFrame:
    trades = read_all_log_trades(LOG_FILES)
    if not trades:
        return pd.DataFrame(
            columns=["timestamp", "buyer", "item_name", "amount", "currency"]
        )
    df = pd.DataFrame(trades)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=client_day_filter)
    return df[df["timestamp"] >= cutoff].sort_values("timestamp")


# ------------- helpers for adding images to cells -------------
# legacy placeholder retained for backward compatibility
BASE_IMAGE_MAP = state.base_image_map
_CATEGORY_WORD_MAP = {
    # Body Armour
    "armour": "Body_Armour",
    "plate": "Body_Armour",
    "jacket": "Body_Armour",
    "coat": "Body_Armour",
    "mail": "Body_Armour",
    "robe": "Body_Armour",
    "vest": "Body_Armour",
    "cuirass": "Body_Armour",
    "mantle": "Body_Armour",
    "garb": "Body_Armour",
    "raiment": "Body_Armour",
    # Boots
    "boots": "Boots",
    "greaves": "Boots",
    "sabatons": "Boots",
    "shoes": "Boots",
    "leggings": "Boots",
    "sandals": "Boots",
    # Gloves
    "gloves": "Gloves",
    "gauntlets": "Gloves",
    "bracers": "Gloves",
    "mitts": "Gloves",
    "cuffs": "Gloves",
    "wraps": "Gloves",
    # Helmet
    "helm": "Helmet",
    "helmet": "Helmet",
    "mask": "Helmet",
    "crown": "Helmet",
    "cap": "Helmet",
    "greathelm": "Helmet",
    "tiara": "Helmet",
    # Jewellery
    "ring": "Ring",
    "amulet": "Amulet",
    "belt": "Belt",
}


def load_base_image_map(path: str):
    _load_base_image_map(state, path)


def find_local_image(item_name: str, root: str) -> Optional[str]:
    return _find_local_image(state, item_name, root)


# Try to render an icon for an item; falls back through defaults safely
def _icon_label(
    parent: ctk.CTkFrame,
    item_name: str,
    target_w: int = 36,
    target_h: int = gui_constants.NAME_ROW_HEIGHT,
) -> Optional[ctk.CTkLabel]:
    return icon_label(state, parent, item_name, target_w=target_w, target_h=target_h, overlay_window=state.overlay)


_MOD_SORT_EPS = 1e-6


def _is_zeroish(value: float) -> bool:
    return is_zeroish(value)


def _is_positiveish(value: float) -> bool:
    return is_positiveish(value)


def _mod_sort_bucket(base_value: float, neighbour_value: float) -> int:
    return helper_mod_sort_bucket(base_value, neighbour_value)


# Render the neighbour comparison rows into the given body frame
def _render_mirror_rows(
    body: ctk.CTkFrame,
    base_series: pd.Series,
    df: pd.DataFrame,
    item_name: str,
    *,
    show_defence_mods: bool = False,
    filters: dict[str, tuple[str, object]] | None = None,
):
    core = list(_CORE_KEYS.keys())
    # Conditionally hide defence patterns: show for jewellery (ring/amulet/belt)
    _SKIP = (set() if show_defence_mods else _HIDE_DEF_PATTERNS) | {
        # never show base/price fields in modifiers list
        "price",
        "Price",
        "currency",
        "Currency",
        "amount",
        "Amount",
        "Cur",
        "cur",
        "price_in_exalts",
        "Price_in_Exalts",
        # raw defence aliases
        "Armour",
        "armour",
        "Evasion",
        "evasion",
        "Evasion Rating",
        "evasion rating",
        "Energy Shield",
        "energy shield",
        "ar",
        "ev",
        "es",
    }

    filters_lookup: dict[str, tuple[str, object]] = {}
    if filters:
        for key, entry in filters.items():
            key_str = str(key)
            filters_lookup[key_str] = entry
            filters_lookup[key_str.lower()] = entry

    def _filter_entry(key: str) -> tuple[str, object] | None:
        entry = filters_lookup.get(key)
        if entry is not None:
            return entry
        return filters_lookup.get(key.lower())

    def _format_filter_label(entry: tuple[str, object] | None, is_core: bool) -> str | None:
        if not entry:
            return None
        op, raw_val = entry
        try:
            if op == "==":
                bound = _fmt_disp(_disp(float(raw_val), is_core))
                return f"={bound}"
            if op == ">=":
                bound = _fmt_disp(_disp(float(raw_val), is_core))
                return f">={bound}"
            if (
                op == "between"
                and isinstance(raw_val, (tuple, list))
                and len(raw_val) == 2
            ):
                lo, hi = raw_val
                lo_f, hi_f = sorted((float(lo), float(hi)))
                lo_txt = _fmt_disp(_disp(lo_f, is_core))
                hi_txt = _fmt_disp(_disp(hi_f, is_core))
                return f"{lo_txt}, {hi_txt}"
        except (TypeError, ValueError):
            return None
        return None

    def _numeric(series: pd.Series, key: str) -> float:
        try:
            return float(series.get(key, 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    def _disp(v: float, is_core: bool) -> float:
        return round(v)

    def _fmt_disp(d: float) -> str:
        return f"{int(d)}" if float(d).is_integer() else f"{d:g}"

    for r, (_, nbr) in enumerate(df.iterrows()):
        # split features: core first, then everything else
        noncore_candidates = sorted((set(base_series.index) | set(nbr.index)) - set(core) - _SKIP)
        noncore_rows = []
        for order_idx, k in enumerate(noncore_candidates):
            b_raw = _numeric(base_series, k)
            n_raw = _numeric(nbr, k)
            b_zero = _is_zeroish(b_raw)
            n_zero = _is_zeroish(n_raw)
            if b_zero and n_zero:
                continue
            bucket = _mod_sort_bucket(b_raw, n_raw)
            noncore_rows.append((bucket, order_idx, k, b_raw, n_raw, b_zero, n_zero))
        noncore_rows.sort(key=lambda entry: (entry[0], entry[1]))

        base_lines = [item_name]
        nbr_lines = [nbr.get("item", "")]

        yellow_l: set[int] = set()
        yellow_r: set[int] = set()
        colours_r: dict[int, str] = {}
        filter_annotations: dict[int, str] = {}

        # ----- core rows first -----
        printed_any_core = False
        for k in core:
            b_raw = _numeric(base_series, k)
            n_raw = _numeric(nbr, k)
            if b_raw == 0 and n_raw == 0:
                continue

            printed_any_core = True
            b_disp = _disp(b_raw, True)
            n_disp = _disp(n_raw, True)

            label = _CORE_KEYS.get(k, k)
            left_txt = f"{label}: {_fmt_disp(b_disp)}"
            right_txt = f"{label}: {_fmt_disp(n_disp)}"

            delta = n_disp - b_disp
            if delta != 0:
                sign = "+" if delta > 0 else ""
                right_txt += f" ({sign}{_fmt_disp(delta)})"
                colours_r[len(nbr_lines)] = "plus" if delta > 0 else "minus"

            filter_label = _format_filter_label(_filter_entry(str(k)), True)
            if filter_label:
                annotation = f"[{filter_label}]"
                right_txt += f" {annotation}"
                filter_annotations[len(nbr_lines)] = annotation
            if (b_raw == 0) ^ (n_raw == 0):
                yellow_l.add(len(base_lines))
                yellow_r.add(len(nbr_lines))

            base_lines.append(left_txt)
            nbr_lines.append(right_txt)

        # one divider after the last printed core row (if any core printed)
        if printed_any_core:
            base_lines.append("--------")
            nbr_lines.append("--------")

        # ----- non-core rows -----
        for _, _, k, b_raw, n_raw, b_zero, n_zero in noncore_rows:
            b_disp = _disp(b_raw, False)
            n_disp = _disp(n_raw, False)

            label = _CORE_KEYS.get(k, k)
            left_txt = f"{label}: {_fmt_disp(b_disp)}"
            right_txt = f"{label}: {_fmt_disp(n_disp)}"

            delta = n_disp - b_disp
            if delta != 0:
                sign = "+" if delta > 0 else ""
                right_txt += f" ({sign}{_fmt_disp(delta)})"
                colours_r[len(nbr_lines)] = "plus" if delta > 0 else "minus"

            filter_label = _format_filter_label(_filter_entry(str(k)), False)
            if filter_label:
                annotation = f"[{filter_label}]"
                right_txt += f" {annotation}"
                filter_annotations[len(nbr_lines)] = annotation
            if b_zero ^ n_zero:
                yellow_l.add(len(base_lines))
                yellow_r.add(len(nbr_lines))

            base_lines.append(left_txt)
            nbr_lines.append(right_txt)

        # neighbour price only
        pr = _price_string(nbr)
        if pr:
            nbr_lines.append("--------")
            nbr_lines.append(f"Price: {pr[0]}")
            colours_r[len(nbr_lines) - 1] = "plus"

        # pad to equal length and compute common height
        pad = max(len(base_lines), len(nbr_lines))
        base_lines += [""] * (pad - len(base_lines))
        nbr_lines += [""] * (pad - len(nbr_lines))
        # Slightly reduce per-line height to match smaller font size
        common_base = max(100, int((pad + 1) * 22))
        common_h = max(20, int(common_base * _KNN_CELL_HEIGHT_FACTOR))

        # left cell
        name_left = base_lines.pop(0)
        f0 = ctk.CTkFrame(body, fg_color="transparent")
        f0.grid(row=r, column=0, sticky="nsew", padx=(6, 4), pady=4)
        f0.columnconfigure(0, weight=1)
        try:
            f0.grid_rowconfigure(0, minsize=_NAME_ROW_H)
        except Exception:
            pass
        hdr0 = ctk.CTkFrame(f0, fg_color="transparent")
        hdr0.grid(row=0, column=0, sticky="nsew")
        try:
            hdr0.columnconfigure(1, weight=1)
        except Exception:
            pass
        lbl0_img = _icon_label(hdr0, name_left, 36)
        if lbl0_img:
            lbl0_img.grid(row=0, column=0, sticky="w", padx=(0, 6))
        name_lbl0 = ctk.CTkLabel(
            hdr0,
            text=f"{name_left} (Your Item)",
            font=("Consolas", 18, "bold"),
            anchor="w",
        )
        name_lbl0.grid(row=0, column=1, sticky="we")
        yellow_l_shift = {i - 1 for i in yellow_l if i > 0}
        _textbox(f0, base_lines, yellow_l_shift, {}, 2, 0, height=common_h)

        # right cell
        name_right = nbr_lines.pop(0)
        f1 = ctk.CTkFrame(body, fg_color="transparent")
        f1.grid(row=r, column=1, sticky="nsew", padx=(4, 6), pady=4)
        f1.columnconfigure(0, weight=1)
        try:
            f1.grid_rowconfigure(0, minsize=_NAME_ROW_H)
        except Exception:
            pass
        hdr1 = ctk.CTkFrame(f1, fg_color="transparent")
        hdr1.grid(row=0, column=0, sticky="nsew")
        try:
            hdr1.columnconfigure(1, weight=1)
        except Exception:
            pass
        lbl1_img = _icon_label(hdr1, name_right, 36)
        if lbl1_img:
            lbl1_img.grid(row=0, column=0, sticky="w", padx=(0, 6))
        name_lbl1 = ctk.CTkLabel(
            hdr1, text=name_right, font=("Consolas", 18, "bold"), anchor="w"
        )
        name_lbl1.grid(row=0, column=1, sticky="we")

        # equalize header heights
        try:
            hdr0.update_idletasks()
            hdr1.update_idletasks()
            name_lbl0.update_idletasks()
            name_lbl1.update_idletasks()
            h_candidates = [_NAME_ROW_H]
            if lbl0_img:
                h_candidates.append(lbl0_img.winfo_reqheight())
            if lbl1_img:
                h_candidates.append(lbl1_img.winfo_reqheight())
            h_candidates.append(name_lbl0.winfo_reqheight())
            h_candidates.append(name_lbl1.winfo_reqheight())
            header_h = max(int(max(h_candidates)), _NAME_ROW_H)
            for fr in (f0, f1):
                fr.grid_rowconfigure(0, minsize=header_h)
            for fr in (hdr0, hdr1):
                fr.configure(height=header_h)
                fr.grid_propagate(False)
        except Exception:
            pass

        yellow_r_shift = {i - 1 for i in yellow_r if i > 0}
        colours_r_shift = {i - 1: v for i, v in colours_r.items() if i > 0}
        filter_tags_shift = {i - 1: v for i, v in filter_annotations.items() if i > 0}
        _textbox(
            f1,
            nbr_lines,
            yellow_r_shift,
            colours_r_shift,
            2,
            0,
            height=common_h,
            filter_tags=filter_tags_shift,
        )



def _bind_overlay_hotkey(custom: str | None) -> None:
    """Bind overlay hotkey to *custom* or default to ctrl+1 with fallback."""
    global _overlay_hotkey_handle

    desired = (custom or "").strip() or DEFAULT_OVERLAY_HOTKEY

    if _overlay_hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_overlay_hotkey_handle)
        except Exception:
            logging.debug("Previous overlay hotkey removal failed", exc_info=True)
        finally:
            _overlay_hotkey_handle = None

    try:
        _overlay_hotkey_handle = keyboard.add_hotkey(
            desired, _handle_hotkey_super, suppress=False
        )
        logging.info("Overlay hotkey bound to %s", desired)
        return
    except Exception as exc:
        logging.error("Failed to bind overlay hotkey %r: %s", desired, exc)

    if desired.lower() != DEFAULT_OVERLAY_HOTKEY:
        try:
            _overlay_hotkey_handle = keyboard.add_hotkey(
                DEFAULT_OVERLAY_HOTKEY, _handle_hotkey_super, suppress=False
            )
            logging.info("Overlay hotkey reverted to %s", DEFAULT_OVERLAY_HOTKEY)
        except Exception as fallback_exc:
            logging.error(
                "Could not bind fallback overlay hotkey %r: %s",
                DEFAULT_OVERLAY_HOTKEY,
                fallback_exc,
            )
            _overlay_hotkey_handle = None
    else:
        _overlay_hotkey_handle = None


def _bind_filtered_overlay_hotkey(custom: str | None) -> None:
    """Bind filtered overlay hotkey to *custom* or the default with fallback."""
    global _filtered_overlay_hotkey_handle

    desired = (custom or "").strip() or DEFAULT_FILTERED_OVERLAY_HOTKEY

    if _filtered_overlay_hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_filtered_overlay_hotkey_handle)
        except Exception:
            logging.debug("Previous filtered overlay hotkey removal failed", exc_info=True)
        finally:
            _filtered_overlay_hotkey_handle = None

    try:
        _filtered_overlay_hotkey_handle = keyboard.add_hotkey(
            desired, _handle_hotkey_filtered, suppress=False
        )
        logging.info("Filtered overlay hotkey bound to %s", desired)
        return
    except Exception as exc:
        logging.error("Failed to bind filtered overlay hotkey %r: %s", desired, exc)

    if desired.lower() != DEFAULT_FILTERED_OVERLAY_HOTKEY:
        try:
            _filtered_overlay_hotkey_handle = keyboard.add_hotkey(
                DEFAULT_FILTERED_OVERLAY_HOTKEY, _handle_hotkey_filtered, suppress=False
            )
            logging.info("Filtered overlay hotkey reverted to %s", DEFAULT_FILTERED_OVERLAY_HOTKEY)
        except Exception as fallback_exc:
            logging.error("Could not bind fallback filtered overlay hotkey %r: %s", DEFAULT_FILTERED_OVERLAY_HOTKEY, fallback_exc)
            _filtered_overlay_hotkey_handle = None
    else:
        _filtered_overlay_hotkey_handle = None


def _bind_discord_api_hotkey(custom: str | None) -> None:
    """Bind Discord API hotkey to *custom* or the default with fallback."""
    global _discord_api_hotkey_handle

    desired = (custom or "").strip() or DEFAULT_DISCORD_API_HOTKEY

    if _discord_api_hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_discord_api_hotkey_handle)
        except Exception:
            logging.debug("Previous Discord API hotkey removal failed", exc_info=True)
        finally:
            _discord_api_hotkey_handle = None

    try:
        _discord_api_hotkey_handle = keyboard.add_hotkey(
            desired, _handle_hotkey_discord_api, suppress=False
        )
        logging.info("Discord API hotkey bound to %s", desired)
        return
    except Exception as exc:
        logging.error("Failed to bind Discord API hotkey %r: %s", desired, exc)

    if desired.lower() != DEFAULT_DISCORD_API_HOTKEY:
        try:
            _discord_api_hotkey_handle = keyboard.add_hotkey(
                DEFAULT_DISCORD_API_HOTKEY, _handle_hotkey_discord_api, suppress=False
            )
            logging.info("Discord API hotkey reverted to %s", DEFAULT_DISCORD_API_HOTKEY)
        except Exception as fallback_exc:
            logging.error(
                "Could not bind fallback Discord API hotkey %r: %s",
                DEFAULT_DISCORD_API_HOTKEY,
                fallback_exc,
            )
            _discord_api_hotkey_handle = None
    else:
        _discord_api_hotkey_handle = None


# ------------- UNSUPERVISED overlay (“Price Mirror”) ----
def _show_unsuper_overlay(
    base_X: pd.DataFrame, df: pd.DataFrame, item_name: str
) -> None:
    """
    Unsupervised "Price Mirror" overlay.

    - OUTER-joins mods (value 0 shown when missing)
    - Rows where both sides are 0 are dropped
    - Core block (ES/AR/EV) is from *_NORM, rounded; dashed separator kept
    - If exactly one side is zero and the other > 0, both cells are yellow
    - +/- (green/red) is computed after rounding so numbers match
    - Left column never shows a price line
    - Flat and % defence modifiers are hidden; already encoded in *_NORM
    """
    global overlay, root
    if not (root and root.winfo_exists()):
        return

    _destroy_overlay()
    overlay = ctk.CTkToplevel(root)
    state.overlay = overlay
    overlay.images = []
    try:
        _ico = str(Path(__file__).with_name("stashsage_logo.ico"))
        overlay.iconbitmap(_ico)
    except Exception:
        pass
    overlay.title("Price Mirror")
    overlay.bind("<Escape>", lambda _e: _destroy_overlay())
    overlay.attributes("-topmost", True)
    overlay.after_idle(lambda: overlay.attributes("-topmost", False))

    # header
    cont = ctk.CTkFrame(overlay, corner_radius=10)
    cont.pack(fill="both", expand=True, padx=8, pady=8)
    cont.columnconfigure((0, 1), weight=1)
    cont.rowconfigure(6, weight=1)

    pf = state.config.get("price_mirror_filter", DEFAULT_PRICE_FILTER)
    title_txt = f"Based on {knn_k} Nearest Items (Ordered) with Price Filter {pf}:"
    tags, vals = [], []
    for _, row in df.iterrows():
        simple = _price_simple(row)
        if simple:
            tags.append(simple)
        pr = _price_string(row)
        if pr:
            vals.append(pr[1])
        if len(tags) == knn_k:
            break

    if vals:
        mean_e = float(np.mean(vals))
        med_e = float(np.median(vals))
        dash = " - "
        stats = f"Price Prediction from Nearest Items{dash}Mean = {_triple(mean_e)}{dash}Median = {_triple(med_e)}"
        ctk.CTkLabel(
            cont, text=stats, font=("Consolas", 21, "bold"), text_color="#FFD700"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

    combined = f"{title_txt} [{', '.join(tags)}]"
    ctk.CTkLabel(cont, text=combined, font=("Consolas", 19), text_color="#CCCCCC").grid(
        row=1, column=0, columnspan=2, sticky="ew"
    )

    # body
    body = ctk.CTkFrame(cont, fg_color="transparent")
    body.grid(row=6, column=0, columnspan=2, sticky="nsew")
    body.columnconfigure((0, 1), weight=1)
    base_series = base_X.iloc[0]
    _render_mirror_rows(body, base_series, df, item_name, show_defence_mods=False)

    # window geometry
    overlay.update_idletasks()
    sw, sh = overlay.winfo_screenwidth(), overlay.winfo_screenheight()
    w = min(1800, overlay.winfo_reqwidth() + 400)
    h = min(1000, overlay.winfo_reqheight() + 20)
    overlay.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")
    overlay.minsize(1200, 500)



# ------------- SUPERVISED overlay (charts) ---------------
def _show_super_overlay(
    item: str,
    price_buf: io.BytesIO | None,
    table_buf: io.BytesIO | None,
    conf_buf: io.BytesIO | None,
    bucket_label: str | None,
    bucket_median: float | None,
    bucket_low: float | None,
    bucket_high: float | None,
    debug_text: str,
) -> None:
    global overlay, root
    if not (root and root.winfo_exists()):
        return

    _destroy_overlay()
    overlay = ctk.CTkToplevel(root)
    state.overlay = overlay
    overlay.images = []
    ov = overlay
    # Set window icon to match main app (Windows-friendly ICO)
    try:
        _ico = str(Path(__file__).with_name("stashsage_logo.ico"))
        ov.iconbitmap(_ico)
    except Exception:
        pass

    ov.title(f"Offer History and Price Aura - {item}")
    ov.bind("<Escape>", lambda _e: _destroy_overlay())
    ov.attributes("-topmost", True)
    ov.after_idle(lambda: ov.attributes("-topmost", False))

    grid = ctk.CTkFrame(ov, corner_radius=10)
    grid.pack(fill="both", expand=True, padx=8, pady=8)
    grid.columnconfigure(0, weight=1)
    for r in range(3):
        grid.rowconfigure(r, weight=1)

    if price_buf:
        _scaled_png_percent(grid, price_buf, 0.5).grid(
            row=0, column=0, sticky="nsew", padx=4, pady=4
        )

    if table_buf:
        _scaled_png_percent(grid, table_buf, 0.5).grid(
            row=1, column=0, sticky="nsew", padx=4, pady=4
        )

    bottom = ctk.CTkFrame(grid, fg_color="transparent")
    bottom.grid(row=2, column=0, sticky="nsew")
    bottom.columnconfigure(0, weight=1)

    if conf_buf:
        _add_png_to_ctklabel(bottom, conf_buf).pack(
            fill="both", expand=True, padx=4, pady=4
        )
    if bucket_label:
        _bucket_badge(bottom, bucket_label, bucket_median, bucket_low, bucket_high)

    # window hugs the native PNG size
    ov.update_idletasks()
    sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
    w = min(ov.winfo_reqwidth(), int(sw * 0.96))
    h = min(ov.winfo_reqheight(), int(sh * 0.96))
    ov.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")
    ov.minsize(w, h)


# ————————————————————————————————————————————————————————————————————————————
# CONSOLIDATED DASHBOARD overlay (Ctrl+1 / Ctrl+0):
#  Top: supervised charts laid out horizontally in a single row
#       (price chart | offers table | confidence plot | bucket badge)
#  Bottom: unsupervised Price Mirror section (existing Ctrl+2 content)
# ————————————————————————————————————————————————————————————————————————————
def _show_dashboard_overlay(
    item: str,
    price_buf: io.BytesIO | None,
    table_buf: io.BytesIO | None,
    conf_buf: io.BytesIO | None,
    bucket_label: str | None,
    bucket_median: float | None,
    bucket_low: float | None,
    bucket_high: float | None,
    display_pred_value: float | None,
    category_title: str | None,
    cat_norm: str | None,
    seg_norm: str | None,
    unsuper_X: Optional[pd.DataFrame],
    unsuper_df: Optional[pd.DataFrame],
    unsuper_item_name: str,
    filters: dict[str, tuple[str, object]] | None = None,
) -> None:
    global overlay, root
    if not (root and root.winfo_exists()):
        return

    _destroy_overlay()
    overlay = ctk.CTkToplevel(root)
    state.overlay = overlay
    overlay.images = []
    ov = overlay
    # Set window icon to match main app (Windows-friendly ICO)
    try:
        _ico = str(Path(__file__).with_name("stashsage_logo.ico"))
        ov.iconbitmap(_ico)
    except Exception:
        pass

    ov.title(f"StashSage Price Predictions — {item}")
    ov.bind("<Escape>", lambda _e: _destroy_overlay())
    ov.attributes("-topmost", True)
    ov.after_idle(lambda: ov.attributes("-topmost", False))

    # Container grid
    # Use a scrollable frame so long content can be scrolled via sidebar
    cont = ctk.CTkScrollableFrame(ov, corner_radius=10)
    cont.pack(fill="both", expand=True, padx=8, pady=8)
    # Three stacked areas: (0) two side-by-side boxes, (1) one horizontal color bar, (2) KNN mirror
    cont.grid_rowconfigure(0, weight=0)
    # Rows: 0=top charts, 1=bar #1, 2=dist plot, 3=bar #2, 4=unsuper mirror
    cont.grid_rowconfigure(1, weight=0)
    cont.grid_rowconfigure(2, weight=0)
    cont.grid_rowconfigure(3, weight=0)
    cont.grid_rowconfigure(4, weight=1)
    cont.grid_columnconfigure((0, 1), weight=1)

    # Row 0: (dropped) top charts removed per request

    # Row 1: Price Prediction #1 bar (dataset)
    if bucket_label and isinstance(display_pred_value, (int, float)):
        badge1_holder = ctk.CTkFrame(cont, fg_color="transparent")
        badge1_holder.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        _bucket_badge(
            badge1_holder,
            bucket_label,
            bucket_median,
            bucket_low,
            bucket_high,
            display_pred_value,
            None,
            None,
            None,
            mode="dataset",
            category_title=(
                category_title or (cat_norm or "").replace("_", " ").title()
            ),
            dataset_pred_value=display_pred_value,
        )

    # Row 2: predicted distribution overlay (prefer JSON; fallback to pre-rendered PNG)
    try:
        dist_buf = None
        dynamic_done = False
        marker_val = display_pred_value

        if cat_norm:
            model_dir = Path(poe2trade_root) / "db" / "super_models"

            # If armour and we have features, infer the segment from ar/ev/es
            if (
                cat_norm in ("body_armour", "helmet", "gloves", "boots")
                and isinstance(unsuper_X, pd.DataFrame)
                and not unsuper_X.empty
            ):
                try:
                    row0 = unsuper_X.iloc[0]
                    ar = float(row0.get("ar_norm", 0) or 0) > 0
                    ev = float(row0.get("ev_norm", 0) or 0) > 0
                    es = float(row0.get("es_norm", 0) or 0) > 0
                    if ar and not (ev or es):
                        seg_norm = "ar_only"
                    elif ev and not (ar or es):
                        seg_norm = "ev_only"
                    elif es and not (ar or ev):
                        seg_norm = "es_only"
                    elif ar and ev and not es:
                        seg_norm = "ar_ev_only"
                    elif ar and es and not ev:
                        seg_norm = "ar_es_only"
                    elif ev and es and not ar:
                        seg_norm = "ev_es_only"
                    elif ar and ev and es:
                        seg_norm = "all_three"
                except Exception:
                    pass

            # Build candidate lists (JSON preferred; XLSX as dynamic fallback; PNG last).
            json_candidates: list[Path] = []
            xlsx_candidates: list[Path] = []
            png_candidates: list[Path] = []

            if seg_norm:
                # Armour: <category>_<segment>
                json_candidates.append(
                    model_dir / f"{cat_norm}_{seg_norm}_scoring.json"
                )
                xlsx_candidates.append(
                    model_dir / f"{cat_norm}_{seg_norm}_scoring.xlsx"
                )
                png_candidates.append(
                    model_dir / f"{cat_norm}_{seg_norm}_price_dists.png"
                )
                # US spelling fallback for body armour
                if cat_norm == "body_armour":
                    json_candidates.append(
                        model_dir / f"body_armor_{seg_norm}_scoring.json"
                    )
                    xlsx_candidates.append(
                        model_dir / f"body_armor_{seg_norm}_scoring.xlsx"
                    )
                    png_candidates.append(
                        model_dir / f"body_armor_{seg_norm}_price_dists.png"
                    )
            else:
                # Jewellery: single global file
                json_candidates.append(model_dir / f"{cat_norm}_scoring.json")
                xlsx_candidates.append(model_dir / f"{cat_norm}_scoring.xlsx")
                png_candidates.append(model_dir / f"{cat_norm}_price_dists.png")
                # Some runs may include kind in the filename
                for kind in ("ring", "amulet", "belt"):
                    json_candidates.append(
                        model_dir / f"{cat_norm}_{kind}_scoring.json"
                    )
                    xlsx_candidates.append(
                        model_dir / f"{cat_norm}_{kind}_scoring.xlsx"
                    )
                    png_candidates.append(
                        model_dir / f"{cat_norm}_{kind}_price_dists.png"
                    )

            # Try JSON first (fast & dynamic so we can place the marker)
            json_path = next((p for p in json_candidates if p.is_file()), None)
            if json_path is not None:
                try:
                    df_scored = _load_scoring_json_once(json_path)
                    if isinstance(df_scored, pd.DataFrame) and not df_scored.empty:
                        dist_buf = generate_predicted_overlay_with_marker(
                            df_scored,
                            marker_val,
                            title=f"{cat_norm}{('/' + seg_norm) if seg_norm else ''} — Predicted Distributions",
                        )
                        dynamic_done = True
                except Exception:
                    dynamic_done = False

            # Fallback #1: XLSX (dynamic marker via parsed Excel)
            if not dynamic_done:
                xlsx_path = next((p for p in xlsx_candidates if p.is_file()), None)
                if xlsx_path is not None:
                    try:
                        df_scored = pd.read_excel(xlsx_path)
                        if isinstance(df_scored, pd.DataFrame) and not df_scored.empty:
                            dist_buf = generate_predicted_overlay_with_marker(
                                df_scored,
                                marker_val,
                                title=f"{cat_norm}{('/' + seg_norm) if seg_norm else ''} — Predicted Distributions",
                            )
                            dynamic_done = True
                    except Exception:
                        dynamic_done = False

            # Fallback #2: pre-rendered PNG (no dynamic marker)
            if not dynamic_done:
                png_path = next((p for p in png_candidates if p.is_file()), None)
                if png_path is not None:
                    with open(png_path, "rb") as f:
                        dist_buf = io.BytesIO(f.read())

        if dist_buf:
            # Shrink distribution image display by ~30%
            _scaled_png_percent(cont, dist_buf, 0.525).grid(
                row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=4
            )
        else:
            ctk.CTkLabel(
                cont,
                text="Score Distribution: not available for this item",
                font=("Helvetica", 18, "bold"),
            ).grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)

    except Exception:
        ctk.CTkLabel(
            cont,
            text="Score Distribution: error loading image",
            font=("Helvetica", 18, "bold"),
        ).grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)

    # Row 3: Price Prediction #2 bar (nearest items)
    # Precompute nearest stats and combined price line if data present
    nearest_mean = nearest_median = None
    combined_line = None
    pf = state.config.get("price_mirror_filter", DEFAULT_PRICE_FILTER)
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty:
        tags, vals = [], []
        for _, row in unsuper_df.iterrows():
            simple = _price_simple(row)
            if simple:
                tags.append(simple)
            pr = _price_string(row)
            if pr:
                vals.append(pr[1])
            if len(tags) == knn_k:
                break
        if vals:
            nearest_mean = float(np.mean(vals))
            nearest_median = float(np.median(vals))
        combined_line = f"Based on {knn_k} Nearest Items (Ordered) with Price Filter {pf}: [{', '.join(tags)}]"

    if bucket_label and (nearest_mean is not None or nearest_median is not None):
        badge2_holder = ctk.CTkFrame(cont, fg_color="transparent")
        badge2_holder.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        _bucket_badge(
            badge2_holder,
            bucket_label,
            bucket_median,
            bucket_low,
            bucket_high,
            None,
            nearest_mean,
            nearest_median,
            combined_line,
            mode="nearest",
        )

    # (combined single-bar UI removed in favor of two separate bars)

    # Row 4: Unsupervised mirror (existing layout), only if data present
    if (
        isinstance(unsuper_df, pd.DataFrame)
        and not unsuper_df.empty
        and unsuper_X is not None
    ):
        # === Header ===
        cont2 = ctk.CTkFrame(cont, corner_radius=10)
        cont2.grid(row=4, column=0, columnspan=2, sticky="nsew")
        cont2.columnconfigure((0, 1), weight=1)
        cont2.rowconfigure(6, weight=1)

        # Header lines (stats and price list) are now shown inside the bar; omit here

        # ctk.CTkLabel(cont2, text="Your Item",
        #              font=("Consolas", 20, "bold"))\
        #     .grid(row=4, column=0, sticky="s")
        # ctk.CTkLabel(cont2, text="Similar Item",
        #              font=("Consolas", 20, "bold"))\
        #     .grid(row=4, column=1, sticky="s")

        # === Body === (refactored via helper)
        body = ctk.CTkFrame(cont2, fg_color="transparent")
        body.grid(row=5, column=0, columnspan=2, sticky="nsew")
        body.columnconfigure((0, 1), weight=1)
        base_series = unsuper_X.iloc[0]
        # Enable defence modifiers for jewellery so they show in overlay
        cat_lc = (cat_norm or "").strip().lower()
        show_defs = cat_lc in ("ring", "amulet", "belt")
        _render_mirror_rows(
            body,
            base_series,
            unsuper_df,
            unsuper_item_name,
            show_defence_mods=show_defs,
            filters=filters,
        )

    # window geometry — start large enough by default, within screen bounds
    ov.update_idletasks()
    sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
    # Reduce default width by ~20% (from 90% to 72% of screen; 1600 ? 1280 cap)
    default_w = min(int(sw * 0.72), 1280)
    default_h = min(int(sh * 0.90), 900)
    ov.geometry(f"{default_w}x{default_h}+{(sw - default_w)//2}+{(sh - default_h)//2}")
    ov.minsize(960, 700)


# ------------- ML pipelines ? overlays -------------------
# (removed: separate unsuper overlay launcher)


def _score_dashboard_async(text: str) -> None:
    """
    Run both pipelines (supervised + unsupervised) off the UI thread,
    then hand the finished buffers/data back to the main loop.
    """
    # (a) Optional: show busy cursor immediately
    try:
        root.after(0, lambda: root.configure(cursor="watch"))
    except Exception:
        pass

    def work():
        try:
            # ---------- HEAVY WORK (off UI thread) ----------
            ml_super = gui_utils_main(text, key="super") or {}
            parsed = parse_copied_item_text(text)

            unsuper = gui_utils_main(text, key="unsuper")
            if unsuper:
                unsuper_X, unsuper_df = unsuper
            else:
                unsuper_X = unsuper_df = None

            # Derive category/segment safely here
            raw_cat = (
                str(parsed.get("Item Category", "default_model"))
                .lower()
                .replace(" ", "_")
            )
            raw_cat = {"boot": "boots", "glove": "gloves"}.get(raw_cat, raw_cat)
            cat_norm = raw_cat or "default_model"
            # For Jewels, switch category to the concrete subtype so scoring JSON resolves
            if cat_norm == 'jewel':
                try:
                    raw_lc = (text or '').lower()
                    jt = next((j for j in (jewel_list or []) if re.search(rf"\b{re.escape(j)}\b", raw_lc, flags=re.I)), None)
                    if jt:
                        cat_norm = jt
                except Exception:
                    pass
            seg_norm = ml_super.get("segment") if isinstance(ml_super, dict) else None
            if not seg_norm:
                try:
                    _c, _s = detect_category_segment(parsed)
                    seg_norm = _s
                except Exception:
                    seg_norm = None

            (
                display_value,
                bucket_label,
                bucket_low,
                bucket_high,
                bucket_median_val,
                intervals,
                conf_buf,
            ) = _extract_supervised_values(ml_super, cat_norm=cat_norm, seg_norm=seg_norm)

            # Names
            item_name = (
                ml_super.get("item_name") or _parse_item(text) or "(Unknown item)"
            )
            unsuper_item_name = parsed.get("Item Name", "(Unknown)")
            try:
                if str(parsed.get('Item Category','')).strip().lower() == 'jewel':
                    raw = (text or '').lower()
                    jt = next((j for j in (jewel_list or []) if re.search(rf"\b{re.escape(j)}\b", raw, flags=re.I)), None)
                    if jt and jt.title() not in unsuper_item_name:
                        unsuper_item_name = (unsuper_item_name + (" " if unsuper_item_name else "") + jt.title()).strip()
            except Exception:
                pass

            # ---------- UI HANDOFF (Tk main thread only) ----------
            def _show():
                try:
                    _show_dashboard_overlay(
                        item_name,
                        None,
                        None,  # price_buf, table_buf (unused)
                        conf_buf,
                        bucket_label,
                        bucket_median_val,
                        bucket_low,
                        bucket_high,
                        display_value,
                        (cat_norm or "").replace("_", " ").title(),
                        cat_norm,
                        seg_norm,
                        unsuper_X,
                        unsuper_df,
                        unsuper_item_name,
                    )
                finally:
                    try:
                        root.configure(cursor="")
                    except Exception:
                        pass

            root.after(0, _show)

        except Exception as exc:
            # Surface any errors on the UI thread
            def _err():
                try:
                    root.configure(cursor="")
                except Exception:
                    pass
                messagebox.showerror("StashSage", f"Scoring failed:\n{exc}")

            root.after(0, _err)

    threading.Thread(target=work, daemon=True).start()


def _process_super_gui(text: str) -> None:
    ml = gui_utils_main(text, key="super") or {}
    item = ml.get("item_name") or _parse_item(text) or "(Unknown item)"

    parsed = parse_copied_item_text(text)
    raw_cat = (
        str(parsed.get("Item Category", "default_model")).lower().replace(" ", "_")
    )
    raw_cat = {"boot": "boots", "glove": "gloves"}.get(raw_cat, raw_cat)
    cat_norm = raw_cat or "default_model"
    seg_norm = ml.get("segment") if isinstance(ml, dict) else None
    if not seg_norm:
        try:
            _c, _s = detect_category_segment(parsed)
            seg_norm = _s
        except Exception:
            seg_norm = None

    (
        display_value,
        bucket_lbl,
        bucket_low,
        bucket_high,
        bucket_median,
        intervals,
        conf_buf,
    ) = _extract_supervised_values(ml, cat_norm=cat_norm, seg_norm=seg_norm)

    _show_super_overlay(
        item,
        None,
        None,
        conf_buf,
        bucket_lbl,
        bucket_median,
        bucket_low,
        bucket_high,
        "",
    )


def _process_dashboard_gui(text: str) -> None:
    """Build consolidated dashboard: super (top row) + unsuper (bottom)."""
    ml = gui_utils_main(text, key="super") or {}
    item = ml.get("item_name") or _parse_item(text) or "(Unknown item)"

    parsed = parse_copied_item_text(text)
    unsuper_item_name = parsed.get("Item Name", "(Unknown)")
    raw_cat = (
        str(parsed.get("Item Category", "default_model")).lower().replace(" ", "_")
    )
    raw_cat = {"boot": "boots", "glove": "gloves"}.get(raw_cat, raw_cat)
    cat_norm = raw_cat or "default_model"
    seg_norm = ml.get("segment") if isinstance(ml, dict) else None
    if not seg_norm:
        try:
            _c, _s = detect_category_segment(parsed)
            seg_norm = _s
        except Exception:
            seg_norm = None

    (
        display_value,
        bucket_lbl,
        bucket_low,
        bucket_high,
        bucket_median_val,
        intervals,
        _conf_unused,
    ) = _extract_supervised_values(ml, cat_norm=cat_norm, seg_norm=seg_norm)

    price_buf = None
    table_buf = None
    conf_buf = None
    if intervals and bucket_lbl:
        try:
            conf_buf = generate_bucket_confidence_plot(
                pred_median=(
                    display_value if isinstance(display_value, (int, float)) else 0.0
                ),
                intervals=intervals,
                bucket_label=bucket_lbl or "Unknown",
                width=IMG_W,
                height=IMG_H * 0.9,
            )
        except Exception:
            conf_buf = None

    result = gui_utils_main(text, key="unsuper")
    if result:
        unsuper_X, unsuper_df = result
    else:
        unsuper_X, unsuper_df = None, None

    _show_dashboard_overlay(
        item,
        price_buf,
        table_buf,
        conf_buf,
        bucket_lbl,
        bucket_median_val,
        bucket_low,
        bucket_high,
        display_value,
        (cat_norm or "").replace("_", " ").title(),
        cat_norm,
        seg_norm,
        unsuper_X,
        unsuper_df,
        unsuper_item_name,
    )


def _handle_hotkey_super(_=None):
    keyboard.press_and_release("ctrl+c")
    root.after(
        200,
        lambda: _run_with_lock(
            _hotkey_busy["super"], _score_dashboard_async, pyperclip.paste()
        ),
    )


def _handle_hotkey_filtered(_=None):
    keyboard.press_and_release("ctrl+c")
    root.after(
        200,
        lambda: _run_with_lock(
            _hotkey_busy["filtered"], _start_filtered_overlay_async, pyperclip.paste()
        ),
    )


def _start_discord_api_send_async(text: str) -> None:
    def worker() -> None:
        try:
            # Ensure services are running if possible
            _enable_services_if_ready(state.config)
            url = "http://127.0.0.1:5005/dm-item-prediction-json"
            res = requests.post(url, json={"item_text": text}, timeout=15)
            logging.info("Discord API DM -> %s %s", res.status_code, res.text[:300])
        except Exception:
            logging.exception("Discord API DM failed")

    threading.Thread(target=worker, daemon=True).start()


def _handle_hotkey_discord_api(_=None):
    keyboard.press_and_release("ctrl+c")
    root.after(
        200,
        lambda: _run_with_lock(
            _hotkey_busy["discord_api"], _start_discord_api_send_async, pyperclip.paste()
        ),
    )





# ------------- GUI widgets & helpers (unchanged) ---------
def _browse_for_client(entry: ctk.CTkEntry) -> None:
    fpath = filedialog.askopenfilename(
        title="Select PoE client.txt log",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    if fpath:
        entry.delete(0, "end")
        entry.insert(0, fpath)


class _CollapsibleSection(ctk.CTkFrame):
    def __init__(self, parent, title: str, *, collapsed: bool = False, on_toggle: Callable[[], None] | None = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self._title = title
        self._collapsed = True
        self._on_toggle = on_toggle

        self._header_btn = ctk.CTkButton(
            self,
            text="",
            command=self.toggle,
            anchor="w",
            height=36,
            corner_radius=8,
            font=("Segoe UI", 16, "bold"),
        )
        self._header_btn.pack(fill="x", padx=10, pady=(12, 6))
        self._header_btn.configure(cursor="hand2")

        self.content = ctk.CTkFrame(self, fg_color="transparent")

        if collapsed:
            self._update_header_text()
            self._notify()
        else:
            self._show_content(initial=True)

    def toggle(self) -> None:
        if self._collapsed:
            self._show_content()
        else:
            self._hide_content()

    def _show_content(self, initial: bool = False) -> None:
        if not self._collapsed and not initial:
            return
        self.content.pack(fill="x", padx=10, pady=(0, 6))
        self._collapsed = False
        self._update_header_text()
        self._notify()

    def _hide_content(self) -> None:
        if self._collapsed:
            return
        self.content.pack_forget()
        self._collapsed = True
        self._update_header_text()
        self._notify()

    def _update_header_text(self) -> None:
        # Simple ASCII indicator to avoid font issues
        indicator = "[-]" if not self._collapsed else "[+]"
        self._header_btn.configure(text=f"{indicator} {self._title}")

    def _notify(self) -> None:
        if self._on_toggle:
            try:
                self._on_toggle()
            except Exception:
                pass

def _entry(
    parent, label, default="", digits_only=False, allow_float=False
) -> ctk.CTkEntry:
    ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=10, pady=(10, 2))
    if digits_only and allow_float:
        raise ValueError("Use either digits_only or allow_float, not both")

    def _check(P: str) -> bool:
        if P == "":
            return True
        if digits_only:
            return P.isdigit()
        if allow_float:
            return re.fullmatch(r"\s*\d*\.?\d*\s*[ecdECD]?", P) is not None
        return True

    e = ctk.CTkEntry(parent, corner_radius=6)
    vcmd = parent.register(_check)
    e.configure(validate="key", validatecommand=(vcmd, "%P"))
    e.pack(fill="x", padx=10, pady=2, expand=True)
    e.insert(0, default)
    return e


def _file_row(parent, label, default="") -> tuple[ctk.CTkEntry, ctk.CTkButton]:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=10, pady=(10, 2))
    ctk.CTkLabel(frame, text=label).pack(anchor="w")
    inner = ctk.CTkFrame(frame, fg_color="transparent")
    inner.pack(fill="x")
    entry = ctk.CTkEntry(inner, corner_radius=6)
    entry.pack(side="left", fill="x", expand=True, pady=2)
    btn = ctk.CTkButton(
        inner, text="Browse…", width=90, command=lambda e=entry: _browse_for_client(e)
    )
    btn.pack(side="left", padx=6, pady=2)
    entry.insert(0, default)
    return entry, btn


def _refresh_log_files(cfg: dict) -> None:
    global LOG_FILES
    typ = cfg.get("client_type", "steam")
    path = cfg.get(
        "steam_client_log_dir" if typ == "steam" else "ggg_client_log_dir", ""
    )
    LOG_FILES = [path] if Path(path).is_file() else []
    logging.info("Log files set: %s", LOG_FILES)


def _enable_services_if_ready(cfg: dict) -> None:
    """Start background services when the supplied config has enough data."""
    global SERVICES_STARTED
    if SERVICES_STARTED:
        return
    token = cfg.get("discord_bot_token", "").strip()
    user_id = cfg.get("discord_user_id", "").strip()
    if not (token and user_id and LOG_FILES):
        return
    try:
        start_services(cfg)
        SERVICES_STARTED = True
        logging.info("Discord Flask + background services started.")
    except Exception as exc:
        logging.exception("Could not start Discord services: %s", exc)


def _on_client_toggle(choice: str) -> None:
    if choice == "steam":
        steam_entry.configure(state="normal")
        steam_browse_btn.configure(state="normal")
        ggg_entry.configure(state="disabled")
        ggg_browse_btn.configure(state="disabled")
    else:
        steam_entry.configure(state="disabled")
        steam_browse_btn.configure(state="disabled")
        ggg_entry.configure(state="normal")
        ggg_browse_btn.configure(state="normal")


# ????????????? save & reload (stores price filter) ??????
def save_and_reload() -> None:
    """Persist the current form values and refresh bindings/services."""
    pf_raw = price_filter_entry.get().strip() or str(DEFAULT_PRICE_FILTER)
    if not PRICE_FILTER_RE.fullmatch(pf_raw):
        messagebox.showerror(
            "Invalid Price Filter",
            "Must be a number followed by E, C, or D (e.g. 100e, 50c, 10D)",
        )
        return
    state.config.update(
        client_type=client_choice.get(),
        steam_client_log_dir=steam_entry.get().strip(),
        ggg_client_log_dir=ggg_entry.get().strip(),
        discord_user_id=discord_id_entry.get().strip(),
        discord_bot_token=discord_token_entry.get().strip(),
        price_mirror_filter=pf_raw,
        custom_hotkey=(
            custom_hotkey_entry.get().strip() if custom_hotkey_entry else ""
        ),
        filtered_overlay_hotkey=(
            filtered_hotkey_entry.get().strip() if filtered_hotkey_entry else ""
        ),
        discord_api_hotkey=(
            discord_api_hotkey_entry.get().strip() if discord_api_hotkey_entry else ""
        ),
    )
    config_manager.save_config(state.config)
    _apply_price_filter(state.config)
    update_config(state.config)
    _bind_overlay_hotkey(state.config.get("custom_hotkey"))
    _bind_filtered_overlay_hotkey(state.config.get("filtered_overlay_hotkey"))
    _bind_discord_api_hotkey(state.config.get("discord_api_hotkey"))
    # _refresh_log_files(state.config)
    _enable_services_if_ready(state.config)
    _auto_resize_root()
    messagebox.showinfo("StashSage", "Settings saved & reloaded!")


# ????????????? main Tk entry-point ???????????????????????
def run_tkinter_app(cfg: Optional[dict] = None) -> None:
    """Launch the CustomTkinter settings window."""
    global root, steam_entry, ggg_entry, steam_browse_btn, ggg_browse_btn
    global discord_id_entry, discord_token_entry, price_filter_entry, filtered_hotkey_entry, discord_api_hotkey_entry
    global client_choice, custom_hotkey_entry

    state.update_config(cfg or {})
    _apply_price_filter(state.config)

    # ?? NEW: preload the icon lookup once at startup
    try:
        load_base_image_map(f"{poe2trade_root}/db/files/base_images.json")
        logging.info("base_images.json loaded (%d entries)", len(state.base_image_map))
    except Exception as exc:
        logging.warning("Could not load base_images.json: %s", exc)

    root = ctk.CTk()
    state.root = root
    root.title(f"StashSage for POE2 (v{__version__} -- {BUILD_DATE})")
    root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    icon_path = str(Path(__file__).with_name("stashsage_logo.ico"))
    root.iconbitmap(icon_path)
    # Also set a default iconphoto to propagate to child windows where supported
    try:
        png_path = Path(poe2trade_root) / "docs" / "stashsage_logo.png"
        if png_path.is_file():
            _img = tk.PhotoImage(file=str(png_path))
            root.iconphoto(True, _img)
            root._icon_img = _img  # keep a reference
    except Exception:
        pass

    _bind_overlay_hotkey(state.config.get("custom_hotkey"))
    _bind_filtered_overlay_hotkey(state.config.get("filtered_overlay_hotkey"))
    _bind_discord_api_hotkey(state.config.get("discord_api_hotkey"))

    general_section = _CollapsibleSection(root, "General Settings", on_toggle=_auto_resize_root)
    general_section.pack(fill="x", expand=False)

    custom_hotkey_entry = _entry(
        general_section.content,
        "Overlay Hotkey (e.g. ctrl+shift+4)",
        state.config.get("custom_hotkey", "").strip(),
    )
    state.custom_hotkey_entry = custom_hotkey_entry

    filtered_hotkey_entry = _entry(
        general_section.content,
        "Filtered Overlay Hotkey (e.g. ctrl+2)",
        (state.config.get("filtered_overlay_hotkey", "") or "").strip()
        or DEFAULT_FILTERED_OVERLAY_HOTKEY,
    )
    state.filtered_hotkey_entry = filtered_hotkey_entry

    price_filter_entry = _entry(
        general_section.content,
        "Nearest Items Price Filter (e.g. 40E, 100d, 20c)",
        str(state.config.get("price_mirror_filter", DEFAULT_PRICE_FILTER)),
        allow_float=True,
    )
    state.price_filter_entry = price_filter_entry
    # conversion hint (rounded whole integers) - start from 1 divine
    try:
        c_per_d = int(round(float(divine_exalt) / max(float(chaos_exalt), 1e-9)))
        e_per_d = int(round(float(divine_exalt)))
        hint = f"(*) Conversion rate used 1 d = {c_per_d} c = {e_per_d} e"
    except Exception:
        hint = "(*) 1 d = ? c = ? e"
    ctk.CTkLabel(
        general_section.content,
        text=hint,
        text_color="#AAAAAA",
        font=("Consolas", 12, "bold"),
    ).pack(pady=(0, 10))

    discord_section = _CollapsibleSection(root, "Discord Bot Settings", on_toggle=_auto_resize_root)
    discord_section.pack(fill="x", expand=False)

    discord_id_entry = _entry(
        discord_section.content,
        "Discord User ID",
        state.config.get("discord_user_id", "").strip(),
        digits_only=True,
    )
    state.discord_id_entry = discord_id_entry
    discord_token_entry = _entry(
        discord_section.content,
        "Discord Bot Token",
        state.config.get("discord_bot_token", "").strip(),
    )
    state.discord_token_entry = discord_token_entry

    discord_api_hotkey_entry = _entry(
        discord_section.content,
        "Discord API Hotkey (e.g. ctrl+3)",
        (state.config.get("discord_api_hotkey", "") or "").strip()
        or DEFAULT_DISCORD_API_HOTKEY,
    )
    state.discord_api_hotkey_entry = discord_api_hotkey_entry

    # client radio buttons
    client_choice = ctk.StringVar(value=state.config.get("client_type", "steam"))
    state.client_choice = client_choice
    sel = ctk.CTkFrame(discord_section.content, corner_radius=8)
    sel.pack(pady=10, padx=10, fill="x")
    ctk.CTkLabel(sel, text="Choose Logs Client:").pack(anchor="w", padx=6, pady=(6, 2))
    for key, caption in (("steam", "Steam"), ("ggg", "GGG")):
        ctk.CTkRadioButton(
            sel,
            text=caption,
            variable=client_choice,
            value=key,
            command=lambda c=key: _on_client_toggle(c),
        ).pack(side="left", padx=10, pady=6)

    steam_entry, steam_browse_btn = _file_row(
        discord_section.content,
        "Steam Log Location",
        state.config.get("steam_client_log_dir", "") or DEFAULT_STEAM,
    )
    state.steam_entry = steam_entry
    state.steam_browse_btn = steam_browse_btn
    ggg_entry, ggg_browse_btn = _file_row(
        discord_section.content,
        "GGG Log Location",
        state.config.get("ggg_client_log_dir", "") or DEFAULT_GGG,
    )
    state.ggg_entry = ggg_entry
    state.ggg_browse_btn = ggg_browse_btn
    _on_client_toggle(client_choice.get())

    button_row = ctk.CTkFrame(root, fg_color="transparent")
    button_row.pack(fill="x", padx=10, pady=14)
    ctk.CTkButton(
        button_row,
        text="Update Settings & Reload",
        command=save_and_reload,
        corner_radius=8,
    ).pack(side="left", expand=True, fill="x", padx=(0, 8))
    ctk.CTkButton(
        button_row,
        text="Update App",
        command=lambda: subprocess.Popen(
            ["start", "https://rheinze08.github.io/StashSage/"],
            shell=True,
        ),
        corner_radius=8,
    ).pack(side="left", expand=True, fill="x")

    # _refresh_log_files(state.config)
    _enable_services_if_ready(state.config)
    _auto_resize_root()
    root.mainloop()


# ------------- tray-icon helpers (unchanged) -------------
def _create_image():
    icon_path = Path(__file__).with_name("stashsage_logo.ico")
    if not icon_path.exists():
        raise FileNotFoundError(f"Tray icon not found: {icon_path}")
    return Image.open(icon_path)


def _on_quit(icon, item):
    icon.stop()
    root.quit()
    sys.exit()


def _show_app(icon, item):
    icon.visible = False
    root.after(0, root.deiconify)
    root.protocol("WM_DELETE_WINDOW", _minimize_to_tray)


def _setup_tray_icon():
    icon = pystray.Icon("stashsage")
    icon.icon = _create_image()
    icon.menu = pystray.Menu(
        pystray.MenuItem("Show", _show_app), pystray.MenuItem("Exit", _on_quit)
    )
    return icon


def _minimize_to_tray(_event=None):
    root.withdraw()
    if not hasattr(root, "tray_icon"):
        icon = _setup_tray_icon()
        root.tray_icon = icon
        threading.Thread(target=icon.run, daemon=True).start()


if __name__ == "__main__":
    run_tkinter_app(config_manager.load_config())




