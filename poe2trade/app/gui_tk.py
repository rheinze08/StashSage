# gui_tk.py -- Tk/CTk front-end for StashSage
# FULL SOURCE -- 24 Jun 2025 -- rev N (2025-09-07)
#
#  Ctrl-1 ? supervised overlay  ("Offer History & Price Aura")
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
import io, logging, math, os, re, subprocess, sys, threading, time
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
from tkinter import filedialog, messagebox, ttk

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
from poe2trade.utils import scrape_stash_utils

# chaos/divine ? exalt conversion constants
from poe2trade import (
    poe2trade_root,
    chaos_exalt,
    divine_exalt,
    annul_exalt,
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
DEFAULT_KNN = int(config_manager.DEFAULT_CONFIG.get("knn_filtered_k", 10))

steam_entry = ggg_entry = steam_browse_btn = ggg_browse_btn = None
prediction_log_entry = prediction_log_browse_btn = None
discord_id_entry = discord_token_entry = price_filter_entry = knn_filtered_k_entry = custom_hotkey_entry = filtered_hotkey_entry = discord_api_hotkey_entry = prediction_log_hotkey_entry = None
show_viz_var = None
auction_hotkey_entry = auction_rule_entry = None
client_choice = None

gui_cfg: dict = state.config
LOG_FILES: List[str] = []
SERVICES_STARTED = False
client_day_filter = 30

_FILTER_ENTRY_MEMORY: dict[str, list[str]] = {}

MIN_WINDOW_WIDTH = 560
MIN_WINDOW_HEIGHT = 240

def _load_stash_categories() -> list[str]:
    """Return the available stash scrape categories."""
    return [entry["name"] for entry in scrape_stash_utils.STASH_SCRAPE_SELECTIONS]


ITEM_CATEGORIES = _load_stash_categories()


def _open_stash_scrape_dialog() -> None:
    if root is None:
        return
    if not ITEM_CATEGORIES:
        messagebox.showwarning("Stash Scrape", "No stash scrape categories are available.")
        return

    dialog = ctk.CTkToplevel(root)
    dialog.title("Stash Scrape")
    dialog_width, dialog_height = 760, 880
    dialog.geometry(f"{dialog_width}x{dialog_height}")
    dialog.minsize(680, 700)
    try:
        dialog.update_idletasks()
        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        x = max((sw - dialog_width) // 2, 0)
        y = max((sh - dialog_height) // 2, 0)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    except Exception:
        pass
    dialog.transient(root)
    dialog.grab_set()
    dialog.focus_force()
    dialog.bind("<Escape>", lambda _event: dialog.destroy())

    content = ctk.CTkFrame(dialog, fg_color="transparent")
    content.pack(fill="both", expand=True)

    form_section = ctk.CTkFrame(content, fg_color="transparent")
    form_section.pack(fill="x", padx=20, pady=(18, 12))
    form_section.grid_columnconfigure(1, weight=1)
    form_section.grid_columnconfigure(2, weight=0)

    username_label = ctk.CTkLabel(form_section, text="Trade API Username")
    username_label.grid(row=0, column=0, sticky="w")
    username_entry = ctk.CTkEntry(form_section)
    username_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(12, 0))

    save_label = ctk.CTkLabel(form_section, text="Save Location")
    save_label.grid(row=1, column=0, sticky="w", pady=(10, 0))
    save_entry = ctk.CTkEntry(form_section)
    save_entry.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))

    def _browse_save() -> None:
        folder = filedialog.askdirectory(parent=dialog)
        if folder:
            save_entry.delete(0, tk.END)
            save_entry.insert(0, folder)

    ctk.CTkButton(
        form_section,
        text="Browse",
        width=90,
        command=_browse_save,
    ).grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(10, 0))

    wait_label = ctk.CTkLabel(form_section, text="Seconds Between Searches")
    wait_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
    wait_entry = ctk.CTkEntry(form_section)
    wait_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(12, 0), pady=(10, 0))

    wait_warning = ctk.CTkLabel(
        form_section,
        text="Warning: Aggressive speeds can result in rate limits. Suggest a minimum of 300 seconds.",
        text_color="#FF5C5C",
        wraplength=520,
        justify="left",
    )
    wait_warning.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

    last_username = str(state.config.get("stash_scrape_username", "") or "").strip()
    last_save_dir = str(state.config.get("stash_scrape_save_dir", "") or "").strip()
    last_listing_type = (
        str(state.config.get("stash_scrape_listing_type", "merchant") or "merchant")
        .strip()
        .lower()
    )
    if last_listing_type not in {"merchant", "all"}:
        last_listing_type = "merchant"
    try:
        last_wait_raw = state.config.get(
            "stash_scrape_search_wait", scrape_stash_utils.SEARCH_WAIT_DEFAULT
        )
        last_wait = int(last_wait_raw)
    except (TypeError, ValueError):
        last_wait = scrape_stash_utils.SEARCH_WAIT_DEFAULT

    if last_username:
        username_entry.insert(0, last_username)
    if last_save_dir:
        save_entry.insert(0, last_save_dir)
    wait_entry.insert(0, str(max(0, last_wait)))

    type_section = ctk.CTkFrame(content, fg_color="transparent")
    type_section.pack(fill="x", padx=20, pady=(0, 12))

    ctk.CTkLabel(type_section, text="Listing Type").pack(anchor="w")
    type_choice = tk.StringVar(value=last_listing_type or "merchant")
    type_row = ctk.CTkFrame(type_section, fg_color="transparent")
    type_row.pack(anchor="w", pady=(4, 0))
    ctk.CTkRadioButton(
        type_row,
        text="All Listings",
        variable=type_choice,
        value="all",
    ).pack(side="left", padx=(0, 16))
    ctk.CTkRadioButton(
        type_row,
        text="Merchant Only",
        variable=type_choice,
        value="merchant",
    ).pack(side="left")

    category_records: list[tuple[ctk.BooleanVar, str]] = []
    if ITEM_CATEGORIES:
        categories_section = ctk.CTkFrame(content, fg_color="transparent")
        categories_section.pack(fill="both", expand=False, padx=20, pady=(0, 12))

        ctk.CTkLabel(categories_section, text="Item Categories").pack(anchor="w")
        ctk.CTkLabel(
            categories_section,
            text="Enable categories to include them and optionally provide a note.",
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(2, 6))

        category_grid = ctk.CTkFrame(categories_section, fg_color="transparent")
        category_grid.pack(fill="x", expand=False)
        total_cats = len(ITEM_CATEGORIES)
        column_count = 3 if total_cats >= 9 else 2 if total_cats >= 4 else 1
        rows_per_column = max(1, math.ceil(total_cats / column_count))

        for idx, cat in enumerate(ITEM_CATEGORIES):
            col = idx // rows_per_column
            row = idx % rows_per_column
            category_grid.grid_columnconfigure(col, weight=1, pad=12)
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(
                category_grid,
                text=cat.replace("_", " ").title(),
                variable=var,
            ).grid(row=row, column=col, sticky="w", pady=4, padx=(0, 18))
            category_records.append((var, cat))

    def _format_range(rng_value) -> str:
        if isinstance(rng_value, (list, tuple)) and len(rng_value) == 2:
            return f"{rng_value[0]} - {rng_value[1]}"
        return str(rng_value)

    def _handle_submit() -> None:
        selected_categories = [cat for var, cat in category_records if var.get()]
        username = username_entry.get().strip()
        save_path = save_entry.get().strip()
        wait_value = wait_entry.get().strip()
        if not save_path:
            messagebox.showwarning(
                "Stash Scrape",
                "Provide a save location before submitting.",
                parent=dialog,
            )
            return

        if not wait_value:
            messagebox.showwarning(
                "Stash Scrape",
                "Provide the seconds between searches.",
                parent=dialog,
            )
            return
        try:
            wait_secs = int(wait_value)
        except ValueError:
            messagebox.showwarning(
                "Stash Scrape",
                "Enter a whole number for seconds between searches.",
                parent=dialog,
            )
            return
        if wait_secs < 0:
            messagebox.showwarning(
                "Stash Scrape",
                "Seconds between searches must be zero or greater.",
                parent=dialog,
            )
            return

        if not selected_categories:
            messagebox.showwarning(
                "Stash Scrape",
                "Select at least one item category before submitting.",
                parent=dialog,
            )
            return

        config_changed = False
        if username != str(state.config.get("stash_scrape_username", "") or ""):
            state.config["stash_scrape_username"] = username
            config_changed = True
        if save_path != str(state.config.get("stash_scrape_save_dir", "") or ""):
            state.config["stash_scrape_save_dir"] = save_path
            config_changed = True
        prev_wait_raw = state.config.get(
            "stash_scrape_search_wait", scrape_stash_utils.SEARCH_WAIT_DEFAULT
        )
        try:
            prev_wait = int(prev_wait_raw)
        except (TypeError, ValueError):
            prev_wait = scrape_stash_utils.SEARCH_WAIT_DEFAULT
        if prev_wait != wait_secs:
            state.config["stash_scrape_search_wait"] = wait_secs
            config_changed = True
        listing_type = type_choice.get().strip().lower() or "merchant"
        if listing_type not in {"merchant", "all"}:
            listing_type = "merchant"
        if listing_type != str(state.config.get("stash_scrape_listing_type", "merchant")):
            state.config["stash_scrape_listing_type"] = listing_type
            config_changed = True
        if config_changed:
            try:
                config_manager.save_config(state.config)
            except Exception as exc:
                logging.warning("Failed to persist stash scrape defaults: %s", exc)

        dialog.destroy()

        progress_dialog = ctk.CTkToplevel(root)
        progress_dialog.title("Stash Scrape Progress")
        progress_dialog.geometry("720x420")
        progress_dialog.minsize(600, 360)
        progress_dialog.transient(root)
        progress_dialog.grab_set()
        progress_dialog.focus_force()
        progress_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        progress_frame = ctk.CTkFrame(progress_dialog, fg_color="transparent")
        progress_frame.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(progress_frame, text="Stash Scrape Progress").pack(
            anchor="w", pady=(0, 8)
        )

        progress_text = ctk.CTkTextbox(progress_frame, height=240, wrap="word")
        progress_text.pack(fill="both", expand=True)
        progress_text.configure(state="disabled")

        status_var = tk.StringVar(value="Running...")
        status_label = ctk.CTkLabel(progress_frame, textvariable=status_var)
        status_label.pack(anchor="w", pady=(10, 0))

        current_selection: Optional[str] = None
        current_stage: Optional[str] = None
        stage_state: dict[str, str] = {}
        stop_event = threading.Event()
        cancel_requested = False
        cancel_button: Optional[ctk.CTkButton] = None
        close_button: Optional[ctk.CTkButton] = None

        def _refresh_status() -> None:
            if not progress_dialog.winfo_exists():
                return
            if current_selection:
                stage_label = current_stage or stage_state.get(current_selection)
                if stage_label:
                    status_var.set(f"Processing {current_selection} [{stage_label}]")
                else:
                    status_var.set(f"Processing {current_selection}")
            else:
                status_var.set("Idle")

        def _close_progress() -> None:
            try:
                progress_dialog.grab_release()
            except Exception:
                pass
            if progress_dialog.winfo_exists():
                progress_dialog.destroy()

        def _append_line(line: str) -> None:
            if not progress_dialog.winfo_exists():
                return
            progress_text.configure(state="normal")
            progress_text.insert("end", line + "\n")
            progress_text.see("end")
            progress_text.configure(state="disabled")

        def _request_cancel() -> None:
            nonlocal cancel_requested
            if not progress_dialog.winfo_exists():
                return
            if cancel_requested or stop_event.is_set():
                return
            cancel_requested = True
            stop_event.set()
            status_var.set("Cancelling...")
            _append_line(f"[{time.strftime('%H:%M:%S')}] Cancel requested by user")
            if cancel_button:
                cancel_button.configure(state="disabled", text="Cancelling...")
            progress_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        btn_row = ctk.CTkFrame(progress_frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(12, 0))

        cancel_button = ctk.CTkButton(
            btn_row,
            text="Cancel",
            command=_request_cancel,
        )
        cancel_button.pack(side="left", padx=(0, 8))

        close_button = ctk.CTkButton(
            btn_row,
            text="Close",
            state="disabled",
            command=_close_progress,
        )
        close_button.pack(side="right")

        progress_dialog.protocol("WM_DELETE_WINDOW", _request_cancel)

        def _format_progress_message(event: str, payload: Mapping[str, object]) -> str:
            if event == "start":
                selections = payload.get("selections") or []
                ua = payload.get("user_agent") or "unknown UA"
                if selections:
                    return f"Starting scrape for {', '.join(map(str, selections))} (UA: {ua})"
                return f"Starting scrape (UA: {ua})"
            if event == "stage":
                selection = payload.get("selection") or "Unknown"
                stage = payload.get("stage") or "?"
                return f"Stage update: {selection} -> {stage}"
            if event == "selection_start":
                selection = payload.get("selection")
                delay = payload.get("expected_delay")
                wait_text = (
                    f"; next search wait ~ {float(delay) / 60:.1f} min" if delay else ""
                )
                return f"Processing {selection}{wait_text}"
            if event == "selection_result":
                selection = payload.get("selection")
                items = int(payload.get("items", 0))
                if items:
                    return f"Completed {selection}: {items} items fetched"
                return f"Completed {selection}: no items found"
            if event == "items_batch":
                selection = payload.get("selection", "Unknown")
                items = int(payload.get("items", 0))
                batch_idx = payload.get("batch_index")
                return f"Fetched {items} items for {selection} (batch {batch_idx})"
            if event == "rate_limited":
                phase = payload.get("phase", "unknown")
                status = payload.get("status", "429")
                return f"Rate limited during {phase} (HTTP {status}); honoring retry"
            if event == "stopped":
                return str(payload.get("message") or "Scrape stopped.")
            if event == "completed":
                summary = payload.get("summary") or {}
                items = summary.get("items", 0)
                errors = summary.get("errors", 0)
                files = len(summary.get("output_files") or [])
                return f"Scrape completed: {items} items, {errors} errors, {files} files saved"
            if event == "error":
                return f"Error: {payload.get('message')}"
            return f"{event}: {dict(payload)}"

        def _handle_progress(event: str, payload: Mapping[str, object]) -> None:
            timestamp = time.strftime("%H:%M:%S")
            message = _format_progress_message(event, payload)

            def _update() -> None:
                nonlocal current_selection, current_stage
                if not progress_dialog.winfo_exists():
                    return
                if message:
                    _append_line(f"[{timestamp}] {message}")
                if event == "stage":
                    selection = payload.get("selection")
                    stage_label = payload.get("stage")
                    if selection:
                        selection_str = str(selection)
                        if stage_label:
                            stage_state[selection_str] = str(stage_label)
                        stage_value = stage_state.get(selection_str)
                        if (
                            current_selection == selection_str
                            or current_selection is None
                            or stage_value in {"Matrix", "Score"}
                        ):
                            current_selection = selection_str
                            current_stage = stage_value
                            _refresh_status()
                    return
                if event == "selection_start":
                    selection = payload.get("selection")
                    if selection:
                        current_selection = str(selection)
                        stage_label = payload.get("stage") or stage_state.get(current_selection) or "Scrape"
                        stage_state[current_selection] = str(stage_label)
                        current_stage = stage_state[current_selection]
                        _refresh_status()
                elif event == "rate_limited":
                    status_var.set("Rate limited; waiting...")
                elif event == "completed":
                    status_var.set("Completed")
                    if cancel_button:
                        cancel_button.configure(state="disabled")
                elif event == "error":
                    status_var.set("Error encountered")
                    if cancel_button:
                        cancel_button.configure(state="disabled")
                elif event == "stopped":
                    status_text = str(payload.get("message") or "Scrape stopped.")
                    status_var.set(status_text)
                    if cancel_button:
                        cancel_button.configure(state="disabled")

            root.after(0, _update)

        def _finalize(summary: Optional[dict], error: Optional[str]) -> None:
            nonlocal current_selection, current_stage
            if not progress_dialog.winfo_exists():
                return
            progress_dialog.protocol("WM_DELETE_WINDOW", _close_progress)
            if close_button:
                close_button.configure(state="normal")
            if cancel_button:
                cancel_button.configure(state="disabled")
            try:
                progress_dialog.grab_release()
            except Exception:
                pass

            current_selection = None
            current_stage = None
            stage_state.clear()
            _refresh_status()

            if error:
                status_var.set("Error encountered")
                _append_line(f"[{time.strftime('%H:%M:%S')}] Error: {error}")
                messagebox.showerror("Stash Scrape", f"Scrape failed: {error}")
                return

            if summary is None:
                return

            cancelled = bool(summary.get("cancelled"))
            cancel_reason = summary.get("cancel_reason") or "Scrape cancelled."
            if cancelled:
                status_var.set(cancel_reason)
                if cancel_button:
                    cancel_button.configure(state="disabled", text="Cancelled")
                _append_line(f"[{time.strftime('%H:%M:%S')}] {cancel_reason}")
                return

            status_var.set("Completed")
            outputs = summary.get("output_files") or []
            scored_items = summary.get("scored_items", 0)
            final_csv = summary.get("final_csv")
            listing_type = str(summary.get("listing_type", "merchant")).strip().lower()

            lines = [
                f"Listing type: {'Merchant Only' if listing_type == 'merchant' else 'All'}",
                f"Categories processed: {summary.get('processed_categories', 0)}",
                f"Items fetched: {summary.get('items', 0)}",
                f"Errors: {summary.get('errors', 0)}",
            ]
            if scored_items:
                lines.append(f"Items scored: {scored_items}")
            if outputs:
                lines.append("")
                lines.append("Saved files:")
                lines.extend(outputs)
            if final_csv:
                lines.append("")
                lines.append(f"Aggregate CSV: {final_csv}")

            messagebox.showinfo("Stash Scrape", "\n".join(lines))

        def _run_scrape() -> None:
            try:
                summary = scrape_stash_utils.run_stash_scrape(
                    username or None,
                    save_path,
                    item_categories=selected_categories or None,
                    prompt_before_clear=False,
                    progress_callback=_handle_progress,
                    search_wait=wait_secs,
                    listing_type=listing_type,
                    stop_event=stop_event,
                )
            except Exception as exc:
                root.after(0, lambda err=str(exc): _finalize(None, err))
                return

            root.after(0, lambda: _finalize(summary, None))

        threading.Thread(target=_run_scrape, daemon=True).start()

    button_row = ctk.CTkFrame(content, fg_color="transparent")
    button_row.pack(side="bottom", fill="x", padx=20, pady=(4, 16))
    ctk.CTkButton(button_row, text="Cancel", command=dialog.destroy, width=120).pack(
        side="right", padx=(8, 0)
    )
    ctk.CTkButton(button_row, text="Submit", command=_handle_submit, width=120).pack(
        side="right"
    )



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
_prediction_log_hotkey_handle = None  # track prediction log hotkey binding
_auction_hotkey_handles: list = []  # track auction tool single-hotkey bindings
_auction_last_ts = 0.0  # last trigger time (monotonic)

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

