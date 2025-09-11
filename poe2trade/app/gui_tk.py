# gui_tk.py — Tk/CTk front-end for StashSage
# FULL SOURCE • 24 Jun 2025 • rev N (2025-09-07)
#
#  Ctrl-1 → supervised overlay  (“Offer History & Price Aura”)
# ---------------------------------------------------------------------

from __future__ import annotations
import io, logging, os, re, subprocess, sys, threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

# force single‐process joblib
os.environ["JOBLIB_MULTIPROCESSING"] = "0"
os.environ["JOBLIB_START_METHOD"]    = "threading"

# ─ third-party ───────────────────────────────────────────
import keyboard, numpy as np, pandas as pd, pyperclip, pystray
import customtkinter as ctk
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

# ─ project ───────────────────────────────────────────────
from poe2trade.app import config_manager
from poe2trade.app.discord_flask import start_services, update_config
from poe2trade.utils.chart_utils import (
    generate_bucket_confidence_plot,
    generate_offers_table_chart,
    generate_price_chart_for_item,
    generate_predicted_overlay_with_marker,
)
from poe2trade.utils.gui_utils import main as gui_utils_main
from poe2trade.utils.gui_utils import parse_copied_item_text
# import defence pattern skips so we can hide them in the UI list as well
from poe2trade.utils.gui_utils import (
    PCT_DEFENCE_PATTERNS,
    FLAT_DEFENCE_PATTERNS,
    detect_category_segment,
)
from poe2trade.utils.log_utils import read_all_log_trades
from poe2trade.utils import ml_unsuper_utils        # live price-filter tweak
# chaos/divine → exalt conversion constants
from poe2trade import poe2trade_root, chaos_exalt, divine_exalt, knn_k, __version__

# ─ look & feel / logging ─────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ─ globals / constants ───────────────────────────────────
DEBUG               = False
IMG_W, IMG_H        = 12, 9
root           : Optional[ctk.CTk]         = None
overlay        : Optional[ctk.CTkToplevel] = None

steam_entry = ggg_entry = steam_browse_btn = ggg_browse_btn = None
discord_id_entry = discord_token_entry = price_filter_entry = None
client_choice      = None

gui_cfg      : dict      = {}
LOG_FILES    : List[str] = []
SERVICES_STARTED       = False
client_day_filter      = 30

DEFAULT_STEAM        = r"C:\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\client.txt"
DEFAULT_GGG          = r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\client.txt"
DEFAULT_PRICE_FILTER = "1e"

# Bucket colours for text accents
# Bucket colours for accents
_BUCKET_COLOURS = {"low":"#E74C3C","medium":"#F39C12","high":"#27AE60"}
# Neutral bar colour to match KNN UI greys
_BAR_COLOUR = "#3A3A3A"
# Fixed height for the two horizontal bars so they are equal and fit two lines
# Fixed height for the two horizontal bars so they are equal and fit two lines
_BAR_HEIGHT_PX = 100
# Fixed name-row height (single line) to keep KNN rows aligned
_NAME_ROW_H = 34
"""
KNN overlay cell height scaling.
Multiply computed cell heights by this factor. For a ~20% reduction,
use 0.8 (i.e., 80% of original height).
"""
_KNN_CELL_HEIGHT_FACTOR = 0.85

# ────────── scoring JSON hot-path cache ──────────
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

# ══════════════════════════════════════════════════════════════
# ════════════   BUCKET BADGE HELPER (restored!)   ═════════════
# ══════════════════════════════════════════════════════════════
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
    # Always use a neutral grey bar colour to match KNN cells
    fr = ctk.CTkFrame(parent, fg_color=_BAR_COLOUR, corner_radius=8)
    fr.configure(height=_BAR_HEIGHT_PX)
    fr.pack(fill="x", padx=4, pady=(0,4))
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
        val = dataset_pred_value if isinstance(dataset_pred_value, (int, float)) else pred_median
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
                    med_txt  = f"{int(round(float(nearest_median)))}e"
                except Exception:
                    med_txt  = f"{nearest_median:.0f}e"
            parts = []
            if mean_txt:
                parts.append(f"{mean_txt} (mean)")
            if med_txt:
                parts.append(f"{med_txt} (median)")
            suffix = ", ".join(parts) if parts else (xe or "")
            line1 = f"Price Prediction #2 - {suffix}".rstrip()
        else:
            line1 = f"Price Prediction #{num} - {xe or ''}".rstrip()
        ctk.CTkLabel(content, text=line1, font=("Helvetica",28,"bold"), text_color="white").pack(padx=8, pady=(4,2))

        # Line 1b – Relative <bucket> Value within {Category}
        # Build as three labels to colour only the bucket word
        if mode == "dataset" and show_line2:
            cat_txt = (category_title or "").strip() or "Category"
            row_ds = ctk.CTkFrame(content, fg_color="transparent")
            row_ds.pack(padx=8, pady=(0,4))
            ctk.CTkLabel(row_ds, text="Relative ", font=("Helvetica",20), text_color="#EEEEEE").pack(side="left")
            bucket = (label or "").capitalize()
            bcol = _BUCKET_COLOURS.get(bucket.lower(), "#EEEEEE")
            ctk.CTkLabel(row_ds, text=bucket, font=("Helvetica",20,"bold"), text_color=bcol).pack(side="left")
            ctk.CTkLabel(row_ds, text=f" Value within {cat_txt}", font=("Helvetica",20), text_color="#EEEEEE").pack(side="left")

    # Line 2 – nearest items (prefer explicit list of prices)
    if show_line2 and mode == "nearest" and combined_prices_line:
        # Keep same font/size as dataset second line for consistency
        ctk.CTkLabel(content, text=combined_prices_line, font=("Helvetica",20), text_color="#EEEEEE").pack(padx=8, pady=(0,4))
        return

    # Line 2 — Price Prediction #2 (nearest items), only exalts
    if show_line2 and mode == "nearest" and isinstance(nearest_mean, (int, float)) and isinstance(nearest_median, (int, float)):
        # Mean/Median are now shown in line 1 to match requested format; avoid duplicating here.
        pass

    # Line 3 — Combined prices list (optional, smaller, not bold)
    # omit third line to keep both bars at two lines

# ══════════════════════════════════════════════════════════════
# ═════════════ stat / mod helpers ══════════════════════════════
# Map core norm columns → pretty labels
_CORE_KEYS = {
    "ar_norm": "Armour",
    "ev_norm": "Evasion",
    "es_norm": "Energy Shield"
}
# Hide these from the modifiers list; handled by *_NORM already
_HIDE_DEF_PATTERNS = PCT_DEFENCE_PATTERNS | FLAT_DEFENCE_PATTERNS

