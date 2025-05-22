"""
gui_tk.py – Tk/CTk overlay front-end for **StashSage**

Overlay layout (new):

    ┌──────────────────── price chart ────────────────────┐
    ├──────────────────── offers table ───────────────────┤
    │  confidence plot + coloured banner (and debug)      │
    └──────────────────────────────────────────────────────┘
"""

from __future__ import annotations

# std-lib / 3ʳᵈ-party ----------------------------------------------------
import io
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

os.environ["JOBLIB_MULTIPROCESSING"] = "0"
os.environ["JOBLIB_START_METHOD"] = "threading"

import keyboard
import pandas as pd
import pyperclip
from PIL import Image
from joblib import parallel_backend
import customtkinter as ctk
from tkinter import filedialog, messagebox

from poe2trade.app import config_manager
from poe2trade.app.discord_flask import start_services, update_config
from poe2trade.utils.chart_utils import (
    generate_offers_table_chart,
    generate_price_chart_for_item,
    generate_bucket_confidence_plot,
)
from poe2trade.utils.gui_utils import predict_item_text
from poe2trade.utils.log_utils import read_all_log_trades

# ---------------------------------------------------------------------- #
# look & feel / logging
# ---------------------------------------------------------------------- #
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ---------------------------------------------------------------------- #
# globals
# ---------------------------------------------------------------------- #
DEBUG = False
IMG_W, IMG_H = 4, 3

root:     Optional[ctk.CTk]         = None
overlay:  Optional[ctk.CTkToplevel] = None

steam_entry = ggg_entry = None
steam_browse_btn = ggg_browse_btn = None
discord_id_entry = discord_token_entry = None
client_choice: Optional[ctk.StringVar] = None

gui_cfg: dict = {}
LOG_FILES: list[str] = []
SERVICES_STARTED = False
client_day_filter = 30

DEFAULT_STEAM = r"C:\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\client.txt"
DEFAULT_GGG   = r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\client.txt"

_BUCKET_COLOURS = {"low": "#E74C3C", "medium": "#F39C12", "high": "#27AE60"}

# ════════════════════════════════════════════════════════════════════════
# validation helpers
# ════════════════════════════════════════════════════════════════════════
def _has_valid_log(cfg: dict) -> bool:
    ctype = cfg.get("client_type", "steam")
    key   = "steam_client_log_dir" if ctype == "steam" else "ggg_client_log_dir"
    p     = Path(cfg.get(key, "").strip())
    if not (p.is_file() and p.suffix.lower() == ".txt"):
        return False
    try:
        p.open("r", encoding="utf-8").read(64)
        return True
    except Exception as e:
        logging.warning("Log unreadable: %s (%s)", p, e)
        return False


def _refresh_log_files(cfg: dict) -> None:
    LOG_FILES.clear()
    key = "steam_client_log_dir" if cfg.get("client_type") == "steam" else "ggg_client_log_dir"
    p = cfg.get(key, "").strip()
    if p:
        LOG_FILES.append(p)
    logging.info("LOG_FILES → %s", LOG_FILES)


def _enable_services_if_ready() -> None:
    global SERVICES_STARTED
    if SERVICES_STARTED:
        return
    if _has_valid_log(gui_cfg):
        start_services(gui_cfg)
        keyboard.add_hotkey("ctrl+q", _handle_hotkey)
        SERVICES_STARTED = True
        logging.info("Background services + hotkey enabled.")
    else:
        messagebox.showwarning(
            "Configure log files",
            "StashSage needs a valid client.txt for the selected client "
            "before it can start.\n\n"
            "Fix the path(s) then press ‘Update Settings & Reload’.",
        )

# ════════════════════════════════════════════════════════════════════════
# config helpers
# ════════════════════════════════════════════════════════════════════════
def save_gui_config() -> dict:
    ctype = client_choice.get()
    cfg = {
        "client_type": ctype,
        "poe_account": "",
        "steam_client_log_dir": steam_entry.get().strip() if ctype == "steam" else "",
        "ggg_client_log_dir":   ggg_entry.get().strip()   if ctype == "ggg"   else "",
        "discord_user_id":      discord_id_entry.get().strip(),
        "discord_bot_token":    discord_token_entry.get().strip(),
    }
    logging.info("Saving GUI config: %s", cfg)
    config_manager.save_config(cfg)
    return cfg