# ---------- feature-importance manifest cache ----------
_FI_MANIFEST_CACHE: Optional[list[dict]] = None
_FI_MANIFEST_MTIME: Optional[float] = None

def _load_fi_manifest() -> list[dict]:
    """Load db/super_models/feature_importances_index.json with mtime cache."""
    global _FI_MANIFEST_CACHE, _FI_MANIFEST_MTIME
    try:
        p = Path(poe2trade_root) / "db" / "super_models" / "feature_importances_index.json"
        if not p.is_file():
            return []
        mt = p.stat().st_mtime
        if _FI_MANIFEST_CACHE is not None and _FI_MANIFEST_MTIME == mt:
            return _FI_MANIFEST_CACHE
        import json as _json
        data = _json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            _FI_MANIFEST_CACHE = data
            _FI_MANIFEST_MTIME = mt
            return data
        return []
    except Exception:
        return []

def _available_fi_models(cat: str | None, seg: str | None) -> list[str]:
    """Return model types available for (category, segment) in FI manifest."""
    if not cat:
        return []
    cat_l = str(cat).strip().lower()
    seg_l = (str(seg).strip().lower() if seg else None)
    items = _load_fi_manifest()
    out: set[str] = set()
    for e in items:
        c = str(e.get("category", "")).strip().lower()
        s = e.get("segment")
        s_l = (str(s).strip().lower() if s is not None else None)
        if c == cat_l and s_l == seg_l:
            mt = str(e.get("model_type", "")).strip().upper() or "XGB"
            out.add(mt)
    # fallback: if no segment match and we have entries with segment None
    if not out:
        for e in items:
            c = str(e.get("category", "")).strip().lower()
            s = e.get("segment")
            if c == cat_l and (s is None or str(s).strip() == ""):
                mt = str(e.get("model_type", "")).strip().upper() or "XGB"
                out.add(mt)
    return sorted(out)