# ╔════════════════ HOT-KEY THROTTLING ════════════════════╗
_hotkey_busy = {
    "super"  : threading.Lock(),  # Ctrl+1 consolidated 
}
def _run_with_lock(lock: threading.Lock, fn, *a, **kw):
    if not lock.acquire(blocking=False):
        return
    try:
        fn(*a, **kw)
    finally:
        lock.release()
# ╚════════════════════════════════════════════════════════╝

# ═════════════ price-filter helpers ══════════════════════
PRICE_FILTER_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[ecd]?\s*$", re.I)
def _apply_price_filter(cfg: dict) -> None:
    raw = str(cfg.get("price_mirror_filter", DEFAULT_PRICE_FILTER)).strip()
    try:
        ml_unsuper_utils.set_price_filter(raw)
        logging.info("KNN price filter set to %r", raw)
    except Exception as exc:
        logging.warning("Invalid price filter %r – defaulting to 1e (%s)", raw, exc)
        ml_unsuper_utils.set_price_filter("1e")

# ═════════════ tiny UI helpers ════════════════════════════
def _textbox(parent, lines, yellow, colours, row, col, height: int | None = None):
    # Compute base height and then apply global shrink factor (~20% reduction)
    if height is None:
        base = max(100, int((len(lines) + 1) * 26))
        height = max(20, int(base * _KNN_CELL_HEIGHT_FACTOR))
    tb = ctk.CTkTextbox(
        parent,
        # wrap long lines to avoid horizontal scrollbars
        wrap="word", font=("Consolas",18),
        border_width=1, border_color="#3A3A3A",
        height=height
    )
    tb.tag_config("yellow", foreground="#FFD700")
    tb.tag_config("plus",   foreground="#4CAF50")
    tb.tag_config("minus",  foreground="#E74C3C")
    for i, ln in enumerate(lines):
        tb.insert("end", ln + "\n")
        if i in yellow:
            tb.tag_add("yellow", f"{i+1}.0", f"{i+1}.end")
        if i in colours:
            p = ln.find("(")
            if p != -1:
                tb.tag_add(colours[i], f"{i+1}.{p}", f"{i+1}.end")
    tb.configure(state="disabled")
    tb.grid(
        row=row, column=col, sticky="nsew",
        padx=(6,0) if col==0 else (0,0), pady=4
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
        # join e.g. ["Mind Mantle", "Ornate Plate"] → "Mind Mantle Ornate Plate"
        return " ".join(item_lines)
    return None

def _destroy_overlay():
    global overlay
    if overlay and overlay.winfo_exists():
        overlay.destroy()
    overlay = None

# ─── put this right next to _destroy_overlay ───────────
def _scaled_png(parent: ctk.CTkFrame, buf: io.BytesIO,
                target_w: int) -> ctk.CTkLabel:
    """Load PNG → scale to target_w keeping aspect ratio → CTkLabel."""
    global overlay
    pil = Image.open(buf)
    w0, h0 = pil.size
    if w0 == 0:     # paranoia
        return ctk.CTkLabel(parent, text="(bad image)")
    scale = target_w / w0
    size  = (target_w, int(h0 * scale))

    img = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
    lbl = ctk.CTkLabel(parent, image=img, text="")
    if overlay is not None:
        overlay.images.append(img)          # keep a ref → no GC
    return lbl

# Scale a PNG to a percentage of its native width
def _scaled_png_percent(parent: ctk.CTkFrame, buf: io.BytesIO, pct: float) -> ctk.CTkLabel:
    try:
        pil = Image.open(buf)
        w0, _ = pil.size
        target = max(1, int(max(1.0, w0) * max(0.05, min(1.0, float(pct)))))
    except Exception:
        target = 400
    # Use a fresh buffer for the scaled render
    return _scaled_png(parent, io.BytesIO(buf.getvalue()), target)

# ──────────────── tiny UI helpers ────────────────
def _add_png_to_ctklabel(parent: ctk.CTkFrame, buf: io.BytesIO) -> ctk.CTkLabel:
    global overlay
    pil = Image.open(buf)
    # use the image’s own size so it renders at full resolution
    img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
    lbl = ctk.CTkLabel(parent, image=img, text="")
    # keep a reference so it isn’t GC’d
    if overlay is not None:
        overlay.images.append(img)
    return lbl

# ═════════════ currency helpers ══════════════════════════
def _price_to_exalt(price:float,cur:str|None)->float:
    cur = (cur or "").lower()
    if cur in ("e","exa","exalt","exalts"): return float(price)
    if cur in ("c","chaos"):                return float(price)*chaos_exalt
    if cur in ("d","div","divine"):         return float(price)*divine_exalt
    return float(price)

def _price_string(row:pd.Series)->tuple[str,float]|None:
    """Return ("Xe/Yc/Zd", exalts_float) with rounded ints for display."""
    e_val: float | None = None
    if {"Price","Currency"}.issubset(row.index) and pd.notna(row.get("Price")):
        e_val = _price_to_exalt(row["Price"], row["Currency"])  # type: ignore[index]
    elif {"price","currency"}.issubset(row.index) and pd.notna(row.get("price")):
        e_val = _price_to_exalt(row["price"], row["currency"])  # type: ignore[index]
    elif "Price_in_Exalts" in row and pd.notna(row.get("Price_in_Exalts")):
        e_val = float(row["Price_in_Exalts"])  # type: ignore[index]
    if e_val is None:
        return None
    try:
        e = int(round(float(e_val)))
        c = int(round(float(e_val) / max(chaos_exalt, 1e-9)))
        d = int(round(float(e_val) / max(divine_exalt, 1e-9)))
    except Exception:
        return None
    return (f"{e}e/{c}c/{d}d", float(e_val))

# simple price like "10e" or "50c" or "2d" for header tags
def _price_simple(row: pd.Series) -> Optional[str]:
    if {"Price","Currency"}.issubset(row.index) and pd.notna(row.get("Price")):
        return f"{int(round(float(row['Price'])))}{str(row['Currency']).lower()[:1]}"
    if {"price","currency"}.issubset(row.index) and pd.notna(row.get("price")):
        return f"{int(round(float(row['price'])))}{str(row['currency']).lower()[:1]}"
    if "Price_in_Exalts" in row and pd.notna(row.get("Price_in_Exalts")):
        return f"{int(round(float(row['Price_in_Exalts'])))}e"
    return None

def _triple(e_val: float) -> str:
    try:
        e = int(round(float(e_val)))
        c = int(round(float(e_val) / max(chaos_exalt, 1e-9)))
        d = int(round(float(e_val) / max(divine_exalt, 1e-9)))
        return f"{e}e/{c}c/{d}d"
    except Exception:
        return f"{e_val:.0f}e"

# ═════════════ log-scraper (for supervised) ═════════════
def _scrape_logs()->pd.DataFrame:
    trades = read_all_log_trades(LOG_FILES)
    if not trades:
        return pd.DataFrame(columns=["timestamp","buyer","item_name","amount","currency"])
    df = pd.DataFrame(trades)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=client_day_filter)
    return df[df["timestamp"]>=cutoff].sort_values("timestamp")