def _apply_new_config(cfg: dict) -> None:
    update_config(cfg)
    _refresh_log_files(cfg)


def save_and_reload() -> None:
    cfg = save_gui_config()
    _apply_new_config(cfg)
    _enable_services_if_ready()
    messagebox.showinfo(
        "Info",
        "Configuration saved. " +
        ("Background services started." if SERVICES_STARTED else
         "Please correct the path and try again."),
    )

# ════════════════════════════════════════════════════════════════════════
# browse helper
# ════════════════════════════════════════════════════════════════════════
def _browse_for_client(entry: ctk.CTkEntry) -> None:
    path = filedialog.askopenfilename(
        title="Select Path of Exile client.txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    if path and os.path.basename(path).lower() == "client.txt":
        entry.delete(0, "end")
        entry.insert(0, path)
    elif path:
        messagebox.showerror("Invalid File", "Please select the correct file: client.txt")

# ════════════════════════════════════════════════════════════════════════
# overlay helpers
# ════════════════════════════════════════════════════════════════════════
def _destroy_overlay() -> None:
    global overlay
    try:
        if overlay and overlay.winfo_exists():
            overlay.destroy()
    except Exception:
        pass
    overlay = None


def _add_png_to_ctklabel(parent: ctk.CTkFrame, buf: io.BytesIO) -> ctk.CTkLabel:
    """Return a CTkLabel with the PNG. Caller handles geometry manager."""
    global overlay
    pil = Image.open(buf)
    img = ctk.CTkImage(light_image=pil, size=pil.size)
    lbl = ctk.CTkLabel(parent, image=img, text="")
    if overlay is not None:   # keep ref alive
        overlay.images.append(img)
    return lbl


def _bucket_badge(
    parent: ctk.CTkFrame,
    label: str,
    median: float | None,      # kept in signature, no longer displayed
    lo: float | None,
    hi: float | None,
) -> None:
    """
    Render the coloured banner.  New copy:

        Price Prediction — Low/Medium/High (80 % Confident in X-Y Exalted Orbs)
    """
    key = (label or "").lower()
    col = _BUCKET_COLOURS.get(key, "#95A5A6")

    banner = ctk.CTkFrame(parent, fg_color=col, corner_radius=8, height=34)
    banner.pack(fill="x", padx=4, pady=(0, 4))

    # ------------------------------------------------------------------ #
    # 📏  banner text
    # ------------------------------------------------------------------ #
    if None not in (lo, hi):
        txt = (
            f"Price Prediction — {label.capitalize()} "
            f"(80 % Confident in {lo:.0f}-{hi:.0f} Exalted Orbs)"
        )
    else:
        txt = f"Price Prediction — {label.capitalize()}"

    ctk.CTkLabel(
        banner,
        text=txt,
        font=("Helvetica", 12, "bold"),
        text_color="white",
    ).place(relx=0.5, rely=0.5, anchor="center")



def _show_overlay(
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
    """
    Create floating overlay window with a **vertical** grid layout:

        row-0  price chart
        row-1  offers table
        row-2  confidence plot + banner (+ debug when DEBUG == True)
    """
    global overlay, root
    if not (root and root.winfo_exists()):
        return

    _destroy_overlay()
    overlay = ctk.CTkToplevel(master=root)
    overlay.images = []  # keep refs to CTkImage objects
    ov = overlay

    ov.bind("<Escape>", lambda _e: _destroy_overlay())
    ov.title(item)
    ov.attributes("-topmost", True)
    ov.after_idle(lambda: ov.attributes("-topmost", False))

    # ── main single-column grid ────────────────────────────────────────
    grid = ctk.CTkFrame(ov, corner_radius=10)
    grid.pack(fill="both", expand=True, padx=8, pady=8)

    grid.columnconfigure(0, weight=1)
    grid.rowconfigure(0, weight=1)   # price chart
    grid.rowconfigure(1, weight=1)   # offers table
    grid.rowconfigure(2, weight=1)   # bottom (confidence plot / badge / debug)

    # ── row 0: price chart ─────────────────────────────────────────────
    if price_buf:
        _add_png_to_ctklabel(grid, price_buf).grid(
            row=0, column=0, sticky="nsew", padx=4, pady=4)

    # ── row 1: offers table ────────────────────────────────────────────
    if table_buf:
        _add_png_to_ctklabel(grid, table_buf).grid(
            row=1, column=0, sticky="nsew", padx=4, pady=4)

    # ── row 2: confidence plot / badge / debug ─────────────────────────
    bottom = ctk.CTkFrame(grid, fg_color="transparent")
    bottom.grid(row=2, column=0, sticky="nsew")
    bottom.columnconfigure(0, weight=1)

    if conf_buf:
        _add_png_to_ctklabel(bottom, conf_buf).pack(
            fill="both", expand=True, padx=4, pady=4)

    if bucket_label:
        _bucket_badge(bottom, bucket_label, bucket_median,
                      bucket_low, bucket_high)

    if DEBUG and debug_text:
        dbg = ctk.CTkTextbox(bottom, height=120, font=("Consolas", 9))
        dbg.insert("end", debug_text)
        dbg.configure(state="disabled")
        dbg.pack(fill="both", expand=True, padx=4, pady=4)

    # centre & limit size
    ov.update_idletasks()
    w, h = ov.winfo_reqwidth(), ov.winfo_reqheight()
    sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
    w = min(w, int(sw * 0.96))
    h = min(h, int(sh * 0.96))
    ov.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    ov.minsize(w, h)

# ════════════════════════════════════════════════════════════════════════
# clipboard → ML → charts
# ════════════════════════════════════════════════════════════════════════
def _scrape_logs() -> pd.DataFrame:
    trades = read_all_log_trades(LOG_FILES)
    if not trades:
        return pd.DataFrame(
            columns=["timestamp", "buyer", "item_name", "amount", "currency"]
        )
    df = pd.DataFrame(trades)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=client_day_filter)
    return df[df["timestamp"] >= cutoff].sort_values("timestamp")


def _parse_item(text: str) -> Optional[str]:
    out, cap = [], False
    for ln in text.splitlines():
        if ln.startswith("Rarity:") and "rare" in ln.lower():
            cap = True
            continue
        if cap:
            if ln.strip().startswith("--------"):
                break
            out.append(ln.strip())
    return " ".join(out) if out else None


def _handle_hotkey() -> None:
    if not root or not root.winfo_exists():
        return
    keyboard.press_and_release("ctrl+c")
    root.after(200, _deferred_clipboard_process)


def _deferred_clipboard_process() -> None:
    _process_clip_gui(pyperclip.paste())


def _process_clip_gui(clip: str) -> None:
    item = _parse_item(clip) or "Unknown Item"

    with parallel_backend("threading"):
        ml = predict_item_text(clip) or {}

    pred_mean   = ml.get("mean")
    pred_med    = ml.get("median")
    pred_min    = ml.get("min")
    pred_max    = ml.get("max")
    bucket_lbl  = ml.get("bucket")
    bucket_med  = ml.get("bucket_median")
    bucket_low  = ml.get("bucket_low")
    bucket_high = ml.get("bucket_high")
    intervals   = ml.get("bucket_intervals", {})

    actual = ml.get("actual")

    debug = ""
    if None not in (pred_min, pred_max, pred_mean, pred_med):
        debug += (
            f"Min {pred_min:.2f}, Max {pred_max:.2f}, "
            f"Mean {pred_mean:.2f}, Med {pred_med:.2f}\n"
        )
    if actual is not None and pred_mean is not None:
        diff = pred_mean - actual
        debug += f"Actual {actual:.2f} → Diff {diff:+.2f}\n"

    df = _scrape_logs()

    price_buf = generate_price_chart_for_item(
        item,
        df,
        predicted_mean=pred_mean,
        predicted_median=pred_med,
        predicted_min=pred_min,
        predicted_max=pred_max,
        bucket_label=bucket_lbl,
        bucket_median=bucket_med,
        width=IMG_W,
        height=IMG_H,
    )

    table_buf = generate_offers_table_chart(item, df)

    conf_buf = (
        generate_bucket_confidence_plot(
            pred_median=pred_med or 0.0,
            intervals=intervals,
            bucket_label=bucket_lbl or "Unknown",
            width=IMG_W,          # now matches price / offers width
            height=IMG_H * 0.9,
        )
        if bucket_lbl and intervals
        else None
    )

    _show_overlay(
        item,
        price_buf,
        table_buf,
        conf_buf,
        bucket_lbl,
        bucket_med,
        bucket_low,
        bucket_high,
        debug,
    )

# ════════════════════════════════════════════════════════════════════════
# CTk helpers (unchanged)
# ════════════════════════════════════════════════════════════════════════
def _file_row(parent, label: str, default: str = "") -> tuple[ctk.CTkEntry, ctk.CTkButton]:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=10, pady=(10, 2))
    ctk.CTkLabel(frame, text=label).pack(anchor="w")
    inner = ctk.CTkFrame(frame, fg_color="transparent")
    inner.pack(fill="x")
    entry = ctk.CTkEntry(inner, corner_radius=6)
    entry.pack(side="left", fill="x", expand=True, pady=2)
    btn = ctk.CTkButton(
        inner, text="Browse…", width=90,
        command=lambda e=entry: _browse_for_client(e)
    )
    btn.pack(side="left", padx=6, pady=2)
    entry.insert(0, default)
    return entry, btn