def _open_fi_popup(cat: str | None, seg: str | None, model_type: str) -> None:
    """Show a simple popup table of feature importances for (cat, seg, model)."""
    if not (root and root.winfo_exists()):
        return
    items = _load_fi_manifest()
    cat_l = str(cat or "").strip().lower()
    seg_l = (str(seg).strip().lower() if seg else None)
    mt_l  = str(model_type or "").strip().upper()
    entry: dict | None = None
    for e in items:
        c = str(e.get("category", "")).strip().lower()
        s = e.get("segment")
        s_l = (str(s).strip().lower() if s is not None else None)
        mt = str(e.get("model_type", "")).strip().upper() or "XGB"
        if c == cat_l and s_l == seg_l and mt == mt_l:
            entry = e
            break
    if entry is None:
        # fallback to segment None
        for e in items:
            c = str(e.get("category", "")).strip().lower()
            s = e.get("segment")
            mt = str(e.get("model_type", "")).strip().upper() or "XGB"
            if c == cat_l and (s is None or str(s).strip() == "") and mt == mt_l:
                entry = e
                break
    popup = ctk.CTkToplevel(root)
    popup.title(f"Mod Importances  —  {cat or ''}{('/' + seg) if seg else ''}")
    try:
        popup.iconbitmap(str(Path(__file__).with_name("stashsage_logo.ico")))
    except Exception:
        pass
    popup.geometry("980x600")
    popup.minsize(600, 400)
    # Ensure the FI window appears on top of the main GUI
    try:
        popup.transient(root)
        popup.attributes("-topmost", True)
        popup.lift(); popup.focus_force()
    except Exception:
        pass
    frm = ctk.CTkFrame(popup)
    frm.pack(fill="both", expand=True, padx=8, pady=8)
    frm.grid_columnconfigure(0, weight=1)
    frm.grid_rowconfigure(0, weight=1)
    frm.grid_rowconfigure(1, weight=1)
    box = ctk.CTkTextbox(frm, wrap="none", font=("Consolas", 12))
    box.grid(row=0, column=0, sticky="nsew")
    # header
    header = f"{'Feature':<60}  {'Importance':>12}\n" + ("-" * 75) + "\n"
    box.insert("end", header)
    heatmap_buf = None
    if isinstance(entry, dict):
        feats = entry.get("features") or []
        is_shield_like_fi = str(cat_l) in ("shield", "buckler")
        def _keep_block_feature(f: dict) -> bool:
            name = str(f.get("name", "")).strip().lower()
            if is_shield_like_fi:
                return name != "#% increased block chance"
            return "block" not in name
        feats = [f for f in feats if _keep_block_feature(f)]
        # sort desc
        try:
            feats = sorted(feats, key=lambda d: float(d.get("importance", 0) or 0), reverse=True)
        except Exception:
            pass
        for f in feats:
            raw_name = str(f.get("name", "")); name_map = {"ar_norm":"armour","ev_norm":"evasion","es_norm":"energy shield","block_norm":"block"}; name = name_map.get(raw_name.strip().lower(), raw_name)
            imp  = float(f.get("importance", 0) or 0)
            perc = imp * 100.0
            box.insert("end", f"{name[:60]:<60}  {perc:>6.1f}%\n")
        # Add horizontal heatÃ¢â‚¬â€˜mapped bar chart for >5% features
        try:
            top_all = [(str(f.get("name", "")), float(f.get("importance", 0) or 0)) for f in feats]
            top = sorted(top_all, key=lambda t: t[1], reverse=True)[:8]
            if top:
                import io as _io
                import matplotlib.pyplot as _plt
                import numpy as _np
                name_map = {"ar_norm":"armour","ev_norm":"evasion","es_norm":"energy shield","block_norm":"block"}; names = [name_map.get(n.strip().lower(), n) for n, _v in top]
                vals = _np.array([v for _n, v in top], dtype=float)
                order = _np.argsort(vals)[::-1]
                names = [names[i] for i in order]
                vals = vals[order]
                cmap = _plt.cm.viridis
                norm = (vals - vals.min()) / (vals.max() - vals.min() + 1e-9)
                colours = cmap(norm)
                height = max(1.8, 0.38 * len(names) + 0.7)
                fig, ax = _plt.subplots(figsize=(6.3, height), dpi=115)
                ax.barh(range(len(names)), vals * 100.0, color=colours, edgecolor="#222")
                ax.set_yticks(range(len(names)))
                ax.set_yticklabels(names)
                ax.invert_yaxis()
                ax.set_xlabel("Importance (%)")
                ax.set_xlim(0, max(5.0, float(vals.max() * 100.0) * 1.10))
                for i, v in enumerate(vals * 100.0):
                    ax.text(v + 0.5, i, f"{v:0.1f}%", va="center", fontsize=9)
                fig.tight_layout()
                heatmap_buf = _io.BytesIO()
                fig.savefig(heatmap_buf, format="png")
                _plt.close(fig)
                heatmap_buf.seek(0)
        except Exception:
            logging.exception("Failed to render FI heatmap")
    box.configure(state="disabled")
    if heatmap_buf is not None:
        try:
            from poe2trade.app.gui.ui_helpers import scaled_png_percent as _scaled
            _scaled(frm, heatmap_buf, 0.9).grid(row=1, column=0, sticky="nsew")
        except Exception:
            logging.debug("Heatmap attach failed", exc_info=True)


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

    # Line 1 Ã¢â‚¬â€œ Price Prediction #1: "Price Prediction #1 - <model> - <Xe>"
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
            if isinstance(nearest_median, (int, float)):
                try:
                    med_txt = f"{int(round(float(nearest_median)))}e"
                except Exception:
                    med_txt = f"{nearest_median:.0f}e"
            if isinstance(nearest_mean, (int, float)):
                try:
                    mean_txt = f"{int(round(float(nearest_mean)))}e"
                except Exception:
                    mean_txt = f"{nearest_mean:.0f}e"
            parts = []
            if med_txt:
                parts.append(f"{med_txt} (median)")
            if mean_txt:
                parts.append(f"{mean_txt} (mean)")
            suffix = ", ".join(parts) if parts else (xe or "")
            line1 = f"Price Prediction #2 - {suffix}".rstrip()
        else:
            line1 = f"Price Prediction #{num} - {xe or ''}".rstrip()
        ctk.CTkLabel(
            content, text=line1, font=("Helvetica", 28, "bold"), text_color="white"
        ).pack(padx=8, pady=(4, 2))

        # Line 1b Ã¢â‚¬â€œ Relative <bucket> Value within {Category}
        # Build as three labels to colour only the bucket word
        if mode == "dataset" and show_line2 and label:
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

    # Line 2 Ã¢â‚¬â€œ nearest items (prefer explicit list of prices)
    if show_line2 and mode == "nearest" and combined_prices_line:
        # Keep same font/size as dataset second line for consistency
        ctk.CTkLabel(
            content,
            text=combined_prices_line,
            font=("Helvetica", 20),
            text_color="#EEEEEE",
        ).pack(padx=8, pady=(0, 4))
        return

    # Line 2  —  Price Prediction #2 (nearest items), only exalts
    if (
        show_line2
        and mode == "nearest"
        and isinstance(nearest_mean, (int, float))
        and isinstance(nearest_median, (int, float))
    ):
        # Mean/Median are now shown in line 1 to match requested format; avoid duplicating here.
        pass

    # Line 3  —  Combined prices list (optional, smaller, not bold)
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
    build_conf: bool = True,
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
    if build_conf and intervals and bucket_label:
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
_CORE_KEYS = {
    "ar_norm": "Armour",
    "ev_norm": "Evasion",
    "es_norm": "Energy Shield",
    # For Shield/Buckler overlays, include normalized Block when available
    "block_norm": "Block",
}

# Accept common synonyms in neighbour overlays to make core rows robust across
# categories and historical model bundles.
_CORE_SYNONYMS = {
    "ar_norm": ["ar_norm", "ar", "armour", "armor"],
    "ev_norm": ["ev_norm", "ev", "evasion rating", "evasion"],
    "es_norm": ["es_norm", "es", "energy shield"],
    "block_norm": ["block_norm", "block", "block chance"],
}

def _series_numeric(series: pd.Series, key: str) -> float:
    try:
        names = [str(n).lower() for n in series.index]
    except Exception:
        names = []
    targets = [str(key).lower()] + [str(a).lower() for a in _CORE_SYNONYMS.get(key, [])]
    for nm in targets:
        try:
            if nm in names:
                real = series.index[names.index(nm)]
                v = series.get(real, 0)
                return float(v if v is not None else 0)
        except Exception:
            continue
    # final fallback: direct access by original key
    try:
        return float(series.get(key, 0) or 0)
    except Exception:
        return 0.0
# Hide these from the modifiers list; handled by *_NORM already
_HIDE_DEF_PATTERNS = PCT_DEFENCE_PATTERNS | FLAT_DEFENCE_PATTERNS

# +---------------- HOT-KEY THROTTLING --------------------+
_hotkey_busy = {
    "super": threading.Lock(),  # Ctrl+1 / Ctrl+0 consolidated
    "filtered": threading.Lock(),  # Filtered overlay flow
    "discord_api": threading.Lock(),  # Discord API JSON DM
    "prediction_log": threading.Lock(),  # Prediction log popup
    "auction": threading.Lock(),  # Auction Tool single hotkey
}

_prediction_log_window: Optional[ctk.CTkToplevel] = None
_prediction_log_lock = threading.Lock()


# ---------------- utility hotkeys (show/copy/paste price) --------------
def _simulate_right_click() -> None:
    try:
        import ctypes
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        # MOUSEEVENTF_RIGHTDOWN = 0x0008; RIGHTUP = 0x0010
        user32.mouse_event(0x0008, 0, 0, 0, 0)
        user32.mouse_event(0x0010, 0, 0, 0, 0)
    except Exception:
        logging.exception("Right-click simulation failed")


def _handle_hotkey_show_price(_=None) -> None:
    try:
        _simulate_right_click()
    except Exception:
        pass


def _extract_int_from_clipboard(text: str) -> Optional[int]:
    import re
    m = re.search(r"[-+]?\d+", str(text))
    if m:
        try:
            return int(m.group(0))
        except Exception:
            return None
    return None


def _handle_hotkey_copy_price(_=None) -> None:
    global _cached_price_value
    try:
        keyboard.send("ctrl+c")
        time.sleep(0.1)
        raw = pyperclip.paste()
        val = _extract_int_from_clipboard(raw)
        if val is not None:
            _cached_price_value = val
            logging.info("Cached price copied: %s", val)
        else:
            logging.info("Clipboard did not contain an integer: %r", raw)
    except Exception:
        logging.exception("copy_price failed")


def _apply_cut_rule(v: int, rule: str) -> int:
    try:
        r = str(rule or "").strip()
        if not r:
            return max(0, int(v))
        # percentage reduction: e.g. "10%"
        if r.endswith('%'):
            num = r[:-1].strip()
            pct = float(num)
            return max(0, int(round(v * (1.0 - (pct / 100.0)))))
        # flat reduction: e.g. "5-"
        if r.endswith('-'):
            num = r[:-1].strip() or "0"
            dec = float(num)
            return max(0, int(round(v - dec)))
        # fallback: numeric treated as flat reduction
        dec = float(r)
        return max(0, int(round(v - dec)))
    except Exception:
        # safe fallback: subtract 5
        try:
            return max(0, int(v) - 5)
        except Exception:
            return 0


def _handle_hotkey_paste_price(_=None) -> None:
    global _cached_price_value
    try:
        # single-hotkey flow: copy -> compute -> replace (type), no clipboard clobber
        try:
            keyboard.send("ctrl+c")
        except Exception:
            pass
        text = _clipboard_text_with_retry(max_wait_ms=600, step_ms=60)
        val = _extract_int_from_clipboard(text)
        if val is None:
            # fallback to any cached value
            val = _cached_price_value
        if val is None:
            return
        rule = str(state.config.get("auction_cut_rule", "5-") or "5-")
        adj = _apply_cut_rule(int(val), rule)
        # Replace current selection by typing (avoids relying on clipboard paste)
        try:
            keyboard.send("backspace")
            time.sleep(0.02)
        except Exception:
            pass
        keyboard.write(str(adj))
    except Exception:
        logging.exception("paste_price failed")