# ═════════════ helpers for adding images to cells ═════════════
BASE_IMAGE_MAP = {}
_CATEGORY_WORD_MAP = {
    # Body Armour
    "armour": "Body_Armour", "plate": "Body_Armour", "jacket": "Body_Armour",
    "coat": "Body_Armour", "mail": "Body_Armour", "robe": "Body_Armour",
    "vest": "Body_Armour", "cuirass": "Body_Armour", "mantle": "Body_Armour",
    "garb": "Body_Armour", "raiment": "Body_Armour",
    # Boots
    "boots": "Boots", "greaves": "Boots", "sabatons": "Boots",
    "shoes": "Boots", "leggings": "Boots", "sandals": "Boots",
    # Gloves
    "gloves": "Gloves", "gauntlets": "Gloves", "bracers": "Gloves",
    "mitts": "Gloves", "cuffs": "Gloves", "wraps": "Gloves",
    # Helmet
    "helm": "Helmet", "helmet": "Helmet", "mask": "Helmet",
    "crown": "Helmet", "cap": "Helmet", "greathelm": "Helmet",
    "tiara": "Helmet",
    # Jewellery
    "ring": "Ring", "amulet": "Amulet", "belt": "Belt",
}

def load_base_image_map(path: str):
    global BASE_IMAGE_MAP
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        base = item["baseType"]
        key = " ".join(base.split()[-2:]).lower()
        BASE_IMAGE_MAP[key] = {
            "path": item["icon"],
            "category": item["category"],
            "baseType": base,
        }

def find_local_image(item_name: str, root: str) -> Optional[str]:
    words = item_name.strip().split()
    if len(words) < 1:
        return None
    # Try last two, then last one
    # if not found in map, try category default by heuristic
    for i in (2, 1):
        key = " ".join(words[-i:]).lower()
        entry = BASE_IMAGE_MAP.get(key)
        if entry:
            category = entry["category"]
            base_type = entry["baseType"]
            # allow hyphen to align with icon file naming
            safe_name = "".join(c for c in base_type if c.isalnum() or c in (" ", "-", "_")).rstrip()
            img_path = os.path.join(root, category, f"{safe_name}.png")
            if os.path.exists(img_path):
                return img_path
            # fallback: default.png in this category
            default_path = os.path.join(root, category, "default.png")
            if os.path.exists(default_path):
                return default_path
    # No entry in map — try to guess category from last word
    last = re.sub(r"[^A-Za-z]", "", words[-1]).lower()
    cat = _CATEGORY_WORD_MAP.get(last)
    if cat:
        default_path = os.path.join(root, cat, "default.png")
        if os.path.exists(default_path):
            return default_path
    return None

# Try to render an icon for an item; falls back through defaults safely
def _icon_label(parent: ctk.CTkFrame, item_name: str, target_w: int = 36, target_h: int = _NAME_ROW_H) -> Optional[ctk.CTkLabel]:
    root_dir = f"{poe2trade_root}/db/base_icons"
    candidates: list[str] = []
    # 1) specific image or category default as per map/heuristic
    p = find_local_image(item_name, root_dir)
    if p:
        candidates.append(p)
    # 2) hard fallbacks: any category default.png
    for cat in ("Body_Armour","Helmet","Boots","Gloves","Ring","Amulet","Belt"):
        candidates.append(os.path.join(root_dir, cat, "default.png"))

    for fp in candidates:
        if not fp or not os.path.exists(fp):
            continue
        try:
            with open(fp, "rb") as f:
                buf = io.BytesIO(f.read())
            lbl = _scaled_png(parent, buf, target_w)
            try:
                # Enforce consistent header height so left/right align
                lbl.configure(height=target_h)
            except Exception:
                pass
            return lbl
        except Exception as exc:
            logging.warning("Icon load failed for %s: %s", fp, exc)
            continue
    return None