def _entry(parent, label: str, default: str = "") -> ctk.CTkEntry:
    ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=10, pady=(10, 2))
    e = ctk.CTkEntry(parent, corner_radius=6)
    e.pack(fill="x", padx=10, pady=2, expand=True)
    e.insert(0, default)
    return e


def _on_client_toggle(choice: str) -> None:
    if choice == "steam":
        steam_entry.configure(state="normal");  steam_browse_btn.configure(state="normal")
        ggg_entry.configure(state="disabled"); ggg_browse_btn.configure(state="disabled")
    else:
        steam_entry.configure(state="disabled"); steam_browse_btn.configure(state="disabled")
        ggg_entry.configure(state="normal");     ggg_browse_btn.configure(state="normal")

# ════════════════════════════════════════════════════════════════════════
# main GUI entry-point (unchanged)
# ════════════════════════════════════════════════════════════════════════
def run_tkinter_app(cfg: Optional[dict] = None) -> None:
    global root, steam_entry, ggg_entry, steam_browse_btn, ggg_browse_btn
    global discord_id_entry, discord_token_entry, gui_cfg, client_choice

    gui_cfg = cfg or {}

    root = ctk.CTk()
    root.title("StashSage for POE2 (developed by Budodude)")
    root.geometry("560x520")

    client_choice = ctk.StringVar(value=gui_cfg.get("client_type", "steam"))
    sel_frame = ctk.CTkFrame(root, corner_radius=8)
    sel_frame.pack(pady=10, padx=10, fill="x")
    ctk.CTkLabel(sel_frame, text="Choose your client:").pack(
        anchor="w", padx=6, pady=(6, 2)
    )

    for key, caption in (("steam", "Steam"), ("ggg", "GGG")):
        rb = ctk.CTkRadioButton(
            sel_frame, text=caption,
            variable=client_choice, value=key,
            command=lambda c=key: _on_client_toggle(c),
        )
        rb.pack(side="left", padx=10, pady=6)

    steam_entry, steam_browse_btn = _file_row(
        root, "Steam Log Location",
        gui_cfg.get("steam_client_log_dir", "") or DEFAULT_STEAM,
    )
    ggg_entry, ggg_browse_btn = _file_row(
        root, "GGG Log Location",
        gui_cfg.get("ggg_client_log_dir", "") or DEFAULT_GGG,
    )
    _on_client_toggle(client_choice.get())

    discord_id_entry = _entry(
        root, "Discord User ID",
        gui_cfg.get("discord_user_id", "").strip(),
    )
    discord_token_entry = _entry(
        root, "Discord Bot Token",
        gui_cfg.get("discord_bot_token", "").strip(),
    )

    ctk.CTkButton(
        root, text="Update Settings & Reload",
        command=save_and_reload, corner_radius=8,
    ).pack(pady=14)

    patreon = ctk.CTkLabel(
        root, text="Support us on Patreon",
        text_color="#1E90FF", cursor="hand2",
        font=("Helvetica", 12, "bold"),
    )
    patreon.pack(pady=18)
    patreon.bind(
        "<Button-1>",
        lambda _e: subprocess.Popen(
            ["start", "https://www.patreon.com/c/Budodude?redirect=true"],
            shell=True,
        ),
    )

    _refresh_log_files(gui_cfg)
    _enable_services_if_ready()
    root.mainloop()


if __name__ == "__main__":
    run_tkinter_app(config_manager.load_config())