def _bind_price_hotkeys() -> None:
    """(Prod) Auction Tool hotkey disabled; dev-only in gui_tk_dev."""
    try:
        logging.info("Auction hotkey disabled in prod build")
    except Exception:
        pass


def _run_with_lock(lock: threading.Lock, fn, *a, **kw):
    if not lock.acquire(blocking=False):
        return
    try:
        fn(*a, **kw)
    finally:
        lock.release()


def _clipboard_text_with_retry(max_wait_ms: int = 800, step_ms: int = 80) -> str:
    """Best-effort clipboard read after issuing Ctrl+C.

    On Windows the clipboard can be briefly locked right after copying.
    Retry for a short window to avoid throwing inside a Tk callback.
    """
    deadline = time.time() + max(0, max_wait_ms) / 1000.0
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            return str(pyperclip.paste() or "")
        except Exception as e:
            last_err = e
            time.sleep(max(1, step_ms) / 1000.0)
    try:
        return str(pyperclip.paste() or "")
    except Exception:
        logging.debug("Clipboard read failed after retries: %s", last_err)
        return ""


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
        # avoid duplicate block entries (we show block once via core block_norm)
        skip.update({"block", "block_norm", "block chance"})
    skip_lc = {s.lower() for s in skip}

    def _numeric(series, key: str) -> float:
        try:
            # Prefer robust lookup using synonyms for core keys
            if key in _CORE_KEYS:
                return _series_numeric(series, key)
            return float(series.get(key, 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    def _disp(value: float) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return float("nan")
        return round(v) if np.isfinite(v) else float("nan")

def _fmt_disp(value: float | None) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if not np.isfinite(v):
        return "-"
    try:
        return f"{int(v)}" if v.is_integer() else f"{v:g}"
    except Exception:
        return f"{v:g}"

    for key in _CORE_KEYS.keys():
        val = _numeric(base_series, key)
        if val == 0:
            continue
        rows.append(
            {
                "key": key,
                "label": str(_CORE_KEYS.get(key, key)).lower(),
                "raw": float(val),
                "display": _fmt_disp(_disp(val)),
                "group": "core",
            }
        )

    # Gather positive modifier values and sort by magnitude to better mirror
    # the prominence shown in KNN overlay cells.
    # Derive overlay columns for this category/segment so the filter list
    # mirrors the same set the KNN overlay uses for the left column.
    overlay_cols: set[str] = set()
    try:
        # Normalize category/segment similar to ml_unsuper path
        cat_lc = (category or "").strip().lower().replace(" ", "_")
        if cat_lc in {"scepter"}:  # alias
            cat_lc = "sceptre"
        # Segment inference from *_norm core values (same heuristic as gui_utils)
        ar, ev, es = (
            float(base_series.get(k, 0) or 0) for k in ("ar_norm", "ev_norm", "es_norm")
        )
        seg = None
        if cat_lc not in {"ring", "amulet", "belt", "jewel", "sceptre", "wand", "quiver"}:
            if ar and not (ev or es):
                seg = "ar_only"
            elif ev and not (ar or es):
                seg = "ev_only"
            elif es and not (ar or ev):
                seg = "es_only"
            elif ar and ev and not es:
                seg = "ar_ev_only"
            elif ar and es and not ev:
                seg = "ar_es_only"
            elif ev and es and not ar:
                seg = "ev_es_only"
            elif ar and ev and es:
                seg = "all_three"
        from pathlib import Path as _Path
        from poe2trade import poe2trade_root as _root
        from poe2trade.utils.ml_unsuper_utils import _load_unsuper_bundle as _load
        b = _load(cat_lc or "default_model", seg, _Path(_root) / "db" / "unsuper_models")
        if isinstance(b, dict) and "overlay_df" in b:
            overlay_cols = set(str(c).lower() for c in b["overlay_df"].columns)
    except Exception:
        overlay_cols = set()

    seen_core = set(_CORE_KEYS.keys())
    mod_candidates: list[tuple[str, float]] = []
    for key in (str(k) for k in base_series.index if str(k) not in seen_core):
        key_l = key.lower()
        if key_l in skip_lc:
            continue
        # If overlay columns are known, restrict to them so we match the KNN overlay set
        if overlay_cols and key_l not in overlay_cols:
            continue
        v = _numeric(base_series, key)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.0
        if v > 0:
            mod_candidates.append((key, v))

    # Sort by descending numeric value; tie-break by key for stability
    mod_candidates.sort(key=lambda kv: (-float(kv[1]), str(kv[0]).lower()))

    for key, v in mod_candidates:
        key_l = key.lower()
        disp_txt = _fmt_disp(_disp(v))
        rows.append(
            {
                "key": key,
                "label": key_l,
                "raw": float(v),
                "display": disp_txt,
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


def _build_filter_rows_from_parsed(parsed: dict, category: str | None) -> list[dict]:
    try:
        cat_l = (category or "").strip().lower()
        is_j = cat_l in {"ring", "amulet", "belt"}
        skip = {"price", "currency"}
        if not is_j:
            skip |= {"armour", "evasion", "evasion rating", "energy shield", "ar", "ev", "es"}
            skip |= {s.lower() for s in _HIDE_DEF_PATTERNS}
            skip |= {"block", "block_norm", "block chance"}
        # normalize parsed to lower keys
        items = []
        for k, v in (parsed or {}).items():
            kl = str(k).strip().lower()
            if kl in skip or kl in _CORE_KEYS:
                continue
            try:
                val = float(v)
            except (TypeError, ValueError):
                continue
            if val > 0:
                items.append((k, val))
        items.sort(key=lambda kv: (-float(kv[1]), str(kv[0]).lower()))
        rows = []
        # core first using parsed values if present
        for key, label in _CORE_KEYS.items():
            try:
                val = float(parsed.get(key, 0) or 0)
            except Exception:
                val = 0.0
            if val <= 0:
                continue
            disp = _fmt_disp(float(round(val)))
            rows.append({'key': key, 'label': str(label).lower(), 'raw': float(val), 'display': disp, 'group': 'core'})
        for k, v in items:
            disp = _fmt_disp(float(round(v)))
            rows.append({'key': str(k), 'label': str(k).lower(), 'raw': float(v), 'display': disp, 'group': 'mods'})
        return rows
    except Exception:
        return []


def _show_filtered_filter_popup(ctx: dict) -> None:
    """Pop up the filtered-overlay dialog to capture mod constraints."""
    if not (root and root.winfo_exists()):
        return

    rows = _build_filter_rows(ctx.get('base_X'), ctx.get('category'))
    if not rows:
        rows = _build_filter_rows_from_parsed(ctx.get('parsed') or {}, ctx.get('category'))
    # Fallback: if nothing was emitted, try to at least surface core rows
    if not rows:
        rows = rows or []
        base_X = ctx.get('base_X')
        if isinstance(base_X, pd.DataFrame) and not base_X.empty:
            base_series = base_X.iloc[0]
            for key, label in _CORE_KEYS.items():
                try:
                    val = _series_numeric(base_series, key)
                except Exception:
                    val = 0.0
                if not val:
                    continue
                rows.append({
                    'key': key,
                    'label': str(label).lower(),
                    'raw': float(val),
                    'display': _fmt_disp(float(round(val))),
                    'group': 'core',
                })
            # If still empty, bail gracefully.
            rows = [r for r in rows if r]
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

    def _populate_entries(builder: Callable[[dict[str, object]], Optional[str]]) -> None:
        for row, entry in entries:
            entry.delete(0, 'end')
            value = builder(row)
            if value:
                entry.insert(0, value)

    def _apply_match_mods() -> None:
        def _builder(row: dict[str, object]) -> Optional[str]:
            try:
                numeric = float(row.get('raw', 0) or 0)
            except (TypeError, ValueError):
                return None
            if numeric <= 0:
                return None
            return '1+'

        _populate_entries(_builder)

    def _apply_match_greater_mods() -> None:
        def _builder(row: dict[str, object]) -> Optional[str]:
            try:
                numeric = float(row.get('raw', 0) or 0)
            except (TypeError, ValueError):
                numeric = 0.0
            if numeric <= 0:
                return None
            display = str(row.get('display') or '').strip()
            if not display or display == '-':
                display = _fmt_disp(numeric)
            if not display or display == '-':
                return None
            return f'{display}+'

        _populate_entries(_builder)

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

    ctk.CTkButton(btn_frame, text='Match Mods', command=_apply_match_mods).pack(side='left', expand=True, fill='x', padx=(0, 6))
    ctk.CTkButton(btn_frame, text='Match Greater Mods', command=_apply_match_greater_mods).pack(side='left', expand=True, fill='x', padx=(0, 6))
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
        filtered_k = _resolve_knn_filtered_k(state.config)
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
                    top=filtered_k,
                    where=filters,
                )
        except Exception:
            logging.exception('Filtered overlay lookup failed')
            nbrs = None
        nbrs = _truncate_knn_df(nbrs, filtered_k)

        def finish() -> None:
            if nbrs is None or (hasattr(nbrs, 'empty') and getattr(nbrs, 'empty')):
                messagebox.showwarning('StashSage', 'No neighbours matched the filtered criteria.')
                return
            ctx_out = dict(ctx)
            ctx_out['filtered_neighbors'] = nbrs
            ctx_out['filters'] = filters
            ctx_out['knn_filtered_k'] = filtered_k
            _show_filtered_overlay_result(ctx_out)

        root.after(0, finish)

    threading.Thread(target=work, daemon=True).start()


def _show_filtered_overlay_result(ctx: dict) -> None:
    """Present the filtered overlay result as the consolidated dashboard."""
    if not (root and root.winfo_exists()):
        return

    base_X = ctx.get('base_X')
    nbrs = ctx.get('filtered_neighbors')
    knn_limit = ctx.get('knn_filtered_k')
    if not isinstance(knn_limit, int) or knn_limit <= 0:
        knn_limit = _resolve_knn_filtered_k(state.config)
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
            show_viz = _show_viz_enabled(state.config)
            ml_super: dict = gui_utils_main(raw_text, key='super') or {}
            parsed = parse_copied_item_text(raw_text)

            # Normalize category using gui_utils to singular internal token
            try:
                cat_norm, _seg_dummy = detect_category_segment(parsed)
            except Exception:
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
            ) = _extract_supervised_values(
                ml_super, cat_norm=cat_norm, seg_norm=seg_norm, build_conf=show_viz
            )
            if not show_viz:
                bucket_label = None
                bucket_low = None
                bucket_high = None
                bucket_median_val = display_value
                conf_buf = None

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

            try:
                log_entry = _build_prediction_log_entry(
                    text=raw_text,
                    ml_super=ml_super if isinstance(ml_super, dict) else {},
                    unsuper_df=nbrs,
                    item_name=item_name,
                    category=cat_norm,
                    segment=seg_norm,
                    source="filtered_overlay",
                    filters=ctx.get('filters'),
                    knn_limit=knn_limit,
                )
                _append_prediction_log(log_entry)
            except Exception:
                logging.exception("Prediction log append failed")

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
                    knn_limit=knn_limit,
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
        logging.warning("Invalid price filter %r Ã¢â‚¬â€œ defaulting to 1e (%s)", raw, exc)
        ml_unsuper_utils.set_price_filter("1e")


def _apply_knn_runtime_k(cfg: dict) -> None:
    raw = cfg.get("knn_filtered_k", config_manager.DEFAULT_CONFIG.get("knn_filtered_k", DEFAULT_KNN))
    try:
        ml_unsuper_utils.set_knn_runtime_k(raw)
        logging.info("KNN runtime k set to %r", raw)
    except Exception as exc:
        logging.warning("Invalid KNN runtime k %r; using default (%s)", raw, exc)
        ml_unsuper_utils.set_knn_runtime_k(DEFAULT_KNN)


def _show_viz_enabled(cfg: dict) -> bool:
    raw = cfg.get("show_viz_param", config_manager.DEFAULT_CONFIG.get("show_viz_param", False))
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _resolve_knn_filtered_k(cfg: dict) -> int:
    raw = cfg.get("knn_filtered_k", config_manager.DEFAULT_CONFIG.get("knn_filtered_k", DEFAULT_KNN))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        try:
            value = int(float(raw))
        except (TypeError, ValueError):
            return DEFAULT_KNN
    return value if value > 0 else DEFAULT_KNN


def _truncate_knn_df(df: Optional[pd.DataFrame], limit: int) -> Optional[pd.DataFrame]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
    try:
        max_rows = int(limit)
    except (TypeError, ValueError):
        return df
    if max_rows <= 0 or len(df) <= max_rows:
        return df
    return df.head(max_rows).reset_index(drop=True)


def _prediction_log_path() -> Optional[Path]:
    raw = str(
        state.config.get("prediction_log_dir")
        or config_manager.DEFAULT_CONFIG.get("prediction_log_dir", "")
    ).strip()
    if not raw:
        return None
    return Path(raw)


def _load_prediction_log_entries() -> list[dict]:
    path = _prediction_log_path()
    if path is None or not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        logging.exception("Prediction log load failed")
        return []
    if isinstance(data, dict):
        entries = data.get("entries", [])
        return entries if isinstance(entries, list) else []
    if isinstance(data, list):
        return data
    return []


def _write_prediction_log_entries(entries: list[dict]) -> None:
    path = _prediction_log_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"entries": entries}
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    except Exception:
        logging.exception("Prediction log save failed")


def _collect_knn_stats(
    unsuper_df: Optional[pd.DataFrame],
    *,
    knn_limit: Optional[int] = None,
) -> tuple[Optional[float], Optional[float], list[dict]]:
    neighbors: list[dict] = []
    vals: list[float] = []
    if isinstance(knn_limit, int) and knn_limit > 0:
        max_rows = knn_limit
    elif isinstance(unsuper_df, pd.DataFrame):
        max_rows = len(unsuper_df)
    else:
        max_rows = DEFAULT_KNN
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty:
        for _, row in unsuper_df.iterrows():
            pr = _price_string(row)
            price_display = None
            price_exalts = None
            if pr:
                price_display, price_exalts = pr
                vals.append(float(price_exalts))
            simple = _price_simple(row)
            item_name = (
                str(
                    row.get("item")
                    or row.get("item_name")
                    or row.get("Item Name")
                    or row.get("name")
                    or ""
                ).strip()
            )
            neighbors.append(
                {
                    "item_name": item_name,
                    "price_simple": simple,
                    "price_display": price_display,
                    "price_exalts": price_exalts,
                }
            )
            if len(neighbors) >= max_rows:
                break
    nearest_mean = float(np.mean(vals)) if vals else None
    nearest_median = float(np.median(vals)) if vals else None
    return nearest_mean, nearest_median, neighbors


def _format_prediction_log_filters(filters: dict[str, tuple[str, object]] | None) -> str:
    if not filters:
        return ""
    parts: list[str] = []

    def _fmt_num(value: object) -> str:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return str(value)
        if not np.isfinite(v):
            return str(value)
        try:
            return f"{int(v)}" if v.is_integer() else f"{v:g}"
        except Exception:
            return f"{v:g}"

    for key in sorted(filters.keys(), key=lambda k: str(k).lower()):
        entry = filters.get(key)
        if not entry:
            continue
        label = str(key).strip()
        if not label:
            continue
        try:
            op, raw_val = entry
        except (TypeError, ValueError):
            continue
        if op == "between" and isinstance(raw_val, (tuple, list)) and len(raw_val) == 2:
            lo, hi = raw_val
            try:
                lo_f, hi_f = sorted((float(lo), float(hi)))
                part = f"{label}: {_fmt_num(lo_f)}-{_fmt_num(hi_f)}"
            except (TypeError, ValueError):
                part = f"{label}: {raw_val}"
        elif op == "==":
            part = f"{label}={_fmt_num(raw_val)}"
        elif op == ">=":
            part = f"{label}>={_fmt_num(raw_val)}"
        else:
            part = f"{label} {op} {_fmt_num(raw_val)}"
        parts.append(part)

    return "; ".join(parts)


def _build_prediction_log_entry(
    *,
    text: str,
    ml_super: dict | None,
    unsuper_df: Optional[pd.DataFrame],
    item_name: str,
    category: str | None,
    segment: str | None,
    source: str,
    filters: dict[str, tuple[str, object]] | None = None,
    knn_limit: Optional[int] = None,
) -> dict:
    preds = {}
    if isinstance(ml_super, dict):
        raw_preds = ml_super.get("predictions")
        if isinstance(raw_preds, Mapping):
            preds = raw_preds
    xgb_val = preds.get("xgb") if isinstance(preds, dict) else None
    nearest_mean, nearest_median, neighbors = _collect_knn_stats(
        unsuper_df, knn_limit=knn_limit
    )
    filters_used = _format_prediction_log_filters(filters)
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "item_name": item_name,
        "category": category,
        "segment": segment,
        "xgb": xgb_val,
        "knn_mean": nearest_mean,
        "knn_median": nearest_median,
        "neighbors": neighbors,
        "item_text": text,
        "source": source,
        "filters_used": filters_used,
    }