# Render the neighbour comparison rows into the given body frame
def _render_mirror_rows(body: ctk.CTkFrame, base_series: pd.Series, df: pd.DataFrame, item_name: str, *, show_defence_mods: bool = False):
    core = list(_CORE_KEYS.keys())
    # Conditionally hide defence patterns: show for jewellery (ring/amulet/belt)
    _SKIP = (set() if show_defence_mods else _HIDE_DEF_PATTERNS) | {
        # never show base/price fields in modifiers list
        "price", "Price", "currency", "Currency",
        "amount", "Amount", "Cur", "cur", "price_in_exalts", "Price_in_Exalts",
        # raw defence aliases
        "Armour", "armour", "Evasion", "evasion", "Evasion Rating", "evasion rating",
        "Energy Shield", "energy shield", "ar", "ev", "es",
    }

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
        feats = core + sorted((set(base_series.index) | set(nbr.index)) - set(core) - _SKIP)

        base_lines = [item_name]
        nbr_lines  = [nbr.get("item", "")]
        yellow_l: set[int] = set()
        yellow_r: set[int] = set()
        colours_r: dict[int, str] = {}

        for k in feats:
            b_raw = _numeric(base_series, k)
            n_raw = _numeric(nbr,         k)
            if b_raw == 0 and n_raw == 0:
                continue
            is_core = k in core
            b_disp  = _disp(b_raw, is_core)
            n_disp  = _disp(n_raw, is_core)
            label   = _CORE_KEYS.get(k, k)
            left_txt  = f"{label}: {_fmt_disp(b_disp)}"
            right_txt = f"{label}: {_fmt_disp(n_disp)}"
            delta = n_disp - b_disp
            if delta != 0:
                sign = "+" if delta > 0 else ""
                right_txt += f" ({sign}{_fmt_disp(delta)})"
                colours_r[len(nbr_lines)] = "plus" if delta > 0 else "minus"
            if (b_raw == 0) ^ (n_raw == 0):
                yellow_l.add(len(base_lines))
                yellow_r.add(len(nbr_lines))
            base_lines.append(left_txt)
            nbr_lines.append(right_txt)
            if k == core[-1]:
                base_lines.append("--------")
                nbr_lines.append("--------")

        pr = _price_string(nbr)
        if pr:
            nbr_lines.append("--------")
            nbr_lines.append(f"Price: {pr[0]}")
            colours_r[len(nbr_lines) - 1] = "plus"

        pad = max(len(base_lines), len(nbr_lines))
        base_lines += [""] * (pad - len(base_lines))
        nbr_lines  += [""] * (pad - len(nbr_lines))
        # Use a common height for both cells in this row to keep tops/bottoms aligned
        common_base = max(100, int((pad + 1) * 26))
        common_h = max(20, int(common_base * _KNN_CELL_HEIGHT_FACTOR))

        name_left = base_lines.pop(0)
        f0 = ctk.CTkFrame(body, fg_color="transparent")
        f0.grid(row=r, column=0, sticky="nsew", padx=(6, 4), pady=4)
        f0.columnconfigure(0, weight=1)
        try:
            f0.grid_rowconfigure(0, minsize=_NAME_ROW_H)
        except Exception:
            pass
        # Header: icon + title on the same line (dynamic height per row)
        hdr0 = ctk.CTkFrame(f0, fg_color="transparent")
        hdr0.grid(row=0, column=0, sticky="nsew")
        try:
            hdr0.columnconfigure(1, weight=1)
        except Exception:
            pass
        lbl0_img = _icon_label(hdr0, name_left, 36)
        if lbl0_img:
            lbl0_img.grid(row=0, column=0, sticky="w", padx=(0,6))
        name_lbl0 = ctk.CTkLabel(
            hdr0, text=f"{name_left} (Your Item)", font=("Consolas", 18, "bold"),
            anchor="w"
        )
        name_lbl0.grid(row=0, column=1, sticky="we")
        yellow_l_shift = {i - 1 for i in yellow_l if i > 0}
        # Compute base and then scale by ~20%
        common_base = max(100, int((pad + 1) * 26))
        common_h = max(20, int(common_base * _KNN_CELL_HEIGHT_FACTOR))
        _textbox(f0, base_lines, yellow_l_shift, {}, 2, 0, height=common_h)

        name_right = nbr_lines.pop(0)
        f1 = ctk.CTkFrame(body, fg_color="transparent")
        f1.grid(row=r, column=1, sticky="nsew", padx=(4, 6), pady=4)
        f1.columnconfigure(0, weight=1)
        try:
            f1.grid_rowconfigure(0, minsize=_NAME_ROW_H)
        except Exception:
            pass
        # Header: icon + title on the same line (right)
        hdr1 = ctk.CTkFrame(f1, fg_color="transparent")
        hdr1.grid(row=0, column=0, sticky="nsew")
        try:
            hdr1.columnconfigure(1, weight=1)
        except Exception:
            pass
        lbl1_img = _icon_label(hdr1, name_right, 36)
        if lbl1_img:
            lbl1_img.grid(row=0, column=0, sticky="w", padx=(0,6))
        name_lbl1 = ctk.CTkLabel(
            hdr1, text=name_right, font=("Consolas", 18, "bold"),
            anchor="w"
        )
        name_lbl1.grid(row=0, column=1, sticky="we")

        # Equalize header heights across both columns so rows align
        try:
            hdr0.update_idletasks(); hdr1.update_idletasks()
            name_lbl0.update_idletasks(); name_lbl1.update_idletasks()
            h_candidates = [_NAME_ROW_H]
            if lbl0_img: h_candidates.append(lbl0_img.winfo_reqheight())
            if lbl1_img: h_candidates.append(lbl1_img.winfo_reqheight())
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
        yellow_r_shift  = {i - 1 for i in yellow_r if i > 0}
        colours_r_shift = {i - 1: v for i, v in colours_r.items() if i > 0}
        _textbox(f1, nbr_lines, yellow_r_shift, colours_r_shift, 2, 0, height=common_h)