def _append_prediction_log(entry: dict) -> None:
    if not entry:
        return
    with _prediction_log_lock:
        entries = _load_prediction_log_entries()
        entries.append(entry)
        _write_prediction_log_entries(entries)


def _show_prediction_log_popup() -> None:
    global _prediction_log_window
    if root is None or not root.winfo_exists():
        return
    if _prediction_log_window and _prediction_log_window.winfo_exists():
        _prediction_log_window.lift()
        _prediction_log_window.focus_force()
        return

    entries = _load_prediction_log_entries()
    if not entries:
        messagebox.showinfo("Prediction Log", "No prediction history found.")
        return

    win = ctk.CTkToplevel(root)
    win.title("Prediction Log")
    win.geometry("1160x720")
    win.minsize(980, 560)
    _prediction_log_window = win

    def _on_close() -> None:
        global _prediction_log_window
        if _prediction_log_window and _prediction_log_window.winfo_exists():
            _prediction_log_window.destroy()
        _prediction_log_window = None

    win.protocol("WM_DELETE_WINDOW", _on_close)

    container = ctk.CTkFrame(win)
    container.pack(fill="both", expand=True, padx=14, pady=14)
    container.rowconfigure(1, weight=1)
    container.columnconfigure(0, weight=1)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    header.columnconfigure(0, weight=1)

    header_label = ctk.CTkLabel(
        header,
        text="Prediction History",
        font=("Segoe UI", 18, "bold"),
    )
    header_label.grid(row=0, column=0, sticky="w")

    content = ctk.CTkFrame(container, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew")
    content.rowconfigure(0, weight=1)
    content.columnconfigure(0, weight=3)
    content.columnconfigure(1, weight=2)

    tree_frame = ctk.CTkFrame(content, corner_radius=12)
    tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    columns = ("timestamp", "item_name", "xgb", "knn_mean", "knn_median", "filters_used")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
    tree.heading("timestamp", text="Timestamp")
    tree.heading("item_name", text="Item")
    tree.heading("xgb", text="XGB")
    tree.heading("knn_mean", text="KNN Mean")
    tree.heading("knn_median", text="KNN Median")
    tree.heading("filters_used", text="Filters Used")

    tree.column("timestamp", width=130, anchor="w", stretch=False)
    tree.column("item_name", width=170, anchor="w", stretch=False)
    tree.column("xgb", width=70, anchor="center", stretch=False)
    tree.column("knn_mean", width=70, anchor="center", stretch=False)
    tree.column("knn_median", width=70, anchor="center", stretch=False)
    tree.column("filters_used", width=200, anchor="w", stretch=True)

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")

    detail_frame = ctk.CTkFrame(content, corner_radius=12)
    detail_frame.grid(row=0, column=1, sticky="nsew")
    detail_frame.columnconfigure(0, weight=1)
    detail_frame.rowconfigure(1, weight=1)

    detail_header = ctk.CTkFrame(detail_frame, fg_color="transparent")
    detail_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
    detail_header.columnconfigure(0, weight=1)

    detail_icon: Optional[ctk.CTkLabel] = None
    detail_item_label = ctk.CTkLabel(detail_header, text="", font=("Segoe UI", 14, "bold"))
    detail_item_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

    detail_box = ctk.CTkTextbox(detail_frame, height=220)
    detail_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(10, 12))

    def _sort_key(entry: dict) -> str:
        return str(entry.get("timestamp") or "")

    sorted_entries = sorted(entries, key=_sort_key, reverse=True)[:50]

    def _fmt(val: object) -> str:
        if isinstance(val, (int, float)):
            return f"{val:.1f}"
        return "" if val is None else str(val)

    def _populate_tree() -> None:
        tree.delete(*tree.get_children())
        for entry in sorted_entries:
            filters_used = entry.get("filters_used") or _format_prediction_log_filters(entry.get("filters"))
            tree.insert(
                "",
                "end",
                values=(
                    entry.get("timestamp", ""),
                    entry.get("item_name", ""),
                    _fmt(entry.get("xgb")),
                    _fmt(entry.get("knn_mean")),
                    _fmt(entry.get("knn_median")),
                    filters_used,
                ),
            )

    def _wipe_logs() -> None:
        nonlocal sorted_entries
        if not messagebox.askyesno("Prediction Log", "Wipe all prediction log entries?"):
            return
        _write_prediction_log_entries([])
        sorted_entries = []
        _populate_tree()
        detail_box.delete("1.0", "end")
        detail_item_label.configure(text="")
        if detail_icon and detail_icon.winfo_exists():
            detail_icon.destroy()

    wipe_btn = ctk.CTkButton(header, text="Wipe Logs", command=_wipe_logs, width=110)
    wipe_btn.grid(row=0, column=1, sticky="e")

    _populate_tree()

    def _update_detail_icon(item_name: str | None) -> None:
        nonlocal detail_icon
        if detail_icon and detail_icon.winfo_exists():
            detail_icon.destroy()
        detail_icon = None
        if not item_name:
            detail_item_label.configure(text="")
            return
        detail_icon = icon_label(
            state,
            detail_header,
            item_name,
            target_w=48,
            target_h=48,
            overlay_window=win,
        )
        if detail_icon:
            detail_icon.grid(row=0, column=0, sticky="w")
        detail_item_label.configure(text=item_name)

    def _on_select(_event=None) -> None:
        sel = tree.selection()
        if not sel:
            return
        idx = tree.index(sel[0])
        if idx < 0 or idx >= len(sorted_entries):
            return
        entry = sorted_entries[idx]
        detail_box.delete("1.0", "end")
        detail_box.insert("end", entry.get("item_text", ""))
        _update_detail_icon(entry.get("item_name"))

    tree.bind("<<TreeviewSelect>>", _on_select)

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
    # Focus
    "focus": "Focus",
    # Helmet
    "helm": "Helmet",
    "helmet": "Helmet",
    "mask": "Helmet",
    "crown": "Helmet",
    "cap": "Helmet",
    "greathelm": "Helmet",
    "tiara": "Helmet",
    # Shields
    "shield": "Shield",
    "buckler": "Buckler",
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
    # Core keys are AR/EV/ES plus Block when available. For shield-like
    # items we want Block at the top of the core section. Since overlay
    # rows for shields/bucklers include a computed 'block_norm', use its
    # presence as a signal to place Block first.
    _core_all = list(_CORE_KEYS.keys())
    # Restrict Block to shield-like items (from item_name heuristics)
    nm_lc = str(item_name or "").lower()
    is_shield_like = ("shield" in nm_lc) or ("buckler" in nm_lc)
    if (
        is_shield_like
        and ("block_norm" in getattr(base_series, "index", []) or "block_norm" in getattr(df, "columns", []))
    ):
        core = ["block_norm"] + [k for k in _core_all if k != "block_norm"]
    else:
        core = [k for k in _core_all if k != "block_norm"]
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

    def _numeric(series: pd.Series, key: str) -> float:
        try:
            if key in _CORE_KEYS:
                return _series_numeric(series, key)
            return float(series.get(key, 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    def _disp(v: float, is_core: bool) -> float:
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return float("nan")
        return round(fv) if np.isfinite(fv) else float("nan")

    def _fmt_disp(d: float | None) -> str:
        try:
            v = float(d)
        except (TypeError, ValueError):
            return "-"
        if not np.isfinite(v):
            return "-"
        try:
            return f"{int(v)}" if v.is_integer() else f"{v:g}"
        except Exception:
            return f"{v:g}"

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

    for r, (_, nbr) in enumerate(df.iterrows()):
        try:
            # split features: core first, then everything else
            noncore_candidates = sorted((set(base_series.index) | set(nbr.index)) - set(core) - _SKIP)
            noncore_rows = []
            for order_idx, k in enumerate(noncore_candidates):
                # Block is a shield/buckler-only base stat. For shield-like items
                # it is shown in the core section; elsewhere hide stale columns.
                try:
                    lk = str(k).strip().lower()
                    is_block_related = (
                        lk in ("block", "block_norm", "block chance")
                        or lk == "#% increased block chance"
                    )
                    if is_block_related:
                        continue
                except Exception:
                    pass
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

            # ----- core rows first (only non-zero base stats) -----
            printed_any_core = False
            for k in core:
                b_raw = _numeric(base_series, k)
                n_raw = _numeric(nbr, k)
                if b_raw == 0 and k != "block_norm":
                    continue

                printed_any_core = True
                b_disp = _disp(b_raw, True)
                n_disp = _disp(n_raw, True)

                label = _CORE_KEYS.get(k, k)
                left_txt = f"{label}: {_fmt_disp(b_disp)}"
                right_txt = f"{label}: {_fmt_disp(n_disp)}"

                delta = n_disp - b_disp
                if np.isfinite(delta) and delta != 0:
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
                if np.isfinite(delta) and delta != 0:
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
        except Exception:
            logging.exception("KNN row render failed")



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



def _bind_prediction_log_hotkey(custom: str | None) -> None:
    """Bind prediction log hotkey to *custom* or default with fallback."""
    global _prediction_log_hotkey_handle

    desired = (custom or "").strip() or "ctrl+3"

    if _prediction_log_hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_prediction_log_hotkey_handle)
        except Exception:
            logging.debug("Previous prediction log hotkey removal failed", exc_info=True)
        finally:
            _prediction_log_hotkey_handle = None

    try:
        _prediction_log_hotkey_handle = keyboard.add_hotkey(
            desired, _handle_hotkey_prediction_log, suppress=False
        )
        logging.info("Prediction log hotkey bound to %s", desired)
        return
    except Exception as exc:
        logging.error("Failed to bind prediction log hotkey %r: %s", desired, exc)

    if desired.lower() != "ctrl+3":
        try:
            _prediction_log_hotkey_handle = keyboard.add_hotkey(
                "ctrl+3", _handle_hotkey_prediction_log, suppress=False
            )
            logging.info("Prediction log hotkey reverted to %s", "ctrl+3")
        except Exception as fallback_exc:
            logging.error(
                "Could not bind fallback prediction log hotkey %r: %s",
                "ctrl+3",
                fallback_exc,
            )
            _prediction_log_hotkey_handle = None
    else:
        _prediction_log_hotkey_handle = None

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


# ------------- UNSUPERVISED overlay (Ã¢â‚¬Å“Price MirrorÃ¢â‚¬Â) ----
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
    effective_knn = _resolve_knn_filtered_k(state.config)
    title_txt = f"Based on {effective_knn} Nearest Items (Ordered) with Price Filter {pf}:"
    tags, vals = [], []
    for _, row in df.iterrows():
        simple = _price_simple(row)
        if simple:
            tags.append(simple)
        pr = _price_string(row)
        if pr:
            vals.append(pr[1])
        if len(tags) == effective_knn:
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
    ov.title(f"StashSage Price Predictions  —  {item}")
    ov.bind("<Escape>", lambda _e: _destroy_overlay())
    ov.attributes("-topmost", True)
    ov.after_idle(lambda: ov.attributes("-topmost", False))
    try:
        ov.state("zoomed")
    except Exception:
        pass
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
    effective_knn = _resolve_knn_filtered_k(state.config)
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty:
        tags, vals = [], []
        for _, row in unsuper_df.iterrows():
            simple = _price_simple(row)
            if simple:
                tags.append(simple)
            pr = _price_string(row)
            if pr:
                vals.append(pr[1])
            if len(tags) == effective_knn:
                break
        if vals:
            nearest_mean = float(np.mean(vals))
            nearest_median = float(np.median(vals))
        combined_line = f"Based on {effective_knn} Nearest Items (Ordered) with Price Filter {pf}: [{', '.join(tags)}]"

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
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty:
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
        # Prefer the base feature row passed in; fall back to an empty series if unavailable
        try:
            base_series = unsuper_X.iloc[0] if isinstance(unsuper_X, pd.DataFrame) and not unsuper_X.empty else pd.Series(dtype=float)
        except Exception:
            base_series = pd.Series(dtype=float)
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

    # window geometry  —  start large enough by default, within screen bounds
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
            show_viz = _show_viz_enabled(state.config)
            ml_super: dict = gui_utils_main(text, key="super") or {}
            parsed = parse_copied_item_text(text)

            unsuper = gui_utils_main(text, key="unsuper")
            if unsuper:
                unsuper_X, unsuper_df = unsuper
            else:
                unsuper_X = unsuper_df = None

            # Derive category/segment safely here
            # Normalize category using gui_utils to singular internal token
            try:
                cat_norm, _seg_dummy = detect_category_segment(parsed)
            except Exception:
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
            ) = _extract_supervised_values(
                ml_super, cat_norm=cat_norm, seg_norm=seg_norm, build_conf=show_viz
            )
            if not show_viz:
                bucket_label = None
                bucket_low = None
                bucket_high = None
                bucket_median_val = display_value
                conf_buf = None

            # Names
            item_name = (
                (ml_super.get("item_name") if isinstance(ml_super, dict) else None)
                or _parse_item(text)
                or "(Unknown item)"
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

            try:
                log_entry = _build_prediction_log_entry(
                    text=text,
                    ml_super=ml_super if isinstance(ml_super, dict) else {},
                    unsuper_df=unsuper_df,
                    item_name=item_name,
                    category=cat_norm,
                    segment=seg_norm,
                    source="overlay",
                )
                _append_prediction_log(log_entry)
            except Exception:
                logging.exception("Prediction log append failed")

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

        except FileNotFoundError as exc:
            exc_msg = str(exc) or "Required model assets are missing for this item."
            def _err_missing() -> None:
                try:
                    root.configure(cursor="")
                except Exception:
                    pass
                messagebox.showerror("StashSage", exc_msg)

            root.after(0, _err_missing)

        except Exception as exc:
            # Surface any errors on the UI thread. Capture message here because
            # exception variables from an `except ... as exc` clause are cleared
            # after the block, which breaks late-bound closures on Tk callbacks.
            exc_msg = f"{exc}"
            def _err():
                try:
                    root.configure(cursor="")
                except Exception:
                    pass
                messagebox.showerror("StashSage", f"Scoring failed:\n{exc_msg}")

            root.after(0, _err)

    threading.Thread(target=work, daemon=True).start()


def _process_super_gui(text: str) -> None:
    if not _show_viz_enabled(state.config):
        messagebox.showinfo(
            "StashSage",
            "XGB visualizations are disabled in settings.",
        )
        return
    ml = gui_utils_main(text, key="super") or {}
    item = ml.get("item_name") or _parse_item(text) or "(Unknown item)"

    parsed = parse_copied_item_text(text)
    try:
        cat_norm, _seg_dummy = detect_category_segment(parsed)
    except Exception:
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
    show_viz = _show_viz_enabled(state.config)
    ml: dict = gui_utils_main(text, key="super") or {}
    item = (ml.get("item_name") if isinstance(ml, dict) else None) or _parse_item(text) or "(Unknown item)"

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
    ) = _extract_supervised_values(
        ml, cat_norm=cat_norm, seg_norm=seg_norm, build_conf=show_viz
    )
    if not show_viz:
        bucket_lbl = None
        bucket_low = None
        bucket_high = None
        bucket_median_val = display_value

    price_buf = None
    table_buf = None
    conf_buf = None
    if show_viz and intervals and bucket_lbl:
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

    try:
        result = gui_utils_main(text, key="unsuper")
    except FileNotFoundError as exc:
        messagebox.showerror("StashSage", str(exc) or "Required model assets are missing for this item.")
        return
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
            _hotkey_busy["super"], _score_dashboard_async, _clipboard_text_with_retry()
        ),
    )