# ═════════════ UNSUPERVISED overlay (“Price Mirror”) ════
def _show_unsuper_overlay(
    base_X: pd.DataFrame,
    df: pd.DataFrame,
    item_name: str
) -> None:
    """
    Unsurpervised “Price-Mirror” overlay.

    • OUTER-joins mods (value 0 shown when missing).
    • Rows where both sides are 0 are dropped.
    • Core block (ES/AR/EV) is from *_NORM, rounded → dashed separator kept.
    • If exactly one side is zero and the other >0, BOTH cells are yellow.
    • Δ (green / red) is computed **after** rounding so numbers match.
    • Left column never shows a price line.
    • Flat and % defence modifiers are hidden; already encoded in *_NORM.
    """
    global overlay, root, gui_cfg
    if not (root and root.winfo_exists()):
        return

    _destroy_overlay()
    overlay = ctk.CTkToplevel(root)
    overlay.images = []
    # Set window icon to match main app (Windows-friendly ICO)
    try:
        _ico = str(Path(__file__).with_name("stashsage_logo.ico"))
        overlay.iconbitmap(_ico)
    except Exception:
        pass
    overlay.title("Price Mirror")
    overlay.bind("<Escape>", lambda _e: _destroy_overlay())
    overlay.attributes("-topmost", True)
    overlay.after_idle(lambda: overlay.attributes("-topmost", False))

    # ── header ───────────────────────────────────────────
    cont = ctk.CTkFrame(overlay, corner_radius=10)
    cont.pack(fill="both", expand=True, padx=8, pady=8)
    cont.columnconfigure((0, 1), weight=1)
    cont.rowconfigure(6, weight=1)

    pf = gui_cfg.get("price_mirror_filter", DEFAULT_PRICE_FILTER)
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

    # Stats first (above title+price list)
    if vals:
        mean_e = float(np.mean(vals)); med_e = float(np.median(vals))
        em = " — "
        stats = f"Price Prediction from Nearest Items{em}Mean = {_triple(mean_e)}{em}Median = {_triple(med_e)}"
        ctk.CTkLabel(cont, text=stats,
                     font=("Consolas", 21, "bold"), text_color="#FFD700")\
            .grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
    # Title + price list merged into one single non-bold line
    combined = f"{title_txt} [{', '.join(tags)}]"
    ctk.CTkLabel(cont, text=combined,
                 font=("Consolas", 19), text_color="#CCCCCC")\
        .grid(row=1, column=0, columnspan=2, sticky="ew")

    # ctk.CTkLabel(cont, text="Your Item",
    #              font=("Consolas", 20, "bold"))\
    #     .grid(row=4, column=0, sticky="s")
    # ctk.CTkLabel(cont, text="Similar Item",
    #              font=("Consolas", 20, "bold"))\
    #     .grid(row=4, column=1, sticky="s")

    # ── body ────────────────────────────────────────────
    body = ctk.CTkFrame(cont, fg_color="transparent")
    body.grid(row=6, column=0, columnspan=2, sticky="nsew")
    body.columnconfigure((0, 1), weight=1)

    base_series = base_X.iloc[0]
    core = list(_CORE_KEYS.keys())           # ["ar_norm","ev_norm","es_norm"]
    # Never show raw base defences in the modifiers list; only *_norm at top.
    # Include lowercase forms and shorthand cols (ar/ev/es) since overlay_df uses lowercase.
    _SKIP = {
        "price", "Price", "currency", "Currency",
        # raw base defence names (various casings/aliases)
        "Armour", "armour", "Evasion", "evasion", "Evasion Rating", "evasion rating",
        "Energy Shield", "energy shield",
        # shorthand raw columns present in overlay_df
        "ar", "ev", "es",
    } | _HIDE_DEF_PATTERNS

    # helper: safe numeric fetch
    def _numeric(s, key) -> float:
        try:
            return float(s.get(key, 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    # helper: get the “display” numeric (rounded for core)
    def _disp(v: float, is_core: bool) -> float:
        return round(v)

    # helper: string render of that display numeric
    def _fmt_disp(d: float) -> str:
        return f"{int(d)}" if float(d).is_integer() else f"{d:g}"

    for r, (_, nbr) in enumerate(df.iterrows()):

        # Only show modifiers excluding core keys, prices, and defence patterns
        feats = core + sorted(
            (set(base_series.index) | set(nbr.index)) - set(core) - _SKIP
        )

        base_lines = [item_name]
        nbr_lines  = [nbr.get("item", "")]
        yellow_l: set[int] = set()
        yellow_r: set[int] = set()
        colours_r: dict[int, str] = {}

        for k in feats:
            b_raw = _numeric(base_series, k)
            n_raw = _numeric(nbr,         k)

            if k in core:
                # Ensure neighbour has *_NORM present; if missing, treat as 0
                pass

            if b_raw == 0 and n_raw == 0:
                continue

            is_core = k in core
            b_disp  = _disp(b_raw, is_core)
            n_disp  = _disp(n_raw, is_core)

            label   = _CORE_KEYS.get(k, k)
            left_txt  = f"{label}: {_fmt_disp(b_disp)}"
            right_txt = f"{label}: {_fmt_disp(n_disp)}"

            delta = n_disp - b_disp                      # after rounding
            if delta != 0:
                sign = "+" if delta > 0 else ""
                right_txt += f" ({sign}{_fmt_disp(delta)})"
                colours_r[len(nbr_lines)] = "plus" if delta > 0 else "minus"

            if (b_raw == 0) ^ (n_raw == 0):
                yellow_l.add(len(base_lines))
                yellow_r.add(len(nbr_lines))

            base_lines.append(left_txt)
            nbr_lines.append(right_txt)

            # separator after the last core line
            if k == core[-1]:
                base_lines.append("--------")
                nbr_lines.append("--------")

        # neighbour price only
        pr = _price_string(nbr)
        if pr:
            nbr_lines.append("--------")
            nbr_lines.append(f"Price: {pr[0]}")
            colours_r[len(nbr_lines) - 1] = "plus"

        # pad to equal length
        pad = max(len(base_lines), len(nbr_lines))
        base_lines += [""] * (pad - len(base_lines))
        nbr_lines  += [""] * (pad - len(nbr_lines))

        # ── left cell ────────────────────────────────────
        name_left = base_lines.pop(0)
        f0 = ctk.CTkFrame(body, fg_color="transparent")
        f0.grid(row=r, column=0, sticky="nsew", padx=(6, 4), pady=4)
        f0.columnconfigure(0, weight=1)
        # Header: icon + title on the same line
        hdr0 = ctk.CTkFrame(f0, fg_color="transparent")
        hdr0.grid(row=0, column=0, sticky="w")
        try:
            hdr0.configure(height=_NAME_ROW_H)
            hdr0.grid_propagate(False)
        except Exception:
            pass
        lbl0 = _icon_label(hdr0, name_left, 36)
        if lbl0:
            lbl0.grid(row=0, column=0, sticky="w", padx=(0,6))
        ctk.CTkLabel(hdr0, text=f"{name_left} (Yours)", font=("Consolas", 18, "bold"))\
            .grid(row=0, column=1, sticky="w")

        yellow_l_shift = {i - 1 for i in yellow_l if i > 0}
        _textbox(f0, base_lines, yellow_l_shift, {}, 2, 0, height=common_h)

        # ── right cell ───────────────────────────────────
        name_right = nbr_lines.pop(0)
        f1 = ctk.CTkFrame(body, fg_color="transparent")
        f1.grid(row=r, column=1, sticky="nsew", padx=(4, 6), pady=4)
        f1.columnconfigure(0, weight=1)
        # Header: icon + title on the same line
        hdr1 = ctk.CTkFrame(f1, fg_color="transparent")
        hdr1.grid(row=0, column=0, sticky="w")
        try:
            hdr1.configure(height=_NAME_ROW_H)
            hdr1.grid_propagate(False)
        except Exception:
            pass
        lbl1 = _icon_label(hdr1, name_right, 36)
        if lbl1:
            lbl1.grid(row=0, column=0, sticky="w", padx=(0,6))
        ctk.CTkLabel(hdr1, text=name_right, font=("Consolas", 18, "bold"))\
            .grid(row=0, column=1, sticky="w")

        yellow_r_shift  = {i - 1 for i in yellow_r if i > 0}
        colours_r_shift = {i - 1: v for i, v in colours_r.items() if i > 0}
        _textbox(f1, nbr_lines, yellow_r_shift, colours_r_shift, 2, 0, height=common_h)

    # ── window geometry ─────────────────────────────────
    overlay.update_idletasks()
    sw, sh = overlay.winfo_screenwidth(), overlay.winfo_screenheight()
    w = min(1800, overlay.winfo_reqwidth() + 400)
    h = min(1000, overlay.winfo_reqheight() + 20)
    overlay.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")
    overlay.minsize(1200, 500)

# ═════════════ SUPERVISED overlay (charts) ═══════════════
def _show_super_overlay(
        item           : str,
        price_buf      : io.BytesIO | None,
        table_buf      : io.BytesIO | None,
        conf_buf       : io.BytesIO | None,
        bucket_label   : str | None,
        bucket_median  : float | None,
        bucket_low     : float | None,
        bucket_high    : float | None,
        debug_text     : str,
) -> None:
    global overlay, root
    if not (root and root.winfo_exists()):
        return

    _destroy_overlay()
    overlay = ctk.CTkToplevel(root)
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
        _scaled_png_percent(grid, price_buf, 0.5)\
            .grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    if table_buf:
        _scaled_png_percent(grid, table_buf, 0.5)\
            .grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

    bottom = ctk.CTkFrame(grid, fg_color="transparent")
    bottom.grid(row=2, column=0, sticky="nsew")
    bottom.columnconfigure(0, weight=1)

    if conf_buf:
        _add_png_to_ctklabel(bottom, conf_buf)\
            .pack(fill="both", expand=True, padx=4, pady=4)
    if bucket_label:
        _bucket_badge(bottom, bucket_label,
                      bucket_median, bucket_low, bucket_high)

    # window hugs the native PNG size
    ov.update_idletasks()
    sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
    w = min(ov.winfo_reqwidth(), int(sw * 0.96))
    h = min(ov.winfo_reqheight(), int(sh * 0.96))
    ov.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")
    ov.minsize(w, h)


# ————————————————————————————————————————————————————————————————————————————
# CONSOLIDATED DASHBOARD overlay (Ctrl+1):
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
        pred_median: float | None,
        dataset_pred_xgb: float | None,
        category_title: str | None,
        cat_norm: str | None,
        seg_norm: str | None,
        unsuper_X: Optional[pd.DataFrame],
        unsuper_df: Optional[pd.DataFrame],
        unsuper_item_name: str,
) -> None:
    global overlay, root, gui_cfg
    if not (root and root.winfo_exists()):
        return

    _destroy_overlay()
    overlay = ctk.CTkToplevel(root)
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
    if bucket_label and isinstance(pred_median, (int, float)):
        badge1_holder = ctk.CTkFrame(cont, fg_color="transparent")
        badge1_holder.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        _bucket_badge(
            badge1_holder, bucket_label,
            bucket_median, bucket_low, bucket_high,
            pred_median,
            None, None, None,
            mode="dataset",
            category_title=(category_title or (cat_norm or "").replace("_"," ").title()),
            dataset_pred_value=dataset_pred_xgb,
        )

    # Row 2: predicted distribution overlay (prefer JSON; fallback to pre-rendered PNG)
    try:
        dist_buf = None
        dynamic_done = False
        # Marker fallback: prefer dataset_pred_xgb else predicted median
        marker_val = dataset_pred_xgb if dataset_pred_xgb is not None else pred_median

        if cat_norm:
            model_dir = Path(poe2trade_root) / "db" / "super_models"

            # If armour and we have features, infer the segment from ar/ev/es
            if cat_norm in ("body_armour", "helmet", "gloves", "boots") and isinstance(unsuper_X, pd.DataFrame) and not unsuper_X.empty:
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
            png_candidates:  list[Path] = []

            if seg_norm:
                # Armour: <category>_<segment>
                json_candidates.append(model_dir / f"{cat_norm}_{seg_norm}_scoring.json")
                xlsx_candidates.append(model_dir / f"{cat_norm}_{seg_norm}_scoring.xlsx")
                png_candidates.append(model_dir / f"{cat_norm}_{seg_norm}_price_dists.png")
                # US spelling fallback for body armour
                if cat_norm == "body_armour":
                    json_candidates.append(model_dir / f"body_armor_{seg_norm}_scoring.json")
                    xlsx_candidates.append(model_dir / f"body_armor_{seg_norm}_scoring.xlsx")
                    png_candidates.append(model_dir / f"body_armor_{seg_norm}_price_dists.png")
            else:
                # Jewellery: single global file
                json_candidates.append(model_dir / f"{cat_norm}_scoring.json")
                xlsx_candidates.append(model_dir / f"{cat_norm}_scoring.xlsx")
                png_candidates.append(model_dir / f"{cat_norm}_price_dists.png")
                # Some runs may include kind in the filename
                for kind in ("ring", "amulet", "belt"):
                    json_candidates.append(model_dir / f"{cat_norm}_{kind}_scoring.json")
                    xlsx_candidates.append(model_dir / f"{cat_norm}_{kind}_scoring.xlsx")
                    png_candidates.append(model_dir / f"{cat_norm}_{kind}_price_dists.png")

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
            _scaled_png_percent(cont, dist_buf, 0.525)\
                .grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
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
    pf = gui_cfg.get("price_mirror_filter", DEFAULT_PRICE_FILTER)
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
            nearest_mean = float(np.mean(vals)); nearest_median = float(np.median(vals))
        combined_line = f"Based on {knn_k} Nearest Items (Ordered) with Price Filter {pf}: [{', '.join(tags)}]"

    if bucket_label and (nearest_mean is not None or nearest_median is not None):
        badge2_holder = ctk.CTkFrame(cont, fg_color="transparent")
        badge2_holder.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        _bucket_badge(
            badge2_holder, bucket_label,
            bucket_median, bucket_low, bucket_high,
            None,
            nearest_mean, nearest_median, combined_line,
            mode="nearest",
        )

    # (combined single-bar UI removed in favor of two separate bars)

    # Row 4: Unsupervised mirror (existing layout), only if data present
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty and unsuper_X is not None:
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
        _render_mirror_rows(body, base_series, unsuper_df, unsuper_item_name, show_defence_mods=show_defs)

    # window geometry — start large enough by default, within screen bounds
    ov.update_idletasks()
    sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
    # Reduce default width by ~20% (from 90% to 72% of screen; 1600 → 1280 cap)
    default_w = min(int(sw * 0.72), 1280)
    default_h = min(int(sh * 0.90), 900)
    ov.geometry(f"{default_w}x{default_h}+{(sw - default_w)//2}+{(sh - default_h)//2}")
    ov.minsize(960, 700)

# ═════════════ ML pipelines → overlays ═══════════════════
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
            parsed   = parse_copied_item_text(text)

            unsuper  = gui_utils_main(text, key="unsuper")
            if unsuper:
                unsuper_X, unsuper_df = unsuper
            else:
                unsuper_X = unsuper_df = None

            # Derive category/segment safely here
            raw_cat  = str(parsed.get("Item Category", "default_model")).lower().replace(" ", "_")
            raw_cat  = {"boot": "boots", "glove": "gloves"}.get(raw_cat, raw_cat)
            cat_norm = raw_cat or "default_model"
            seg_norm = ml_super.get("segment") if isinstance(ml_super, dict) else None
            if not seg_norm:
                try:
                    _c, _s = detect_category_segment(parsed)
                    seg_norm = _s
                except Exception:
                    seg_norm = None

            # Confidence plot buffer (safe to render off-thread)
            conf_buf = None
            intervals = ml_super.get("bucket_intervals", {}) if isinstance(ml_super, dict) else {}
            if intervals and ml_super.get("bucket"):
                try:
                    conf_buf = generate_bucket_confidence_plot(
                        pred_median = ml_super.get("median") or 0.0,
                        intervals   = intervals,
                        bucket_label= ml_super.get("bucket") or "Unknown",
                        width=IMG_W, height=IMG_H*0.9
                    )
                except Exception:
                    conf_buf = None

            # Optional: xgb value for line #1 text
            preds_map = ml_super.get("predictions", {}) if isinstance(ml_super, dict) else {}
            dataset_pred_xgb = None
            try:
                if preds_map.get("xgb") is not None:
                    dataset_pred_xgb = float(preds_map.get("xgb"))
            except Exception:
                dataset_pred_xgb = None

            # Names
            item_name          = ml_super.get("item_name") or _parse_item(text) or "(Unknown item)"
            unsuper_item_name  = parsed.get("Item Name", "(Unknown)")

            # ---------- UI HANDOFF (Tk main thread only) ----------
            def _show():
                try:
                    _show_dashboard_overlay(
                        item_name,
                        None, None,                   # price_buf, table_buf (unused)
                        conf_buf,
                        ml_super.get("bucket") if isinstance(ml_super, dict) else None,
                        ml_super.get("bucket_median") if isinstance(ml_super, dict) else None,
                        ml_super.get("bucket_low") if isinstance(ml_super, dict) else None,
                        ml_super.get("bucket_high") if isinstance(ml_super, dict) else None,
                        ml_super.get("median") if isinstance(ml_super, dict) else None,
                        dataset_pred_xgb,
                        (cat_norm or "").replace("_", " ").title(),
                        cat_norm, seg_norm,
                        unsuper_X, unsuper_df, unsuper_item_name,
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

    pred_mean = ml.get("mean");   pred_med = ml.get("median")
    pred_min  = ml.get("min");    pred_max = ml.get("max")
    bucket_lbl = ml.get("bucket")
    bucket_med = ml.get("bucket_median")
    bucket_low = ml.get("bucket_low")
    bucket_high= ml.get("bucket_high")
    intervals  = ml.get("bucket_intervals", {})

    # Gather per-model predictions for formatting bar text
    preds_map = ml.get("predictions", {}) if isinstance(ml, dict) else {}
    xgb_val = None
    try:
        xgb_val = float(preds_map.get("xgb")) if preds_map.get("xgb") is not None else None
    except Exception:
        xgb_val = None

    # Top charts dropped from dashboard; still compute buffers for compatibility
    df_logs = _scrape_logs()
    price_buf = None
    table_buf = None
    conf_buf  = (generate_bucket_confidence_plot(
                    pred_median=pred_med or 0.0,
                    intervals=intervals,
                    bucket_label=bucket_lbl or "Unknown",
                    width=IMG_W, height=IMG_H*0.9
                ) if bucket_lbl and intervals else None)

    _show_super_overlay(
        item, price_buf, table_buf, conf_buf,
        bucket_lbl, bucket_med, bucket_low, bucket_high,
        ""
    )

def _process_dashboard_gui(text: str) -> None:
    """Build consolidated dashboard: super (top row) + unsuper (bottom)."""
    # Supervised part
    ml = gui_utils_main(text, key="super") or {}
    item = ml.get("item_name") or _parse_item(text) or "(Unknown item)"

    pred_mean = ml.get("mean");   pred_med = ml.get("median")
    pred_min  = ml.get("min");    pred_max = ml.get("max")
    bucket_lbl = ml.get("bucket")
    bucket_med = ml.get("bucket_median")
    bucket_low = ml.get("bucket_low")
    bucket_high= ml.get("bucket_high")
    intervals  = ml.get("bucket_intervals", {})

    # No top charts in dashboard
    price_buf = None
    table_buf = None
    conf_buf  = (generate_bucket_confidence_plot(
                    pred_median=pred_med or 0.0,
                    intervals=intervals,
                    bucket_label=bucket_lbl or "Unknown",
                    width=IMG_W, height=IMG_H*0.9
                ) if bucket_lbl and intervals else None)

    # Unsupervised part (optional)
    parsed = parse_copied_item_text(text)
    unsuper_item_name = parsed.get("Item Name", "(Unknown)")
    # Determine category/segment for distribution PNG lookup
    raw_cat = str(parsed.get("Item Category", "default_model")).lower().replace(" ", "_")
    raw_cat = {"boot": "boots", "glove": "gloves"}.get(raw_cat, raw_cat)
    cat_norm = raw_cat or "default_model"
    # Prefer segment from ML (computed on normalized defence values)
    seg_norm = ml.get("segment") if isinstance(ml, dict) else None
    if not seg_norm:
        # Fallback: best-effort detect from parsed (may be missing *_norm)
        try:
            _c, _s = detect_category_segment(parsed)
            seg_norm = _s
        except Exception:
            seg_norm = None
    result = gui_utils_main(text, key="unsuper")
    if result:
        unsuper_X, unsuper_df = result
    else:
        unsuper_X, unsuper_df = None, None

    # Extract xgboost prediction value for the first bar line
    preds_map = ml.get("predictions", {}) if isinstance(ml, dict) else {}
    xgb_val = None
    try:
        xgb_val = float(preds_map.get("xgb")) if preds_map.get("xgb") is not None else None
    except Exception:
        xgb_val = None

    _show_dashboard_overlay(
        item,
        price_buf, table_buf, conf_buf,
        bucket_lbl, bucket_med, bucket_low, bucket_high,
        pred_med,
        xgb_val,
        (cat_norm or "").replace("_"," ").title(),
        cat_norm, seg_norm,
        unsuper_X, unsuper_df, unsuper_item_name,
    )

# ═════════════ HOT-KEY handlers ═══════════════════════════
def _handle_hotkey_super(_=None):
    keyboard.press_and_release("ctrl+c")
    root.after(200, lambda: _run_with_lock(
        _hotkey_busy["super"], _score_dashboard_async, pyperclip.paste()))

# (removed: Ctrl+2 handler)

# ═════════════ GUI widgets & helpers (unchanged) ═════════
def _browse_for_client(entry: ctk.CTkEntry) -> None:
    fpath = filedialog.askopenfilename(
        title="Select PoE client.txt log",
        filetypes=[("Text files","*.txt"),("All files","*.*")],
    )
    if fpath:
        entry.delete(0,"end")
        entry.insert(0,fpath)

def _entry(parent, label, default="", digits_only=False, allow_float=False) -> ctk.CTkEntry:
    ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=10, pady=(10,2))
    if digits_only and allow_float:
        raise ValueError("Use either digits_only or allow_float, not both")
    def _check(P: str) -> bool:
        if P=="": return True
        if digits_only:  return P.isdigit()
        if allow_float:  return re.fullmatch(r"\s*\d*\.?\d*\s*[ecdECD]?", P) is not None
        return True
    e = ctk.CTkEntry(parent, corner_radius=6)
    vcmd = parent.register(_check)
    e.configure(validate="key", validatecommand=(vcmd,"%P"))
    e.pack(fill="x", padx=10, pady=2, expand=True)
    e.insert(0, default)
    return e

def _file_row(parent,label,default="") -> tuple[ctk.CTkEntry,ctk.CTkButton]:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=10, pady=(10,2))
    ctk.CTkLabel(frame, text=label).pack(anchor="w")
    inner = ctk.CTkFrame(frame, fg_color="transparent"); inner.pack(fill="x")
    entry = ctk.CTkEntry(inner, corner_radius=6)
    entry.pack(side="left", fill="x", expand=True, pady=2)
    btn = ctk.CTkButton(inner, text="Browse…", width=90,
                        command=lambda e=entry: _browse_for_client(e))
    btn.pack(side="left", padx=6, pady=2)
    entry.insert(0, default)
    return entry, btn

def _refresh_log_files(cfg: dict) -> None:
    global LOG_FILES
    typ  = cfg.get("client_type","steam")
    path = cfg.get("steam_client_log_dir" if typ=="steam" else "ggg_client_log_dir","")
    LOG_FILES = [path] if Path(path).is_file() else []
    logging.info("Log files set: %s", LOG_FILES)

def _enable_services_if_ready(cfg: dict) -> None:
    global SERVICES_STARTED
    if SERVICES_STARTED: return
    token   = cfg.get("discord_bot_token","").strip()
    user_id = cfg.get("discord_user_id","").strip()
    if not (token and user_id and LOG_FILES): return
    try:
        start_services(cfg)
        SERVICES_STARTED = True
        logging.info("Discord Flask + background services started.")
    except Exception as exc:
        logging.exception("Could not start Discord services: %s", exc)

def _on_client_toggle(choice: str) -> None:
    if choice=="steam":
        steam_entry.configure(state="normal"); steam_browse_btn.configure(state="normal")
        ggg_entry.configure(state="disabled");  ggg_browse_btn.configure(state="disabled")
    else:
        steam_entry.configure(state="disabled"); steam_browse_btn.configure(state="disabled")
        ggg_entry.configure(state="normal");     ggg_browse_btn.configure(state="normal")