def _handle_hotkey_filtered(_=None):
    keyboard.press_and_release("ctrl+c")
    root.after(
        200,
        lambda: _run_with_lock(
            _hotkey_busy["filtered"], _start_filtered_overlay_async, _clipboard_text_with_retry()
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
            _hotkey_busy["discord_api"], _start_discord_api_send_async, _clipboard_text_with_retry()
        ),
    )


def _handle_hotkey_prediction_log(_=None):
    root.after(
        0,
        lambda: _run_with_lock(
            _hotkey_busy["prediction_log"], _show_prediction_log_popup
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
        inner, text="Browse...", width=90, command=lambda e=entry: _browse_for_client(e)
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
    def _entry_or_config(entry_obj, key: str) -> str:
        value = str(state.config.get(key, "") or "").strip()
        if entry_obj is not None:
            try:
                value = entry_obj.get().strip()
            except Exception:
                pass
        return value

    pf_raw = price_filter_entry.get().strip() or str(DEFAULT_PRICE_FILTER)
    if not PRICE_FILTER_RE.fullmatch(pf_raw):
        messagebox.showerror(
            "Invalid Price Filter",
            "Must be a number followed by E, C, or D (e.g. 100e, 50c, 10D)",
        )
        return
    knn_filtered_raw = ""
    if knn_filtered_k_entry is not None:
        try:
            knn_filtered_raw = knn_filtered_k_entry.get().strip()
        except Exception:
            knn_filtered_raw = ""
    if not knn_filtered_raw:
        knn_filtered_val = _resolve_knn_filtered_k(config_manager.DEFAULT_CONFIG)
    else:
        if not knn_filtered_raw.isdigit():
            messagebox.showerror(
                "Invalid Filtered KNN Count",
                "Filtered KNN count must be a whole number (e.g. 3, 10).",
            )
            return
        knn_filtered_val = int(knn_filtered_raw)
        if knn_filtered_val <= 0:
            messagebox.showerror(
                "Invalid Filtered KNN Count",
                "Filtered KNN count must be at least 1.",
            )
            return
    show_viz_value = _show_viz_enabled(state.config)
    if show_viz_var is not None:
        try:
            show_viz_value = bool(show_viz_var.get())
        except Exception:
            show_viz_value = _show_viz_enabled(state.config)
    state.config.update(
        auction_hotkey=_entry_or_config(auction_hotkey_entry, "auction_hotkey"),
        auction_cut_rule=_entry_or_config(auction_rule_entry, "auction_cut_rule"),
        client_type=client_choice.get(),
        steam_client_log_dir=steam_entry.get().strip(),
        ggg_client_log_dir=ggg_entry.get().strip(),
        prediction_log_dir=_entry_or_config(prediction_log_entry, "prediction_log_dir"),
        discord_user_id=discord_id_entry.get().strip(),
        discord_bot_token=discord_token_entry.get().strip(),
        price_mirror_filter=pf_raw,
        knn_filtered_k=knn_filtered_val,
        show_viz_param=show_viz_value,
        custom_hotkey=(
            custom_hotkey_entry.get().strip() if custom_hotkey_entry else ""
        ),
        filtered_overlay_hotkey=(
            filtered_hotkey_entry.get().strip() if filtered_hotkey_entry else ""
        ),
        discord_api_hotkey=(
            discord_api_hotkey_entry.get().strip() if discord_api_hotkey_entry else ""
        ),
        prediction_log_hotkey=(
            prediction_log_hotkey_entry.get().strip()
            if prediction_log_hotkey_entry
            else ""
        ),
    )
    _apply_price_filter(state.config)
    _apply_knn_runtime_k(state.config)
    _apply_knn_runtime_k(state.config)
    # Persist to disk first, then hot-reload in running services
    try:
        config_manager.save_config(state.config)
    except Exception as exc:
        logging.exception("Failed to save config to disk")
        messagebox.showerror(
            "StashSage",
            f"Could not save settings:\n{exc}",
            parent=root if root else None,
        )
        return
    update_config(state.config)
    _bind_price_hotkeys()
    _bind_overlay_hotkey(state.config.get("custom_hotkey"))
    _bind_filtered_overlay_hotkey(state.config.get("filtered_overlay_hotkey"))
    _bind_discord_api_hotkey(state.config.get("discord_api_hotkey"))
    _bind_prediction_log_hotkey(state.config.get("prediction_log_hotkey"))
    # _refresh_log_files(state.config)
    _enable_services_if_ready(state.config)
    _auto_resize_root()
    messagebox.showinfo(
        "StashSage",
        "Settings updated and reloaded successfully.",
        parent=root if root else None,
    )


# ????????????? main Tk entry-point ???????????????????????
def run_tkinter_app(cfg: Optional[dict] = None) -> None:
    """Launch the CustomTkinter settings window."""
    global root, steam_entry, ggg_entry, steam_browse_btn, ggg_browse_btn
    global prediction_log_entry, prediction_log_browse_btn
    global discord_id_entry, discord_token_entry, price_filter_entry, knn_filtered_k_entry, show_viz_var, filtered_hotkey_entry, discord_api_hotkey_entry
    global prediction_log_hotkey_entry, client_choice, custom_hotkey_entry

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
    _bind_prediction_log_hotkey(state.config.get("prediction_log_hotkey"))

    def _set_entry(entry_obj, value: str) -> None:
        if entry_obj is None:
            return
        entry_obj.delete(0, "end")
        entry_obj.insert(0, value)

    def _reset_overlay_defaults() -> None:
        defaults = config_manager.DEFAULT_CONFIG
        _set_entry(custom_hotkey_entry, defaults.get("custom_hotkey", ""))
        _set_entry(
            filtered_hotkey_entry,
            defaults.get("filtered_overlay_hotkey", DEFAULT_FILTERED_OVERLAY_HOTKEY),
        )
        _set_entry(
            prediction_log_hotkey_entry,
            defaults.get("prediction_log_hotkey", "ctrl+3"),
        )
        if show_viz_var is not None:
            try:
                show_viz_var.set(bool(defaults.get("show_viz_param", False)))
            except Exception:
                pass
        _set_entry(
            knn_filtered_k_entry,
            str(defaults.get("knn_filtered_k", DEFAULT_KNN)),
        )
        _set_entry(
            price_filter_entry,
            str(defaults.get("price_mirror_filter", DEFAULT_PRICE_FILTER)),
        )

    def _reset_file_defaults() -> None:
        defaults = config_manager.DEFAULT_CONFIG
        client_default = defaults.get("client_type", "steam")
        if client_choice is not None:
            client_choice.set(client_default)
        _set_entry(steam_entry, defaults.get("steam_client_log_dir", DEFAULT_STEAM))
        _set_entry(ggg_entry, defaults.get("ggg_client_log_dir", DEFAULT_GGG))
        _set_entry(prediction_log_entry, defaults.get("prediction_log_dir", ""))
        _on_client_toggle(client_default)

    def _reset_discord_defaults() -> None:
        defaults = config_manager.DEFAULT_CONFIG
        _set_entry(discord_id_entry, defaults.get("discord_user_id", ""))
        _set_entry(discord_token_entry, defaults.get("discord_bot_token", ""))
        _set_entry(
            discord_api_hotkey_entry,
            defaults.get("discord_api_hotkey", DEFAULT_DISCORD_API_HOTKEY),
        )

    general_section = _CollapsibleSection(
        root, "Overlay Settings", collapsed=True, on_toggle=_auto_resize_root
    )
    general_section.pack(fill="x", expand=False)

    custom_hotkey_entry = _entry(
        general_section.content,
        "Overlay Hotkey (e.g. ctrl+1)",
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

    prediction_log_hotkey_entry = _entry(
        general_section.content,
        "Prediction Log Hotkey (e.g. ctrl+3)",
        (state.config.get("prediction_log_hotkey", "") or "").strip(),
    )
    state.prediction_log_hotkey_entry = prediction_log_hotkey_entry

    show_viz_var = ctk.BooleanVar(value=_show_viz_enabled(state.config))
    state.show_viz_var = show_viz_var
    ctk.CTkCheckBox(
        general_section.content,
        text="Show XGB visualizations (Low/Medium/High, distributions, FI)",
        variable=show_viz_var,
    ).pack(anchor="w", padx=10, pady=(12, 2))
    ctk.CTkLabel(
        general_section.content,
        text="Turn off to skip XGB charts and feature importances for faster overlays.",
        text_color="#AAAAAA",
        font=("Consolas", 11),
    ).pack(anchor="w", padx=10, pady=(0, 6))

    knn_filtered_k_entry = _entry(
        general_section.content,
        "Number of Similar Items Returned",
        str(state.config.get("knn_filtered_k", config_manager.DEFAULT_CONFIG.get("knn_filtered_k", DEFAULT_KNN))),
        digits_only=True,
    )
    state.knn_filtered_k_entry = knn_filtered_k_entry

    price_filter_entry = _entry(
        general_section.content,
        "Nearest Items Price Filter (e.g. 40e, 100d, 20c, 10a)",
        str(state.config.get("price_mirror_filter", DEFAULT_PRICE_FILTER)),
        allow_float=True,
    )
    state.price_filter_entry = price_filter_entry
    # conversion hint (rounded whole integers) - start from 1 divine
    try:
        c_per_d = int(round(float(divine_exalt) / max(float(chaos_exalt), 1e-9)))
        e_per_d = int(round(float(divine_exalt)))
        a_per_d = int(round(float(divine_exalt) / max(float(annul_exalt), 1e-9)))
        hint = f"(*) Conversion rate used 1 d = {c_per_d} c = {e_per_d} e = {a_per_d} a"
    except Exception:
        hint = "(*) 1 d = ? c = ? e = ? a"
    ctk.CTkLabel(
        general_section.content,
        text=hint,
        text_color="#AAAAAA",
        font=("Consolas", 12, "bold"),
    ).pack(pady=(0, 10))
    ctk.CTkButton(
        general_section.content,
        text="Reset Overlay Settings",
        command=_reset_overlay_defaults,
        corner_radius=8,
    ).pack(anchor="w", padx=10, pady=(0, 10))

    discord_section = _CollapsibleSection(
        root, "Discord Bot Settings", collapsed=True, on_toggle=_auto_resize_root
    )
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
        "Discord API Hotkey (e.g. ctrl+4)",
        (state.config.get("discord_api_hotkey", "") or "").strip()
        or DEFAULT_DISCORD_API_HOTKEY,
    )
    state.discord_api_hotkey_entry = discord_api_hotkey_entry

    file_section = _CollapsibleSection(
        root, "File Settings", collapsed=True, on_toggle=_auto_resize_root
    )
    file_section.pack(fill="x", expand=False)

    # client radio buttons
    client_choice = ctk.StringVar(value=state.config.get("client_type", "steam"))
    state.client_choice = client_choice
    sel = ctk.CTkFrame(file_section.content, corner_radius=8)
    sel.pack(pady=8, padx=10, fill="x")
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
        file_section.content,
        "Steam Log Location",
        state.config.get("steam_client_log_dir", "") or DEFAULT_STEAM,
    )
    state.steam_entry = steam_entry
    state.steam_browse_btn = steam_browse_btn
    ggg_entry, ggg_browse_btn = _file_row(
        file_section.content,
        "GGG Log Location",
        state.config.get("ggg_client_log_dir", "") or DEFAULT_GGG,
    )
    state.ggg_entry = ggg_entry
    state.ggg_browse_btn = ggg_browse_btn
    prediction_log_entry, prediction_log_browse_btn = _file_row(
        file_section.content,
        "Prediction Log Location",
        state.config.get("prediction_log_dir", "") or "",
    )
    state.prediction_log_entry = prediction_log_entry
    state.prediction_log_browse_btn = prediction_log_browse_btn
    _on_client_toggle(client_choice.get())
    ctk.CTkButton(
        discord_section.content,
        text="Reset Discord Settings",
        command=_reset_discord_defaults,
        corner_radius=8,
    ).pack(anchor="w", padx=10, pady=(4, 10))
    ctk.CTkButton(
        file_section.content,
        text="Reset File Settings",
        command=_reset_file_defaults,
        corner_radius=8,
    ).pack(anchor="w", padx=10, pady=(4, 10))

    # (Prod) Auction Price Tool section removed; keep in gui_tk_dev only


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
    ctk.CTkButton(
        button_row,
        text="Stash Scrape",
        command=_open_stash_scrape_dialog,
        corner_radius=8,
    ).pack(side="left", expand=True, fill="x", padx=(8, 0))

    # _refresh_log_files(state.config)
    _enable_services_if_ready(state.config)
    _bind_price_hotkeys()
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




# ------------- CONSOLIDATED DASHBOARD (supervised + KNN) -------------
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
    *,
    filters: dict[str, tuple[str, object]] | None = None,
    knn_limit: Optional[int] = None,
) -> None:
    """Combined overlay with supervised bars/charts and KNN mirror cells."""
    global overlay, root
    if not (root and root.winfo_exists()):
        return
    show_viz = _show_viz_enabled(state.config)

    _destroy_overlay()
    overlay = ctk.CTkToplevel(root)
    state.overlay = overlay
    overlay.images = []
    ov = overlay

    # Window chrome
    try:
        _ico = str(Path(__file__).with_name("stashsage_logo.ico"))
        ov.iconbitmap(_ico)
    except Exception:
        pass
    # Stable, centered window (no maximize) to avoid load-time reflow
    ov.title(f"StashSage Price Predictions  —  {item}")
    ov.bind("<Escape>", lambda _e: _destroy_overlay())
    ov.attributes("-topmost", True)
    ov.after_idle(lambda: ov.attributes("-topmost", False))

    # Pre-size and center early to reduce visual jumping while widgets layout
    try:
        sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
        init_w = min(int(sw * 0.80), 1600)
        init_h = min(int(sh * 0.88), 1000)
        ov.geometry(f"{init_w}x{init_h}+{(sw - init_w)//2}+{(sh - init_h)//2}")
        ov.minsize(1000, 700)
    except Exception:
        pass

    # Container
    cont = ctk.CTkScrollableFrame(ov, corner_radius=10)
    cont.pack(fill="both", expand=True, padx=8, pady=8)
    cont.grid_rowconfigure(0, weight=0)
    cont.grid_rowconfigure(1, weight=0)
    cont.grid_rowconfigure(2, weight=0)
    cont.grid_rowconfigure(3, weight=0)
    cont.grid_rowconfigure(4, weight=1)
    cont.grid_columnconfigure((0, 1), weight=1)

    # Row 0: toolbar removed (FI button no longer shown)

    # Row 1: dataset bar
    if isinstance(display_pred_value, (int, float)):
        bar1 = ctk.CTkFrame(cont, fg_color="transparent")
        bar1.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        _bucket_badge(
            bar1,
            bucket_label,
            bucket_median,
            bucket_low,
            bucket_high,
            display_pred_value,
            None,
            None,
            None,
            mode="dataset",
            category_title=(category_title or (cat_norm or "").replace("_", " ").title()),
            dataset_pred_value=display_pred_value,
        )

    if show_viz:
        # Row 2: predicted distribution (left) + feature importances (right)
        try:
            model_dir = Path(poe2trade_root) / "db" / "super_models"
            cand: list[Path] = []
            if cat_norm and seg_norm:
                cand.append(model_dir / f"{cat_norm}_{seg_norm}_scoring.json")
                if cat_norm == "body_armour":
                    cand.append(model_dir / f"body_armor_{seg_norm}_scoring.json")
            elif cat_norm:
                cand.append(model_dir / f"{cat_norm}_scoring.json")
            json_path = next((p for p in cand if p.is_file()), None)
            if json_path is not None:
                df_scored = _load_scoring_json_once(json_path)
                if isinstance(df_scored, pd.DataFrame) and not df_scored.empty:
                    buf = generate_predicted_overlay_with_marker(
                        df_scored,
                        display_pred_value if isinstance(display_pred_value, (int, float)) else 0.0,
                        title=f"{cat_norm}{('/' + seg_norm) if seg_norm else ''} — Predicted Distributions",
                    )
                    _scaled_png_percent(cont, buf, 0.49).grid(
                        row=2, column=0, columnspan=1, sticky="nsew", padx=4, pady=4
                    )
        except Exception:
            pass

        # Row 2 (right): embedded feature importances viz from manifest
        try:
            items = _load_fi_manifest()
            cat_l = str(cat_norm or "").strip().lower()
            seg_l = (str(seg_norm).strip().lower() if seg_norm else None)
            entry: dict | None = None
            # prefer XGB entry if available
            for e in items:
                c = str(e.get("category", "")).strip().lower()
                s = e.get("segment")
                s_l = (str(s).strip().lower() if s is not None else None)
                mt = str(e.get("model_type", "")).strip().upper() or "XGB"
                if c == cat_l and s_l == seg_l and mt == "XGB":
                    entry = e; break
            if entry is None:
                # fallback to matching category with no segment, or any model
                for e in items:
                    c = str(e.get("category", "")).strip().lower()
                    s = e.get("segment")
                    s_l = (str(s).strip().lower() if s is not None else None)
                    if c == cat_l and (s_l is None):
                        entry = e; break
            if isinstance(entry, dict):
                feats = entry.get("features") or []
                is_shield_like_fi = cat_l in ("shield", "buckler")
                feats = [
                    f for f in feats
                    if (
                        str(f.get("name", "")).strip().lower() != "#% increased block chance"
                        if is_shield_like_fi
                        else "block" not in str(f.get("name", "")).strip().lower()
                    )
                ]
                # sort and limit to top 8
                try:
                    feats = sorted(feats, key=lambda d: float(d.get("importance", 0) or 0), reverse=True)[:8]
                except Exception:
                    pass
                if feats:
                    import io as _io
                    import matplotlib.pyplot as _plt
                    import numpy as _np
                    name_map = {"ar_norm":"armour","ev_norm":"evasion","es_norm":"energy shield","block_norm":"block"}
                    names = [name_map.get(str(f.get("name","")) .strip().lower(), str(f.get("name",""))) for f in feats]
                    vals  = _np.array([float(f.get("importance", 0) or 0) for f in feats], dtype=float)
                    order = _np.argsort(vals)[::-1]
                    names = [names[i] for i in order]
                    vals  = vals[order]
                    height = max(1.8, 0.38 * len(names) + 0.7)
                    fig, ax = _plt.subplots(figsize=(6.3, height), dpi=115)
                    cmap = _plt.cm.viridis
                    norm = (vals - vals.min()) / (vals.max() - vals.min() + 1e-9)
                    colours = cmap(norm)
                    ax.barh(range(len(names)), vals * 100.0, color=colours, edgecolor="#222")
                    ax.set_yticks(range(len(names)))
                    ax.set_yticklabels(names)
                    ax.invert_yaxis()
                    ax.set_xlabel("Importance (%)")
                    ax.set_xlim(0, max(5.0, float(vals.max() * 100.0) * 1.10))
                    for i, v in enumerate(vals * 100.0):
                        ax.text(v + 0.5, i, f"{v:0.1f}%", va="center", fontsize=9)
                    fig.tight_layout()
                    fi_buf = _io.BytesIO()
                    fig.savefig(fi_buf, format="png")
                    _plt.close(fig)
                    fi_buf.seek(0)
                    _scaled_png_percent(cont, fi_buf, 0.49).grid(
                        row=2, column=1, columnspan=1, sticky="nsew", padx=4, pady=4
                    )
        except Exception:
            logging.debug("Embedded FI viz failed", exc_info=True)


    # Row 3: nearest-items bar
    nearest_mean = nearest_median = None
    combined_line = None
    pf = state.config.get("price_mirror_filter", DEFAULT_PRICE_FILTER)
    effective_knn = (
        knn_limit
        if isinstance(knn_limit, int) and knn_limit > 0
        else _resolve_knn_filtered_k(state.config)
    )
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty:
        unsuper_df = _truncate_knn_df(unsuper_df, effective_knn)
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty:
        vals, tags = [], []
        for _, r in unsuper_df.iterrows():
            pr = _price_string(r)
            if pr:
                vals.append(pr[1])
            simple = _price_simple(r)
            if simple:
                tags.append(simple)
            if len(tags) >= effective_knn:
                break
        if vals:
            nearest_mean = float(np.mean(vals))
            nearest_median = float(np.median(vals))
        if tags:
            combined_line = f"Based on {effective_knn} Nearest Items (Ordered) with Price Filter {pf}: [{', '.join(tags)}]"
    if nearest_mean is not None or nearest_median is not None:
        bar2 = ctk.CTkFrame(cont, fg_color="transparent")
        bar2.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        _bucket_badge(
            bar2,
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

    # Row 4: KNN mirror cells
    if isinstance(unsuper_df, pd.DataFrame) and not unsuper_df.empty:
        cont2 = ctk.CTkFrame(cont, corner_radius=10)
        cont2.grid(row=4, column=0, columnspan=2, sticky="nsew")
        cont2.columnconfigure((0, 1), weight=1)
        cont2.rowconfigure(6, weight=1)
        body = ctk.CTkFrame(cont2, fg_color="transparent")
        body.grid(row=5, column=0, columnspan=2, sticky="nsew")
        body.columnconfigure((0, 1), weight=1)
        try:
            base_series = unsuper_X.iloc[0] if isinstance(unsuper_X, pd.DataFrame) and not unsuper_X.empty else pd.Series(dtype=float)
        except Exception:
            base_series = pd.Series(dtype=float)
        _render_mirror_rows(
            body,
            base_series,
            unsuper_df,
            unsuper_item_name,
            show_defence_mods=(str(cat_norm or '').strip().lower() in ("ring","amulet","belt")),
            filters=filters,
        )

    # Final geometry pass to keep centered size (no maximize)
    try:
        ov.update_idletasks()
        sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
        default_w = min(int(sw * 0.80), 1600)
        default_h = min(int(sh * 0.88), 1000)
        ov.geometry(f"{default_w}x{default_h}+{(sw - default_w)//2}+{(sh - default_h)//2}")
        ov.minsize(1000, 700)
    except Exception:
        pass
# cache for price hotkeys
_cached_price_value: Optional[int] = None





def _auction_hotkey_callback() -> None:
    """Throttle and run the auction paste flow once per key press."""
    global _auction_last_ts
    now = time.monotonic()
    # Ignore repeats within 600ms
    if now - _auction_last_ts < 0.6:
        return
    _auction_last_ts = now
    _run_with_lock(_hotkey_busy["auction"], _handle_hotkey_paste_price)