# ═════════════ save & reload (stores price filter) ══════
def save_and_reload() -> None:
    pf_raw = price_filter_entry.get().strip() or str(DEFAULT_PRICE_FILTER)
    if not PRICE_FILTER_RE.fullmatch(pf_raw):
        messagebox.showerror(
            "Invalid Price Filter",
            "Must be a number followed by E, C, or D (e.g. 100e, 50c, 10D)",
        ); return
    gui_cfg.update(
        client_type           = client_choice.get(),
        steam_client_log_dir  = steam_entry.get().strip(),
        ggg_client_log_dir    = ggg_entry.get().strip(),
        discord_user_id       = discord_id_entry.get().strip(),
        discord_bot_token     = discord_token_entry.get().strip(),
        price_mirror_filter   = pf_raw,
    )
    config_manager.save_config(gui_cfg)
    _apply_price_filter(gui_cfg)
    update_config(gui_cfg)
    _refresh_log_files(gui_cfg)
    _enable_services_if_ready(gui_cfg)
    messagebox.showinfo("StashSage","Settings saved & reloaded!")

# ═════════════ main Tk entry-point ═══════════════════════
def run_tkinter_app(cfg: Optional[dict] = None) -> None:
    """
    Main Tk entry-point, now also pre-loads the base-image map so the
    unsupervised overlay can grab icons instantly.
    """
    global root, steam_entry, ggg_entry, steam_browse_btn, ggg_browse_btn
    global discord_id_entry, discord_token_entry, price_filter_entry
    global gui_cfg, client_choice

    gui_cfg = cfg or {}
    _apply_price_filter(gui_cfg)

    # ── NEW: preload the icon lookup once at startup
    try:
        load_base_image_map(f"{poe2trade_root}/db/files/base_images.json")
        logging.info("base_images.json loaded (%d entries)", len(BASE_IMAGE_MAP))
    except Exception as exc:
        logging.warning("Could not load base_images.json: %s", exc)

    root = ctk.CTk()
    root.title(f"StashSage for POE2 (v{__version__})")
    root.geometry("560x580")
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

    keyboard.add_hotkey("ctrl+1", _handle_hotkey_super,   suppress=False)

    # client radio buttons
    client_choice = ctk.StringVar(value=gui_cfg.get("client_type", "steam"))
    sel = ctk.CTkFrame(root, corner_radius=8); sel.pack(pady=10, padx=10, fill="x")
    ctk.CTkLabel(sel, text="Choose your client:")\
        .pack(anchor="w", padx=6, pady=(6, 2))
    for key, caption in (("steam", "Steam"), ("ggg", "GGG")):
        ctk.CTkRadioButton(
            sel, text=caption, variable=client_choice, value=key,
            command=lambda c=key: _on_client_toggle(c)
        ).pack(side="left", padx=10, pady=6)

    steam_entry, steam_browse_btn = _file_row(
        root, "Steam Log Location",
        gui_cfg.get("steam_client_log_dir", "") or DEFAULT_STEAM)
    ggg_entry, ggg_browse_btn = _file_row(
        root, "GGG Log Location",
        gui_cfg.get("ggg_client_log_dir", "") or DEFAULT_GGG)
    _on_client_toggle(client_choice.get())

    discord_id_entry    = _entry(root, "Discord User ID",
                                 gui_cfg.get("discord_user_id", "").strip(),
                                 digits_only=True)
    discord_token_entry = _entry(root, "Discord Bot Token",
                                 gui_cfg.get("discord_bot_token", "").strip())
    price_filter_entry  = _entry(
        root,
        "Nearest Items Price Filter (e.g. 40E, 100d, 20c)",
        str(gui_cfg.get("price_mirror_filter", DEFAULT_PRICE_FILTER)),
        allow_float=True,
    )
    # conversion hint (rounded whole integers) — start from 1 divine
    try:
        c_per_d = int(round(float(divine_exalt) / max(float(chaos_exalt), 1e-9)))
        e_per_d = int(round(float(divine_exalt)))
        hint = f"(*) Conversion rate used 1 d = {c_per_d} c = {e_per_d} e"
    except Exception:
        hint = "(*) 1 d = ? c = ? e"
    ctk.CTkLabel(root, text=hint, text_color="#AAAAAA", font=("Consolas", 12, "bold"))\
        .pack(pady=(0, 10))

    ctk.CTkButton(root, text="Update Settings & Reload",
                  command=save_and_reload, corner_radius=8)\
        .pack(pady=14)

    patreon = ctk.CTkLabel(root, text="Support us on Patreon",
                           text_color="#1E90FF", cursor="hand2",
                           font=("Helvetica", 12, "bold"))
    patreon.pack(pady=18)
    patreon.bind(
        "<Button-1>",
        lambda _e: subprocess.Popen(
            ["start", "https://www.patreon.com/c/Budodude?redirect=true"],
            shell=True)
    )

    _refresh_log_files(gui_cfg)
    _enable_services_if_ready(gui_cfg)
    root.mainloop()

# ═════════════ tray-icon helpers (unchanged) ═════════════
def _create_image():
    icon_path = Path(__file__).with_name("stashsage_logo.ico")
    if not icon_path.exists():
        raise FileNotFoundError(f"Tray icon not found: {icon_path}")
    return Image.open(icon_path)

def _on_quit(icon, item):
    icon.stop(); root.quit(); sys.exit()

def _show_app(icon, item):
    icon.visible = False
    root.after(0, root.deiconify)
    root.protocol("WM_DELETE_WINDOW", _minimize_to_tray)

def _setup_tray_icon():
    icon = pystray.Icon("stashsage")
    icon.icon = _create_image()
    icon.menu = pystray.Menu(
        pystray.MenuItem("Show", _show_app), pystray.MenuItem("Exit", _on_quit))
    return icon

def _minimize_to_tray(_event=None):
    root.withdraw()
    if not hasattr(root,"tray_icon"):
        icon = _setup_tray_icon()
        root.tray_icon = icon
        threading.Thread(target=icon.run, daemon=True).start()

if __name__ == "__main__":
    run_tkinter_app(config_manager.load_config())
