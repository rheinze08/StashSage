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
import ctypes, io, logging, math, multiprocessing, os, random, re, subprocess, sys, tempfile, threading, time, webbrowser
import queue
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional, Mapping, Tuple, Callable
import json
import pkgutil

# force single-process joblib
os.environ["JOBLIB_MULTIPROCESSING"] = "0"
os.environ["JOBLIB_START_METHOD"] = "threading"

# - third-party -------------------------------------------
import numpy as np, pandas as pd, pyperclip, pystray
import customtkinter as ctk
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Use one stable process scale while testing cross-monitor dragging.  This
# prevents CustomTkinter from rebuilding root geometry at mixed-DPI monitor
# boundaries; prediction overlay placement has its own monitor-aware sizing.
if sys.platform.startswith("win"):
    ctk.deactivate_automatic_dpi_awareness()

# - project -----------------------------------------------
# Cross-platform global-hotkey + key-injection backend. Imported as `keyboard`
# so existing `keyboard.*` call sites are unchanged; on Linux this routes
# through pynput (the `keyboard` package needs root there). See utils/hotkeys.py
from poe2trade.utils import hotkeys as keyboard
from poe2trade.app import config_manager
from poe2trade.app import asset_paths
from poe2trade.app import updater
from poe2trade.app import prediction_worker
from poe2trade.app import single_instance
from poe2trade.app import update_self_test
from poe2trade.utils.chart_utils import (
    generate_bucket_confidence_plot,
    generate_prediction_vs_listings_chart,
    generate_predicted_overlay_from_profile,
    generate_predicted_overlay_with_marker,
)
from poe2trade.utils.gui_utils import (
    main as gui_utils_main,
    prepare_item_features,
    call_super_prepared,
    call_unsuper_prepared,
    parse_copied_item_text,
)

# import defence pattern skips so we can hide them in the UI list as well
from poe2trade.utils.gui_utils import (
    PCT_DEFENCE_PATTERNS,
    FLAT_DEFENCE_PATTERNS,
    DPS_WEAPON_CATEGORIES,
    detect_category_segment,
)
from poe2trade.utils import ml_unsuper_utils  # live price-filter tweak
from poe2trade.utils import scrape_stash_utils
from poe2trade.utils import craft_potential
from poe2trade.utils.craft_display import craft_roll_text
from poe2trade.utils.parse_utils import WAYSTONE_MODEL_PROPERTY_LABELS

# chaos/divine ? exalt conversion constants
from poe2trade import (
    poe2trade_root,
    __version__,
    __build_commit__,
    __build_date__,
    quantile_splitters,
)
from poe2trade.pricing import conversion

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
    currency_orb_label,
    format_price as helper_format_price,
    AUTO_DIVINE_THRESHOLD_EXALTS,
    HoverTip,
    help_badge,
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
_overlay_backdrop: Optional[tk.Toplevel] = None
_overlay_loading = False
_overlay_loading_window: Optional[ctk.CTkToplevel] = None
_overlay_loading_cover: Optional[ctk.CTkFrame] = None
_prediction_loader_windows: list[ctk.CTkToplevel] = []
_prediction_request_id = 0
_prediction_popup_process: multiprocessing.Process | None = None
_prediction_popup_queue: Any = None
_prediction_popup_request_id: int | None = None
_popup_event_queue: Any = None
_prediction_popup_shutdown_event: Any = None
_prediction_popup_prewarmed = False
_craft_popup_session_id: int | None = None
_prediction_launch_dimmer: Optional[tk.Toplevel] = None
_active_prediction_release_lock: threading.Lock | None = None
_active_dashboard_process: multiprocessing.Process | None = None
_prediction_worker_manager: prediction_worker.PredictionWorkerManager | None = None
_prediction_worker_poll_after_id: Any = None
_prediction_request_texts: dict[int, str] = {}


def _popup_event_get_nowait(event_queue: Any):
    """Read the presenter event pipe without creating a Queue feeder thread.

    The presenter is a Tk process.  Its outbound queue deliberately uses
    ``SimpleQueue`` because Python 3.13 can fatally abort while finalizing a
    normal multiprocessing Queue feeder alongside Tcl/Pillow.  SimpleQueue
    does not expose ``get_nowait``, but its connection can be polled safely.
    """
    reader = getattr(event_queue, "_reader", None)
    if reader is None or not reader.poll():
        raise queue.Empty
    return event_queue.get()


def _log_presenter_lifecycle(value: Any) -> None:
    """Record child presenter events in the main rotating application log."""
    if isinstance(value, Mapping):
        logging.info(
            "Presenter telemetry: stage=%s request=%s details=%s",
            value.get("stage"),
            value.get("request_id"),
            {key: item for key, item in value.items() if key not in {"stage", "request_id"}},
        )
    else:
        logging.info("Presenter telemetry: %r", value)
# Monitor (left, top, width, height) the current overlay is pinned to. Captured
# when a price check starts, from the cursor's screen, so the backdrop and the
# result window share one monitor even if the cursor later moves.
_overlay_monitor_rect: Optional[tuple[int, int, int, int]] = None
# The root window hosts long-lived application views.  Game-facing price
# overlays remain independent windows, but routine StashSage work should not
# proliferate windows in the task bar.
_workspace: Optional[ctk.CTkFrame] = None
_workspace_views: dict[str, ctk.CTkFrame] = {}
_active_workspace_view: Optional[str] = None
_workspace_nav_buttons: dict[str, ctk.CTkButton] = {}
_workspace_nav_rows: dict[str, ctk.CTkFrame] = {}
_workspace_nav_texts: dict[str, ctk.CTkLabel] = {}
_workspace_nav_images: dict[str, ctk.CTkImage] = {}
_stash_scrape_embedded_parent: Optional[ctk.CTkFrame] = None
_stash_scrape_run_frame: Optional[ctk.CTkFrame] = None


def _clear_stash_scrape_run_frame(event) -> None:
    """Drop the tracked embedded run frame once it (not a child) is destroyed."""
    global _stash_scrape_run_frame
    if _stash_scrape_run_frame is not None and event.widget is _stash_scrape_run_frame:
        _stash_scrape_run_frame = None
_settings_view: Optional[ctk.CTkScrollableFrame] = None
_sidebar: Optional[ctk.CTkFrame] = None
_sidebar_host: Optional[tk.Frame] = None
_sidebar_collapsed = False
_sidebar_animation_active = False
_sidebar_toggle_button: Optional[ctk.CTkButton] = None
_sidebar_brand: Optional[ctk.CTkFrame] = None
_sidebar_brand_mask: Optional[ctk.CTkFrame] = None
_sidebar_footer: Optional[ctk.CTkLabel] = None
_sidebar_transition_view: Optional[ctk.CTkFrame] = None
# Persistent bottom-of-window updater status strip (replaces the old popup
# progress window + result messageboxes). ``None`` until the main window builds
# it; updater-flow helpers lazily fall back to a headless instance (tests).
_update_status_bar: "Optional[_UpdateStatusBar]" = None
_currency_banner_value_labels: list[dict[str, ctk.CTkLabel]] = []
_currency_refresh_buttons: list[ctk.CTkButton] = []
_live_price_refresh_in_flight = False
_update_progress_bytes = 0
_update_progress_total = 0
_update_progress_kind = "download"
_update_progress_version: Optional[str] = None
# Status-strip text colours by tone.
_STATUS_MUTED = "#9AA0A6"
_STATUS_WARN = "#E0A53B"
_STATUS_READY = "#4CC2A0"
_STATUS_TONES = {"muted": _STATUS_MUTED, "warn": _STATUS_WARN, "ready": _STATUS_READY}
# Handle to the in-flight update-check thread; used to single-flight the auto
# and manual checks so they can't run concurrently and double-download assets.
_update_check_thread: Optional[threading.Thread] = None
_manual_update_result_requested = False
_test_update_hotkey_handle = None
# Re-run the background update check periodically so a long-running session
# eventually notices a new release without needing a restart. The prompt-once-
# per-version guard keeps these rechecks from nagging the user.
_UPDATE_RECHECK_INTERVAL_MS = 6 * 60 * 60 * 1000  # 6 hours
_UPDATE_RECHECK_JITTER_MS = 5 * 60 * 1000  # up to 5 minutes
# Application exit. Every exit path (tray Exit, window close, Restart & Update)
# funnels through _shutdown_app. The presenter child is deliberately non-daemon,
# so Python waits for it at interpreter exit; if it never stops, the process
# would linger forever and the update helper, which waits for it, never swaps.
# The watchdog bounds that wait. It is armed only by the real app
# (run_tkinter_app) so tests exercising the exit paths cannot kill pytest.
_SHUTDOWN_GRACE_SECONDS = 8.0
_exit_watchdog_enabled = False
_exit_watchdog_armed = False
_shutdown_root = None
# How often the running instance looks for a show request from a second launch.
_SHOW_REQUEST_POLL_MS = 1000
TEST_UPDATE_MANIFEST_URL = "https://rheinze08.github.io/StashSage/update-manifest-test.json"
LOCAL_TEST_UPDATE_MANIFEST_URL = "https://local.stashsage.test/update-manifest-local.json"
TEST_UPDATE_HOTKEY = "ctrl+alt+shift+u"
TEST_UPDATE_ENV_VAR = "STASHSAGE_ENABLE_TEST_UPDATES"
DEFAULT_KNN = int(config_manager.DEFAULT_CONFIG.get("knn_filtered_k", 10))
DEFAULT_COPY_HOTKEY = gui_constants.DEFAULT_COPY_HOTKEY

prediction_log_entry = prediction_log_browse_btn = None
price_filter_entry = max_price_filter_entry = knn_filtered_k_entry = copy_hotkey_entry = custom_hotkey_entry = filtered_hotkey_entry = craft_potential_hotkey_entry = None
stash_scrape_hotkey_entry = None
close_behavior_var = None
# Views that re-render when the price denomination changes. A plain list keeps
# the stash viewer's own selector in step with the one in Settings.
_PRICE_DISPLAY_LISTENERS: list = []
auction_hotkey_entry = auction_rule_entry = None

gui_cfg: dict = state.config
client_day_filter = 30

_FILTER_ENTRY_MEMORY: dict[str, list[str]] = {}

# The persistent sidebar consumes part of the old single-column layout.  Give
# the settings workspace enough room by default, while still fitting smaller
# displays through ``_set_screen_aware_geometry``.
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 640
DEFAULT_WINDOW_WIDTH = 1120
DEFAULT_WINDOW_HEIGHT = 840
WINDOW_SCREEN_MARGIN = 80

# Shared typography roles. Keep general interface copy in Segoe UI and reserve
# Consolas for fixed-width data such as item text, paths, and price values.
_FONT_PAGE_TITLE = ("Segoe UI", 20, "bold")
_FONT_SECTION_TITLE = ("Segoe UI", 16, "bold")
_FONT_SUBHEADING = ("Segoe UI", 14, "bold")
_FONT_STATUS_BANNER = ("Segoe UI", 16, "bold")
_FONT_BODY = ("Segoe UI", 12)
_FONT_BODY_BOLD = ("Segoe UI", 12, "bold")
_FONT_HELPER = ("Segoe UI", 11)
_FONT_CAPTION = ("Segoe UI", 10)
_FONT_NAV = ("Segoe UI", 15)
_FONT_TABLE = ("Segoe UI", 11)
_FONT_TABLE_BOLD = ("Segoe UI", 11, "bold")
_FONT_MONO = ("Consolas", 12)
_FONT_MONO_SMALL = ("Consolas", 11)


def _configure_default_widget_fonts() -> None:
    """Set one baseline for all CTk widgets that use their default font."""
    try:
        default_font = ctk.ThemeManager.theme["CTkFont"]
        default_font["family"] = "Segoe UI"
        default_font["size"] = 12
        default_font["weight"] = "normal"
    except Exception:
        logging.debug("Could not configure shared CustomTkinter typography", exc_info=True)


def _set_nav_row_color(name: str, *, hovered: bool = False) -> None:
    """Paint one stationary nav row without changing its geometry."""
    active = name == _active_workspace_view
    color = "#1F6AA5" if active else ("#263846" if hovered else "transparent")
    row = _workspace_nav_rows.get(name)
    if row is not None:
        row.configure(fg_color=color)
    button = _workspace_nav_buttons.get(name)
    if button is not None:
        # CTkButton permits transparent foregrounds, but its documented
        # hover_color accepts only a real color. Keep the inactive hover blue
        # while the row background provides the visual surface.
        button.configure(
            fg_color=color,
            hover_color=color if color != "transparent" else "#263846",
        )


def _set_active_nav_button(view_name: str) -> None:
    """Synchronize active coloring for the fixed navigation rows."""
    for name, button in _workspace_nav_buttons.items():
        # Keep this assignment explicit for existing state consumers and then
        # paint the matching row surface.
        button.configure(fg_color="#1F6AA5" if name == view_name else "transparent")
        _set_nav_row_color(name)


def _activate_workspace_view(
    view_name: str, title: str, *, fresh: bool = False
) -> tuple[ctk.CTkFrame, bool] | None:
    """Show a single primary view inside the root StashSage window.

    Views stay alive while the app is running.  This avoids a CustomTkinter
    DPI-scaling race on Windows where a just-destroyed dropdown can still be
    visited while the window crosses monitors.  ``fresh`` creates a new view
    without destroying the old one, for a new price-check result.
    """
    global _active_workspace_view
    if _workspace is None:
        return None

    for child in _workspace.winfo_children():
        child.grid_remove()
    previous = _workspace_views.get(view_name)
    if not fresh and previous is not None and previous.winfo_exists():
        previous.grid(row=0, column=0, sticky="nsew")
        _active_workspace_view = view_name
        if root is not None:
            try:
                root.title(f"StashSage — {title}")
            except Exception:
                pass
        _set_active_nav_button(view_name)
        return previous, False

    view = ctk.CTkFrame(_workspace, fg_color="transparent")
    view.grid(row=0, column=0, sticky="nsew")
    _workspace_views[view_name] = view
    _active_workspace_view = view_name
    if root is not None:
        try:
            root.title(f"StashSage — {title}")
        except Exception:
            pass
    _set_active_nav_button(view_name)
    return view, True


def _show_settings_view() -> None:
    """Return to the persistent settings/home view."""
    global _active_workspace_view
    if _workspace is None or _settings_view is None:
        return
    for child in _workspace.winfo_children():
        child.grid_remove()
    _settings_view.grid(row=0, column=0, sticky="nsew")
    _active_workspace_view = "home"
    if root is not None:
        try:
            root.title(f"StashSage for POE2 (v{__version__} -- {BUILD_DATE})")
        except Exception:
            pass
    _set_active_nav_button("home")


def _sync_settings_workspace_width() -> None:
    """Force CTkScrollableFrame's inner canvas to the settled workspace width."""
    if _settings_view is None:
        return
    try:
        canvas = _settings_view._parent_canvas  # CustomTkinter's scroll canvas
        canvas.itemconfigure(_settings_view._create_window_id, width=canvas.winfo_width())
        canvas.configure(scrollregion=canvas.bbox("all"))
    except Exception:
        logging.debug("Could not synchronize settings canvas width", exc_info=True)


def _sidebar_nav_icon(filename: str) -> Optional[ctk.CTkImage]:
    """Load a readable sidebar icon without losing its visual detail."""
    try:
        icon_path = Path(__file__).with_name("sidebar_icons") / filename
        image = Image.open(icon_path).convert("RGBA")
        # Preserve the silver and sapphire parts of the artwork.  Only lift
        # its near-black fill to a muted blue so it no longer disappears into
        # the dark rail.
        pixels = np.array(image)
        rgb = pixels[:, :, :3]
        alpha = pixels[:, :, 3]
        dark_fill = (rgb.max(axis=2) < 90) & (alpha > 0)
        rgb[dark_fill] = (69, 120, 166)
        sapphire = (rgb[:, :, 2] > rgb[:, :, 0] * 1.3) & (rgb[:, :, 2] > rgb[:, :, 1] * 1.1) & (alpha > 0)
        rgb[sapphire] = np.maximum(rgb[sapphire], (64, 145, 245))
        image = Image.fromarray(pixels, "RGBA")
        # Generated assets intentionally include canvas breathing room. Trim
        # it here, then add back a small consistent margin so each mark uses
        # the 32px navigation slot rather than reading as a 20px icon.
        # Ignore the faint anti-aliased glow when centering. Those few almost
        # transparent pixels differed per asset and made the compact rail look
        # subtly misaligned even though its widget slots matched.
        visible_alpha = image.getchannel("A").point(lambda value: 255 if value >= 64 else 0)
        bounds = visible_alpha.getbbox()
        if bounds:
            icon = image.crop(bounds)
            icon.thumbnail((88, 88), Image.Resampling.LANCZOS)
            # The generated Sage logo is a large square PNG. Reusing that
            # source canvas here leaves the visible crest as a tiny speck in
            # the 36px CTkImage slot. Fit the cropped mark to the compact
            # navigation canvas instead.
            fitted = Image.new("RGBA", (96, 96))
            x = (fitted.width - icon.width) // 2
            y = (fitted.height - icon.height) // 2
            fitted.paste(icon, (x, y), icon)
            image = fitted
        # Keep one shared image slot so every label begins on the same x-axis.
        # Home and sonar retain their 32px visible size inside the 36px slot;
        # the circular History mark uses the full slot for visual parity.
        if filename != "history.png":
            slotted = Image.new("RGBA", (108, 108))
            slotted.paste(image, (6, 6), image)
            image = slotted
        return ctk.CTkImage(light_image=image, dark_image=image, size=(36, 36))
    except Exception:
        logging.debug("Could not load sidebar icon %s", filename, exc_info=True)
        return None


def _sidebar_transition_width(start: int, target: int, step: int, steps: int = 8) -> int:
    """Return an eased integer rail width for a single animation frame."""
    progress = min(1.0, max(0.0, step / max(1, steps)))
    eased = progress * progress * (3.0 - 2.0 * progress)
    return round(start + (target - start) * eased)


def _freeze_workspace_for_sidebar_transition() -> Optional[ctk.CTkFrame]:
    """Keep the active page at one rendered size while the rail moves."""
    if _workspace is None:
        return None
    view = _workspace_views.get(_active_workspace_view or "")
    if view is None or not view.winfo_exists():
        return None
    try:
        # CTkScrollableFrame delegates geometry management to its private
        # parent frame, while ``winfo_width`` on the inner canvas frame can
        # still be 1 during an idle layout pass. Freeze the managed outer
        # frame's actual/requested size instead.
        layout_widget = getattr(view, "_parent_frame", view)
        width = max(1, layout_widget.winfo_width(), layout_widget.winfo_reqwidth())
        height = max(1, layout_widget.winfo_height(), layout_widget.winfo_reqheight())
        view.grid_remove()
        # CustomTkinter accepts dimensions through ``configure``, not
        # ``place``. Keep this legacy helper safe even though the current
        # sidebar transition no longer uses it.
        view.configure(width=width, height=height)
        view.place(x=0, y=0)
        view.lift()
        return view
    except Exception:
        logging.debug("Could not freeze workspace during sidebar transition", exc_info=True)
        return None


def _thaw_workspace_after_sidebar_transition(view: Optional[ctk.CTkFrame]) -> None:
    """Restore a frozen page to grid after its parent has settled."""
    if view is None or not view.winfo_exists():
        return
    try:
        view.place_forget()
        view.grid(row=0, column=0, sticky="nsew")
        if view is _settings_view:
            _sync_settings_workspace_width()
    except Exception:
        logging.debug("Could not settle workspace after sidebar transition", exc_info=True)


def _toggle_sidebar() -> None:
    """Animate a clipped rail while its navigation geometry stays immutable."""
    global _sidebar_collapsed, _sidebar_animation_active
    if _sidebar is None or _sidebar_host is None or root is None or _sidebar_animation_active:
        return
    target_collapsed = not _sidebar_collapsed
    start_width = 72 if _sidebar_collapsed else 178
    target_width = 72 if target_collapsed else 178

    def _set_nav_controls(collapsed: bool, *, settle_row_width: bool = True) -> None:
        """Toggle copy and settle the selected pill into its state-specific width."""
        for text_label in _workspace_nav_texts.values():
            if collapsed:
                text_label.place_forget()
            else:
                # Leave a right inset: CTkLabel's canvas is rectangular and
                # would otherwise paint over the row frame's rounded corner.
                text_label.place(x=68, y=0)
        if settle_row_width:
            row_width = 56 if collapsed else 162
            for nav_row in _workspace_nav_rows.values():
                nav_row.configure(width=row_width)

    def _set_controls(
        collapsed: bool,
        *,
        show_nav_labels: bool = True,
        show_sections: bool = True,
        position_toggle: bool = True,
        settle_row_width: bool = True,
    ) -> None:
        if _sidebar_toggle_button is not None:
            _sidebar_toggle_button.configure(text="\u00bb" if collapsed else "\u00ab")
            # Keep one neutral glyph; its state never needs to be redrawn.
            _sidebar_toggle_button.configure(text="\u2630")
            if position_toggle:
                # The menu control shares the navigation-icon axis in both
                # states, so it never needs to move during a rail transition.
                _sidebar_toggle_button.place(x=6, y=20)
            _sidebar_toggle_button.lift()
        if show_sections and _sidebar_brand is not None:
            if collapsed:
                _sidebar_brand.place_forget()
            else:
                _sidebar_brand.place(x=54, y=2)
            if _sidebar_toggle_button is not None:
                _sidebar_toggle_button.lift()
        if show_sections and _sidebar_footer is not None:
            if collapsed:
                _sidebar_footer.place_forget()
            else:
                _sidebar_footer.place(relx=0, rely=1, x=14, y=-16, anchor="sw")
        if show_nav_labels:
            _set_nav_controls(collapsed, settle_row_width=settle_row_width)

    _sidebar_animation_active = True
    try:
        # Never remove a CTkScrollableFrame from its managed parent during a
        # transition. Its canvas/inner-frame relationship is not safe to
        # switch between grid and place at runtime.
        if target_collapsed:
            # The fixed menu control stays visible while only the copy hides.
            _set_controls(True, position_toggle=False, settle_row_width=False)
        else:
            # Reveal the fixed children before the clip opens. They remain
            # hidden outside the 72px rail until there is room for them.
            _set_nav_controls(False, settle_row_width=True)
            if _sidebar_brand is not None:
                _sidebar_brand.place(x=54, y=2)
            if _sidebar_footer is not None:
                _sidebar_footer.place(relx=0, rely=1, x=14, y=-16, anchor="sw")
            # Expansion needs room for the rail; resize the workspace once,
            # before the visual rail begins to grow.
            _sidebar_host.configure(width=target_width)
            root.grid_columnconfigure(0, minsize=target_width)
        steps = 8
        interval = 20

        def step(index: int) -> None:
            global _sidebar_collapsed, _sidebar_animation_active
            if root is None or not root.winfo_exists():
                _sidebar_animation_active = False
                return
            width = _sidebar_transition_width(start_width, target_width, index, steps)
            # Fixed-size children are clipped by this rail. Their x/y/width
            # never participates in the animation, which prevents selected
            # pills from stretching and icons from bobbing at DPI boundaries.
            _sidebar.configure(width=width)
            if index < steps:
                root.after(interval, lambda: step(index + 1))
                return

            def finish() -> None:
                global _sidebar_collapsed, _sidebar_animation_active
                if root is None or not root.winfo_exists():
                    _sidebar_animation_active = False
                    return
                if target_collapsed:
                    _sidebar_host.configure(width=target_width)
                    root.grid_columnconfigure(0, minsize=target_width)
                _sidebar_collapsed = target_collapsed
                _set_controls(target_collapsed)

                def settle_workspace() -> None:
                    global _sidebar_animation_active
                    if root is not None and root.winfo_exists():
                        _sync_settings_workspace_width()
                    _sidebar_animation_active = False

                # Let Tk process the single grid change before asking the
                # scroll canvas to set its embedded-window width.
                root.after_idle(settle_workspace)

            root.after_idle(finish)

        if target_collapsed:
            step(0)
        else:
            root.after_idle(lambda: step(0))
    except Exception:
        logging.debug("Could not switch sidebar layout", exc_info=True)
        _sidebar_animation_active = False
        return


def _build_app_shell(parent: ctk.CTk) -> ctk.CTkFrame:
    """Create the unified root window shell and its primary navigation."""
    global _workspace, _active_workspace_view, _sidebar, _sidebar_host, _sidebar_collapsed
    global _sidebar_toggle_button, _sidebar_brand, _sidebar_brand_mask, _sidebar_footer, _sidebar_transition_view
    _workspace_views.clear()
    _workspace_nav_buttons.clear()
    _workspace_nav_rows.clear()
    _workspace_nav_texts.clear()
    _workspace_nav_images.clear()
    _active_workspace_view = None
    _sidebar_collapsed = False
    _sidebar_transition_view = None
    parent.grid_columnconfigure(0, weight=0)
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_columnconfigure(0, minsize=178)
    parent.grid_rowconfigure(0, weight=1)

    # A plain Tk host owns the grid column's requested width.  CTk widgets can
    # retain an old scaled request after ``configure(width=...)``; placing the
    # visual sidebar inside this host makes compact mode deterministic.
    sidebar_host = tk.Frame(parent, width=178, bg="#111C26")
    # The rail's left edge is fixed to the app while it animates. Its right
    # edge retracts left; the workspace takes the released area at the end.
    sidebar_host.grid(row=0, column=0, sticky="nsw")
    sidebar_host.grid_propagate(False)
    sidebar = ctk.CTkFrame(sidebar_host, width=178, corner_radius=0, fg_color="#111C26")
    # Leave width under the widget's ``configure(width=...)`` control.  A
    # CTk frame cannot safely switch between relative-width placement and an
    # explicit width during animation: that can resolve to a zero-width rail.
    sidebar.place(x=0, y=0, relheight=1)
    _sidebar_host = sidebar_host
    _sidebar = sidebar
    # Explicit slots avoid pack/grid recalculation as the rail is clipped.
    # This keeps the header and the first navigation icon on one vertical axis
    # in both sidebar states, including at non-integer Windows DPI scaling.
    header = ctk.CTkFrame(sidebar, fg_color="transparent", width=158, height=78)
    # Align the sidebar's brand/button centre with the fixed main-pane header.
    # The main header stays in place; only this sidebar group shifts downward.
    header.place(x=10, y=20)
    header.pack_propagate(False)
    brand = ctk.CTkFrame(header, fg_color="transparent", width=98, height=74)
    brand.place(x=54, y=2)
    # Use fixed, compact line slots. CTk's default label heights are generous
    # enough to make a mixed pack/place stack overlap at some DPI scales.
    ctk.CTkLabel(brand, text="StashSage", font=("Segoe UI", 19, "bold"), height=26).place(x=6, y=10)
    ctk.CTkLabel(brand, text="POE2 companion", text_color="#9AA7B4", height=16).place(x=6, y=35)
    ctk.CTkLabel(
        brand, text=f"Version {__version__}", text_color="#718292", font=("Segoe UI", 11), height=15
    ).place(x=6, y=51)
    _sidebar_brand = brand
    _sidebar_brand_mask = None
    _sidebar_toggle_button = ctk.CTkButton(
        header, text="«", width=38, height=38, corner_radius=8,
        font=("Segoe UI", 18, "bold"),
        fg_color="#244B67", hover_color="#2F607F", command=_toggle_sidebar,
    )
    _sidebar_toggle_button.configure(text="\u2630", font=("Segoe UI Symbol", 17, "bold"))
    _sidebar_toggle_button.place(x=6, y=20)
    _sidebar_toggle_button.lift()

    _workspace = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
    _workspace.grid(row=0, column=1, sticky="nsew")
    _workspace.grid_rowconfigure(0, weight=1)
    _workspace.grid_columnconfigure(0, weight=1)

    nav_specs = (
        ("home", "Home", "home.png", _show_settings_view),
        ("history", "History", "history.png", _show_prediction_log_popup),
        ("topmods", "Top Mods", "", _show_top_mods_view),
        ("stash", "StashScrape", "stashscrape.png", _show_stash_scrape_default),
        ("help", "Help", "", _show_help_view),
    )
    for index, (name, label, icon_filename, command) in enumerate(nav_specs):
        nav_image = _sidebar_nav_icon(icon_filename) if icon_filename else None
        # A fixed 162px row is clipped by the rail instead of being resized.
        # The selected pill therefore never stretches, and each icon's center
        # remains at x=36/y=(131 + 52*n) in both states.
        nav_row = ctk.CTkFrame(sidebar, width=162, height=50, corner_radius=7, fg_color="transparent")
        nav_row.place(x=8, y=104 + index * 52)
        nav_row.pack_propagate(False)
        button = ctk.CTkButton(
            nav_row,
            text=("\u2637" if name == "topmods" else ("?" if name == "help" else "")),
            image=nav_image, compound="top", anchor="center",
            width=56, height=44, corner_radius=7, border_spacing=0,
            font=("Segoe UI Symbol", 20, "bold"),
            fg_color="transparent", hover_color="#263846", command=command,
        )
        button.place(x=0, y=3)
        text_label = ctk.CTkLabel(
            nav_row, text=label, font=_FONT_NAV, anchor="w", width=86, height=50
        )
        text_label.place(x=68, y=0)

        def _enter(_event=None, nav_name=name):
            _set_nav_row_color(nav_name, hovered=True)

        def _leave(_event=None, nav_name=name):
            _set_nav_row_color(nav_name)

        nav_row.bind("<Enter>", _enter)
        nav_row.bind("<Leave>", _leave)
        nav_row.bind("<Button-1>", lambda _event, action=command: action())
        text_label.bind("<Enter>", _enter)
        text_label.bind("<Leave>", _leave)
        text_label.bind("<Button-1>", lambda _event, action=command: action())
        button.bind("<Enter>", _enter)
        button.bind("<Leave>", _leave)
        for widget in (nav_row, text_label):
            canvas = getattr(widget, "_canvas", None)
            if canvas is not None:
                canvas.configure(cursor="hand2")
        _workspace_nav_buttons[name] = button
        _workspace_nav_rows[name] = nav_row
        _workspace_nav_texts[name] = text_label
        if nav_image is not None:
            _workspace_nav_images[name] = nav_image

    _sidebar_footer = ctk.CTkLabel(
        sidebar,
        text="Price-check hotkeys remain available\nwhile StashSage is minimized.",
        justify="left", anchor="w", wraplength=150, text_color="#7E8C99",
        font=_FONT_HELPER,
    )
    _sidebar_footer.place(relx=0, rely=1, x=14, y=-16, anchor="sw")
    return _workspace


def _fit_window_to_screen(
    win,
    preferred_width: int,
    preferred_height: int,
    min_width: int,
    min_height: int,
    *,
    margin: int = WINDOW_SCREEN_MARGIN,
) -> tuple[int, int, int, int]:
    """Return screen-bounded width, height, min_width, min_height for *win*."""
    try:
        screen_width = int(win.winfo_screenwidth())
    except Exception:
        screen_width = 0
    try:
        screen_height = int(win.winfo_screenheight())
    except Exception:
        screen_height = 0

    fallback_width = max(preferred_width, min_width)
    fallback_height = max(preferred_height, min_height)
    available_width = max(360, screen_width - margin) if screen_width > 0 else fallback_width
    available_height = max(320, screen_height - margin) if screen_height > 0 else fallback_height

    fitted_min_width = min(min_width, available_width)
    fitted_min_height = min(min_height, available_height)
    width = min(max(preferred_width, fitted_min_width), available_width)
    height = min(max(preferred_height, fitted_min_height), available_height)
    return int(width), int(height), int(fitted_min_width), int(fitted_min_height)


def _set_screen_aware_geometry(
    win,
    preferred_width: int,
    preferred_height: int,
    min_width: int,
    min_height: int,
    *,
    center: bool = True,
) -> tuple[int, int]:
    """Apply a startup geometry that is large by default but bounded by screen."""
    width, height, fitted_min_width, fitted_min_height = _fit_window_to_screen(
        win, preferred_width, preferred_height, min_width, min_height
    )
    try:
        win.minsize(fitted_min_width, fitted_min_height)
    except Exception:
        pass

    geometry = f"{width}x{height}"
    if center:
        try:
            screen_width = int(win.winfo_screenwidth())
            screen_height = int(win.winfo_screenheight())
            x = max((screen_width - width) // 2, 0)
            y = max((screen_height - height) // 2, 0)
            geometry = f"{geometry}+{x}+{y}"
        except Exception:
            pass
    try:
        win.geometry(geometry)
    except Exception:
        pass
    return width, height


def _install_dpi_grow_guard(win) -> None:
    """Keep the root's pixel size steady while CTk changes monitor DPI.

    CTk 5.2.2's built-in root callback forces the window to the *newly scaled*
    logical dimensions and temporarily sets its minimum and maximum to that
    exact size.  On a mixed-DPI desktop this makes a dragged main window swell
    and feel as though it catches on the monitor border.  Widgets should still
    scale, but the root should retain its pre-transition native pixel bounds.
    """
    if not sys.platform.startswith("win"):
        return

    try:
        from customtkinter.windows.widgets.scaling.scaling_base_class import CTkScalingBaseClass
        from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker
    except Exception:
        logging.debug("Could not load CustomTkinter DPI hooks", exc_info=True)
        return

    state: dict[str, Any] = {"native_size": None}

    def _begin_dpi_transition() -> None:
        # ScalingTracker calls this after it has detected the new monitor DPI
        # but before any scale callbacks run, which is the one moment the
        # stable native size can be captured without a visible correction.
        try:
            state["native_size"] = (int(win.winfo_width()), int(win.winfo_height()))
            win._block_update_dimensions_event = True
        except Exception:
            logging.debug("Could not begin root DPI transition", exc_info=True)

    def _finish_dpi_transition() -> None:
        try:
            win._block_update_dimensions_event = False
        except Exception:
            pass
        finally:
            state["native_size"] = None

    def _set_root_scaling(new_widget_scaling: float, new_window_scaling: float) -> None:
        # Update CTk's scaling state exactly as its base class does, then apply
        # normal scaled resize bounds.  Deliberately do not use CTk.CTk's
        # _set_scaling(): that method locks min/max to the full window size and
        # re-applies an enlarged geometry during every monitor transition.
        CTkScalingBaseClass._set_scaling(win, new_widget_scaling, new_window_scaling)
        native_size = state.get("native_size")
        if not native_size:
            return
        native_width, native_height = native_size
        try:
            win._current_width = native_width / new_window_scaling
            win._current_height = native_height / new_window_scaling
            tk.Tk.minsize(
                win,
                round(win._min_width * new_window_scaling),
                round(win._min_height * new_window_scaling),
            )
            tk.Tk.maxsize(
                win,
                round(win._max_width * new_window_scaling),
                round(win._max_height * new_window_scaling),
            )
            # Bypass CTk.geometry(), which would scale these physical pixels a
            # second time.  The window stays the same size while its contents
            # update to the new monitor's scale.
            tk.Tk.geometry(win, f"{native_width}x{native_height}")
        except Exception:
            logging.debug("Could not preserve root size through DPI transition", exc_info=True)

    try:
        callbacks = ScalingTracker.window_widgets_dict.get(win)
        if callbacks is None:
            return
        original_callback = win._set_scaling
        for index, callback in enumerate(callbacks):
            if callback == original_callback:
                callbacks[index] = _set_root_scaling
                break
        else:
            logging.debug("Could not locate root DPI scaling callback")
            return

        # CTk 5.2.2's implementations both set this flag to False.  Use
        # instance hooks so Configure cannot overwrite the preserved logical
        # dimensions halfway through the scaling callbacks.
        win.block_update_dimensions_event = _begin_dpi_transition
        win.unblock_update_dimensions_event = _finish_dpi_transition
    except Exception:
        logging.debug("Could not install root DPI transition guard", exc_info=True)


def _apply_window_icon(win) -> None:
    """Set *win*'s title-bar/taskbar icon in a cross-platform-safe way.

    Windows Tk supports the bundled ``.ico`` via ``iconbitmap``. On Linux/macOS
    ``iconbitmap`` cannot load a Windows ``.ico`` and raises ``TclError`` (which
    crashed the app at startup), so there we render the same ``.ico`` through
    PIL and set it with ``iconphoto``. Never raises -- a missing/garbled icon
    must not take down the window.
    """
    try:
        ico = Path(__file__).with_name("stashsage_logo.ico")
        if sys.platform == "win32":
            win.iconbitmap(str(ico))
            return
        from PIL import ImageTk

        photo = ImageTk.PhotoImage(Image.open(ico))
        win.iconphoto(True, photo)
        win._icon_img = photo  # keep a reference so Tk doesn't GC it
    except Exception:
        logging.debug("Failed to set window icon", exc_info=True)


def _safe_grab_set(win, *, _attempt: int = 0, _max_attempts: int = 5) -> bool:
    """Best-effort modal grab that tolerates delayed Linux toplevel mapping."""
    try:
        if hasattr(win, "winfo_exists") and not win.winfo_exists():
            return False
    except Exception:
        return False

    try:
        win.update_idletasks()
    except Exception:
        pass

    try:
        if hasattr(win, "winfo_viewable") and not win.winfo_viewable():
            if _attempt < _max_attempts and hasattr(win, "after"):
                win.after(50, lambda: _safe_grab_set(win, _attempt=_attempt + 1))
            return False
    except Exception:
        pass

    try:
        win.grab_set()
        return True
    except tk.TclError as exc:
        if _attempt < _max_attempts and "viewable" in str(exc).lower() and hasattr(win, "after"):
            win.after(50, lambda: _safe_grab_set(win, _attempt=_attempt + 1))
        else:
            logging.debug("Failed to grab Tk window", exc_info=True)
        return False
    except Exception:
        logging.debug("Failed to grab Tk window", exc_info=True)
        return False


def _load_stash_categories() -> list[str]:
    """Return the available stash scrape categories."""
    try:
        names: list[str] = []
        for entry in getattr(scrape_stash_utils, "STASH_SCRAPE_SELECTIONS", []) or []:
            if not isinstance(entry, Mapping):
                continue
            name = str(entry.get("name") or "").strip()
            if name:
                names.append(name)
        return sorted(names, key=str.casefold)
    except Exception:
        logging.warning("Could not load stash scrape categories", exc_info=True)
        return []


def _stash_category_display_name(category_name: str) -> str:
    """Return a readable label without changing the stable internal category key."""
    for entry in getattr(scrape_stash_utils, "STASH_SCRAPE_SELECTIONS", []) or []:
        if not isinstance(entry, Mapping) or entry.get("name") != category_name:
            continue
        display_name = str(entry.get("display_name") or "").strip()
        if display_name:
            return display_name
        break
    return category_name.replace("_", " ").title()


ITEM_CATEGORIES = _load_stash_categories()


def _check_save_location_writable(save_path: str) -> Optional[str]:
    """Return a user-facing error message if ``save_path`` is not writable, else None.

    Windows denies writes to protected locations like ``C:\\Program Files`` for
    non-elevated processes, surfacing as ``[WinError 5] Access is denied``. Catch
    that here so the user gets a clear instruction instead of a raw OS error mid-scrape.
    """
    try:
        target = Path(save_path).expanduser().resolve()
    except (OSError, ValueError, RuntimeError):
        return (
            "That save location could not be understood. Pick a personal folder "
            "such as Desktop or Documents."
        )

    # Walk up to the nearest existing ancestor; we need write access there to
    # create the save directory (and the run folder inside it).
    probe = target
    while not probe.exists():
        if probe.parent == probe:
            break
        probe = probe.parent

    try:
        probe.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=probe):
            pass
    except PermissionError:
        return (
            f"Windows blocked writing to:\n{target}\n\n"
            "This usually happens with system folders like Program Files. "
            "Choose a personal folder instead \u2014 Desktop or Documents works well."
        )
    except OSError as exc:
        return (
            f"Could not write to:\n{target}\n\n{exc}\n\n"
            "Choose a personal folder such as Desktop or Documents."
        )
    return None


def _format_stash_scrape_progress_message(
    event: str, payload: Mapping[str, object]
) -> tuple[str, Optional[str]]:
    """Return one encoding-stable stash-scrape progress message and color tag."""
    if event == "category_registry":
        source = str(payload.get("source") or "bundled")
        remapped = payload.get("remapped") or []
        skipped = payload.get("skipped") or []
        details = [f"Trade categories validated from {source}"]
        if remapped:
            details.append(f"{len(remapped)} updated ID(s) resolved")
        if skipped:
            details.append(f"{len(skipped)} unsupported category(s) skipped")
        warning = payload.get("warning")
        if warning:
            details.append(str(warning))
        return "; ".join(details), "warning" if warning or skipped else "muted"
    if event == "start":
        selections = payload.get("selections") or []
        ua = payload.get("user_agent") or "unknown UA"
        if selections:
            return f"Starting scrape for {', '.join(map(str, selections))} (UA: {ua})", "info"
        return f"Starting scrape (UA: {ua})", "info"
    if event == "stage":
        selection = payload.get("selection") or "Unknown"
        stage = payload.get("stage") or "?"
        return f"{selection} \u2192 {stage}", "muted"
    if event == "selection_start":
        selection = payload.get("selection")
        return f"Starting {selection}", "info"
    if event == "selection_result":
        selection = payload.get("selection")
        items = int(payload.get("items", 0))
        if payload.get("had_error"):
            return f"Completed {selection}: request failed; see error above", "error"
        delay = payload.get("expected_delay")
        wait_text = f" (next wait ~ {float(delay) / 60:.1f} min)" if delay else ""
        if items:
            return f"Completed {selection}: {items} items fetched{wait_text}", "success"
        return f"Completed {selection}: category empty; no listed items matched{wait_text}", "warning"
    if event == "empty":
        selection = payload.get("selection") or "Category"
        return f"{selection}: category empty; no listed items matched", "warning"
    if event == "items_batch":
        selection = payload.get("selection", "Unknown")
        items = int(payload.get("items", 0))
        batch_idx = payload.get("batch_index")
        return f"  Batch {batch_idx}: {items} items ({selection})", None
    if event == "rate_limited":
        phase = payload.get("phase", "unknown")
        status = payload.get("status", "429")
        return f"Rate limited during {phase} (HTTP {status}); honoring retry", "warning"
    if event == "stopped":
        return str(payload.get("message") or "Scrape stopped."), "warning"
    if event == "completed":
        summary = payload.get("summary") or {}
        items = summary.get("items", 0)
        errors = summary.get("errors", 0)
        files = len(summary.get("output_files") or [])
        tag = "error" if errors else "success"
        return f"Scrape completed: {items} items, {errors} errors, {files} files saved", tag
    if event == "error":
        return f"Error: {payload.get('message')}", "error"
    return f"{event}: {dict(payload)}", None


def _refresh_trade_category_registry_async() -> None:
    """Refresh Trade API category IDs once per GUI launch without blocking Tk."""
    def _worker() -> None:
        registry = scrape_stash_utils.refresh_trade_category_registry()
        if registry.warning:
            logging.warning(
                "Trade category registry refresh used %s fallback: %s",
                registry.source,
                registry.warning,
            )
        else:
            logging.info(
                "Trade category registry refreshed (%d options)",
                len(registry.options),
            )

    threading.Thread(
        target=_worker,
        name="trade-category-registry-refresh",
        daemon=True,
    ).start()


def _open_stash_scrape_results(
    preselect: "str | os.PathLike[str] | None", close_progress: Callable[[], None]
) -> None:
    """Close scrape progress and reveal/reload the completed results view."""
    close_progress()
    _show_stash_scrape_viewer(preselect=preselect)


def _open_stash_scrape_dialog() -> None:
    global _stash_scrape_embedded_parent, _stash_scrape_run_frame
    if root is None:
        return
    if not ITEM_CATEGORIES:
        messagebox.showwarning("Stash Scrape", "No stash scrape categories are available.")
        return

    embedded_parent = _stash_scrape_embedded_parent
    embedded = embedded_parent is not None and embedded_parent.winfo_exists()
    if embedded:
        # Reuse an already-open run frame instead of stacking another over the
        # tile (the sidebar entry can re-trigger this while it is showing).
        if _stash_scrape_run_frame is not None and _stash_scrape_run_frame.winfo_exists():
            _stash_scrape_run_frame.lift()
            return
        dialog = ctk.CTkFrame(embedded_parent, fg_color="#202020", corner_radius=0)
        dialog.place(relx=0, rely=0, relwidth=1, relheight=1)
        _stash_scrape_run_frame = dialog
        dialog.bind("<Destroy>", lambda _e: _clear_stash_scrape_run_frame(_e), add="+")
    else:
        dialog = ctk.CTkToplevel(root)
        dialog.title("Stash Scrape")
        _set_screen_aware_geometry(dialog, 860, 900, 740, 700)
        dialog.transient(root)
        _safe_grab_set(dialog)
        dialog.focus_force()
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    def _open_existing_scrapes() -> None:
        if embedded:
            dialog.destroy()
        else:
            try:
                dialog.grab_release()
            except Exception:
                pass
        _show_stash_scrape_viewer()

    # Header mirrors the StashScrape viewer's header so the toggle button
    # ("View StashScrapes" here, "Run StashScrape" there) stays in the same spot
    # when the tile swaps between the two views.
    header_bar = ctk.CTkFrame(dialog, corner_radius=10, fg_color="#202A33")
    header_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 8))
    header_bar.columnconfigure(0, weight=1)
    title_row = ctk.CTkFrame(header_bar, fg_color="transparent")
    title_row.grid(row=0, column=0, sticky="w", padx=12, pady=10)
    ctk.CTkLabel(title_row, text="Run StashScrape", font=_FONT_PAGE_TITLE).pack(side="left")
    _help_bubble(
        title_row,
        "Queries the PoE2 trade API for live listings across the public stash "
        "tabs on a given account, scores every item with the XGB and KNN "
        "models, and saves the results to your chosen folder. At most 100 "
        "items per category; leave a generous wait between searches to avoid "
        "trade API rate limits. Switch to View StashScrapes to browse "
        "completed runs.",
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(
        header_bar,
        text="View StashScrapes",
        width=150,
        command=_open_existing_scrapes,
    ).grid(row=0, column=1, sticky="e", padx=12, pady=10)

    content = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew")

    ctk.CTkLabel(
        content,
        text="Queries the PoE2 trade API for live listing data and saves scored results to your chosen folder.",
        text_color="gray60",
        font=ctk.CTkFont(size=12),
        wraplength=700,
        justify="left",
    ).pack(anchor="w", padx=20, pady=(10, 0))

    ctk.CTkLabel(
        content,
        text=(
            "Supports public Premium, Quad, and Merchant tabs, including listings without a "
            "defined price. At most 100 items per category can be scraped. Trade API rate-limit "
            "headers may be inaccurate, so aggressive requests can cause a temporary rate limit. "
            "The API can also take 10 minutes or more to sync recent listings and price changes."
        ),
        text_color="gray60",
        font=ctk.CTkFont(size=12, slant="italic"),
        wraplength=700,
        justify="left",
    ).pack(anchor="w", padx=20, pady=(4, 0))

    form_section = ctk.CTkFrame(content, fg_color="transparent")
    form_section.pack(fill="x", padx=20, pady=(18, 12))
    form_section.grid_columnconfigure(1, weight=1)
    form_section.grid_columnconfigure(2, weight=0)

    username_label_row = ctk.CTkFrame(form_section, fg_color="transparent")
    username_label_row.grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(username_label_row, text="Trade API Username").pack(side="left")
    username_help_badge = ctk.CTkLabel(
        username_label_row,
        text="?",
        font=("Segoe UI", 10, "bold"),
        text_color="#0B0E11",
        fg_color="#6E7F8D",
        corner_radius=9,
        width=18,
        height=18,
    )
    username_help_badge.pack(side="left", padx=(6, 0))
    _HoverTip(
        username_help_badge,
        "Your Path of Exile account name (e.g. Player#1234) - shown in-game on the Social tab. "
        "Used to look up the public stash tabs listed under that name.",
    )
    username_entry = ctk.CTkEntry(form_section)
    username_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(12, 0))

    save_label_row = ctk.CTkFrame(form_section, fg_color="transparent")
    save_label_row.grid(row=1, column=0, sticky="w", pady=(10, 0))
    ctk.CTkLabel(save_label_row, text="Save Location").pack(side="left")
    _help_bubble(
        save_label_row,
        "Use Downloads or Documents. Avoid System Folders. Save location for StashScrape CSVs.",
    ).pack(side="left", padx=(6, 0))
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

    wait_label = ctk.CTkLabel(form_section, text="Wait Between Searches (sec)")
    wait_label.grid(row=3, column=0, sticky="w", pady=(10, 0))
    wait_entry = ctk.CTkEntry(form_section)
    wait_entry.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(12, 0), pady=(10, 0))

    wait_warning = ctk.CTkLabel(
        form_section,
        text="Aggressive speeds can cause a temporary rate limit. Suggest a minimum of 120-300s between category searches.",
        text_color="#FF5C5C",
        wraplength=520,
        justify="left",
    )
    wait_warning.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))

    time_estimate_label = ctk.CTkLabel(
        form_section,
        text="",
        text_color="gray60",
        font=ctk.CTkFont(size=12),
        justify="left",
    )
    time_estimate_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=(2, 0))

    category_records: list[tuple[ctk.BooleanVar, str]] = []

    def _update_wait_warning(*_args) -> None:
        try:
            v = int(wait_entry.get().strip())
            wait_warning.grid() if v < 120 else wait_warning.grid_remove()
        except (ValueError, tk.TclError):
            wait_warning.grid()
        _update_time_estimate()

    def _update_time_estimate(*_args) -> None:
        try:
            secs = int(wait_entry.get().strip())
            n_cats = sum(1 for var, _ in category_records if var.get()) if category_records else 0
            if n_cats > 0 and secs > 0:
                total_min = (secs * n_cats) // 60
                time_estimate_label.configure(
                    text=f"~{total_min} min estimated ({n_cats} categories \u00d7 {secs}s)"
                )
                time_estimate_label.grid()
            else:
                time_estimate_label.grid_remove()
        except (ValueError, tk.TclError):
            time_estimate_label.grid_remove()

    wait_entry.bind("<KeyRelease>", _update_wait_warning)

    last_username = str(state.config.get("stash_scrape_username", "") or "").strip()
    last_save_dir = str(state.config.get("stash_scrape_save_dir", "") or "").strip()
    if not last_save_dir:
        # Fall back to the personal-folder default (e.g. for older configs that
        # stored an empty save dir) so users don't start on a protected path.
        last_save_dir = str(
            config_manager.DEFAULT_CONFIG.get("stash_scrape_save_dir", "") or ""
        ).strip()
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
    _update_wait_warning()

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

    ctk.CTkLabel(
        type_section,
        text="Merchant Only filters to merchant/securable stash listings. All Listings includes all available public offers.",
        text_color="gray60",
        font=ctk.CTkFont(size=12),
        wraplength=660,
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    if ITEM_CATEGORIES:
        categories_section = ctk.CTkFrame(content, fg_color="transparent")
        categories_section.pack(fill="both", expand=False, padx=20, pady=(0, 12))

        cat_header_row = ctk.CTkFrame(categories_section, fg_color="transparent")
        cat_header_row.pack(fill="x", anchor="w")
        ctk.CTkLabel(cat_header_row, text="Item Categories").pack(side="left", anchor="w")
        ctk.CTkButton(
            cat_header_row, text="All", width=50,
            command=lambda: [v.set(True) for v, _ in category_records],
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            cat_header_row, text="None", width=50,
            command=lambda: [v.set(False) for v, _ in category_records],
        ).pack(side="right", padx=(4, 0))

        ctk.CTkLabel(
            categories_section,
            text="Select the categories to include in the scrape.",
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(2, 6))

        last_selected_cats: set[str] = set(
            state.config.get("stash_scrape_selected_categories", None) or []
        )

        category_grid = ctk.CTkFrame(categories_section, fg_color="transparent")
        category_grid.pack(fill="x", expand=False)
        total_cats = len(ITEM_CATEGORIES)
        # Use the available horizontal space so the grid stays short and every
        # category is visible without scrolling the form. Embedded in the tab
        # the dialog is full workspace width, so it can take an extra column.
        if total_cats >= 16:
            column_count = 5 if embedded else 4
        elif total_cats >= 9:
            column_count = 3
        elif total_cats >= 4:
            column_count = 2
        else:
            column_count = 1
        rows_per_column = max(1, math.ceil(total_cats / column_count))

        for idx, cat in enumerate(ITEM_CATEGORIES):
            col = idx // rows_per_column
            row = idx % rows_per_column
            category_grid.grid_columnconfigure(col, weight=1, pad=12)
            var = ctk.BooleanVar(value=(cat in last_selected_cats))
            var.trace_add("write", _update_time_estimate)
            ctk.CTkCheckBox(
                category_grid,
                text=_stash_category_display_name(cat),
                variable=var,
            ).grid(row=row, column=col, sticky="w", pady=4, padx=(0, 18))
            category_records.append((var, cat))

    _update_time_estimate()

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

        writable_error = _check_save_location_writable(save_path)
        if writable_error:
            messagebox.showwarning(
                "Stash Scrape",
                writable_error,
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
        prev_cats = list(state.config.get("stash_scrape_selected_categories", None) or [])
        if sorted(selected_categories) != sorted(prev_cats):
            state.config["stash_scrape_selected_categories"] = selected_categories
            config_changed = True
        if config_changed:
            try:
                config_manager.save_config(state.config)
            except Exception as exc:
                logging.warning("Failed to persist stash scrape defaults: %s", exc)

        dialog.destroy()

        if embedded:
            progress_dialog = ctk.CTkFrame(embedded_parent, fg_color="#202020", corner_radius=0)
            progress_dialog.place(relx=0, rely=0, relwidth=1, relheight=1)
        else:
            progress_dialog = ctk.CTkToplevel(root)
            progress_dialog.title("Stash Scrape Progress")
            progress_dialog.geometry("760x560")
            progress_dialog.minsize(640, 460)
            progress_dialog.transient(root)
            _safe_grab_set(progress_dialog)
            progress_dialog.focus_force()

        def _set_progress_close_handler(handler) -> None:
            if not embedded:
                progress_dialog.protocol("WM_DELETE_WINDOW", handler)

        def _release_progress_grab() -> None:
            if not embedded:
                try:
                    progress_dialog.grab_release()
                except Exception:
                    pass

        _set_progress_close_handler(lambda: None)

        progress_frame = ctk.CTkFrame(progress_dialog, fg_color="transparent")
        progress_frame.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(progress_frame, text="Stash Scrape Progress", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(0, 8)
        )

        # --- Stage pipeline indicator ---
        _PIPELINE_STAGES = ["Scrape", "Parse", "Matrix", "Score"]
        _STAGE_COLOR_ACTIVE = "#4CAF50"
        _STAGE_COLOR_PENDING = "#555555"
        _STAGE_COLOR_CURRENT = "#FF9800"

        pipeline_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
        pipeline_frame.pack(fill="x", pady=(0, 8))
        pipeline_stage_labels: dict[str, ctk.CTkLabel] = {}
        for i, stage_name in enumerate(_PIPELINE_STAGES):
            lbl = ctk.CTkLabel(
                pipeline_frame,
                text=stage_name,
                text_color=_STAGE_COLOR_PENDING,
                font=ctk.CTkFont(size=12),
            )
            lbl.pack(side="left")
            pipeline_stage_labels[stage_name] = lbl
            if i < len(_PIPELINE_STAGES) - 1:
                ctk.CTkLabel(
                    pipeline_frame, text=" \u2192 ", text_color=_STAGE_COLOR_PENDING
                ).pack(side="left")

        def _update_pipeline(active_stage: Optional[str], completed_stages: set[str]) -> None:
            if not progress_dialog.winfo_exists():
                return
            for name, lbl in pipeline_stage_labels.items():
                if name in completed_stages:
                    lbl.configure(text_color=_STAGE_COLOR_ACTIVE)
                elif name == active_stage:
                    lbl.configure(text_color=_STAGE_COLOR_CURRENT)
                else:
                    lbl.configure(text_color=_STAGE_COLOR_PENDING)

        completed_pipeline_stages: set[str] = set()

        # --- Scrollable log ---
        progress_text = ctk.CTkTextbox(progress_frame, height=220, wrap="word")
        progress_text.pack(fill="both", expand=True)
        progress_text.configure(state="disabled")
        # Color tags (applied via underlying tk widget)
        _inner_text = progress_text._textbox  # type: ignore[attr-defined]
        _inner_text.tag_configure("error", foreground="#FF5C5C")
        _inner_text.tag_configure("success", foreground="#4CAF50")
        _inner_text.tag_configure("warning", foreground="#FF9800")
        _inner_text.tag_configure("info", foreground="#64B5F6")
        _inner_text.tag_configure("muted", foreground="#888888")

        # --- Status bar ---
        status_var = tk.StringVar(value="Running...")
        status_label = ctk.CTkLabel(progress_frame, textvariable=status_var, anchor="w")
        status_label.pack(fill="x", pady=(8, 0))

        # --- Progress bar + category counter ---
        prog_meta_row = ctk.CTkFrame(progress_frame, fg_color="transparent")
        prog_meta_row.pack(fill="x", pady=(4, 0))
        cat_counter_var = tk.StringVar(value="")
        ctk.CTkLabel(prog_meta_row, textvariable=cat_counter_var, anchor="w").pack(side="left")
        countdown_var = tk.StringVar(value="")
        ctk.CTkLabel(prog_meta_row, textvariable=countdown_var, anchor="e", text_color="#888888").pack(side="right")

        scrape_progress_bar = ctk.CTkProgressBar(progress_frame, mode="determinate")
        scrape_progress_bar.set(0)
        scrape_progress_bar.pack(fill="x", pady=(4, 0))

        current_selection: Optional[str] = None
        current_stage: Optional[str] = None
        stage_state: dict[str, str] = {}
        stop_event = threading.Event()
        cancel_requested = False
        cancel_button: Optional[ctk.CTkButton] = None
        close_button: Optional[ctk.CTkButton] = None
        open_folder_button: Optional[ctk.CTkButton] = None
        _total_items_fetched = 0
        _total_categories = len(selected_categories)
        _completed_categories = 0
        _countdown_end: Optional[float] = None
        _countdown_after_id: Optional[str] = None
        close_after_cancel = False
        scrape_finished = False

        def _refresh_status() -> None:
            if not progress_dialog.winfo_exists():
                return
            item_suffix = (
                f" \u2014 {_total_items_fetched} items" if _total_items_fetched else ""
            )
            if current_selection:
                stage_label = current_stage or stage_state.get(current_selection)
                if stage_label:
                    status_var.set(f"Processing {current_selection} [{stage_label}]{item_suffix}")
                else:
                    status_var.set(f"Processing {current_selection}{item_suffix}")
            else:
                status_var.set("Idle")

        def _close_progress() -> None:
            _release_progress_grab()
            if progress_dialog.winfo_exists():
                progress_dialog.destroy()

        def _append_line(line: str, tag: Optional[str] = None) -> None:
            if not progress_dialog.winfo_exists():
                return
            progress_text.configure(state="normal")
            if tag:
                start = _inner_text.index("end-1c")
                progress_text.insert("end", line + "\n")
                end = _inner_text.index("end-1c")
                _inner_text.tag_add(tag, start, end)
            else:
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
            _set_progress_close_handler(lambda: None)

        def _request_cancel_and_close() -> None:
            nonlocal close_after_cancel
            if scrape_finished:
                _close_progress()
                return
            close_after_cancel = True
            _request_cancel()
            if close_button:
                close_button.configure(state="disabled", text="Cancelling...")

        btn_row = ctk.CTkFrame(progress_frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(12, 0))

        cancel_button = ctk.CTkButton(
            btn_row,
            text="Cancel",
            command=_request_cancel,
        )
        cancel_button.pack(side="left", padx=(0, 8))

        def _open_output_folder() -> None:
            try:
                if sys.platform == "win32":
                    os.startfile(save_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", save_path])
                else:
                    subprocess.Popen(["xdg-open", save_path])
            except Exception:
                pass

        open_folder_button = ctk.CTkButton(
            btn_row,
            text="Open Folder",
            state="disabled",
            command=_open_output_folder,
        )
        open_folder_button.pack(side="left")

        result_run_dir = {"path": None}

        def _view_results() -> None:
            _open_stash_scrape_results(result_run_dir["path"], _close_progress)

        view_results_button = ctk.CTkButton(
            btn_row,
            text="View Results",
            state="disabled",
            command=_view_results,
        )
        view_results_button.pack(side="left", padx=(8, 0))

        close_button = ctk.CTkButton(
            btn_row,
            text="Close",
            command=_request_cancel_and_close,
        )
        close_button.pack(side="right")

        _set_progress_close_handler(_request_cancel)

        def _tick_countdown() -> None:
            nonlocal _countdown_after_id, _countdown_end
            if not progress_dialog.winfo_exists():
                return
            if _countdown_end is None:
                countdown_var.set("")
                return
            remaining = _countdown_end - time.monotonic()
            if remaining <= 0:
                countdown_var.set("")
                _countdown_end = None
                return
            mins, secs = divmod(int(remaining), 60)
            countdown_var.set(f"Next search in {mins}:{secs:02d}")
            _countdown_after_id = progress_dialog.after(1000, _tick_countdown)

        def _handle_progress(event: str, payload: Mapping[str, object]) -> None:
            nonlocal _total_items_fetched, _completed_categories, _countdown_end
            timestamp = time.strftime("%H:%M:%S")
            message, tag = _format_stash_scrape_progress_message(event, payload)

            # Accumulate item count off the main thread (safe: GIL-protected int add)
            if event == "items_batch":
                _total_items_fetched += int(payload.get("items", 0))
            if event == "selection_result":
                _completed_categories += 1

            def _update() -> None:
                nonlocal current_selection, current_stage, _countdown_end, _countdown_after_id
                if not progress_dialog.winfo_exists():
                    return
                if message:
                    _append_line(f"[{timestamp}] {message}", tag)

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
                        # Update pipeline
                        if stage_label:
                            stage_str = str(stage_label)
                            _stage_order = ["Scrape", "Parse", "Matrix", "Score"]
                            active_idx = _stage_order.index(stage_str) if stage_str in _stage_order else -1
                            for si, sn in enumerate(_stage_order):
                                if si < active_idx:
                                    completed_pipeline_stages.add(sn)
                            _update_pipeline(stage_str, completed_pipeline_stages)
                    return

                if event == "selection_start":
                    selection = payload.get("selection")
                    if selection:
                        current_selection = str(selection)
                        stage_label = payload.get("stage") or stage_state.get(current_selection) or "Scrape"
                        stage_state[current_selection] = str(stage_label)
                        current_stage = stage_state[current_selection]
                        _refresh_status()
                    # Reset pipeline to Scrape for new category
                    completed_pipeline_stages.clear()
                    _update_pipeline("Scrape", completed_pipeline_stages)
                    # Update category counter + progress bar
                    done = _completed_categories
                    total = _total_categories or 1
                    cat_counter_var.set(f"Category {done + 1} of {total}")
                    scrape_progress_bar.set(done / total)
                    # Start countdown if a wait delay is expected
                    delay = payload.get("expected_delay")
                    if delay:
                        _countdown_end = time.monotonic() + float(delay)
                        if _countdown_after_id:
                            try:
                                progress_dialog.after_cancel(_countdown_after_id)
                            except Exception:
                                pass
                        _tick_countdown()
                    else:
                        _countdown_end = None
                        countdown_var.set("")

                elif event == "selection_result":
                    done = _completed_categories
                    total = _total_categories or 1
                    cat_counter_var.set(f"Category {done} of {total}")
                    scrape_progress_bar.set(done / total)
                    delay = payload.get("expected_delay")
                    if delay:
                        _countdown_end = time.monotonic() + float(delay)
                        if _countdown_after_id:
                            try:
                                progress_dialog.after_cancel(_countdown_after_id)
                            except Exception:
                                pass
                        _tick_countdown()
                    else:
                        _countdown_end = None
                        countdown_var.set("")

                elif event == "items_batch":
                    _refresh_status()

                elif event == "rate_limited":
                    status_var.set("Rate limited; waiting for retry...")

                elif event == "empty":
                    status_var.set("Category empty; continuing...")

                elif event == "completed":
                    status_var.set("Completed")
                    scrape_progress_bar.set(1.0)
                    cat_counter_var.set(f"Category {_total_categories} of {_total_categories}")
                    _countdown_end = None
                    countdown_var.set("")
                    completed_pipeline_stages.update(["Scrape", "Parse", "Matrix", "Score"])
                    _update_pipeline(None, completed_pipeline_stages)
                    if cancel_button:
                        cancel_button.configure(state="disabled")

                elif event == "error":
                    # A category/search error does not stop the scrape; keep
                    # Cancel usable so the user can stop the remaining queue.
                    status_var.set("Request error; continuing...")

                elif event == "stopped":
                    status_text = str(payload.get("message") or "Scrape stopped.")
                    status_var.set(status_text)
                    _countdown_end = None
                    countdown_var.set("")
                    if cancel_button:
                        cancel_button.configure(state="disabled")

            root.after(0, _update)

        def _finalize(summary: Optional[dict], error: Optional[str]) -> None:
            nonlocal current_selection, current_stage, scrape_finished
            if not progress_dialog.winfo_exists():
                return
            scrape_finished = True
            _set_progress_close_handler(_close_progress)
            if close_button:
                close_button.configure(state="normal", text="Close", command=_close_progress)
            if cancel_button:
                cancel_button.configure(state="disabled")
            _release_progress_grab()

            current_selection = None
            current_stage = None
            stage_state.clear()
            _refresh_status()

            ts = time.strftime("%H:%M:%S")

            if error:
                status_var.set("Error encountered")
                _append_line(f"[{ts}] Error: {error}", "error")
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
                _append_line(f"[{ts}] {cancel_reason}", "warning")
                if close_after_cancel:
                    _close_progress()
                return

            status_var.set("Completed")
            scored_items = summary.get("scored_items", 0)
            final_csv = summary.get("final_csv")
            listing_type = str(summary.get("listing_type", "merchant")).strip().lower()

            # Enable Open Folder once we have a valid output directory
            if open_folder_button and save_path and os.path.isdir(save_path):
                open_folder_button.configure(state="normal")

            # Enable View Results once an aggregate summary CSV was written
            if final_csv:
                result_run_dir["path"] = summary.get("run_directory") or save_path
                if view_results_button:
                    view_results_button.configure(state="normal")

            # Mirror summary to the log so it persists after the messagebox is dismissed
            _append_line(f"[{ts}] -- Summary " + "-" * 28, "info")
            _append_line(f"[{ts}] League: {summary.get('league') or 'Unknown'}", "info")
            _append_line(f"[{ts}] Listing type: {'Merchant Only' if listing_type == 'merchant' else 'All'}", "info")
            registry_source = str(summary.get("category_registry_source") or "bundled")
            _append_line(f"[{ts}] Trade category registry: {registry_source}", "info")
            _append_line(f"[{ts}] Categories processed: {summary.get('processed_categories', 0)}", "info")
            _append_line(f"[{ts}] Items fetched: {summary.get('items', 0)}", "info")
            errors_count = summary.get('errors', 0)
            _append_line(f"[{ts}] Errors: {errors_count}", "error" if errors_count else "info")
            if scored_items:
                _append_line(f"[{ts}] Items scored: {scored_items}", "info")
            if final_csv:
                _append_line(f"[{ts}] Aggregate CSV: {final_csv}", "info")

            category_remaps = summary.get("category_remaps") or []
            skipped_categories = summary.get("skipped_categories") or []
            for remap in category_remaps:
                if isinstance(remap, dict):
                    _append_line(
                        f"[{ts}] Updated category ID for {remap.get('selection')}: "
                        f"{remap.get('from')} -> {remap.get('to')}",
                        "warning",
                    )
            for skipped in skipped_categories:
                if isinstance(skipped, dict):
                    _append_line(
                        f"[{ts}] Skipped {skipped.get('selection')}: {skipped.get('reason')}",
                        "warning",
                    )

            postprocess_issues = []
            for record in summary.get("category_outputs", []) or []:
                if not isinstance(record, dict):
                    continue
                category = str(record.get("category") or record.get("slug") or "Category")
                rec_error = record.get("error") or record.get("scoring_warning")
                if rec_error:
                    postprocess_issues.append(f"{category}: {rec_error}")
            if postprocess_issues:
                _append_line(f"[{ts}] Post-processing issues:", "warning")
                for issue in postprocess_issues:
                    _append_line(f"[{ts}]   {issue}", "warning")

            # Build messagebox text from same data
            msg_lines = [
                f"League: {summary.get('league') or 'Unknown'}",
                f"Listing type: {'Merchant Only' if listing_type == 'merchant' else 'All'}",
                f"Trade category registry: {registry_source}",
                f"Categories processed: {summary.get('processed_categories', 0)}",
                f"Items fetched: {summary.get('items', 0)}",
                f"Errors: {errors_count}",
            ]
            if scored_items:
                msg_lines.append(f"Items scored: {scored_items}")
            if final_csv:
                msg_lines.extend(["", f"Aggregate CSV: {final_csv}"])
            if category_remaps:
                msg_lines.append(f"Updated category IDs resolved: {len(category_remaps)}")
            if skipped_categories:
                msg_lines.extend(
                    ["", "Skipped unsupported categories:"]
                    + [
                        f"{row.get('selection')}: {row.get('reason')}"
                        for row in skipped_categories
                        if isinstance(row, dict)
                    ]
                )
            if postprocess_issues:
                msg_lines.extend(["", "Post-processing issues:"] + postprocess_issues)

            messagebox.showinfo("Stash Scrape", "\n".join(msg_lines))

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

    button_row = ctk.CTkFrame(dialog, fg_color="transparent")
    button_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 16))

    ctk.CTkButton(button_row, text="Submit", command=_handle_submit, width=120).pack(
        side="right"
    )
    ctk.CTkButton(button_row, text="Cancel", command=dialog.destroy, width=120).pack(
        side="right", padx=(0, 8)
    )


def _show_stash_scrape_default() -> None:
    """Sidebar entry point: open the StashScrape tile on the Run view.

    The viewer is activated first so the run form embeds into the workspace
    tile; its "View StashScrapes" toggle drops back to the aggregate viewer.
    """
    _show_stash_scrape_viewer()
    _open_stash_scrape_dialog()



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
    """Refresh layout after a settings section changes without moving the root.

    Calling ``geometry`` here fights the Windows move/resize loop, particularly
    when crossing monitors with different scale factors.  The scrollable home
    view handles its own height, so a dimension rewrite is unnecessary.
    """
    if root is None:
        return
    try:
        root.update_idletasks()
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

DEFAULT_PRICE_FILTER = gui_constants.DEFAULT_PRICE_FILTER
DEFAULT_MAX_PRICE_FILTER = gui_constants.DEFAULT_MAX_PRICE_FILTER
DEFAULT_OVERLAY_HOTKEY = gui_constants.DEFAULT_OVERLAY_HOTKEY
DEFAULT_FILTERED_OVERLAY_HOTKEY = gui_constants.DEFAULT_FILTERED_OVERLAY_HOTKEY
DEFAULT_STASH_SCRAPE_HOTKEY = gui_constants.DEFAULT_STASH_SCRAPE_HOTKEY
DEFAULT_CRAFT_POTENTIAL_HOTKEY = gui_constants.DEFAULT_CRAFT_POTENTIAL_HOTKEY
DEV_SAMPLE_HOTKEY = gui_constants.DEV_SAMPLE_HOTKEY
DEV_CRAFT_SAMPLE_HOTKEY = gui_constants.DEV_CRAFT_SAMPLE_HOTKEY
_overlay_hotkey_handle = None  # track overlay hotkey binding
_filtered_overlay_hotkey_handle = None  # track filtered overlay hotkey binding
_stash_scrape_hotkey_handle = None  # track StashScrape workspace hotkey binding
_craft_potential_hotkey_handle = None  # track Craft Potential hotkey binding
_dev_sample_hotkey_handle = None  # track Ctrl+0 validation picker binding
_dev_craft_sample_hotkey_handle = None  # track Ctrl+Shift+0 validation binding
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

# ---------- bucket/distribution stats cache ----------
_CATEGORY_STATS_CACHE: Optional[dict[str, Any]] = None
_CATEGORY_STATS_MTIME: Optional[float] = None

# ---------- feature-importance manifest cache ----------
_FI_MANIFEST_CACHE: Optional[list[dict]] = None
_FI_MANIFEST_MTIME: Optional[tuple[str, int, int]] = None
# Rendered feature-importance charts, keyed by (category, segment). The chart
# depends only on the manifest, so it is reused across predictions and reset
# whenever the manifest's mtime moves.
_FI_CHART_CACHE: dict[tuple[str, Optional[str]], Optional[bytes]] = {}
_FI_CHART_MTIME: Optional[tuple[str, int, int]] = None

# ---------- opt-in inference profiling ----------
_PROFILE_INFERENCE = os.environ.get("STASHSAGE_PROFILE", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


class _StageTimings:
    """Accumulate per-stage milliseconds for one worker build.

    Unlike `_InferenceTimer` this is always on: the cost is two `perf_counter`
    calls per stage, and the result rides back on the worker event's existing
    `timings` field.  Stages accumulate, so a phase split across the function
    (chart rendering, for one) can be marked more than once.
    """

    def __init__(self) -> None:
        self._totals: dict[str, float] = {}
        self._mark = time.perf_counter()

    def stage(self, name: str) -> None:
        """Attribute everything since the previous mark to `name`."""
        now = time.perf_counter()
        self._totals[name] = self._totals.get(name, 0.0) + (now - self._mark) * 1000.0
        self._mark = now

    def as_dict(self) -> dict[str, int]:
        return {name: round(ms) for name, ms in self._totals.items()}


class _InferenceTimer:
    def __init__(self, label: str) -> None:
        self.label = label
        self.enabled = _PROFILE_INFERENCE
        self._last = time.perf_counter()
        self._parts: list[tuple[str, float]] = []

    def mark(self, name: str) -> None:
        if not self.enabled:
            return
        now = time.perf_counter()
        self._parts.append((name, (now - self._last) * 1000.0))
        self._last = now

    def finish(self) -> None:
        if not self.enabled:
            return
        total = sum(ms for _, ms in self._parts)
        parts = ", ".join(f"{name}={ms:.1f}ms" for name, ms in self._parts)
        logging.info("[profile:%s] total=%.1fms %s", self.label, total, parts)


def _generated_super_models_dir() -> Path:
    return asset_paths.generated_assets_root() / "super_models"


def _super_model_dirs() -> list[Path]:
    # Writable per-user override (where the updater drops fetched models) first,
    # bundled copy as fallback. See poe2trade.app.asset_paths.
    return asset_paths.asset_search_dirs("super_models")


def _load_category_segment_stats() -> dict[str, Any]:
    """Load category_segment_stats.json with mtime invalidation."""
    global _CATEGORY_STATS_CACHE, _CATEGORY_STATS_MTIME
    try:
        p = asset_paths.resolve_asset_file("super_models", "category_segment_stats.json")
        if not p.is_file():
            return {}
        mt = p.stat().st_mtime
        if _CATEGORY_STATS_CACHE is not None and _CATEGORY_STATS_MTIME == mt:
            return _CATEGORY_STATS_CACHE
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _CATEGORY_STATS_CACHE = data
            _CATEGORY_STATS_MTIME = mt
            return data
    except Exception:
        logging.debug("Failed to load category_segment_stats.json", exc_info=True)
    return {}


def _category_stats_entry(cat_norm: str | None, seg_norm: str | None) -> Optional[Mapping[str, Any]]:
    cat = (cat_norm or "").strip().lower()
    seg = (seg_norm or "").strip().lower()
    if not cat:
        return None
    stats = _load_category_segment_stats()
    candidates = [f"{cat}_{seg}"] if seg else [cat]
    if cat == "body_armour":
        candidates.extend([f"body_armor_{seg}"] if seg else ["body_armor"])
    for key in candidates:
        entry = stats.get(key)
        if isinstance(entry, Mapping):
            return entry
    return None


_SEGMENTED_ARMOUR_CATEGORIES = {"body_armour", "helmet", "gloves", "boots"}
_JEWELLERY_CATEGORIES = {"ring", "amulet", "belt"}


def _infer_armour_segment_from_features(features: Any) -> Optional[str]:
    """Infer ar/ev/es segment from a normalized one-row feature frame."""
    if features is None:
        return None
    try:
        if isinstance(features, pd.DataFrame):
            if features.empty:
                return None
            row = features.iloc[0]
        elif isinstance(features, pd.Series):
            row = features
        else:
            return None
    except Exception:
        return None

    def _has(key: str) -> bool:
        try:
            return float(row.get(key, 0) or 0) > 0
        except Exception:
            return False

    ar = _has("ar_norm")
    ev = _has("ev_norm")
    es = _has("es_norm")
    if ar and not (ev or es):
        return "ar_only"
    if ev and not (ar or es):
        return "ev_only"
    if es and not (ar or ev):
        return "es_only"
    if ar and ev and not es:
        return "ar_ev_only"
    if ar and es and not ev:
        return "ar_es_only"
    if ev and es and not ar:
        return "ev_es_only"
    if ar and ev and es:
        return "all_three"
    return None


def _resolve_dashboard_category_segment(
    cat_norm: str | None,
    seg_norm: str | None,
    features: Any = None,
) -> tuple[str | None, str | None]:
    """Normalize dashboard category/segment and recover missing armour segments."""
    cat = (cat_norm or "").strip().lower() or None
    seg = (seg_norm or "").strip().lower() or None
    if cat in _JEWELLERY_CATEGORIES:
        return cat, None
    if cat in _SEGMENTED_ARMOUR_CATEGORIES and not seg:
        seg = _infer_armour_segment_from_features(features)
    return cat, seg


def _scoring_artifact_candidates(
    cat_norm: str | None, seg_norm: str | None
) -> tuple[list[Path], list[Path], list[Path]]:
    """Return scoring JSON/XLSX/PNG candidates in runtime search order."""
    cat = (cat_norm or "").strip().lower()
    seg = (seg_norm or "").strip().lower()
    json_candidates: list[Path] = []
    xlsx_candidates: list[Path] = []
    png_candidates: list[Path] = []
    if not cat:
        return json_candidates, xlsx_candidates, png_candidates

    def _append(base: str) -> None:
        for model_dir in _super_model_dirs():
            json_candidates.append(model_dir / f"{base}_scoring.json")
            xlsx_candidates.append(model_dir / f"{base}_scoring.xlsx")
            png_candidates.append(model_dir / f"{base}_price_dists.png")

    if seg:
        _append(f"{cat}_{seg}")
        if cat == "body_armour":
            _append(f"body_armor_{seg}")
    else:
        _append(cat)
        for kind in ("ring", "amulet", "belt"):
            _append(f"{cat}_{kind}")

    return json_candidates, xlsx_candidates, png_candidates


def _prediction_distribution_buffer(
    cat_norm: str | None,
    seg_norm: str | None,
    marker_value: float | None,
) -> Optional[io.BytesIO]:
    """Build the predicted distribution plot with robust artifact fallbacks."""
    cat = (cat_norm or "").strip().lower()
    seg = (seg_norm or "").strip().lower() or None
    if not cat:
        return None

    title = "XGB · Category Price Distribution"
    marker = _coerce_float(marker_value)
    if marker is None:
        marker = 0.0

    stats_entry = _category_stats_entry(cat, seg)
    if isinstance(stats_entry, Mapping):
        profile = stats_entry.get("distribution_profile")
        if isinstance(profile, Mapping):
            try:
                return generate_predicted_overlay_from_profile(
                    profile,
                    marker,
                    title=title,
                )
            except Exception:
                logging.debug("Distribution profile render failed", exc_info=True)

    json_candidates, xlsx_candidates, png_candidates = _scoring_artifact_candidates(
        cat, seg
    )

    json_path = next((p for p in json_candidates if p.is_file()), None)
    if json_path is not None:
        try:
            df_scored = _load_scoring_json_once(json_path)
            if isinstance(df_scored, pd.DataFrame) and not df_scored.empty:
                return generate_predicted_overlay_with_marker(
                    df_scored,
                    marker,
                    title=title,
                )
        except Exception:
            logging.debug("Distribution JSON render failed for %s", json_path, exc_info=True)

    xlsx_path = next((p for p in xlsx_candidates if p.is_file()), None)
    if xlsx_path is not None:
        try:
            df_scored = pd.read_excel(xlsx_path)
            if isinstance(df_scored, pd.DataFrame) and not df_scored.empty:
                return generate_predicted_overlay_with_marker(
                    df_scored,
                    marker,
                    title=title,
                )
        except Exception:
            logging.debug("Distribution XLSX render failed for %s", xlsx_path, exc_info=True)

    png_path = next((p for p in png_candidates if p.is_file()), None)
    if png_path is not None:
        try:
            with open(png_path, "rb") as handle:
                return io.BytesIO(handle.read())
        except Exception:
            logging.debug("Distribution PNG load failed for %s", png_path, exc_info=True)

    return None


def _recover_bucket_for_display(
    bucket_label: str | None,
    bucket_low: float | None,
    bucket_high: float | None,
    bucket_median: float | None,
    display_pred_value: float | None,
    cat_norm: str | None,
    seg_norm: str | None,
) -> tuple[str | None, float | None, float | None, float | None]:
    display_value = _coerce_float(display_pred_value)
    if display_value is None:
        return bucket_label, bucket_low, bucket_high, bucket_median
    if bucket_label and bucket_low is not None and bucket_high is not None:
        return bucket_label, bucket_low, bucket_high, bucket_median

    ml_stub: dict[str, Any] = {
        "predictions": {"xgb": display_value},
        "bucket": bucket_label,
        "bucket_low": bucket_low,
        "bucket_high": bucket_high,
        "bucket_median": bucket_median,
    }
    try:
        ctx = _compute_display_context(ml_stub, cat_norm=cat_norm, seg_norm=seg_norm)
    except Exception:
        logging.debug("Bucket recovery failed", exc_info=True)
        return bucket_label, bucket_low, bucket_high, bucket_median

    return (
        bucket_label or ctx.bucket_label,
        bucket_low if bucket_low is not None else ctx.bucket_low,
        bucket_high if bucket_high is not None else ctx.bucket_high,
        bucket_median if bucket_median is not None else display_value,
    )


def _load_fi_manifest() -> list[dict]:
    """Load db/super_models/feature_importances_index.json with mtime cache."""
    global _FI_MANIFEST_CACHE, _FI_MANIFEST_MTIME
    try:
        p = asset_paths.resolve_asset_file("super_models", "feature_importances_index.json")
        if not p.is_file():
            _FI_MANIFEST_CACHE = None
            _FI_MANIFEST_MTIME = None
            return []
        stat = p.stat()
        mt = (str(p.resolve()), stat.st_mtime_ns, stat.st_size)
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


def _feature_importance_dashboard_buffer(cat: str | None, seg: str | None) -> io.BytesIO | None:
    """Compact FI chart for one category/segment, as a fresh buffer.

    The rendered PNG depends only on (category, segment) and the manifest, not
    on the scored item, so it is cached; a new BytesIO is handed out per call
    because callers read the buffer to exhaustion.
    """
    global _FI_CHART_CACHE, _FI_CHART_MTIME
    cat_l = str(cat or "").strip().lower()
    seg_l = str(seg or "").strip().lower() or None
    _load_fi_manifest()  # refreshes _FI_MANIFEST_MTIME before we key off it
    if _FI_CHART_MTIME != _FI_MANIFEST_MTIME:
        _FI_CHART_CACHE = {}
        _FI_CHART_MTIME = _FI_MANIFEST_MTIME
    key = (cat_l, seg_l)
    if key not in _FI_CHART_CACHE:
        _FI_CHART_CACHE[key] = _render_feature_importance_png(cat_l, seg_l)
    png = _FI_CHART_CACHE[key]
    return io.BytesIO(png) if png is not None else None


def _render_feature_importance_png(cat_l: str, seg_l: str | None) -> bytes | None:
    """Render the compact FI chart off the Tk thread/process."""
    try:
        entry = next((e for e in _load_fi_manifest()
                      if str(e.get("category", "")).strip().lower() == cat_l
                      and (str(e.get("segment") or "").strip().lower() or None) == seg_l
                      and (str(e.get("model_type", "XGB")).upper() == "XGB")), None)
        feats = (entry or {}).get("features") or []
        feats = [f for f in feats if "block" not in str(f.get("name", "")).lower()][:8]
        if not feats:
            return None
        from poe2trade.utils.chart_utils import ensure_matplotlib
        _, plt, _ = ensure_matplotlib()
        feats = sorted(feats, key=lambda f: float(f.get("importance", 0) or 0), reverse=True)
        names = [str(f.get("name", "")).replace("_norm", "").replace("_", " ") for f in feats]
        vals = np.array([float(f.get("importance", 0) or 0) * 100 for f in feats])
        fig, ax = plt.subplots(figsize=(6.3, max(1.8, .38 * len(names) + .7)), dpi=115)
        ax.barh(range(len(names)), vals, color=plt.cm.viridis((vals - vals.min()) / (vals.max() - vals.min() + 1e-9)), edgecolor="#222")
        ax.set_yticks(range(len(names))); ax.set_yticklabels(names); ax.invert_yaxis(); ax.set_xlabel("Importance (%)")
        fig.tight_layout(); buf = io.BytesIO(); fig.savefig(buf, format="png"); plt.close(fig)
        return buf.getvalue()
    except Exception:
        logging.debug("Feature-importance render failed", exc_info=True)
        return None

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
    popup.title(f"Mod Importances - {cat or ''}{('/' + seg) if seg else ''}")
    _apply_window_icon(popup)
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
    box = ctk.CTkTextbox(frm, wrap="none", font=_FONT_MONO)
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
        # Add horizontal heat-mapped bar chart for >5% features
        try:
            top_all = [(str(f.get("name", "")), float(f.get("importance", 0) or 0)) for f in feats]
            top = sorted(top_all, key=lambda t: t[1], reverse=True)[:8]
            if top:
                import io as _io
                from poe2trade.utils.chart_utils import ensure_matplotlib as _ensure_mpl
                _, _plt, _ = _ensure_mpl()  # Agg backend: safe off the Tk thread
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


def _fi_display_name(value: object, *, empty: str = "All") -> str:
    """Turn manifest identifiers into compact UI labels."""
    text = str(value or "").strip()
    return text.replace("_", " ").replace("-", " ").title() if text else empty


def _fi_ranked_features(entry: dict | None, limit: int = 10) -> list[tuple[str, float]]:
    """Return the visible, rank-sorted feature importances for one model."""
    if not isinstance(entry, dict):
        return []
    category = str(entry.get("category") or "").strip().lower()
    rows: list[tuple[str, float]] = []
    name_map = {
        "ar_norm": "Armour",
        "ev_norm": "Evasion",
        "es_norm": "Energy Shield",
        "block_norm": "Block",
    }
    for feature in entry.get("features") or []:
        raw_name = str(feature.get("name") or "").strip()
        lower_name = raw_name.lower()
        if (category in {"shield", "buckler"} and lower_name == "#% increased block chance") or (
            category not in {"shield", "buckler"} and "block" in lower_name
        ):
            continue
        try:
            importance = float(feature.get("importance") or 0.0)
        except (TypeError, ValueError):
            continue
        if importance <= 0:
            continue
        display_name = name_map.get(lower_name, raw_name.replace("_", " "))
        rows.append((display_name, importance))
    rows.sort(key=lambda row: row[1], reverse=True)
    return rows[: max(0, int(limit))]


def _show_top_mods_view() -> None:
    """Browse the top feature-importance rows from every trained model."""
    activated = _activate_workspace_view("topmods", "Top Mods")
    if activated is None:
        return
    win, created = activated
    if not created:
        return

    win.columnconfigure(0, weight=1)
    win.rowconfigure(2, weight=1)
    header = ctk.CTkFrame(win, corner_radius=10, fg_color="#202A33")
    header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
    ctk.CTkLabel(header, text="Top Mods", font=_FONT_PAGE_TITLE).pack(
        anchor="w", padx=12, pady=(10, 2)
    )
    ctk.CTkLabel(
        header,
        text=(
            "Top 10 modifiers for item value in each trained XGB model. Importances are "
            "normalized within the selected model and do not imply a fixed currency value."
        ),
        text_color="#9AA7B4",
        anchor="w",
        justify="left",
        wraplength=900,
    ).pack(fill="x", padx=12, pady=(0, 10))

    manifest = [
        entry for entry in _load_fi_manifest()
        if isinstance(entry, dict)
        and str(entry.get("model_type") or "XGB").strip().upper() == "XGB"
    ]
    if not manifest:
        ctk.CTkLabel(win, text="No feature-importance tables are installed.").grid(
            row=1, column=0, sticky="w", padx=20, pady=20
        )
        return

    controls = ctk.CTkFrame(win, fg_color="transparent")
    controls.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
    controls.columnconfigure(4, weight=1)
    category_var = tk.StringVar()
    segment_var = tk.StringVar()

    categories = sorted({str(entry.get("category") or "") for entry in manifest})
    category_labels = {_fi_display_name(category): category for category in categories}
    ctk.CTkLabel(controls, text="Category").grid(row=0, column=0, sticky="w")
    category_menu = ctk.CTkOptionMenu(
        controls, variable=category_var, values=list(category_labels), width=190
    )
    category_menu.grid(row=0, column=1, sticky="w", padx=(8, 18))
    ctk.CTkLabel(controls, text="Segment").grid(row=0, column=2, sticky="w")
    segment_menu = ctk.CTkOptionMenu(controls, variable=segment_var, values=["All"], width=170)
    segment_menu.grid(row=0, column=3, sticky="w", padx=(8, 18))

    table_frame = ctk.CTkFrame(win, corner_radius=10)
    table_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
    table_frame.columnconfigure(0, weight=1)
    table_frame.rowconfigure(1, weight=1)
    model_info = ctk.CTkLabel(table_frame, text="", anchor="w", text_color="#9AA7B4")
    model_info.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
    tree = ttk.Treeview(
        table_frame,
        columns=("rank", "feature", "importance"),
        show="headings",
        style="TopMods.Treeview",
        height=10,
    )
    tree.heading("rank", text="#")
    tree.heading("feature", text="Modifier / Feature")
    tree.heading("importance", text="Importance")
    tree.column("rank", width=55, minwidth=45, stretch=False, anchor="center")
    tree.column("feature", width=650, minwidth=280, anchor="w")
    tree.column("importance", width=150, minwidth=110, stretch=False, anchor="e")
    tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "TopMods.Treeview", background="#202020", foreground="#F0F0F0",
        fieldbackground="#202020", rowheight=34, font=("Segoe UI", 11),
        borderwidth=0, relief="flat", lightcolor="#202020", darkcolor="#202020",
    )
    style.configure(
        "TopMods.Treeview.Heading", background="#2E3A46", foreground="#FFFFFF",
        font=("Segoe UI", 11, "bold"), padding=(6, 7), relief="flat",
        borderwidth=0, lightcolor="#2E3A46", darkcolor="#2E3A46",
    )
    style.map(
        "TopMods.Treeview",
        background=[("selected", "#1F6AA5")],
        foreground=[("selected", "#FFFFFF")],
    )
    style.map(
        "TopMods.Treeview.Heading",
        background=[("active", "#3A4A59")],
        relief=[("pressed", "flat"), ("active", "flat")],
    )

    segment_values: dict[str, object] = {}

    def selected_entries() -> list[dict]:
        category = category_labels.get(category_var.get(), "")
        segment = segment_values.get(segment_var.get())
        return [
            entry for entry in manifest
            if str(entry.get("category") or "") == category
            and entry.get("segment") == segment
        ]

    def render_table(*_args) -> None:
        tree.delete(*tree.get_children())
        entries = selected_entries()
        entry = entries[0] if entries else None
        rows = _fi_ranked_features(entry)
        for rank, (name, importance) in enumerate(rows, start=1):
            tree.insert("", "end", values=(rank, name, f"{importance * 100:.1f}%"))
        if entry is None:
            model_info.configure(text="No table is available for this selection.")
            return
        r2 = entry.get("r2")
        score = f"  |  R-squared: {float(r2):.3f}" if isinstance(r2, (int, float)) else ""
        model_info.configure(text=f"{len(rows)} ranked features{score}")

    def refresh_segments(*_args) -> None:
        category = category_labels.get(category_var.get(), "")
        raw_segments = sorted(
            {entry.get("segment") for entry in manifest if str(entry.get("category") or "") == category},
            key=lambda value: str(value or ""),
        )
        segment_values.clear()
        for segment in raw_segments:
            label = _fi_display_name(segment)
            segment_values[label] = segment
        labels = list(segment_values) or ["All"]
        segment_menu.configure(values=labels)
        segment_var.set(labels[0])
        render_table()

    category_menu.configure(command=refresh_segments)
    segment_menu.configure(command=render_table)
    category_var.set(next(iter(category_labels)))
    refresh_segments()


def _add_help_copy(parent, heading: str, paragraphs: list[str], bullets: list[str]) -> None:
    """Add one readable section to a scrollable Help tab."""
    ctk.CTkLabel(parent, text=heading, font=_FONT_SUBHEADING, anchor="w").pack(
        fill="x", padx=16, pady=(16, 6)
    )
    for paragraph in paragraphs:
        ctk.CTkLabel(
            parent, text=paragraph, anchor="w", justify="left", wraplength=900,
            text_color="#C8D2DC",
        ).pack(fill="x", padx=20, pady=(0, 7))
    for bullet in bullets:
        ctk.CTkLabel(
            parent, text=f"\u2022  {bullet}", anchor="w", justify="left",
            wraplength=880, text_color="#C8D2DC",
        ).pack(fill="x", padx=28, pady=3)


def _show_help_view() -> None:
    """Show native in-app guidance adapted from index.html.j2."""
    activated = _activate_workspace_view("help", "Help")
    if activated is None:
        return
    win, created = activated
    if not created:
        return
    win.columnconfigure(0, weight=1)
    win.rowconfigure(1, weight=1)
    header = ctk.CTkFrame(win, corner_radius=10, fg_color="#202A33")
    header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
    ctk.CTkLabel(header, text="Help", font=_FONT_PAGE_TITLE).pack(
        anchor="w", padx=12, pady=(10, 2)
    )
    ctk.CTkLabel(
        header, text="How StashSage approaches pricing and how to use its main tools.",
        text_color="#9AA7B4", anchor="w",
    ).pack(fill="x", padx=12, pady=(0, 2))
    website_url = "https://rheinze08.github.io/StashSage/"
    website_link = ctk.CTkLabel(
        header,
        text=f"For more reference, visit {website_url}",
        text_color="#58A6D8",
        anchor="w",
        cursor="hand2",
        font=("Segoe UI", 12, "underline"),
    )
    website_link.pack(fill="x", padx=12, pady=(0, 10))
    website_link.bind("<Button-1>", lambda _event: webbrowser.open(website_url))

    tabs = ctk.CTkTabview(win)
    tabs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
    for tab_name in ("Why StashSage", "Explore Features", "Discussion", "Notes"):
        tab = tabs.add(tab_name)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        if tab_name == "Why StashSage":
            _add_help_copy(scroll, "Does this sound like you?", [], [
                "You pick up items that could be good, but are not quite sure.",
                "Your stash fills with items you plan to price later.",
                "Typing mods, comparing rolls, and using the trade UI feels tedious.",
                "You do not need a perfect price; you want a smart starting point.",
                "One hotkey, instant comparable items, list it, and get back to mapping.",
            ])
            _add_help_copy(scroll, "Why estimates differ", [
                "There is no single right price. Demand changes with leagues and patches, and the available data comes from current unsold listings. Expensive listings linger while good deals disappear, so raw trade results can behave more like a noisy price ceiling.",
                "StashSage focuses on faster, practical choices: judge a reasonable listing price, encode market patterns, and avoid obvious trolls or stale posts.",
            ], [])
        elif tab_name == "Explore Features":
            _add_help_copy(scroll, "Prediction UI", [], [
                "Hover an item in-game and press Ctrl+1, or your configured Overlay hotkey.",
                "Use Ctrl+2 for a filtered comparison where selected modifiers stay fixed.",
                "Compare XGBoost's whole-dataset estimate with KNN's similar-item estimate.",
                "Review saved snapshots from the History tab.",
            ])
            _add_help_copy(scroll, "StashScrape", [], [
                "Open StashScrape, enter your Trade API username, and choose a save folder.",
                "Choose a conservative delay between searches and the categories to scrape.",
                "Run the pipeline, then browse completed CSV results in View StashScrapes.",
            ])
            _add_help_copy(scroll, "CraftOracle and Top Mods", [], [
                "CraftOracle estimates how eligible missing modifiers could move the XGB prediction.",
                "Top Mods shows the ten most important trained features for each category and segment.",
            ])
        elif tab_name == "Discussion":
            _add_help_copy(scroll, "Model insights", [], [
                "Models are trained on current unsold listings, so even reasonably priced items may not sell.",
                "XGBoost evaluates modifiers and their interactions across the category dataset.",
                "KNN uses modifier weighting to find similar items, then summarizes their listed prices.",
                "The two approaches can disagree; each provides a different perspective on potential value.",
                "Be careful pricing items with fewer modifiers against six-mod comparables.",
                "Models are trained for rare items, not magic or unique items.",
                "The overlay is optimized for Windowed Fullscreen.",
            ])
        else:
            _add_help_copy(scroll, "Model notes", [], [
                'The model ignores "mark of the abyssal lord", "allocates passive", and "on corruption" modifiers.',
                "Socketables are ignored because they are not treated as underlying item modifiers.",
                "Quality and socketable effects are normalized back to base modifier values.",
                "Armour, evasion, and energy shield modifiers are represented in the resulting base stats.",
            ])


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
    """Render a single-line horizontal price band with contextual text.

    Two modes are supported:
    - mode="dataset": shows the supervised model's prediction and bucket label
    - mode="nearest": shows quick stats derived from nearest items

    Both model bars keep their header and values on one line.
    """
    bucket = (label or "").capitalize()
    bcol = _BUCKET_COLOURS.get(bucket.lower(), "#EEEEEE")
    bar_colour = bcol if mode == "dataset" and bucket else _BAR_COLOUR
    fr = ctk.CTkFrame(parent, fg_color=bar_colour, corner_radius=8)
    fr.configure(height=44)
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

    if mode == "nearest":
        parts = ["Model #2 \u00b7 Similar Items"]
        if isinstance(nearest_median, (int, float)):
            parts.append(f"Median {_priced_text(nearest_median)}")
        if isinstance(nearest_mean, (int, float)):
            parts.append(f"Mean {_priced_text(nearest_mean)}")
        if combined_prices_line:
            parts.append(combined_prices_line)
        text = "  |  ".join(parts)
    else:
        val = dataset_pred_value if isinstance(dataset_pred_value, (int, float)) else pred_median
        price_text = _priced_text(val) if isinstance(val, (int, float)) else "?e"
        category = (category_title or "Category").strip().title()
        text = (
            f"Model #1 \u00b7 XGB  |  Prediction {price_text}"
            f"  |  Relative {bucket or 'Estimated'} value  |  {category}"
        )
    ctk.CTkLabel(
        content,
        text=text,
        font=("Segoe UI", 15, "bold"),
        text_color="white",
    ).pack(fill="x", padx=8, pady=5)


def _currency_conversion_text() -> str:
    """Return the active shorthand-to-exalt conversion line for the UI."""
    try:
        return (
            f"1d = {int(round(conversion.divine))}e,  "
            f"1c = {int(round(conversion.chaos))}e"
        )
    except (TypeError, ValueError, OverflowError, AttributeError):
        return "1d = ?e,  1c = ?e"


def _model_conversion_text(snapshot: Mapping[str, Any]) -> str:
    """Format a frozen model-training conversion snapshot for the overlay."""
    values = snapshot.get("conversions") if isinstance(snapshot, Mapping) else None
    if not isinstance(values, Mapping):
        return "1d = ?e,  1c = ?e"
    try:
        return (
            f"1d = {int(round(float(values.get('divine'))))}e,  "
            f"1c = {int(round(float(values.get('chaos'))))}e"
        )
    except (TypeError, ValueError, OverflowError):
        return "1d = ?e,  1c = ?e"


def _model_conversion_banner(parent, snapshot: Mapping[str, Any], *, grid_row: int) -> None:
    """Render the model-specific conversion context already resolved by the worker."""
    frame = ctk.CTkFrame(parent, corner_radius=8, fg_color="#243642")
    frame.grid(row=grid_row, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 6))
    is_mock = bool(snapshot.get("is_mock", False))
    heading = "Model training conversions (demo)" if is_mock else "Model training conversions"
    ctk.CTkLabel(
        frame,
        text=f"{heading}:  {_model_conversion_text(snapshot)}",
        font=_FONT_STATUS_BANNER,
        text_color="#BBD8F0" if not is_mock else "#E0A53B",
        anchor="center",
        justify="center",
    ).pack(fill="x", padx=12, pady=(8, 7))


def _refresh_currency_banner_text() -> None:
    values = {"d": conversion.divine, "c": conversion.chaos}
    for labels in list(_currency_banner_value_labels):
        try:
            for unit, label in labels.items():
                if label.winfo_exists():
                    label.configure(text=str(int(round(float(values[unit])))))
        except Exception:
            pass


def _refresh_live_prices_async(*, force: bool, user_requested: bool = False) -> None:
    """Fetch rates off-thread, then update every visible conversion banner."""
    global _live_price_refresh_in_flight
    if _live_price_refresh_in_flight:
        return
    _live_price_refresh_in_flight = True
    if user_requested:
        for button in list(_currency_refresh_buttons):
            try:
                if button.winfo_exists():
                    button.configure(state="disabled", text="Refreshing…")
            except Exception:
                pass

    def work() -> None:
        try:
            snapshot = conversion.refresh(force=force, league=active_league())
            error = None
        except Exception as exc:
            logging.exception("Live price refresh failed")
            snapshot = None
            error = str(exc)

        def finish() -> None:
            global _live_price_refresh_in_flight
            _live_price_refresh_in_flight = False
            if snapshot is not None:
                _refresh_currency_banner_text()
                _apply_price_filter(state.config)
                _apply_max_price_filter(state.config)
                result = "Updated" if snapshot.source == "poe2scout" else "Using cached rates"
            else:
                result = "Refresh failed"
            if user_requested:
                for button in list(_currency_refresh_buttons):
                    try:
                        if not button.winfo_exists():
                            _currency_refresh_buttons.remove(button)
                            continue
                        button.configure(state="normal", text=result)
                        button.after(1800, lambda btn=button: btn.winfo_exists() and btn.configure(text="Refresh prices"))
                    except Exception:
                        pass
            if user_requested and snapshot is None:
                messagebox.showwarning(
                    "Live Prices",
                    f"Could not refresh live prices. Existing conversions were kept.\n\n{error}",
                    parent=root if root and root.winfo_exists() else None,
                )

        if root is not None and root.winfo_exists():
            root.after(0, finish)

    threading.Thread(target=work, daemon=True, name="LivePriceRefresh").start()


def _currency_conversion_banner(
    parent, *, compact: bool = False, grid: bool = False, grid_row: int = 0
):
    """Render the active pricing conversions prominently in a parent frame."""
    frame = ctk.CTkFrame(parent, corner_radius=8, fg_color="#263B4A")
    if grid:
        frame.grid(row=grid_row, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 6))
    else:
        frame.pack(fill="x", padx=10, pady=(4 if compact else 8, 8))
    content = ctk.CTkFrame(frame, fg_color="transparent")
    content.pack(fill="x", padx=12, pady=(6, 6))
    ctk.CTkLabel(
        content,
        text="Live Prices",
        font=_FONT_STATUS_BANNER,
        text_color="#F7D774",
        anchor="center",
    ).pack(side="left", padx=(0, 18))
    values = {"d": conversion.divine, "c": conversion.chaos}
    value_labels: dict[str, ctk.CTkLabel] = {}
    for index, unit in enumerate(("d", "c")):
        group = ctk.CTkFrame(content, fg_color="transparent")
        group.pack(side="left", padx=(0 if index == 0 else 14, 0))
        icon = currency_orb_label(group, unit, size=20)
        if icon is not None:
            icon.pack(side="left", padx=(0, 3))
        ctk.CTkLabel(
            group, text="=", font=("Segoe UI", 14, "bold"), text_color="white"
        ).pack(side="left", padx=(0, 3))
        try:
            value = str(int(round(float(values[unit]))))
        except (TypeError, ValueError, OverflowError):
            value = "?"
        value_label = ctk.CTkLabel(
            group, text=value, font=("Segoe UI", 14, "bold"), text_color="white"
        )
        value_label.pack(side="left", padx=(0, 2))
        value_labels[unit] = value_label
        exalt = currency_orb_label(group, "e", size=20)
        if exalt is not None:
            exalt.pack(side="left")
    _currency_banner_value_labels.append(value_labels)
    refresh_button = ctk.CTkButton(
        frame,
        text="Refresh prices",
        width=110,
        height=28,
        font=_FONT_HELPER,
        fg_color="#33414E",
        hover_color="#3F5160",
        command=lambda: _refresh_live_prices_async(force=True, user_requested=True),
    )
    refresh_button.place(relx=1.0, rely=0.5, x=-10, anchor="e")
    _currency_refresh_buttons.append(refresh_button)
    return frame


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

    json_candidates: list[Path] = []
    xlsx_candidates: list[Path] = []

    # Search the writable override dir before the bundled one so updated scoring
    # sidecars take priority; non-existent candidates are filtered by .is_file().
    for model_dir in _super_model_dirs():
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
    stats_entry = _category_stats_entry(cat_norm, seg_norm)
    if not intervals and isinstance(stats_entry, Mapping):
        intervals = _normalise_bucket_intervals(stats_entry.get("bucket_intervals", {}))

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

    if percentile_values is None and isinstance(stats_entry, Mapping):
        percentile_values = _normalize_percentiles(stats_entry.get("percentile_values"))

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
_DPS_CORE_KEYS = (
    "dps_total",
    "dps_physical",
    "dps_fire",
    "dps_cold",
    "dps_lightning",
    "dps_chaos",
)
_CORE_KEYS = {
    _DPS_CORE_KEYS[0]: "Total DPS",
    _DPS_CORE_KEYS[1]: "Physical DPS",
    _DPS_CORE_KEYS[2]: "Fire DPS",
    _DPS_CORE_KEYS[3]: "Cold DPS",
    _DPS_CORE_KEYS[4]: "Lightning DPS",
    _DPS_CORE_KEYS[5]: "Chaos DPS",
    "crit_chance": "Critical Chance",
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
    "dps_total": ["dps_total", "total dps"],
    "dps_physical": ["dps_physical", "physical dps", "phys dps"],
    "dps_fire": ["dps_fire", "fire dps"],
    "dps_cold": ["dps_cold", "cold dps"],
    "dps_lightning": ["dps_lightning", "lightning dps"],
    "dps_chaos": ["dps_chaos", "chaos dps"],
    "crit_chance": ["crit_chance", "critical chance", "critical hit chance", "crit"],
}

_EXTRA_MIRROR_KEYS = {
    "extra_sockets": "Extra Sockets",
    **WAYSTONE_MODEL_PROPERTY_LABELS,
}
_EXTRA_STATUS_KEYS = set()

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
    "prediction_log": threading.Lock(),  # Prediction log popup
    "auction": threading.Lock(),  # Auction Tool single hotkey
    "sample": threading.Lock(),  # Ctrl+0 validation sample picker
    "craft_sample": threading.Lock(),  # Ctrl+Shift+0 CraftOracle validation picker
    "craft_potential": threading.Lock(),  # Counterfactual mod analysis
}

_prediction_log_window: Optional[ctk.CTkToplevel] = None
_stash_viewer_window: Optional[ctk.CTkToplevel] = None
_prediction_log_lock = threading.Lock()
_prediction_log_queue: "queue.Queue[dict]" = queue.Queue()
_prediction_log_worker_started = False
_prediction_log_worker_lock = threading.Lock()


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
        _copy_item_description()
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
            _copy_item_description()
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


def _left_mouse_button_down() -> bool | None:
    """Return the physical left-button state when Windows exposes it.

    This is deliberately telemetry only: the presenter remains the sole owner
    of game-facing UI and its backdrop owns dismissal clicks.  Recording the
    state at the hotkey boundary lets us distinguish a launch-time held click
    from a click that happened after the backdrop was already visible.
    """
    if sys.platform != "win32":
        return None
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
    except (AttributeError, OSError):
        return None


def _copy_item_description() -> None:
    """Invoke the user's native in-game copy shortcut with a safe fallback."""
    configured = str(state.config.get("copy_hotkey", DEFAULT_COPY_HOTKEY) or "").strip()
    desired = configured or DEFAULT_COPY_HOTKEY
    try:
        keyboard.press_and_release(desired)
    except Exception as exc:
        if desired.lower() == DEFAULT_COPY_HOTKEY:
            raise
        logging.warning(
            "Native copy hotkey %r failed; falling back to %s: %s",
            desired,
            DEFAULT_COPY_HOTKEY,
            exc,
        )
        keyboard.press_and_release(DEFAULT_COPY_HOTKEY)


def _clipboard_text_with_retry(max_wait_ms: int = 800, step_ms: int = 80) -> str:
    """Best-effort clipboard read after issuing the configured copy shortcut.

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


def _looks_like_poe_item_clipboard(text: str) -> bool:
    """Return whether *text* has the stable headers of a copied PoE item."""
    normalized = str(text or "").replace("\r\n", "\n")
    return "Item Class:" in normalized and "Rarity:" in normalized


def _begin_fresh_item_copy() -> str | None:
    """Clear the clipboard, then ask the game to copy the item under the cursor.

    Clearing first is deliberate: comparing against the old clipboard alone cannot
    distinguish a newly copied item from an identical stale item.  The original
    text is returned so it can be restored if the game does not provide a valid
    item payload.
    """
    try:
        previous = _clipboard_text_with_retry()
        try:
            pyperclip.copy("")
        except Exception:
            # A transient clipboard lock must not prevent the configured native
            # copy hotkey from reaching the game. The subsequent fresh-item
            # validation still rejects non-item clipboard contents.
            logging.debug("Could not clear clipboard before item copy", exc_info=True)
        _copy_item_description()
        return previous
    except Exception:
        logging.info("Could not start fresh item clipboard capture", exc_info=True)
        return None


def _wait_for_fresh_item_copy(
    previous_clipboard: str,
    *,
    max_wait_ms: int = 800,
    step_ms: int = 50,
) -> str | None:
    """Wait for a new valid item copy, restoring the clipboard if none arrives."""
    deadline = time.monotonic() + max(0, max_wait_ms) / 1000.0
    while time.monotonic() < deadline:
        text = _clipboard_text_with_retry()
        if _looks_like_poe_item_clipboard(text):
            # Keep the successful item copy on the clipboard, as PoE normally
            # does.
            return text
        time.sleep(max(1, step_ms) / 1000.0)

    try:
        pyperclip.copy(previous_clipboard)
    except Exception:
        logging.debug("Could not restore clipboard after empty item copy", exc_info=True)
    logging.info("Price hotkey ignored: no fresh PoE item was copied")
    return None


def _run_fresh_item_hotkey(
    kind: str,
    start: Callable[[str, threading.Lock], None],
) -> None:
    """Run an item-ingest hotkey only after its own fresh copy succeeds."""
    lock = _hotkey_busy[kind]
    if not lock.acquire(blocking=False):
        return

    logging.info(
        "Presenter telemetry: stage=hotkey_received kind=%s left_button_down=%s",
        kind,
        _left_mouse_button_down(),
    )

    previous = _begin_fresh_item_copy()
    if previous is None:
        lock.release()
        return

    def wait_for_item() -> None:
        text = _wait_for_fresh_item_copy(previous)
        if not text:
            lock.release()
            return
        try:
            root.after(0, lambda: start(text, lock))
        except Exception:
            lock.release()

    threading.Thread(target=wait_for_item, daemon=True).start()


def _prepare_filtered_context(text: str) -> dict | None:
    try:
        prepared = prepare_item_features(text)
    except Exception:
        logging.exception("Failed to prepare filtered overlay context")
        return None

    try:
        parsed = dict(prepared.raw_parsed or {})
        name_raw = (parsed.get("Item Name") or "").strip()
        base_type_raw = (parsed.get("Base Type") or "").strip()
        item_name = name_raw or base_type_raw or "(Unknown item)"
        icon_name = base_type_raw or name_raw or item_name
        cat = prepared.model_category or prepared.category
        seg = None if cat in ("ring", "amulet", "belt") else prepared.segment
        if prepared.category == "jewel":
            seg = None

        return {
            "text": text,
            "parsed": parsed,
            "category": cat,
            "segment": seg,
            "base_X": (
                prepared.display_features
                if getattr(prepared, "display_features", None) is not None
                else prepared.features
            ),
            "item_name": item_name,
            "icon_name": icon_name,
        }
    except Exception:
        logging.exception("Failed to prepare filtered overlay context")
        return None


def _fmt_disp(value: float | None) -> str:
    """Format a numeric value for display, returning '-' for non-finite input."""
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


def _craft_roll_label(row: craft_potential.CraftPotentialRow) -> str:
    """Render one Craft roll using the shared presentation contract."""
    return craft_roll_text(row)


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

    for key in _CORE_KEYS.keys():
        val = _numeric(base_series, key)
        if val == 0 and not (key in _DPS_CORE_KEYS and key in getattr(base_series, "index", [])):
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
        if cat_lc in {"staves", "staffs"}:
            cat_lc = "staff"
        # Segment inference from *_norm core values (same heuristic as gui_utils)
        ar, ev, es = (
            float(base_series.get(k, 0) or 0) for k in ("ar_norm", "ev_norm", "es_norm")
        )
        seg = None
        if cat_lc not in {"ring", "amulet", "belt", "jewel", "sceptre", "staff", "wand", "quiver", "tablet", "waystone", *DPS_WEAPON_CATEGORIES}:
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
        from poe2trade.utils.ml_unsuper_utils import _load_unsuper_bundle as _load
        # Search the override dir then the bundled dir per file: a partial
        # updater override of unsuper_models must not hide a bundle that only
        # exists in the package directory.
        b = None
        for _mdl_dir in asset_paths.asset_search_dirs("unsuper_models"):
            b = _load(cat_lc or "default_model", seg, _mdl_dir)
            if isinstance(b, dict) and "overlay_df" in b:
                break
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


def _show_filtered_filter_popup(
    ctx: dict,
    release_lock: threading.Lock | None = None,
) -> None:
    """Pop up the filtered-overlay dialog to capture mod constraints."""
    released = False

    def release_once() -> None:
        nonlocal released
        if released or release_lock is None:
            return
        released = True
        try:
            release_lock.release()
        except RuntimeError:
            pass

    if not (root and root.winfo_exists()):
        release_once()
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
        release_once()
        return

    def _close_popup() -> None:
        for window in (popup, backdrop):
            try:
                if window is not None and window.winfo_exists():
                    window.destroy()
            except Exception:
                logging.debug("filter overlay teardown failed", exc_info=True)
        release_once()

    backdrop, popup = _create_overlay_dialog(on_cancel=_close_popup)

    def _overlay_error(title: str, message: str) -> None:
        # A native error dialog can hide behind the top-most overlay windows, so
        # drop their top-most flag while it is shown, then restore it.
        for window in (backdrop, popup):
            try:
                window.attributes('-topmost', False)
            except Exception:
                pass
        messagebox.showerror(title, message, parent=popup)
        for window in (backdrop, popup):
            try:
                if window.winfo_exists():
                    window.attributes('-topmost', True)
            except Exception:
                pass
        try:
            popup.lift()
            popup.focus_force()
        except Exception:
            pass

    frame = ctk.CTkFrame(popup)
    frame.pack(fill='both', expand=True, padx=16, pady=16)

    # No title bar on the frameless overlay, so surface the heading in-content.
    ctk.CTkLabel(
        frame,
        text='Filtered Mods for Nearest Items',
        font=_FONT_SECTION_TITLE,
        anchor='w',
    ).pack(anchor='w', pady=(0, 8))

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
        text='Enter filters like 35+ (at least 35), 35= (exactly 35), or 35% (+/-35%).',
        wraplength=560,
        justify='left',
        ).pack(anchor='w')

    scroll = ctk.CTkScrollableFrame(frame, height=360, width=540)
    scroll.pack(fill='both', expand=True, pady=12)

    entries: list[tuple[dict, ctk.CTkEntry]] = []

    header_row = ctk.CTkFrame(scroll, fg_color='transparent')
    header_row.pack(fill='x', pady=(0, 6))
    header_row.grid_columnconfigure(0, weight=1)
    header_row.grid_columnconfigure(1, weight=0)
    ctk.CTkLabel(
        header_row, text='Modifier and current value', anchor='w', font=_FONT_BODY_BOLD
    ).grid(row=0, column=0, sticky='ew', padx=(0, 12))
    ctk.CTkLabel(
        header_row, text='Filter', anchor='e', font=_FONT_BODY_BOLD
    ).grid(row=0, column=1, sticky='e')

    for idx, row in enumerate(rows):
        row_frame = ctk.CTkFrame(scroll, fg_color='transparent')
        row_frame.pack(fill='x', pady=4)
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, weight=0)

        label_txt = f"{row['label']}: {row['display']}"
        ctk.CTkLabel(row_frame, text=label_txt, anchor='w', wraplength=390).grid(
            row=0, column=0, sticky='ew', padx=(0, 12)
        )

        entry = ctk.CTkEntry(row_frame, width=120)
        entry.grid(row=0, column=1, sticky='e')
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

    def _clear_entries() -> None:
        for _, entry in entries:
            entry.delete(0, 'end')

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
                _overlay_error('Invalid filter', str(exc))
                return
            filters[row['key']] = (op, val)

        _close_popup()
        if item_key:
            _FILTER_ENTRY_MEMORY[item_key] = snapshot
        _start_filtered_overlay_with_filters(ctx, filters)

    def _cancel() -> None:
        _close_popup()

    ctk.CTkButton(btn_frame, text='Match Existing', command=_apply_match_mods).pack(side='left', expand=True, fill='x', padx=(0, 6))
    ctk.CTkButton(btn_frame, text='Match Current or Better', command=_apply_match_greater_mods).pack(side='left', expand=True, fill='x', padx=(0, 6))
    ctk.CTkButton(btn_frame, text='Clear', command=_clear_entries).pack(side='left', expand=True, fill='x', padx=(0, 6))
    ctk.CTkButton(btn_frame, text='Apply', command=_apply_filters).pack(side='left', expand=True, fill='x', padx=(0, 6))
    ctk.CTkButton(btn_frame, text='Cancel', command=_cancel).pack(side='left', expand=True, fill='x')

    _center_overlay_dialog(popup)


def _start_filtered_overlay_async(text: str, release_lock: threading.Lock | None = None) -> None:
    """Prepare Ctrl+2 off-thread while its hotkey lock owns the full session."""
    def release_once() -> None:
        if release_lock is None:
            return
        try:
            release_lock.release()
        except RuntimeError:
            pass

    def work() -> None:
        try:
            ctx = _prepare_filtered_context(text)

            def show() -> None:
                if ctx is None:
                    messagebox.showerror('StashSage', 'Could not prepare filtered overlay for this item.')
                    release_once()
                    return
                if not _launch_filtered_filter_popup(ctx, release_lock=release_lock):
                    _show_filtered_filter_popup(ctx, release_lock=release_lock)

            root.after(0, show)
        except Exception:
            logging.exception("Could not prepare filtered overlay")
            release_once()

    threading.Thread(target=work, daemon=True).start()


def _start_filtered_overlay_with_filters(
    ctx: dict,
    filters: dict[str, tuple[str, object]],
    *,
    handoff_delay_ms: int = 80,
) -> None:
    """Pass filters to scoring after the Apply mouse release is safely complete."""
    ctx_out = dict(ctx)
    ctx_out["filters"] = filters
    ctx_out["knn_filtered_k"] = _resolve_knn_filtered_k(state.config)
    # The isolated filter stays visible for this brief release-safe interval.
    # Replacing it during the button's native release can expose the game just
    # in time for that same click to pick up the hovered item.
    root.after(handoff_delay_ms, lambda: _show_filtered_overlay_result(ctx_out))


def _show_filtered_overlay_result(ctx: dict) -> None:
    """Start filtered scoring through the same payload/presenter pipeline."""
    if not (root and root.winfo_exists()):
        return

    knn_limit = ctx.get('knn_filtered_k')
    if not isinstance(knn_limit, int) or knn_limit <= 0:
        knn_limit = _resolve_knn_filtered_k(state.config)
    raw_text = ctx.get('text') or ''

    _score_dashboard_async(raw_text, filters=ctx.get('filters'), knn_limit=knn_limit)


# +--------------------------------------------------------+

# ------------- price-filter helpers ----------------------
PRICE_FILTER_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[ecd]?\s*$", re.I)


def _apply_price_filter(cfg: dict) -> None:
    raw = str(cfg.get("price_mirror_filter", DEFAULT_PRICE_FILTER)).strip()
    try:
        ml_unsuper_utils.set_price_filter(raw)
        logging.info("KNN price filter set to %r", raw)
    except Exception as exc:
        logging.warning("Invalid price filter %r - defaulting to 1e (%s)", raw, exc)
        ml_unsuper_utils.set_price_filter("1e")


def _apply_max_price_filter(cfg: dict) -> None:
    raw = str(cfg.get("price_mirror_max_filter", DEFAULT_MAX_PRICE_FILTER)).strip()
    try:
        ml_unsuper_utils.set_max_price_filter(raw)
        logging.info("KNN max price filter set to %r", raw)
    except Exception as exc:
        logging.warning("Invalid max price filter %r - defaulting to 100d (%s)", raw, exc)
        ml_unsuper_utils.set_max_price_filter("100d")


def _apply_knn_runtime_k(cfg: dict) -> None:
    raw = cfg.get("knn_filtered_k", config_manager.DEFAULT_CONFIG.get("knn_filtered_k", DEFAULT_KNN))
    try:
        ml_unsuper_utils.set_knn_runtime_k(raw)
        logging.info("KNN runtime k set to %r", raw)
    except Exception as exc:
        logging.warning("Invalid KNN runtime k %r; using default (%s)", raw, exc)
        ml_unsuper_utils.set_knn_runtime_k(DEFAULT_KNN)


def _show_viz_enabled(cfg: dict) -> bool:
    # XGB visualizations (distributions + feature importance) are always
    # computed now; the inference popup's "Show Model #1 diagnostics" toggle is
    # the sole control for whether they are displayed. The old show_viz_param
    # settings checkbox has been retired.
    return True


def _coerce_bool(raw, *, default: bool = False) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"1", "true", "yes", "y", "on"}:
            return True
        if value in {"0", "false", "no", "n", "off"}:
            return False
    return default


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


def _update_prediction_log_sold(timestamp: str, item_name: str, sold: str) -> bool:
    """Update the "sold" value of a single prediction log entry, identified
    by its timestamp + item name, leaving every other entry untouched."""
    with _prediction_log_lock:
        entries = _load_prediction_log_entries()
        updated = False
        for entry in entries:
            if entry.get("timestamp") == timestamp and entry.get("item_name") == item_name:
                entry["sold"] = sold
                updated = True
                break
        if updated:
            _write_prediction_log_entries(entries)
        return updated


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
        "release": __version__,
    }


def _append_prediction_log(entry: dict) -> None:
    if not entry:
        return
    _ensure_prediction_log_worker()
    try:
        _prediction_log_queue.put_nowait(entry)
    except Exception:
        logging.exception("Prediction log enqueue failed")


def _ensure_prediction_log_worker() -> None:
    global _prediction_log_worker_started
    if _prediction_log_worker_started:
        return
    with _prediction_log_worker_lock:
        if _prediction_log_worker_started:
            return
        threading.Thread(
            target=_prediction_log_worker,
            daemon=True,
            name="PredictionLogWriter",
        ).start()
        _prediction_log_worker_started = True


def _prediction_log_worker() -> None:
    while True:
        entry = _prediction_log_queue.get()
        try:
            with _prediction_log_lock:
                entries = _load_prediction_log_entries()
                entries.append(entry)
                _write_prediction_log_entries(entries)
        except Exception:
            logging.exception("Prediction log append failed")
        finally:
            _prediction_log_queue.task_done()


def _show_prediction_log_popup(*, refresh: bool = False) -> None:
    if root is None or not root.winfo_exists():
        return
    activated = _activate_workspace_view("history", "Prediction History", fresh=refresh)
    if activated is None:
        return
    win, created = activated
    if not created:
        return
    win.images = []

    with _prediction_log_lock:
        entries = _load_prediction_log_entries()
    if not entries:
        empty_header = ctk.CTkFrame(win, corner_radius=10, fg_color="#202A33")
        empty_header.pack(fill="x", padx=14, pady=(14, 8))
        ctk.CTkLabel(
            empty_header, text="Prediction History", font=_FONT_PAGE_TITLE
        ).pack(anchor="w", padx=12, pady=10)
        ctk.CTkLabel(
            win,
            text="No predictions have been recorded yet.",
            font=_FONT_BODY,
            justify="center",
        ).pack(expand=True)
        return

    container = ctk.CTkFrame(win)
    container.pack(fill="both", expand=True, padx=14, pady=14)
    container.rowconfigure(2, weight=1)
    container.columnconfigure(0, weight=1)

    # ---- Header: title + count + clear button --------------------------
    header = ctk.CTkFrame(container, corner_radius=10, fg_color="#202A33")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    header.columnconfigure(0, weight=1)

    title_box = ctk.CTkFrame(header, fg_color="transparent")
    title_box.grid(row=0, column=0, sticky="w", padx=12, pady=10)

    header_label = ctk.CTkLabel(
        title_box,
        text="Prediction History",
        font=_FONT_PAGE_TITLE,
    )
    header_label.grid(row=0, column=0, sticky="w")

    history_help_badge = ctk.CTkLabel(
        title_box,
        text="?",
        font=("Segoe UI", 10, "bold"),
        text_color="#0B0E11",
        fg_color="#6E7F8D",
        corner_radius=9,
        width=18,
        height=18,
    )
    history_help_badge.grid(row=0, column=1, sticky="w", padx=(8, 0))
    _HoverTip(
        history_help_badge,
        "Each Overlay / Filtered Overlay hotkey run is snapshotted here - the "
        "item text, both model estimates, and any active filters (Filtered "
        "Overlay only). Fill in what an item actually sold for to keep your own "
        "record for comparison and validation.",
        wraplength=340,
    )

    count_label = ctk.CTkLabel(
        title_box,
        text="",
        font=_FONT_BODY,
        text_color="#9AA7B4",
    )
    count_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

    wipe_btn = ctk.CTkButton(
        header,
        text="Clear History",
        command=lambda: _wipe_logs(),
        width=120,
        height=34,
        fg_color="#8A2D2D",
        hover_color="#A33636",
    )
    wipe_btn.grid(row=0, column=1, sticky="e", padx=(0, 8), pady=10)
    ctk.CTkButton(
        header,
        text="Refresh",
        command=lambda: _show_prediction_log_popup(refresh=True),
        width=84,
        height=34,
        fg_color="#33414E",
        hover_color="#3F5160",
    ).grid(row=0, column=2, sticky="e", padx=(0, 12), pady=10)

    # ---- Search / filter bar -------------------------------------------
    search_bar = ctk.CTkFrame(container, fg_color="transparent")
    search_bar.grid(row=1, column=0, sticky="ew", pady=(8, 12))
    search_bar.columnconfigure(1, weight=1)

    search_label = ctk.CTkLabel(
        search_bar,
        text="\U0001F50D",
        font=_FONT_SUBHEADING,
    )
    search_label.grid(row=0, column=0, sticky="w", padx=(2, 6))

    search_var = tk.StringVar()
    search_entry = ctk.CTkEntry(
        search_bar,
        textvariable=search_var,
        placeholder_text="Search by item name or mod text…",
        height=34,
    )
    search_entry.grid(row=0, column=1, sticky="ew")

    clear_search_btn = ctk.CTkButton(
        search_bar,
        text="Clear",
        command=lambda: search_var.set(""),
        width=72,
        height=34,
        fg_color="#33414E",
        hover_color="#3F5160",
    )
    clear_search_btn.grid(row=0, column=2, sticky="e", padx=(8, 0))

    content = ctk.CTkFrame(container, fg_color="transparent")
    content.grid(row=2, column=0, sticky="nsew")
    content.rowconfigure(0, weight=3)
    content.rowconfigure(1, weight=2)
    content.columnconfigure(0, weight=1)

    tree_frame = ctk.CTkFrame(content, corner_radius=12)
    tree_frame.grid(row=0, column=0, sticky="nsew")
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Prediction.Treeview",
        background="#202020",
        foreground="#F0F0F0",
        fieldbackground="#202020",
        bordercolor="#3A3A3A",
        borderwidth=0,
        rowheight=30,
        font=_FONT_TABLE,
    )
    style.configure(
        "Prediction.Treeview.Heading",
        background="#2E3A46",
        foreground="#FFFFFF",
        relief="flat",
        padding=(8, 6),
        font=_FONT_TABLE_BOLD,
    )
    style.map(
        "Prediction.Treeview.Heading",
        background=[("active", "#3A4A59")],
    )
    style.map(
        "Prediction.Treeview",
        background=[("selected", "#1F6AA5")],
        foreground=[("selected", "#FFFFFF")],
    )

    # "release" (app version at prediction time) is still persisted in each log
    # entry for later validation analysis, but it is not shown here: the
    # timestamp is the more intuitive staleness cue, and live currency rates
    # drift within a release anyway.
    columns = ("timestamp", "item_name", "sold", "xgb", "knn_mean", "knn_median", "filters_used")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12, style="Prediction.Treeview")
    tree.heading("timestamp", text="Timestamp")
    tree.heading("item_name", text="Item")
    tree.heading("sold", text="Sold")
    tree.heading("xgb", text="XGB")
    tree.heading("knn_mean", text="KNN Mean")
    tree.heading("knn_median", text="KNN Median")
    tree.heading("filters_used", text="Filters Used")

    tree.column("timestamp", width=130, anchor="w", stretch=False)
    tree.column("item_name", width=140, anchor="w", stretch=True)
    tree.column("sold", width=80, anchor="center", stretch=False)
    tree.column("xgb", width=70, anchor="center", stretch=False)
    tree.column("knn_mean", width=100, anchor="center", stretch=False)
    tree.column("knn_median", width=105, anchor="center", stretch=False)
    tree.column("filters_used", width=180, anchor="w", stretch=True)

    # Zebra striping for readability.
    tree.tag_configure("oddrow", background="#202020")
    tree.tag_configure("evenrow", background="#191919")

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
    vsb.grid(row=0, column=1, sticky="ns")

    detail_frame = ctk.CTkFrame(content, corner_radius=12)
    detail_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
    detail_frame.columnconfigure(0, weight=0, minsize=280)
    detail_frame.columnconfigure(1, weight=1)
    detail_frame.rowconfigure(1, weight=1)

    detail_title = ctk.CTkLabel(
        detail_frame,
        text="Selected Item",
        font=_FONT_BODY_BOLD,
        text_color="#9AA7B4",
    )
    detail_title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))
    ctk.CTkLabel(
        detail_frame,
        text="Full Item Text",
        font=_FONT_BODY_BOLD,
        text_color="#9AA7B4",
    ).grid(row=0, column=1, sticky="w", padx=14, pady=(12, 0))

    detail_header = ctk.CTkFrame(detail_frame, fg_color="transparent")
    detail_header.grid(row=1, column=0, sticky="new", padx=12, pady=(6, 0))
    detail_header.columnconfigure(0, weight=0)
    detail_header.columnconfigure(1, weight=1)

    detail_icon: Optional[ctk.CTkLabel] = None
    detail_item_label = ctk.CTkLabel(
        detail_header, text="", font=_FONT_SUBHEADING, wraplength=200, justify="left",
    )
    detail_item_label.grid(row=0, column=1, sticky="w", padx=(8, 0))

    detail_box = ctk.CTkTextbox(detail_frame, height=150, font=_FONT_MONO)
    detail_box.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(8, 12), pady=(6, 12))

    _detail_placeholder = "Select a prediction above to view its full item text."
    detail_box.insert("end", _detail_placeholder)

    sold_frame = ctk.CTkFrame(detail_frame, fg_color="transparent")
    sold_frame.grid(row=2, column=0, sticky="sew", padx=12, pady=(10, 12))
    sold_frame.columnconfigure(1, weight=1)

    sold_label = ctk.CTkLabel(sold_frame, text="Sold:", font=_FONT_BODY_BOLD)
    sold_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

    sold_var = tk.StringVar()
    sold_entry = ctk.CTkEntry(
        sold_frame,
        textvariable=sold_var,
        placeholder_text="Enter sold price…",
        height=32,
        state="disabled",
    )
    sold_entry.grid(row=0, column=1, sticky="ew")

    sold_save_btn = ctk.CTkButton(
        sold_frame,
        text="Save",
        width=80,
        height=32,
        state="disabled",
        command=lambda: _save_sold(),
    )
    sold_save_btn.grid(row=0, column=2, sticky="e", padx=(8, 0))

    def _sort_key(entry: dict) -> str:
        return str(entry.get("timestamp") or "")

    all_entries = sorted(entries, key=_sort_key, reverse=True)[:50]
    filtered_entries: list[dict] = list(all_entries)

    def _fmt(val: object) -> str:
        if isinstance(val, (int, float)):
            return f"{val:.0f}"
        return "" if val is None else str(val)

    def _update_count() -> None:
        total = len(all_entries)
        shown = len(filtered_entries)
        if not total:
            count_label.configure(text="No predictions recorded yet")
        elif shown == total:
            count_label.configure(text=f"{total} prediction{'s' if total != 1 else ''}")
        else:
            count_label.configure(text=f"Showing {shown} of {total} predictions")

    def _populate_tree() -> None:
        tree.delete(*tree.get_children())
        for idx, entry in enumerate(filtered_entries):
            filters_used = entry.get("filters_used") or _format_prediction_log_filters(entry.get("filters"))
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            tree.insert(
                "",
                "end",
                tags=(tag,),
                values=(
                    entry.get("timestamp", ""),
                    entry.get("item_name", ""),
                    entry.get("sold", "") or "",
                    _fmt(entry.get("xgb")),
                    _fmt(entry.get("knn_mean")),
                    _fmt(entry.get("knn_median")),
                    filters_used,
                ),
            )

    def _entry_haystack(entry: dict) -> str:
        return f"{entry.get('item_name', '')}\n{entry.get('item_text', '')}".lower()

    def _apply_filter(*_args) -> None:
        nonlocal filtered_entries
        needle = search_var.get().strip().lower()
        if needle:
            tokens = needle.split()
            filtered_entries = [
                e for e in all_entries if all(tok in _entry_haystack(e) for tok in tokens)
            ]
        else:
            filtered_entries = list(all_entries)
        _populate_tree()
        _update_count()

    def _wipe_logs() -> None:
        nonlocal all_entries, filtered_entries
        if not messagebox.askyesno("Prediction Log", "Clear all prediction history entries?"):
            return
        _write_prediction_log_entries([])
        all_entries = []
        filtered_entries = []
        _populate_tree()
        _update_count()
        detail_box.delete("1.0", "end")
        detail_box.insert("end", _detail_placeholder)
        detail_item_label.configure(text="")
        if detail_icon and detail_icon.winfo_exists():
            detail_icon.destroy()

    search_var.trace_add("write", _apply_filter)
    search_entry.bind("<Escape>", lambda _e: search_var.set(""))

    _populate_tree()
    _update_count()

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
            target_w=44,
            target_h=44,
            overlay_window=win,
        )
        if detail_icon:
            detail_icon.grid(row=0, column=0, sticky="w")
        detail_item_label.configure(text=item_name)

    selected_entry: dict | None = None

    def _on_select(_event=None) -> None:
        nonlocal selected_entry
        sel = tree.selection()
        if not sel:
            return
        idx = tree.index(sel[0])
        if idx < 0 or idx >= len(filtered_entries):
            return
        entry = filtered_entries[idx]
        selected_entry = entry
        detail_box.delete("1.0", "end")
        detail_box.insert("end", entry.get("item_text", ""))
        _update_detail_icon(entry.get("item_name"))
        sold_var.set(str(entry.get("sold", "") or ""))
        sold_entry.configure(state="normal")
        sold_save_btn.configure(state="normal")

    def _save_sold() -> None:
        if selected_entry is None:
            return
        value = sold_var.get().strip()
        timestamp = selected_entry.get("timestamp", "")
        item_name = selected_entry.get("item_name", "")
        if not _update_prediction_log_sold(timestamp, item_name, value):
            messagebox.showerror("Prediction Log", "Could not find this entry to update.")
            return
        selected_entry["sold"] = value
        sel = tree.selection()
        if sel:
            tree.set(sel[0], "sold", value)

    tree.bind("<<TreeviewSelect>>", _on_select)


# ------------- Stash scrape aggregate viewer -----------------

STASH_SUMMARY_FILENAME = "stash_scrape_summary.csv"
_STASH_RUN_DIR_RE = re.compile(r"^stash_scrape_(\d{8}_\d{6})(?:_\d+)?$")

# (column key, heading, anchor, width, stretch)
_STASH_SUMMARY_COLUMNS = (
    ("category", "Cat", "center", 68, False),
    ("segment", "Seg", "center", 58, False),
    ("item", "Item", "w", 145, False),
    ("item_copy", "\u29c9", "center", 24, False),
    ("regex", "Regex", "w", 180, False),
    ("regex_copy", "\u29c9", "center", 24, False),
    ("price", "Price", "center", 52, False),
    ("currency", "Cur", "center", 52, False),
    ("pred_xgb", "XGB", "center", 58, False),
    ("bucket_label", "Bucket", "center", 58, False),
    ("knn_median", "KNN Med", "center", 66, False),
    ("knn_mean", "KNN Mean", "center", 66, False),
    ("stash_name", "Stash", "w", 82, False),
    ("stash_x", "X", "center", 30, False),
    ("stash_y", "Y", "center", 30, False),
)
_STASH_NUMERIC_COLUMNS = {"price", "pred_xgb", "knn_median", "knn_mean", "stash_x", "stash_y"}
_STASH_PREDICTION_COLUMNS = ("pred_xgb", "knn_median", "knn_mean")


def _convert_stash_predictions(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    """Return a view-ready copy with prediction values in the selected currency.

    Stash scrape prediction columns are persisted as exalt equivalents.  Keep the
    saved dataframe unchanged and convert only the XGB/KNN prediction columns for
    display, so switching the selector is lossless.
    """
    out = df.copy()
    mode = _PRICE_DISPLAY_LABELS.get(str(currency).strip(), str(currency).strip().lower())
    if mode in {"d", "divines"}:
        mode = "divine"
    elif mode in {"c"}:
        mode = "chaos"
    if mode == "auto":
        # Pick per column set, from the largest prediction on screen: a mixed
        # table reads worse if each row uses a different unit.
        peak = 0.0
        for column in _STASH_PREDICTION_COLUMNS:
            if column in out.columns:
                values = pd.to_numeric(out[column], errors="coerce")
                if len(values):
                    top = float(values.abs().max(skipna=True) or 0.0)
                    peak = max(peak, top if np.isfinite(top) else 0.0)
        mode = "divine" if peak >= AUTO_DIVINE_THRESHOLD_EXALTS else "exalted"
    if mode not in {"divine", "chaos"}:
        return out
    try:
        factor = float(conversion.divine if mode == "divine" else conversion.chaos)
    except (TypeError, ValueError, OverflowError):
        return out
    if not np.isfinite(factor) or factor <= 0:
        return out
    for column in _STASH_PREDICTION_COLUMNS:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce") / factor
    return out


def _discover_stash_scrape_runs(save_dir: "str | os.PathLike[str] | None") -> list[dict]:
    """Find stash-scrape runs that produced an aggregate summary CSV.

    Returns dicts (newest first) with keys ``path`` (run folder), ``csv``
    (summary path), ``timestamp`` (datetime) and ``label`` (display string).
    Runs without a summary CSV (e.g. scrapes that yielded no scored rows) are
    skipped, so every entry is guaranteed to have an aggregate matrix to show.
    """
    runs: list[dict] = []
    if not save_dir:
        return runs
    root_dir = Path(save_dir).expanduser()
    try:
        if not root_dir.is_dir():
            return runs
        children = list(root_dir.iterdir())
    except OSError:
        return runs
    for child in children:
        try:
            if not child.is_dir():
                continue
            summary = child / STASH_SUMMARY_FILENAME
            if not summary.is_file():
                continue
        except OSError:
            continue
        match = _STASH_RUN_DIR_RE.match(child.name)
        stamp: Optional[datetime.datetime] = None
        if match:
            try:
                stamp = datetime.datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
            except ValueError:
                stamp = None
        if stamp is None:
            try:
                stamp = datetime.datetime.fromtimestamp(summary.stat().st_mtime)
            except OSError:
                stamp = datetime.datetime.min
        runs.append({
            "path": child,
            "csv": summary,
            "timestamp": stamp,
            "label": stamp.strftime("%Y-%m-%d %H:%M:%S"),
        })
    runs.sort(key=lambda r: r["timestamp"], reverse=True)
    return runs


def _load_summary_matrix(csv_path: "str | os.PathLike[str]") -> pd.DataFrame:
    """Load an aggregate stash-scrape summary CSV (written as utf-8-sig)."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = [scrape_stash_utils._fix_encoding(c).strip().lower() for c in df.columns]
    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].map(
            lambda value: value if pd.isna(value) else scrape_stash_utils._fix_encoding(value)
        )
    for key, *_rest in _STASH_SUMMARY_COLUMNS:
        if key not in df.columns:
            df[key] = ""
    return df


def _show_stash_scrape_viewer(preselect: "str | os.PathLike[str] | None" = None) -> None:
    """Show aggregate stash-scrape results in the unified application window."""
    global _stash_scrape_embedded_parent
    if root is None or not root.winfo_exists():
        return
    activated = _activate_workspace_view("stash", "StashScrape")
    if activated is None:
        return
    win, created = activated
    if not created:
        if preselect is not None:
            reload_runs = getattr(win, "_stash_reload_runs", None)
            if callable(reload_runs):
                reload_runs(preselect)
        return
    _stash_scrape_embedded_parent = win
    win.images = []

    # --- mutable view state (dicts so closures can mutate in place) ---------
    current_dir = {"path": str(state.config.get("stash_scrape_save_dir", "") or "").strip()}
    runs: list[dict] = []
    run_by_label: dict[str, dict] = {}
    full_df = {"df": pd.DataFrame()}
    filtered_df = {"df": pd.DataFrame()}
    sort_state: dict[str, object] = {"col": None, "reverse": False}
    prediction_currency = {"value": "Exalts"}

    container = ctk.CTkFrame(win)
    container.pack(fill="both", expand=True, padx=8, pady=8)
    container.rowconfigure(6, weight=1)
    container.columnconfigure(0, weight=1)

    # ---- Header --------------------------------------------------------
    header = ctk.CTkFrame(container, corner_radius=10, fg_color="#202A33")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    header.columnconfigure(0, weight=1)
    ctk.CTkLabel(header, text="View StashScrapes", font=_FONT_PAGE_TITLE).grid(
        row=0, column=0, sticky="w", padx=12, pady=(10, 0)
    )
    ctk.CTkButton(
        header,
        text="Run StashScrape",
        width=150,
        command=_open_stash_scrape_dialog,
    ).grid(row=0, column=1, rowspan=2, sticky="e", padx=12, pady=10)
    currency_bar = ctk.CTkFrame(container, fg_color="transparent")
    currency_bar.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 2))
    ctk.CTkLabel(currency_bar, text="Prediction currency:", font=_FONT_BODY).pack(side="left")
    currency_selector = ctk.CTkSegmentedButton(
        currency_bar,
        values=["Auto", "Exalts", "Divines", "Chaos"],
        variable=tk.StringVar(
            value=_PRICE_DISPLAY_VALUES.get(price_display_mode(), "Auto")
        ),
        command=lambda value: _set_prediction_currency(value),
    )
    currency_selector.pack(side="left", padx=(10, 0))
    ctk.CTkLabel(
        currency_bar,
        text="XGB and KNN predictions are converted for display; saved scrape data is unchanged.",
        text_color="#9AA7B4",
        font=_FONT_HELPER,
    ).pack(side="left", padx=(12, 0))

    # ---- Folder row (the source the runs are discovered in) -----------
    folder_row = ctk.CTkFrame(container, fg_color="transparent")
    folder_row.grid(row=3, column=0, sticky="ew", padx=4, pady=(4, 2))
    folder_row.columnconfigure(3, weight=1)
    ctk.CTkLabel(folder_row, text="Scrape folder", font=_FONT_BODY, width=92, anchor="w").grid(
        row=0, column=0, sticky="w", padx=(0, 8)
    )
    folder_entry = ctk.CTkEntry(folder_row, font=_FONT_MONO_SMALL, width=430)
    folder_entry.grid(row=0, column=1, sticky="w")
    folder_entry.configure(state="readonly")

    def _set_folder_entry(text: str) -> None:
        folder_entry.configure(state="normal")
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, text)
        folder_entry.configure(state="readonly")

    ctk.CTkButton(folder_row, text="Browse", width=90, command=lambda: _browse_dir()).grid(
        row=0, column=2, sticky="w", padx=(8, 0)
    )

    # ---- Run row (the aggregate doc selected within that folder) -------
    selector = ctk.CTkFrame(container, fg_color="transparent")
    selector.grid(row=4, column=0, sticky="ew", padx=4, pady=(2, 6))
    selector.columnconfigure(4, weight=1)
    ctk.CTkLabel(selector, text="Run", font=_FONT_BODY, width=92, anchor="w").grid(
        row=0, column=0, sticky="w", padx=(0, 8)
    )
    run_var = tk.StringVar(value="")
    run_menu = ctk.CTkOptionMenu(
        selector, variable=run_var, values=["(no runs)"], width=430,
        command=lambda _v: _on_run_selected()
    )
    run_menu.grid(row=0, column=1, sticky="w")
    ctk.CTkButton(selector, text="\u21bb Refresh", width=90, command=lambda: _reload_runs()).grid(
        row=0, column=2, sticky="w", padx=(8, 0)
    )
    ctk.CTkButton(selector, text="Open", width=90, command=lambda: _open_run_folder()).grid(
        row=0, column=3, sticky="w", padx=(8, 0)
    )

    # ---- Filter bar ----------------------------------------------------
    filter_bar = ctk.CTkFrame(container, fg_color="transparent")
    filter_bar.grid(row=5, column=0, sticky="ew", padx=6, pady=(2, 10))
    filter_bar.columnconfigure(1, weight=1)
    ctk.CTkLabel(filter_bar, text="\U0001F50D", font=_FONT_SUBHEADING).grid(
        row=0, column=0, sticky="w", padx=(2, 6)
    )
    search_var = tk.StringVar()
    search_entry = ctk.CTkEntry(
        filter_bar,
        textvariable=search_var,
        placeholder_text="Filter by item, category, segment, or stash\u2026",
        height=28,
    )
    search_entry.grid(row=0, column=1, sticky="ew")
    ctk.CTkLabel(filter_bar, text="Category:", font=_FONT_BODY).grid(
        row=0, column=2, sticky="e", padx=(12, 6)
    )
    category_var = tk.StringVar(value="All")
    category_menu = ctk.CTkOptionMenu(
        filter_bar, variable=category_var, values=["All"], width=150, command=lambda _v: _apply_filter()
    )
    category_menu.grid(row=0, column=3, sticky="e")
    ctk.CTkButton(
        filter_bar,
        text="Clear",
        width=72,
        fg_color="#33414E",
        hover_color="#3F5160",
        command=lambda: (search_var.set(""), category_var.set("All"), _apply_filter()),
    ).grid(row=0, column=4, sticky="e", padx=(8, 0))

    # ---- Matrix (Treeview) ---------------------------------------------
    tree_frame = ctk.CTkFrame(container, corner_radius=12)
    tree_frame.grid(row=6, column=0, sticky="nsew", padx=6)
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "StashMatrix.Treeview",
        background="#202020",
        foreground="#F0F0F0",
        fieldbackground="#202020",
        bordercolor="#3A3A3A",
        borderwidth=0,
        rowheight=23,
        font=("Segoe UI", 9),
    )
    style.configure(
        "StashMatrix.Treeview.Heading",
        background="#2E3A46",
        foreground="#FFFFFF",
        relief="flat",
        padding=(3, 3),
        font=("Segoe UI", 9, "bold"),
    )
    style.map("StashMatrix.Treeview.Heading", background=[("active", "#3A4A59")])
    style.map(
        "StashMatrix.Treeview",
        background=[("selected", "#1F6AA5")],
        foreground=[("selected", "#FFFFFF")],
    )

    columns = tuple(c[0] for c in _STASH_SUMMARY_COLUMNS)
    tree = ttk.Treeview(
        tree_frame, columns=columns, show="headings", height=16, style="StashMatrix.Treeview"
    )
    for key, title, anchor, width, stretch in _STASH_SUMMARY_COLUMNS:
        heading_command = (lambda: None) if key in {"item_copy", "regex_copy"} else (lambda c=key: _sort_by(c))
        tree.heading(key, text=title, command=heading_command)
        tree.column(key, width=width, anchor=anchor, stretch=stretch)
    tree.tag_configure("oddrow", background="#202020")
    tree.tag_configure("evenrow", background="#191919")

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscroll=vsb.set, xscroll=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    copy_columns = {
        f"#{columns.index('item_copy') + 1}": "item",
        f"#{columns.index('regex_copy') + 1}": "regex",
    }
    toast_state = {"after_id": None, "label": None}

    def _show_copy_toast() -> None:
        """Briefly confirm a successful clipboard action without a popup."""
        previous_after_id = toast_state["after_id"]
        if previous_after_id:
            try:
                win.after_cancel(previous_after_id)
            except tk.TclError:
                pass
        previous_label = toast_state["label"]
        if previous_label is not None:
            try:
                previous_label.destroy()
            except tk.TclError:
                pass

        toast = ctk.CTkLabel(
            win,
            text="Copied!",
            fg_color="#2D7D46",
            text_color="#FFFFFF",
            corner_radius=8,
            font=_FONT_BODY_BOLD,
        )
        toast.place(relx=1.0, x=-18, y=18, anchor="ne")
        toast_state["label"] = toast

        def _dismiss_toast() -> None:
            try:
                toast.destroy()
            except tk.TclError:
                pass
            toast_state["label"] = None
            toast_state["after_id"] = None

        toast_state["after_id"] = win.after(1400, _dismiss_toast)

    def _copy_from_row(event) -> None:
        """Copy the item or regex for the clicked row's copy cell."""
        if tree.identify_region(event.x, event.y) != "cell":
            return
        source_column = copy_columns.get(tree.identify_column(event.x))
        if source_column is None:
            return
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        values = tree.item(row_id, "values")
        source_index = columns.index(source_column)
        value = str(values[source_index]) if source_index < len(values) else ""
        try:
            win.clipboard_clear()
            win.clipboard_append(value)
            win.update()
            _show_copy_toast()
        except tk.TclError:
            pass

    tree.bind("<Button-1>", _copy_from_row, add="+")

    # ---- Behaviour -----------------------------------------------------
    def _fmt_cell(col: str, val: object) -> str:
        if val is None:
            return ""
        if isinstance(val, float) and pd.isna(val):
            return ""
        if col in _STASH_NUMERIC_COLUMNS:
            try:
                num = float(val)
            except (TypeError, ValueError):
                return str(val)
            if pd.isna(num):
                return ""
            if col in {"stash_x", "stash_y"}:
                return str(int(round(num)))
            if float(num).is_integer():
                return f"{int(num):,}"
            return f"{num:,.1f}"
        return str(val)

    def _set_prediction_currency(value: str) -> None:
        # Write through to the shared setting rather than keeping a private
        # copy, so this selector and the one in Settings cannot disagree.
        if value in _PRICE_DISPLAY_LABELS:
            _persist_price_display(value)
        prediction_currency["value"] = value if value in _PRICE_DISPLAY_LABELS else "Auto"
        _update_headings()
        if not full_df["df"].empty:
            _apply_filter()

    def _populate_tree() -> None:
        tree.delete(*tree.get_children())
        df = _convert_stash_predictions(filtered_df["df"], prediction_currency["value"])
        for idx, (_, row) in enumerate(df.iterrows()):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            values = tuple(
                "\u29c9" if col in {"item_copy", "regex_copy"} else _fmt_cell(col, row.get(col, ""))
                for col in columns
            )
            tree.insert("", "end", tags=(tag,), values=values)

    def _update_headings() -> None:
        # Carries both the sort arrow and the display currency: the prediction
        # columns are converted for display, so their unit has to be visible
        # or the numbers are ambiguous.
        suffix = {"exalted": "e", "divine": "d", "chaos": "c"}.get(
            price_display_mode(), "auto"
        )
        for key, title, *_rest in _STASH_SUMMARY_COLUMNS:
            arrow = ""
            if sort_state["col"] == key:
                arrow = " \u25bc" if sort_state["reverse"] else " \u25b2"
            label = f"{title} ({suffix})" if key in _STASH_PREDICTION_COLUMNS else title
            tree.heading(key, text=f"{label}{arrow}")

    def _apply_sort() -> None:
        col = sort_state["col"]
        if not col:
            return
        df = filtered_df["df"]
        if df.empty or col not in df.columns:
            return
        if col in _STASH_NUMERIC_COLUMNS:
            keys = pd.to_numeric(df[col], errors="coerce")
        else:
            keys = df[col].astype(str).str.lower()
        filtered_df["df"] = (
            df.assign(_sortkey=keys)
            .sort_values("_sortkey", ascending=not sort_state["reverse"], kind="stable", na_position="last")
            .drop(columns="_sortkey")
        )

    def _sort_by(col: str) -> None:
        if sort_state["col"] == col:
            sort_state["reverse"] = not sort_state["reverse"]
        else:
            sort_state["col"] = col
            sort_state["reverse"] = False
        _update_headings()
        _apply_sort()
        _populate_tree()

    def _row_haystack(row) -> str:
        return " ".join(str(row.get(c, "")) for c in ("item", "category", "segment", "stash_name")).lower()

    def _apply_filter(*_args) -> None:
        df = full_df["df"]
        if df.empty:
            filtered_df["df"] = df
            _populate_tree()
            return
        mask = pd.Series(True, index=df.index)
        cat = category_var.get()
        if cat and cat != "All":
            mask &= df["category"].astype(str) == cat
        needle = search_var.get().strip().lower()
        if needle:
            hay = df.apply(_row_haystack, axis=1)
            for tok in needle.split():
                mask &= hay.str.contains(re.escape(tok), regex=True)
        filtered_df["df"] = df[mask]
        _apply_sort()
        _populate_tree()

    def _load_selected_into_view(run: "dict | None") -> None:
        if not run:
            full_df["df"] = pd.DataFrame(columns=list(columns))
            filtered_df["df"] = full_df["df"]
            category_menu.configure(values=["All"])
            category_var.set("All")
            _populate_tree()
            return
        try:
            df = _load_summary_matrix(run["csv"])
        except Exception as exc:
            messagebox.showerror("Stash Scrape Viewer", f"Could not read summary:\n{exc}")
            return
        full_df["df"] = df
        cats = ["All"]
        try:
            cats += sorted({str(c) for c in df["category"].dropna().unique() if str(c).strip()})
        except Exception:
            pass
        category_menu.configure(values=cats)
        if category_var.get() not in cats:
            category_var.set("All")
        _apply_filter()

    def _on_run_selected() -> None:
        _load_selected_into_view(run_by_label.get(run_var.get()))

    def _open_path_in_explorer(target: str) -> None:
        if not target:
            return
        try:
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception:
            pass

    def _open_run_folder() -> None:
        run = run_by_label.get(run_var.get())
        _open_path_in_explorer(str(run["path"]) if run else current_dir["path"])

    def _reload_runs(preselect_path: "str | os.PathLike[str] | None" = None) -> None:
        nonlocal runs, run_by_label
        runs = _discover_stash_scrape_runs(current_dir["path"])
        run_by_label = {}
        labels: list[str] = []
        seen: dict[str, int] = {}
        for r in runs:
            label = r["label"]
            if label in seen:
                seen[label] += 1
                label = f"{label} (#{seen[label]})"
            else:
                seen[label] = 1
            r["display"] = label
            run_by_label[label] = r
            labels.append(label)
        _set_folder_entry(current_dir["path"] or "(no folder configured)")
        if not labels:
            run_menu.configure(values=["(no runs)"])
            run_var.set("(no runs)")
            _load_selected_into_view(None)
            return
        run_menu.configure(values=labels)
        chosen = labels[0]
        if preselect_path:
            try:
                target = Path(preselect_path).expanduser().resolve()
            except OSError:
                target = None
            if target is not None:
                for r in runs:
                    try:
                        if r["path"].resolve() == target:
                            chosen = r["display"]
                            break
                    except OSError:
                        continue
        run_var.set(chosen)
        _on_run_selected()

    def _browse_dir() -> None:
        chosen = filedialog.askdirectory(parent=win, initialdir=current_dir["path"] or None)
        if not chosen:
            return
        current_dir["path"] = chosen
        _reload_runs()

    search_var.trace_add("write", _apply_filter)
    search_entry.bind("<Escape>", lambda _e: search_var.set(""))

    _set_prediction_currency(_PRICE_DISPLAY_VALUES.get(price_display_mode(), "Auto"))
    win._stash_reload_runs = _reload_runs
    _reload_runs(preselect_path=preselect)


# ------------- tiny UI helpers ----------------------------
def _textbox(parent, lines, yellow, colours, row, col, height: int | None = None,
             filter_tags: dict[int, str] | None = None, columnspan: int = 1):
    return helper_textbox(
        parent,
        lines,
        yellow,
        colours,
        row,
        col,
        height=height,
        filter_tags=filter_tags,
        columnspan=columnspan,
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


def _destroy_overlay(*, invalidate_request: bool = True):
    global overlay, _overlay_backdrop, _overlay_loading, _overlay_loading_window, _overlay_loading_cover, _prediction_loader_windows, _prediction_request_id, _active_prediction_release_lock, _active_dashboard_process
    global _overlay_monitor_rect
    cancelled_request_id = _prediction_request_id
    if invalidate_request:
        _prediction_request_id += 1
        _prediction_request_texts.pop(cancelled_request_id, None)
    active_lock, _active_prediction_release_lock = _active_prediction_release_lock, None
    if active_lock is not None:
        try:
            active_lock.release()
        except RuntimeError:
            pass
    worker_process = _active_dashboard_process
    if worker_process is not None and worker_process.is_alive():
        try:
            worker_process.terminate()
            worker_process.join(timeout=0.25)
        except Exception:
            logging.debug("Could not cancel dashboard worker", exc_info=True)
    if _prediction_worker_manager is not None:
        try:
            if _prediction_worker_manager.cancel(cancelled_request_id):
                # Cancelling recycles the worker process, which takes its model
                # caches with it. Warm a replacement so the next hotkey is not
                # a cold start again -- scheduled rather than inline, because
                # dismissing an overlay has to stay instant.
                _schedule_prediction_worker_rewarm()
        except Exception:
            logging.debug("Could not cancel resident dashboard worker", exc_info=True)
    _close_prediction_popup()
    _overlay_monitor_rect = None
    try:
        if _overlay_backdrop and _overlay_backdrop.winfo_exists():
            _overlay_backdrop.destroy()
    except tk.TclError:
        pass
    _overlay_backdrop = None
    windows = (overlay, state.overlay, _overlay_loading_window, *_prediction_loader_windows)
    destroyed: set[int] = set()
    for window in windows:
        try:
            if window is not None and id(window) not in destroyed and window.winfo_exists():
                window.destroy()
                destroyed.add(id(window))
        except tk.TclError:
            pass
    state.reset_overlay()
    overlay = None
    _overlay_loading = False
    _overlay_loading_window = None
    _overlay_loading_cover = None
    _prediction_loader_windows = []
    try:
        if root and root.winfo_exists():
            root.configure(cursor="")
    except tk.TclError:
        pass


def _close_prediction_popup(*, stop_process: bool = False) -> None:
    """Hide the presenter now, or fully stop it only when explicitly asked."""
    global _prediction_popup_process, _prediction_popup_queue, _prediction_popup_request_id, _popup_event_queue, _prediction_popup_shutdown_event, _prediction_popup_prewarmed
    try:
        if root and root.winfo_exists():
            root.configure(cursor="")
    except tk.TclError:
        pass
    # Dismissing a prediction must never depend on bookkeeping that says
    # whether this process is "prewarmed".  If it is alive, hide it and leave
    # teardown for application exit; otherwise a stale flag takes the slow
    # shutdown path and makes click-out wait for its timeout.
    if (not stop_process and _prediction_popup_process is not None
            and _prediction_popup_process.is_alive() and _prediction_popup_queue is not None):
        try:
            _prediction_popup_queue.put(("hide", None))
        except Exception:
            pass
        _prediction_popup_request_id = None
        return
    process, command_queue = _prediction_popup_process, _prediction_popup_queue
    _prediction_popup_process = None
    _prediction_popup_queue = None
    _prediction_popup_request_id = None
    event_queue = _popup_event_queue
    _popup_event_queue = None
    shutdown_event = _prediction_popup_shutdown_event
    _prediction_popup_shutdown_event = None
    _destroy_prediction_launch_dimmer()
    if process is None:
        return
    try:
        if shutdown_event is not None:
            shutdown_event.set()
        logging.info("Prediction presenter shutdown requested (pid=%s)", process.pid)
        if process.is_alive() and command_queue is not None:
            command_queue.put(("close", None))

        # The child owns a Tk interpreter and is the producer for the event
        # queue.  Wait for its post-Tk ``stopped`` acknowledgement instead of
        # terminating it while a Tcl callback or Queue feeder thread is live.
        deadline = time.monotonic() + 1.5
        stopped = False
        while process.is_alive() and time.monotonic() < deadline:
            if event_queue is not None:
                try:
                    event, _value = _popup_event_get_nowait(event_queue)
                    stopped = stopped or event == "stopped"
                    if event in {"shutdown_started", "stopped"}:
                        logging.info("Prediction presenter lifecycle event: %s", event)
                except queue.Empty:
                    pass
                except Exception:
                    pass
            process.join(timeout=0.02 if not stopped else 0.10)

        if process.is_alive():
            # Never terminate a live Tk interpreter. On CPython 3.13 that
            # produces PyEval_RestoreThread fatal errors. This process is
            # deliberately non-daemon, so Python will finish waiting for its
            # clean exit during application shutdown rather than killing it.
            logging.error("Prediction presenter did not acknowledge shutdown within 1.5s (pid=%s)", process.pid)
    except Exception:
        logging.debug("Could not close prediction popup process", exc_info=True)
    finally:
        # If the child missed the acknowledgement deadline, leave its queue
        # handles intact. Closing the receiver while its Tk process can still
        # write is another shutdown race; the non-daemon child will instead
        # complete its own normal exit as Python finalizes.
        if process.is_alive():
            return
        try:
            if command_queue is not None:
                command_queue.close()
                command_queue.join_thread()
        except Exception:
            pass
        try:
            if event_queue is not None:
                event_queue.close()
        except Exception:
            pass


def _terminate_prediction_popup() -> None:
    """Fully stop a warm presenter before switching to another popup type."""
    global _prediction_popup_prewarmed
    _prediction_popup_prewarmed = False
    _close_prediction_popup(stop_process=True)


def _prewarm_prediction_popup() -> None:
    """Start the lightweight presenter process before the first hotkey."""
    global _prediction_popup_process, _prediction_popup_queue, _prediction_popup_request_id
    global _popup_event_queue, _prediction_popup_shutdown_event, _prediction_popup_prewarmed
    if _prediction_popup_process is not None and _prediction_popup_process.is_alive():
        return
    try:
        from poe2trade.app.prediction_popup import run_prediction_popup
        ctx = multiprocessing.get_context("spawn")
        command_queue, event_queue = ctx.Queue(), ctx.SimpleQueue()
        shutdown_event = ctx.Event()
        process = ctx.Process(
            target=run_prediction_popup,
            args=(command_queue, event_queue, 0, None, True, shutdown_event),
            name="StashSagePredictionPresenter",
            daemon=False,
        )
        process.start()
        _prediction_popup_process = process
        _prediction_popup_queue = command_queue
        _prediction_popup_request_id = None
        _popup_event_queue = event_queue
        _prediction_popup_shutdown_event = shutdown_event
        _prediction_popup_prewarmed = True
    except Exception:
        logging.debug("Could not prewarm prediction presenter", exc_info=True)


def _destroy_prediction_launch_dimmer() -> None:
    """Remove the main-process dimmer used while the DPI presenter starts."""
    global _prediction_launch_dimmer
    dimmer, _prediction_launch_dimmer = _prediction_launch_dimmer, None
    try:
        if dimmer is not None and dimmer.winfo_exists():
            dimmer.destroy()
    except tk.TclError:
        pass


def _show_prediction_launch_dimmer() -> None:
    """Give instant feedback while the isolated DPI-aware presenter imports."""
    global _prediction_launch_dimmer
    _destroy_prediction_launch_dimmer()
    if not (root and root.winfo_exists()):
        return
    dimmer = tk.Toplevel(root)
    dimmer.overrideredirect(True)
    dimmer.configure(background="#000000")
    dimmer.attributes("-alpha", 0.0)
    dimmer.attributes("-topmost", True)
    mon_x, mon_y, mon_w, mon_h = _overlay_anchor_rect(root)
    dimmer.geometry(f"{mon_w}x{mon_h}+{mon_x}+{mon_y}")
    dimmer.lift()
    _prediction_launch_dimmer = dimmer

    def fade(alpha: float = 0.0) -> None:
        try:
            if _prediction_launch_dimmer is not dimmer or not dimmer.winfo_exists():
                return
            next_alpha = min(0.48, alpha + 0.08)
            dimmer.attributes("-alpha", next_alpha)
            if next_alpha < 0.48:
                dimmer.after(20, lambda: fade(next_alpha))
        except tk.TclError:
            pass

    dimmer.update_idletasks()
    fade()


def _launch_prediction_popup(request_id: int) -> bool:
    """Start the DPI-aware presenter process and show its immediate loader."""
    global _prediction_popup_process, _prediction_popup_queue, _prediction_popup_request_id, _popup_event_queue, _prediction_popup_shutdown_event, _prediction_popup_prewarmed
    try:
        from poe2trade.app.prediction_popup import run_prediction_popup

        monitor_rect = _overlay_anchor_rect(root)

        def poll_presenter_events() -> None:
            # A warm process is shared by prediction, Ctrl+2, and craft UI.
            # Once another popup type takes over, this older poller must stop
            # consuming events from the shared queue.
            if process is not _prediction_popup_process or _prediction_popup_request_id != request_id:
                return
            try:
                event, value = _popup_event_get_nowait(event_queue)
            except queue.Empty:
                if process.is_alive() and root and root.winfo_exists():
                    root.after(40, poll_presenter_events)
                return
            except Exception:
                logging.debug("Prediction presenter event read failed", exc_info=True)
                return
            if event == "presenter_lifecycle":
                _log_presenter_lifecycle(value)
            elif event == "presenter_closed" and value == request_id:
                logging.info("Presenter telemetry: stage=prediction_closed request=%s", request_id)
                # Escape/backdrop close happens in the child process. Invalidate
                # the worker token here so a late model result cannot recreate a
                # prediction popup after the user already dismissed it.
                global _prediction_request_id
                _prediction_request_id += 1
                _close_prediction_popup()
                return
            if process.is_alive() and root and root.winfo_exists():
                root.after(40, poll_presenter_events)

        if (_prediction_popup_prewarmed and _prediction_popup_process is not None
                and _prediction_popup_process.is_alive() and _prediction_popup_queue is not None):
            process = _prediction_popup_process
            event_queue = _popup_event_queue
            if event_queue is None:
                return False
            _prediction_popup_request_id = request_id
            _prediction_popup_queue.put(("show", {"request_id": request_id, "monitor_rect": monitor_rect}))
            root.after(40, poll_presenter_events)
            return True

        ctx = multiprocessing.get_context("spawn")
        command_queue = ctx.Queue()
        # The child produces these UI events.  A SimpleQueue writes directly
        # to its pipe, avoiding the background feeder thread that crashes
        # Python 3.13 when a CustomTkinter child interpreter exits.
        event_queue = ctx.SimpleQueue()
        shutdown_event = ctx.Event()
        process = ctx.Process(
            target=run_prediction_popup,
            args=(command_queue, event_queue, request_id, monitor_rect, True, shutdown_event),
            name="StashSagePredictionPopup",
            daemon=False,
        )
        process.start()
        _prediction_popup_process = process
        _prediction_popup_queue = command_queue
        _prediction_popup_request_id = request_id
        _popup_event_queue = event_queue
        _prediction_popup_shutdown_event = shutdown_event
        _prediction_popup_prewarmed = True
        command_queue.put(("show", {"request_id": request_id, "monitor_rect": monitor_rect}))

        root.after(40, poll_presenter_events)

        return True
    except Exception:
        logging.exception("Could not start isolated prediction popup")
        _prediction_popup_process = None
        _prediction_popup_queue = None
        _prediction_popup_request_id = None
        _popup_event_queue = None
        _prediction_popup_shutdown_event = None
        _destroy_prediction_launch_dimmer()
        return False


def _launch_filtered_filter_popup(
    ctx: dict,
    *,
    release_lock: threading.Lock | None = None,
) -> bool:
    """Show Ctrl+2's editor in the warm presenter process."""
    global _prediction_popup_process, _prediction_popup_queue, _prediction_popup_request_id, _popup_event_queue, _prediction_popup_prewarmed
    released = False

    def release_once() -> None:
        nonlocal released
        if released or release_lock is None:
            return
        released = True
        try:
            release_lock.release()
        except RuntimeError:
            pass

    try:
        if not (_prediction_popup_prewarmed and _prediction_popup_process is not None
                and _prediction_popup_process.is_alive() and _prediction_popup_queue is not None):
            _prewarm_prediction_popup()
        process, command_queue, event_queue = _prediction_popup_process, _prediction_popup_queue, _popup_event_queue
        if process is None or not process.is_alive() or command_queue is None or event_queue is None:
            return False
        _prediction_popup_prewarmed = True
        # Disable any prediction poller left from the previous use of the warm
        # process; otherwise it can steal filtered_apply from this editor.
        _prediction_popup_request_id = None
        rows = _build_filter_rows(ctx.get("base_X"), ctx.get("category"))
        if not rows:
            rows = _build_filter_rows_from_parsed(ctx.get("parsed") or {}, ctx.get("category"))
        item_key = str(ctx.get("item_name") or "").strip().lower()
        icon_map = _prepare_comparison_icon_pngs([str(ctx.get("icon_name") or ctx.get("item_name") or "")], size=48)
        icon_name = str(ctx.get("icon_name") or ctx.get("item_name") or "")
        command_queue.put(("filtered_show", {
            "rows": rows,
            "item_name": ctx.get("item_name"),
            "icon_png": icon_map.get(icon_name),
            "snapshot": _FILTER_ENTRY_MEMORY.get(item_key, []),
            "monitor_rect": _overlay_anchor_rect(root),
        }))
        logging.info("Presenter telemetry: stage=ctrl2_filter_requested route=presenter")
        handoff_started = False

        def poll_events() -> None:
            nonlocal handoff_started
            if handoff_started:
                return
            if process is not _prediction_popup_process or not process.is_alive():
                release_once()
                return
            try:
                event, value = _popup_event_get_nowait(event_queue)
            except queue.Empty:
                if process.is_alive() and root and root.winfo_exists():
                    root.after(40, poll_events)
                return
            except Exception:
                logging.exception("Filtered popup event read failed")
                release_once()
                return
            if event == "presenter_lifecycle":
                _log_presenter_lifecycle(value)
                if process.is_alive() and root and root.winfo_exists():
                    root.after(40, poll_events)
                return
            elif event == "filtered_apply" and isinstance(value, dict):
                logging.info("Presenter telemetry: stage=ctrl2_filter_applied")
                handoff_started = True
                snapshot = value.get("snapshot")
                if isinstance(snapshot, list) and item_key:
                    _FILTER_ENTRY_MEMORY[item_key] = [str(item or "") for item in snapshot]
                release_once()
                _start_filtered_overlay_with_filters(ctx, value.get("filters") or {})
            elif event == "filtered_cancel":
                logging.info("Presenter telemetry: stage=ctrl2_filter_cancelled")
                handoff_started = True
                _close_prediction_popup()
                release_once()
            elif event == "error":
                _close_prediction_popup()
                release_once()
                messagebox.showerror("StashSage", str(value))
            else:
                # The warm process may still have its startup acknowledgement
                # queued when Ctrl+2 opens. Do not let that unrelated event
                # terminate the filter poller before Apply is pressed.
                if process.is_alive() and root and root.winfo_exists():
                    root.after(40, poll_events)

        root.after(40, poll_events)
        return True
    except Exception:
        logging.exception("Could not start isolated filtered popup")
        return False


def _launch_craft_potential_popup(text: str, release_lock: threading.Lock) -> bool:
    """Show Craft Potential UI in the warm presenter; calculate here."""
    global _prediction_popup_process, _prediction_popup_queue, _prediction_popup_request_id, _popup_event_queue, _prediction_popup_prewarmed, _craft_popup_session_id
    try:
        if not (_prediction_popup_prewarmed and _prediction_popup_process is not None
                and _prediction_popup_process.is_alive() and _prediction_popup_queue is not None):
            _prewarm_prediction_popup()
        if not (_prediction_popup_process is not None and _prediction_popup_process.is_alive()):
            return False
        _prediction_popup_prewarmed = True
        _prediction_popup_request_id = None
        session_id = time.monotonic_ns()
        _craft_popup_session_id = session_id
        _prediction_popup_queue.put(("craft_show", {
            "text": text,
            "monitor_rect": _overlay_anchor_rect(root),
            "session_id": session_id,
        }))

        def release_once() -> None:
            try:
                release_lock.release()
            except RuntimeError:
                pass

        def start_calculation() -> None:
            def report(done: int, total: int) -> None:
                try:
                    if _prediction_popup_queue is not None:
                        _prediction_popup_queue.put(("craft_progress", {"session_id": session_id, "done": done, "total": total}))
                except Exception:
                    pass

            def work() -> None:
                try:
                    result = craft_potential.analyze(text, progress=report)
                    icon_map = _prepare_comparison_icon_pngs([result.item_name], size=52)
                    payload = {
                        "session_id": session_id,
                        "item_name": result.item_name,
                        "icon_png": icon_map.get(result.item_name),
                        "baseline_prediction": result.baseline_prediction,
                        "explicit_count": result.explicit_count,
                        "rows": [
                            {
                                "pattern": row.pattern,
                                "maximum_roll": row.maximum_roll,
                                "effective_roll": row.effective_roll,
                                "affix_sides": row.affix_sides,
                                "winning_tier": row.winning_tier,
                                "required_level": row.required_level,
                                "observations": row.observations,
                                "tier_observations": row.tier_observations,
                                "affix_names": row.affix_names,
                                "prediction": row.prediction,
                                "delta": row.delta,
                                "delta_percent": row.delta_percent,
                            }
                            for row in result.rows
                        ],
                    }
                    if _prediction_popup_queue is not None:
                        _prediction_popup_queue.put(("craft_result", payload))
                except craft_potential.CraftPotentialError as exc:
                    if _prediction_popup_queue is not None:
                        _prediction_popup_queue.put(("craft_error", {"session_id": session_id, "message": str(exc)}))
                except Exception as exc:
                    logging.exception("Craft Potential failed")
                    if _prediction_popup_queue is not None:
                        _prediction_popup_queue.put(("craft_error", {"session_id": session_id, "message": f"Analysis failed:\n{exc}"}))
                finally:
                    release_once()

            threading.Thread(target=work, daemon=True).start()

        def poll_events() -> None:
            global _craft_popup_session_id
            if _craft_popup_session_id != session_id:
                return
            if _prediction_popup_process is None or not _prediction_popup_process.is_alive():
                release_once()
                return
            try:
                event, value = _popup_event_get_nowait(_popup_event_queue)
            except queue.Empty:
                root.after(30, poll_events)
                return
            if event == "presenter_lifecycle":
                _log_presenter_lifecycle(value)
                root.after(30, poll_events)
            elif event == "craft_start" and isinstance(value, Mapping) and value.get("session_id") == session_id:
                logging.info("Presenter telemetry: stage=ctrl4_craft_started")
                _prediction_popup_queue.put(("craft_progress", {"session_id": session_id, "done": None, "total": None}))
                start_calculation()
            elif event == "craft_cancel" and isinstance(value, Mapping) and value.get("session_id") == session_id:
                logging.info("Presenter telemetry: stage=ctrl4_craft_cancelled")
                _craft_popup_session_id = None
                release_once()
                _close_prediction_popup()
            else:
                root.after(30, poll_events)
                return

        root.after(30, poll_events)
        return True
    except Exception:
        logging.exception("Could not start isolated Craft Potential popup")
        return False


def _send_prediction_popup_result(payload: Mapping[str, Any], request_id: int) -> bool:
    """Deliver one complete dashboard contract to its isolated presenter."""
    process, command_queue = _prediction_popup_process, _prediction_popup_queue
    if (
        request_id != _prediction_popup_request_id
        or process is None
        or not process.is_alive()
        or command_queue is None
    ):
        return False
    try:
        command_queue.put(("result", dict(payload)))
        return True
    except Exception:
        logging.exception("Could not send prediction payload to popup")
        return False


def _enable_overlay_escape(window) -> None:
    """Give a price-result overlay keyboard focus and an Escape close path."""
    def _close_on_escape(_event=None):
        _destroy_overlay()
        return "break"

    window.bind("<Escape>", _close_on_escape)

    def _focus_window() -> None:
        try:
            if window.winfo_exists():
                window.lift()
                window.focus_force()
                if sys.platform == "win32":
                    try:
                        from ctypes import windll
                        hwnd = int(window.winfo_id())
                        windll.user32.BringWindowToTop(hwnd)
                        windll.user32.SetForegroundWindow(hwnd)
                        windll.user32.SetActiveWindow(hwnd)
                    except (ImportError, AttributeError, OSError, TypeError, ValueError):
                        pass
        except tk.TclError:
            pass

    for delay in (0, 40, 120, 250, 500):
        window.after(delay, _focus_window)


def _select_poe_window_rect(
    candidates: list[tuple[int, tuple[int, int, int, int], str]], foreground_hwnd: int,
) -> tuple[int, int, int, int] | None:
    """Choose the active PoE client when Windows exposes duplicate titles.

    PoE can leave a second visible, desktop-sized titled surface behind the
    active game client.  EnumWindows ordering is not a reliable way to choose
    between those two surfaces; hotkeys are invoked while the game is the
    foreground window, so that HWND is the authoritative candidate.
    """
    for hwnd, rect, _title in candidates:
        if hwnd == foreground_hwnd:
            return rect
    return candidates[0][1] if candidates else None


def _poe_window_rect() -> tuple[int, int, int, int] | None:
    """Return (left, top, width, height) of the Path of Exile game window.

    Enumerates visible top-level windows and matches the PoE title, so the
    overlay can be placed over the game itself rather than a monitor guess.
    Returns None when the game window is not found.  The main process
    deliberately runs DPI-unaware, while the presenter is per-monitor aware,
    so ``GetWindowRect`` can be DPI-virtualized here.  Convert both corners to
    native screen pixels before passing the rectangle to the presenter.
    Windows-only; returns None elsewhere (e.g. Linux).
    """
    if not sys.platform.startswith("win"):
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        candidates: list[tuple[int, tuple[int, int, int, int], str]] = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def _enum(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if not length:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if "path of exile" in (buffer.value or "").lower():
                rect = wintypes.RECT()
                # GetWindowRect virtualizes results for this (DPI-unaware)
                # caller. Switch only this native query to per-monitor-aware
                # mode; restoring immediately leaves the main Tk thread and
                # all of its windows in their existing DPI policy.
                set_context = getattr(user32, "SetThreadDpiAwarenessContext", None)
                previous_context = None
                used_native_context = False
                if set_context is not None:
                    try:
                        set_context.argtypes = [ctypes.c_void_p]
                        set_context.restype = ctypes.c_void_p
                        previous_context = set_context(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
                        used_native_context = bool(previous_context)
                    except (AttributeError, OSError, TypeError, ValueError):
                        previous_context = None
                try:
                    got_rect = user32.GetWindowRect(hwnd, ctypes.byref(rect))
                finally:
                    if previous_context:
                        try:
                            set_context(previous_context)
                        except (AttributeError, OSError, TypeError, ValueError):
                            pass
                if got_rect:
                    # Older Windows lacks the thread DPI API. In that case,
                    # use the target window's per-monitor point conversion as
                    # a best-effort fallback.
                    if not used_native_context:
                        top_left = wintypes.POINT(rect.left, rect.top)
                        bottom_right = wintypes.POINT(rect.right, rect.bottom)
                        convert_point = getattr(user32, "LogicalToPhysicalPointForPerMonitorDPI", None)
                        if convert_point is not None:
                            try:
                                converted = (
                                    convert_point(hwnd, ctypes.byref(top_left))
                                    and convert_point(hwnd, ctypes.byref(bottom_right))
                                )
                            except OSError:
                                converted = False
                            if converted:
                                rect.left, rect.top = top_left.x, top_left.y
                                rect.right, rect.bottom = bottom_right.x, bottom_right.y
                    width, height = rect.right - rect.left, rect.bottom - rect.top
                    if width > 0 and height > 0:
                        native_rect = (int(rect.left), int(rect.top), int(width), int(height))
                        candidates.append((int(hwnd), native_rect, buffer.value))
            return True

        user32.EnumWindows(_enum, 0)
        foreground = int(user32.GetForegroundWindow() or 0)
        selected = _select_poe_window_rect(candidates, foreground)
        if selected is not None:
            logging.info(
                "PoE window candidates=%s foreground=%s selected=%s",
                [(hwnd, rect, title) for hwnd, rect, title in candidates],
                foreground,
                selected,
            )
        return selected
    except Exception:
        logging.debug("PoE window lookup failed", exc_info=True)
        return None


def _cursor_monitor_rect(window) -> tuple[int, int, int, int]:
    """Return (left, top, width, height) of the monitor under the mouse cursor.

    Fallback anchor when the PoE window can't be found. The process is
    per-monitor DPI-aware, so Win32 and Tk share one physical-pixel coordinate
    space. Falls back to the Tk screen dimensions (also on non-Windows systems).
    """
    if not sys.platform.startswith("win"):
        return 0, 0, int(window.winfo_screenwidth()), int(window.winfo_screenheight())
    try:
        import ctypes
        from ctypes import wintypes

        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        monitor = ctypes.windll.user32.MonitorFromPoint(point, 2)  # NEAREST

        class _MonitorInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(_MonitorInfo)
        if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            rect = info.rcMonitor
            width, height = rect.right - rect.left, rect.bottom - rect.top
            if width > 0 and height > 0:
                return int(rect.left), int(rect.top), int(width), int(height)
    except Exception:
        logging.debug("cursor monitor lookup failed", exc_info=True)
    return 0, 0, int(window.winfo_screenwidth()), int(window.winfo_screenheight())


def _overlay_anchor_rect(window) -> tuple[int, int, int, int]:
    """Rect the overlay should sit over: the PoE window, else the cursor screen."""
    return _poe_window_rect() or _cursor_monitor_rect(window)


def _active_overlay_monitor_rect(window) -> tuple[int, int, int, int]:
    """Overlay anchor rect: the pinned one, else a live PoE-window/cursor lookup."""
    if _overlay_monitor_rect is not None:
        return _overlay_monitor_rect
    return _overlay_anchor_rect(window)


def _prediction_overlay_geometry(window) -> str:
    """Return a result geometry centred over the game monitor.

    Centres on the monitor the price check was launched from (the cursor's
    screen, i.e. POE2), not the StashSage main window or the primary monitor,
    so the result lands over the game on multi-monitor / mixed-DPI setups.
    """
    mon_x, mon_y, mon_w, mon_h = _active_overlay_monitor_rect(window)
    width = min(int(mon_w * 0.80), 1600)
    height = min(int(mon_h * 0.88), 1000)
    x = mon_x + (mon_w - width) // 2
    y = mon_y + (mon_h - height) // 2
    geometry = f"{width}x{height}+{x}+{y}"
    logging.debug("overlay geometry %s from anchor (%d,%d,%d,%d)", geometry, mon_x, mon_y, mon_w, mon_h)
    return geometry


def _fit_overlay_over_backdrop(window) -> None:
    """Size a CTk overlay window to the backdrop and centre it by measurement.

    The backdrop (plain Tk) always covers the game screen in physical pixels.
    The result window is a CustomTkinter toplevel whose geometry width/height is
    multiplied by the monitor's DPI scaling. So we compute the desired physical
    size from the backdrop, pre-divide it by the window's scaling factor so it
    renders at that physical size, then measure the realized rectangle and
    centre it inside the backdrop with a position-only geometry (not rescaled).
    """
    try:
        backdrop = _overlay_backdrop
        if not (backdrop is not None and backdrop.winfo_exists() and window.winfo_exists()):
            return
        backdrop.update_idletasks()
        bx, by = int(backdrop.winfo_rootx()), int(backdrop.winfo_rooty())
        bw, bh = int(backdrop.winfo_width()), int(backdrop.winfo_height())
        if bw <= 1 or bh <= 1:
            return
        target_w = min(int(bw * 0.80), 1600)
        target_h = min(int(bh * 0.88), 1000)
        try:
            scale = float(window._get_window_scaling())
        except Exception:
            scale = 1.0
        if scale <= 0:
            scale = 1.0
        # CTk multiplies the requested width/height by `scale`; pre-divide so the
        # rendered (physical) size matches the target.
        req_w = max(1, round(target_w / scale))
        req_h = max(1, round(target_h / scale))
        window.geometry(f"{req_w}x{req_h}")
        window.update()  # realize the size so winfo_* reflects the true rect
        actual_w = int(window.winfo_width())
        actual_h = int(window.winfo_height())
        if actual_w <= 1 or actual_h <= 1:
            actual_w, actual_h = target_w, target_h
        x = bx + (bw - actual_w) // 2
        y = by + (bh - actual_h) // 2
        window.geometry(f"+{x}+{y}")
        message = (
            f"overlay fit: backdrop={bw}x{bh}+{bx}+{by} target={target_w}x{target_h} "
            f"scale={scale:.3f} req={req_w}x{req_h} actual={actual_w}x{actual_h} -> pos +{x}+{y}"
        )
        logging.info(message)
        # Also append to a fixed file so the line is visible even from the
        # packaged (--noconsole) build where stdout is hidden. Diagnostic only.
        try:
            log_path = Path(tempfile.gettempdir()) / "stashsage_overlay_fit.log"
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {message}\n")
        except Exception:
            logging.debug("overlay fit file log failed", exc_info=True)
    except Exception:
        logging.debug("overlay fit failed", exc_info=True)


def _create_prediction_overlay_window(*, hidden: bool = False) -> ctk.CTkToplevel:
    """Create the prediction overlay window.

    A ``CTkToplevel`` so CustomTkinter scales the window (and its content) for
    the monitor it lands on. With per-monitor DPI awareness active, the final
    size and centring are handled by ``_fit_overlay_over_backdrop``.
    """
    ov = ctk.CTkToplevel(root)
    if hidden:
        ov.withdraw()
    ov.overrideredirect(True)
    _apply_window_icon(ov)
    _enable_overlay_escape(ov)
    ov.attributes("-topmost", True)
    ov.geometry(_prediction_overlay_geometry(ov))
    ov.minsize(1000, 700)
    ov.images = []
    return ov


def _make_backdrop_nonactivating(backdrop) -> None:
    """Keep fallback dialog backdrops from taking focus on Windows clicks."""
    if sys.platform.startswith("linux"):
        try:
            backdrop.wm_attributes("-type", "splash")
        except tk.TclError:
            pass
        return
    if sys.platform != "win32":
        return
    try:
        hwnd = int(backdrop.winfo_id())
        user32 = ctypes.windll.user32
        is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
        get_style = user32.GetWindowLongPtrW if is_64bit else user32.GetWindowLongW
        set_style = user32.SetWindowLongPtrW if is_64bit else user32.SetWindowLongW
        long_type = ctypes.c_ssize_t if is_64bit else ctypes.c_long
        get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
        get_style.restype = long_type
        set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, long_type]
        set_style.restype = long_type
        ex_style = int(get_style(hwnd, -20))  # GWL_EXSTYLE
        set_style(hwnd, -20, long_type(ex_style | 0x08000000))  # WS_EX_NOACTIVATE
    except (AttributeError, OSError, TypeError, ValueError):
        logging.debug("Could not make overlay backdrop non-activating", exc_info=True)


def _create_prediction_overlay_shell(*, reveal_after_ms: int = 0) -> ctk.CTkToplevel:
    """Create a prediction dimmer, then optionally reveal its panel shortly after."""
    global overlay, _overlay_backdrop
    _overlay_backdrop = tk.Toplevel(root)
    _overlay_backdrop.overrideredirect(True)
    _overlay_backdrop.configure(background="#000000")
    _overlay_backdrop.attributes("-alpha", 0.0)
    _overlay_backdrop.attributes("-topmost", True)
    mon_x, mon_y, mon_w, mon_h = _active_overlay_monitor_rect(_overlay_backdrop)
    _overlay_backdrop.geometry(f"{mon_w}x{mon_h}+{mon_x}+{mon_y}")
    _make_backdrop_nonactivating(_overlay_backdrop)
    def _consume_overlay_click(_event=None):
        root.after_idle(_destroy_overlay)
        return "break"

    _overlay_backdrop.bind("<Button-1>", _consume_overlay_click)
    _overlay_backdrop.lift()

    def _fade_backdrop(alpha: float = 0.0) -> None:
        try:
            if _overlay_backdrop is None or not _overlay_backdrop.winfo_exists():
                return
            next_alpha = min(0.48, alpha + 0.08)
            _overlay_backdrop.attributes("-alpha", next_alpha)
            if overlay is not None and overlay.winfo_exists():
                overlay.lift()
            if next_alpha < 0.48:
                _overlay_backdrop.after(20, lambda: _fade_backdrop(next_alpha))
        except tk.TclError:
            return

    # Map the backdrop on its own event-loop turn before creating the visible
    # panel. This makes the dimmer feel immediate even while the loader window
    # is being sized for its monitor.
    _overlay_backdrop.update_idletasks()
    _fade_backdrop()

    ov = _create_prediction_overlay_window(hidden=reveal_after_ms > 0)

    def _reveal_window() -> None:
        try:
            if not ov.winfo_exists():
                return
            if reveal_after_ms > 0:
                # Map fully transparent first, so CTk's per-monitor DPI pass
                # happens before anything is visible.  The old flow revealed at
                # the provisional geometry and then visibly corrected it on an
                # idle callback.
                ov.attributes("-alpha", 0.0)
                ov.deiconify()
                ov.update_idletasks()
                _fit_overlay_over_backdrop(ov)
                ov.attributes("-alpha", 1.0)
            ov.lift()
            if reveal_after_ms <= 0:
                # Once realised, size/centre the window against the measured
                # backdrop so its per-monitor scaling can't leave it oversized
                # or off-centre.
                ov.after_idle(lambda: _fit_overlay_over_backdrop(ov))
        except tk.TclError:
            return

    if reveal_after_ms > 0:
        ov.after(reveal_after_ms, _reveal_window)
    else:
        ov.after_idle(_reveal_window)
    overlay = ov
    state.overlay = ov
    return ov


def _create_overlay_dialog(on_cancel) -> tuple[tk.Toplevel, ctk.CTkToplevel]:
    """Create a frameless, dimmed, screen-centred modal overlay dialog.

    Mirrors the prediction overlay's look (full-screen dimmed backdrop over the
    game, borderless top-most window, Escape / click-outside to dismiss) but is
    self-contained so it can host arbitrary interactive content. The caller is
    responsible for sizing/positioning the returned window once its content is
    built and for destroying both windows via ``on_cancel``.
    """
    backdrop = tk.Toplevel(root)
    backdrop.overrideredirect(True)
    backdrop.configure(background="#000000")
    backdrop.attributes("-alpha", 0.48)
    backdrop.attributes("-topmost", True)
    mon_x, mon_y, mon_w, mon_h = _active_overlay_monitor_rect(backdrop)
    backdrop.geometry(f"{mon_w}x{mon_h}+{mon_x}+{mon_y}")
    _make_backdrop_nonactivating(backdrop)

    win = ctk.CTkToplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    # Remember the chosen monitor so _center_overlay_dialog lands on the same
    # screen the backdrop covers, even if the cursor moves while it builds.
    win._overlay_monitor_rect = (mon_x, mon_y, mon_w, mon_h)
    _apply_window_icon(win)

    def _dismiss(_event=None):
        # Match the prediction presenter's immediate, click-consuming close
        # behavior while letting Tk finish dispatching this mouse event first.
        backdrop.after(0, on_cancel)
        return "break"

    backdrop.bind("<Button-1>", _dismiss)
    win.bind("<Escape>", _dismiss)
    backdrop.lift()
    return backdrop, win


def _center_overlay_dialog(win) -> None:
    """Size a frameless overlay dialog to its content and centre it on its monitor."""
    win.update_idletasks()
    width = win.winfo_reqwidth()
    height = win.winfo_reqheight()
    mon_x, mon_y, mon_w, mon_h = getattr(win, "_overlay_monitor_rect", None) or (
        0, 0, win.winfo_screenwidth(), win.winfo_screenheight()
    )
    x = mon_x + max(0, (mon_w - width) // 2)
    y = mon_y + max(0, (mon_h - height) // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.lift()
    win.after_idle(win.focus_force)


def _show_prediction_loading_overlay(request_id: int | None = None) -> None:
    """Show immediate feedback while the asynchronous price check is running."""
    global _overlay_loading, _overlay_loading_window, _overlay_loading_cover, _prediction_loader_windows
    global _overlay_monitor_rect
    if not (root and root.winfo_exists()):
        return
    if request_id is not None and request_id != _prediction_request_id:
        return
    _destroy_overlay(invalidate_request=False)
    # Pin the whole overlay lifecycle to the PoE window (falling back to the
    # cursor's screen) so the loader, backdrop, and result all sit over the
    # game and agree with each other even if focus/cursor moves afterward.
    _overlay_monitor_rect = _overlay_anchor_rect(root)
    logging.info("overlay anchored to rect %s (poe=%s)", _overlay_monitor_rect, _poe_window_rect())
    ov = _create_prediction_overlay_shell(reveal_after_ms=110)
    _overlay_loading = True
    _overlay_loading_window = ov
    _prediction_loader_windows = [ov]

    panel = ctk.CTkFrame(ov, corner_radius=0, fg_color="#1E1E1E")
    panel.place(relx=0, rely=0, relwidth=1, relheight=1)
    _overlay_loading_cover = panel
    ctk.CTkLabel(panel, text="Pricing item…", font=("Segoe UI", 20, "bold")).pack(
        pady=(28, 8)
    )
    ctk.CTkLabel(
        panel,
        text="Checking model estimates and comparable listings.",
        text_color="#AEBCC9",
    ).pack(pady=(0, 20))
    progress = ctk.CTkProgressBar(
        panel,
        mode="indeterminate",
        indeterminate_speed=1,
        width=300,
        height=14,
    )
    progress.pack(pady=(0, 12))
    progress.start()
    ctk.CTkLabel(panel, text="Press Esc to cancel", text_color="#7E8C99", font=("Segoe UI", 11)).pack()
    # Draw the initial marquee segment before returning to the event loop. The
    # worker is intentionally launched on a later tick, so this is visible
    # even on the first prediction after startup.
    ov.update_idletasks()



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


def _price_string(row: pd.Series, *, conversions=None) -> tuple[str, float] | None:
    return helper_price_string(row, conversions=conversions)


# simple price like "10e" or "50c" or "2d" for header tags
def _price_simple(row: pd.Series) -> Optional[str]:
    return helper_price_simple(row)


def _triple(e_val: float) -> str:
    return helper_triple(e_val)


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
    "wand": "Wand",
    "sceptre": "Sceptre",
    "scepter": "Sceptre",
    "staff": "Staff",
    "staves": "Staff",
    "quiver": "Quiver",
    "tablet": "Tablet",
    "waystone": "Waystone",
    "bow": "Bow",
    "shortbow": "Bow",
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


@dataclass
class ComparisonLine:
    """One already-compared line in a similar-item card.

    This deliberately contains presentation metadata rather than pandas/Tk
    objects, so it can be assembled in the spawned scoring process.
    """
    left_text: str
    right_text: str
    left_style: str | None = None
    right_style: str | None = None
    filter_annotation: str | None = None
    divider: bool = False
    comparison_kind: str = "explicit"
    change_kind: str | None = None
    delta: float | None = None


@dataclass
class ComparisonCard:
    your_item_name: str
    matched_item_name: str
    lines: list[ComparisonLine]
    left_icon_png: bytes | None = None
    right_icon_png: bytes | None = None


@dataclass
class PredictionPayload:
    item_name: str
    category: str
    segment: str | None
    display_value: float | None
    bucket_label: str | None
    bucket_low: float | None
    bucket_high: float | None
    bucket_median: float | None
    nearest_mean: float | None
    nearest_median: float | None
    similar_items_summary: str | None
    distribution_png: bytes | None
    category_distribution_png: bytes | None
    comparison_cards: list[ComparisonCard]


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
        "socket_count",
        "Socket Count",
        "sockets",
        "Sockets",
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

    def _append_divider_once(base_lines: list[str], nbr_lines: list[str]) -> None:
        if base_lines and base_lines[-1] == "--------" and nbr_lines and nbr_lines[-1] == "--------":
            return
        base_lines.append("--------")
        nbr_lines.append("--------")

    def _format_extra_value(key: str, value: float) -> str:
        if key in _EXTRA_STATUS_KEYS:
            return "Yes" if not _is_zeroish(value) else "No"
        return _fmt_disp(_disp(value, False))

    for r, (_, nbr) in enumerate(df.iterrows()):
        try:
            # split features: core first, then everything else
            extra_keys = set(_EXTRA_MIRROR_KEYS)
            noncore_candidates = sorted(
                (set(base_series.index) | set(nbr.index)) - set(core) - _SKIP - extra_keys
            )
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
                key_present = (
                    k in getattr(base_series, "index", [])
                    or k in getattr(nbr, "index", [])
                    or k in getattr(df, "columns", [])
                )
                if k in _DPS_CORE_KEYS and not key_present:
                    continue
                b_raw = _numeric(base_series, k)
                n_raw = _numeric(nbr, k)
                if b_raw == 0 and k != "block_norm" and k not in _DPS_CORE_KEYS:
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

            # ----- extra non-mod comparison rows -----
            extra_rows: list[tuple[str, float, float]] = []
            for k in _EXTRA_MIRROR_KEYS:
                k_in_base = k in getattr(base_series, "index", [])
                if not k_in_base:
                    continue
                b_raw = _numeric(base_series, k)
                n_raw = _numeric(nbr, k)
                extra_rows.append((k, b_raw, n_raw))

            if extra_rows:
                _append_divider_once(base_lines, nbr_lines)
                for k, b_raw, n_raw in extra_rows:
                    label = _EXTRA_MIRROR_KEYS.get(k, k)
                    left_txt = f"{label}: {_format_extra_value(k, b_raw)}"
                    right_txt = f"{label}: {_format_extra_value(k, n_raw)}"

                    if k not in _EXTRA_STATUS_KEYS:
                        b_disp = _disp(b_raw, False)
                        n_disp = _disp(n_raw, False)
                        delta = n_disp - b_disp
                        if np.isfinite(delta) and delta != 0:
                            sign = "+" if delta > 0 else ""
                            right_txt += f" ({sign}{_fmt_disp(delta)})"
                            colours_r[len(nbr_lines)] = "plus" if delta > 0 else "minus"

                    if _is_zeroish(b_raw) ^ _is_zeroish(n_raw):
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
            lbl0_img = _icon_label(hdr0, name_left, 46)
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
            lbl1_img = _icon_label(hdr1, name_right, 46)
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



@dataclass(frozen=True)
class _ActionBindingResult:
    active: str

    @property
    def disabled(self) -> bool:
        return self.active == "off"


_action_hotkey_values: dict[str, str] = {}
_pending_hotkey_cleanup: list = []


def _bind_action_hotkey(handle_name, custom, default, callback) -> _ActionBindingResult:
    desired = keyboard.action_shortcut(custom, default)
    previous = globals()[handle_name]
    if previous is not None and _action_hotkey_values.get(handle_name) == desired:
        return _ActionBindingResult(desired)
    keyboard.validate_hotkey(desired)
    candidate = None
    try:
        if desired != "off":
            candidate = keyboard.add_hotkey(desired, callback, suppress=True)
        if previous is not None:
            keyboard.remove_hotkey(previous)
    except Exception:
        if candidate is not None:
            try:
                keyboard.remove_hotkey(candidate)
            except Exception:
                _pending_hotkey_cleanup.append(candidate)
                logging.exception("Replacement hotkey cleanup failed; retaining its handle")
        raise
    globals()[handle_name] = candidate
    _action_hotkey_values[handle_name] = desired
    logging.info("Action hotkey %s active=%s app_version=%s", handle_name, desired, __version__)
    return _ActionBindingResult(desired)


def _bind_overlay_hotkey(custom: str | None) -> _ActionBindingResult:
    return _bind_action_hotkey("_overlay_hotkey_handle", custom,
                              DEFAULT_OVERLAY_HOTKEY, _handle_hotkey_super)


def _bind_filtered_overlay_hotkey(custom: str | None) -> _ActionBindingResult:
    return _bind_action_hotkey("_filtered_overlay_hotkey_handle", custom,
                              DEFAULT_FILTERED_OVERLAY_HOTKEY, _handle_hotkey_filtered)


def _bind_craft_potential_hotkey(custom: str | None) -> _ActionBindingResult:
    return _bind_action_hotkey("_craft_potential_hotkey_handle", custom,
                              DEFAULT_CRAFT_POTENTIAL_HOTKEY, _handle_hotkey_craft_potential)


def _bind_stash_scrape_hotkey(custom: str | None) -> _ActionBindingResult:
    return _bind_action_hotkey("_stash_scrape_hotkey_handle", custom,
                              DEFAULT_STASH_SCRAPE_HOTKEY, _handle_hotkey_stash_scrape)


def _action_hotkey_label(handle_name: str) -> str:
    value = _action_hotkey_values.get(handle_name)
    return "Disabled" if value == "off" else value or "Unavailable"


def _commit_action_hotkey(entry, key, rebind) -> bool:
    if entry is None:
        return True
    value = entry.get().strip().lower()
    previous = state.config.get(key, "")
    try:
        rebind(value)
    except Exception as exc:
        logging.exception("Rebinding hotkey %s failed", key)
        entry.delete(0, "end")
        entry.insert(0, previous)
        messagebox.showerror("Shortcut unchanged", str(exc), parent=root)
        return False
    state.config[key] = value
    if _persist_settings_to_disk(key):
        return True
    state.config[key] = previous
    try:
        rebind(previous)
        entry.delete(0, "end")
        entry.insert(0, previous)
    except Exception:
        # Keep the actual live value truthful even if a rollback cannot bind.
        state.config[key] = value
        logging.exception("Could not restore shortcut after save failure")
        messagebox.showerror("Shortcut not saved", "The new shortcut is active for this session only.", parent=root)
    return False


def _reset_action_hotkeys(bindings) -> bool:
    """Release old assignments together so swapped shortcuts can reset."""
    previous = {key: state.config.get(key, "") for _entry, key, _binder in bindings}
    try:
        for _entry, _key, binder in bindings:
            binder("off")
        for entry, key, binder in bindings:
            value = entry.get().strip().lower()
            binder(value)
            state.config[key] = value
        if _persist_settings_to_disk("default shortcuts"):
            return True
    except Exception as exc:
        logging.exception("Could not reset action shortcuts")
        messagebox.showerror("Shortcut reset failed", str(exc), parent=root)
    try:
        for _entry, _key, binder in bindings:
            binder("off")
        for entry, key, binder in bindings:
            binder(previous[key])
            state.config[key] = previous[key]
            entry.delete(0, "end")
            entry.insert(0, previous[key])
    except Exception:
        logging.exception("Could not restore all shortcuts after reset failure")
        messagebox.showerror("Shortcut recovery failed", "Check the active shortcut summary before continuing.", parent=root)
    return False


def _bind_dev_sample_hotkeys() -> None:
    """Bind validation hotkeys once, even if the GUI is initialized again."""
    global _dev_sample_hotkey_handle, _dev_craft_sample_hotkey_handle

    bindings = (
        ("_dev_sample_hotkey_handle", DEV_SAMPLE_HOTKEY, _handle_hotkey_sample_picker),
        (
            "_dev_craft_sample_hotkey_handle",
            DEV_CRAFT_SAMPLE_HOTKEY,
            _handle_hotkey_craft_sample,
        ),
    )
    for handle_name, hotkey, callback in bindings:
        previous = globals()[handle_name]
        if previous is not None:
            try:
                keyboard.remove_hotkey(previous)
            except Exception:
                logging.debug("Previous validation hotkey removal failed", exc_info=True)
            finally:
                globals()[handle_name] = None
        try:
            globals()[handle_name] = keyboard.add_hotkey(
                hotkey, callback, suppress=False
            )
        except Exception as exc:
            logging.warning("Could not bind validation hotkey %r: %s", hotkey, exc)


# ------------- UNSUPERVISED overlay (Price Mirror) ----
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
    _apply_window_icon(overlay)
    overlay.title("Price Mirror")
    _enable_overlay_escape(overlay)
    overlay.attributes("-topmost", True)
    overlay.after_idle(lambda: overlay.attributes("-topmost", False))

    # header
    cont = ctk.CTkFrame(overlay, corner_radius=10)
    cont.pack(fill="both", expand=True, padx=8, pady=8)
    cont.columnconfigure((0, 1), weight=1)
    cont.rowconfigure(7, weight=1)

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
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))

    combined = f"{title_txt} [{', '.join(tags)}]"
    ctk.CTkLabel(cont, text=combined, font=("Consolas", 19), text_color="#CCCCCC").grid(
        row=2, column=0, columnspan=2, sticky="ew"
    )

    # body
    body = ctk.CTkFrame(cont, fg_color="transparent")
    body.grid(row=7, column=0, columnspan=2, sticky="nsew")
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
    _apply_window_icon(ov)
    ov.title(f"StashSage Price Predictions - {item}")
    _enable_overlay_escape(ov)
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
            model_dirs = _super_model_dirs()

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
                for model_dir in model_dirs:
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
                    for model_dir in model_dirs:
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
                for model_dir in model_dirs:
                    json_candidates.append(model_dir / f"{cat_norm}_scoring.json")
                    xlsx_candidates.append(model_dir / f"{cat_norm}_scoring.xlsx")
                    png_candidates.append(model_dir / f"{cat_norm}_price_dists.png")
                # Some runs may include kind in the filename
                for kind in ("ring", "amulet", "belt"):
                    for model_dir in model_dirs:
                        json_candidates.append(
                            model_dir / f"{cat_norm}_{kind}_scoring.json"
                        )
                        xlsx_candidates.append(
                            model_dir / f"{cat_norm}_{kind}_scoring.xlsx"
                        )
                        png_candidates.append(
                            model_dir / f"{cat_norm}_{kind}_price_dists.png"
                        )

            # Try pre-binned stats first; it avoids loading all scored rows.
            stats_entry = _category_stats_entry(cat_norm, seg_norm)
            if isinstance(stats_entry, Mapping):
                profile = stats_entry.get("distribution_profile")
                if isinstance(profile, Mapping):
                    try:
                        dist_buf = generate_predicted_overlay_from_profile(
                            profile,
                            marker_val,
                        title=f"{cat_norm}{('/' + seg_norm) if seg_norm else ''} - Price context by model bucket",
                        )
                        dynamic_done = True
                    except Exception:
                        dynamic_done = False

            # Try JSON next (dynamic marker via full scored rows)
            json_path = next((p for p in json_candidates if p.is_file()), None)
            if not dynamic_done and json_path is not None:
                try:
                    df_scored = _load_scoring_json_once(json_path)
                    if isinstance(df_scored, pd.DataFrame) and not df_scored.empty:
                        dist_buf = generate_predicted_overlay_with_marker(
                            df_scored,
                            marker_val,
                            title=f"{cat_norm}{('/' + seg_norm) if seg_norm else ''} - Predicted Distributions",
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
                                title=f"{cat_norm}{('/' + seg_norm) if seg_norm else ''} - Predicted Distributions",
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
                font=_FONT_SECTION_TITLE,
            ).grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)

    except Exception:
        ctk.CTkLabel(
            cont,
            text="Score Distribution: error loading image",
            font=_FONT_SECTION_TITLE,
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

    # window geometry - start large enough by default, within screen bounds
    ov.update_idletasks()
    sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
    # Reduce default width by ~20% (from 90% to 72% of screen; 1600 ? 1280 cap)
    default_w = min(int(sw * 0.72), 1280)
    default_h = min(int(sh * 0.90), 900)
    ov.geometry(f"{default_w}x{default_h}+{(sw - default_w)//2}+{(sh - default_h)//2}")
    ov.minsize(960, 700)


# ------------- ML pipelines / process-safe view models -------------------
def build_comparison_cards(
    base_series: pd.Series,
    neighbors: pd.DataFrame,
    item_name: str,
    *,
    show_defence_mods: bool = False,
    filters: dict[str, tuple[str, object]] | None = None,
    price_conversions: Mapping[str, Any] | None = None,
) -> list[ComparisonCard]:
    """Apply the legacy mirror comparison rules without creating any widgets."""
    base_series = pd.Series(base_series)
    frame = neighbors if isinstance(neighbors, pd.DataFrame) else pd.DataFrame(neighbors)
    core_all = list(_CORE_KEYS)
    shield_like = any(word in str(item_name or "").lower() for word in ("shield", "buckler"))
    core = (["block_norm"] if shield_like and ("block_norm" in base_series.index or "block_norm" in frame.columns) else [])
    core += [key for key in core_all if key != "block_norm"]
    skip = (set() if show_defence_mods else set(_HIDE_DEF_PATTERNS)) | {
        "price", "Price", "currency", "Currency", "amount", "Amount", "Cur", "cur",
        "price_in_exalts", "Price_in_Exalts", "socket_count", "Socket Count", "sockets", "Sockets",
        "Armour", "armour", "Evasion", "evasion", "Evasion Rating", "evasion rating",
        "Energy Shield", "energy shield", "ar", "ev", "es",
    }
    filter_map = {str(key).lower(): value for key, value in (filters or {}).items()}

    def numeric(series: pd.Series, key: str) -> float:
        try:
            return _series_numeric(series, key) if key in _CORE_KEYS else float(series.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def display(value: float) -> str:
        try:
            value = round(float(value))
            return _fmt_disp(value) if np.isfinite(value) else "-"
        except (TypeError, ValueError):
            return "-"

    def annotation(key: str) -> str | None:
        entry = filter_map.get(str(key).lower())
        if not entry:
            return None
        try:
            op, value = entry
            if op in {"==", ">="}:
                return ("=" if op == "==" else ">=") + display(float(value))
            if op == "between" and isinstance(value, (tuple, list)) and len(value) == 2:
                low, high = sorted((float(value[0]), float(value[1])))
                return f"{display(low)}, {display(high)}"
        except (TypeError, ValueError):
            pass
        return None

    cards: list[ComparisonCard] = []
    for _, neighbor in frame.iterrows():
        lines: list[ComparisonLine] = []
        printed_core = False
        for key in core:
            present = key in base_series.index or key in neighbor.index or key in frame.columns
            if key in _DPS_CORE_KEYS and not present:
                continue
            base, matched = numeric(base_series, key), numeric(neighbor, key)
            if base == 0 and key != "block_norm" and key not in _DPS_CORE_KEYS:
                continue
            printed_core = True
            delta = round(matched) - round(base)
            right = f"{_CORE_KEYS.get(key, key)}: {display(matched)}"
            if delta:
                right += f" ({'+' if delta > 0 else ''}{display(delta)})"
            tag = annotation(key)
            if tag:
                right += f" [{tag}]"
            one_sided = _is_zeroish(base) ^ _is_zeroish(matched)
            lines.append(ComparisonLine(f"{_CORE_KEYS.get(key, key)}: {display(base)}", right,
                "yellow" if one_sided else None, "yellow" if one_sided else ("plus" if delta > 0 else "minus" if delta < 0 else None), tag,
                comparison_kind="core", change_kind="replacement" if one_sided else ("roll" if delta else None), delta=float(delta)))
        if printed_core:
            lines.append(ComparisonLine("--------", "--------", divider=True))
        extras = set(_EXTRA_MIRROR_KEYS)
        candidates = sorted((set(base_series.index) | set(neighbor.index)) - set(core) - skip - extras)
        rows = []
        for order, key in enumerate(candidates):
            if str(key).strip().lower() in {"block", "block_norm", "block chance", "#% increased block chance"}:
                continue
            base, matched = numeric(base_series, key), numeric(neighbor, key)
            if _is_zeroish(base) and _is_zeroish(matched):
                continue
            rows.append((_mod_sort_bucket(base, matched), order, key, base, matched))
        for _, _, key, base, matched in sorted(rows):
            delta = round(matched) - round(base)
            right = f"{_CORE_KEYS.get(key, key)}: {display(matched)}"
            if delta:
                right += f" ({'+' if delta > 0 else ''}{display(delta)})"
            tag = annotation(key)
            if tag:
                right += f" [{tag}]"
            one_sided = _is_zeroish(base) ^ _is_zeroish(matched)
            lines.append(ComparisonLine(f"{_CORE_KEYS.get(key, key)}: {display(base)}", right,
                "yellow" if one_sided else None, "yellow" if one_sided else ("plus" if delta > 0 else "minus" if delta < 0 else None), tag,
                comparison_kind="explicit", change_kind="replacement" if one_sided else ("roll" if delta else None), delta=float(delta)))
        extra_rows = [(key, numeric(base_series, key), numeric(neighbor, key)) for key in _EXTRA_MIRROR_KEYS if key in base_series.index]
        if extra_rows:
            if not lines or not lines[-1].divider:
                lines.append(ComparisonLine("--------", "--------", divider=True))
            for key, base, matched in extra_rows:
                label = _EXTRA_MIRROR_KEYS[key]
                left, right = ("Yes" if not _is_zeroish(base) else "No"), ("Yes" if not _is_zeroish(matched) else "No")
                delta = round(matched) - round(base)
                if key not in _EXTRA_STATUS_KEYS and delta:
                    right += f" ({'+' if delta > 0 else ''}{display(delta)})"
                one_sided = _is_zeroish(base) ^ _is_zeroish(matched)
                lines.append(ComparisonLine(f"{label}: {left}", f"{label}: {right}", "yellow" if one_sided else None,
                    "yellow" if one_sided else ("plus" if delta > 0 else "minus" if delta < 0 else None),
                    comparison_kind="extra", change_kind="replacement" if one_sided else ("roll" if delta else None), delta=float(delta)))
        price = (
            _price_string(neighbor, conversions=price_conversions)
            if price_conversions is not None else _price_string(neighbor)
        )
        if price:
            lines.extend((ComparisonLine("", "--------", divider=True, comparison_kind="divider"), ComparisonLine("", f"Price: {price[0]}", right_style="plus", comparison_kind="price")))
        cards.append(ComparisonCard(str(item_name or "Your Item"), str(neighbor.get("item", "Similar Item") or "Similar Item"), lines))
    return cards


def _format_mirror_row_view_models(base: Mapping[str, Any], neighbours: list[Mapping[str, Any]], item_name: str, **kwargs) -> list[ComparisonCard]:
    return build_comparison_cards(pd.Series(dict(base or {})), pd.DataFrame(neighbours), item_name, **kwargs)


_ICON_FALLBACK_CATEGORIES = (
    "Body_Armour", "Helmet", "Boots", "Gloves", "Focus", "Shield", "Buckler",
    "Ring", "Amulet", "Belt", "Wand", "Sceptre", "Staff", "Quiver", "Bow",
)


@lru_cache(maxsize=2)
def _icon_base_map(manifest_path: str, _mtime: float) -> Optional[dict[str, tuple[str, str]]]:
    """Map the last one or two words of a base type to (category, baseType).

    `base_images.json` is ~330 KB and was reparsed on every prediction. The
    mtime is part of the key, so an asset refresh rebuilds this on next use.
    Returns None when the manifest cannot be read, which callers treat as
    "no icons" rather than falling through to the default artwork.
    """
    try:
        items = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    base_map: dict[str, tuple[str, str]] = {}
    for entry in items if isinstance(items, list) else []:
        base_type = str(entry.get("baseType") or "").strip()
        if not base_type:
            continue
        key = " ".join(base_type.split()[-2:]).lower()
        base_map[key] = (str(entry.get("category") or ""), base_type)
    return base_map


@lru_cache(maxsize=512)
def _comparison_icon_candidates(
    raw_name: str, manifest_path: str, manifest_mtime: float
) -> tuple[str, ...]:
    """Existing icon files for one item name, best match first.

    Resolution probes up to ~30 paths, so it is cached per name. Every existing
    candidate is kept rather than only the first: an unreadable image still
    falls through to the category default, as it did before caching.
    """
    base_map = _icon_base_map(manifest_path, manifest_mtime)
    if base_map is None:
        return ()
    roots = asset_paths.asset_search_dirs("base_icons")
    words = raw_name.split()
    candidates: list[Path] = []
    for span in (2, 1):
        entry = base_map.get(" ".join(words[-span:]).lower()) if words else None
        if entry is None:
            continue
        category, base_type = entry
        safe_name = "".join(char for char in base_type if char.isalnum() or char in (" ", "-", "_"))
        for icon_root in roots:
            candidates.extend((icon_root / category / f"{safe_name}.png", icon_root / category / "default.png"))
    for category in _ICON_FALLBACK_CATEGORIES:
        for icon_root in roots:
            candidates.append(icon_root / category / "default.png")
    return tuple(str(c) for c in candidates if c.is_file())


@lru_cache(maxsize=256)
def _render_icon_png(icon_path: str, size: int, _mtime: float) -> Optional[bytes]:
    """Decode and letterbox one icon to `size`, or None if it cannot be read.

    Keyed by path, size and mtime: base types repeat constantly across
    predictions, so the decode and LANCZOS resize run once each.
    """
    try:
        with Image.open(icon_path) as source:
            icon = source.convert("RGBA")
            icon.thumbnail((size, size), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size, size))
            canvas.paste(icon, ((size - icon.width) // 2, (size - icon.height) // 2), icon)
            buffer = io.BytesIO()
            canvas.save(buffer, format="PNG")
            return buffer.getvalue()
    except (OSError, ValueError):
        return None


def _prepare_comparison_icon_pngs(item_names: list[str], size: int = 46) -> dict[str, bytes]:
    """Resolve and resize comparison thumbnails in the prediction worker."""
    try:
        manifest_path = asset_paths.resolve_asset_file("files", "base_images.json")
        manifest_mtime = manifest_path.stat().st_mtime
    except (OSError, ValueError, TypeError):
        return {}
    manifest_key = str(manifest_path)
    if _icon_base_map(manifest_key, manifest_mtime) is None:
        return {}

    prepared: dict[str, bytes] = {}
    for raw_name in dict.fromkeys(str(name or "") for name in item_names):
        for candidate in _comparison_icon_candidates(raw_name, manifest_key, manifest_mtime):
            try:
                icon_mtime = os.stat(candidate).st_mtime
            except OSError:
                continue
            png = _render_icon_png(candidate, size, icon_mtime)
            if png is not None:
                prepared[raw_name] = png
                break
    return prepared


def _render_prepared_comparison_card(body, card: ComparisonCard, row_index: int) -> None:
    """Small UI-only renderer for one already formatted comparison card."""
    if isinstance(card, Mapping):
        card = ComparisonCard(
            your_item_name=str(card.get("your_item_name") or "Your Item"),
            matched_item_name=str(card.get("matched_item_name") or "Similar Item"),
            lines=[
                ComparisonLine(
                    str(line.get("left_text") or ""), str(line.get("right_text") or ""),
                    line.get("left_style"), line.get("right_style"),
                    line.get("filter_annotation"), bool(line.get("divider", False)),
                    str(line.get("comparison_kind") or "explicit"), line.get("change_kind"), line.get("delta"),
                )
                for line in card.get("lines", []) if isinstance(line, Mapping)
            ],
            left_icon_png=card.get("left_icon_png"),
            right_icon_png=card.get("right_icon_png"),
        )
    left = ctk.CTkFrame(body, fg_color="transparent")
    right = ctk.CTkFrame(body, fg_color="transparent")
    left.grid(row=row_index, column=0, sticky="nsew", padx=(6, 4), pady=4)
    right.grid(row=row_index, column=1, sticky="nsew", padx=(4, 6), pady=4)
    cards = (
        (left, f"{card.your_item_name} (Your Item)", card.left_icon_png, card.lines, "left"),
        (right, card.matched_item_name, card.right_icon_png, card.lines, "right"),
    )
    for parent, title, icon_png, lines, side in cards:
        parent.columnconfigure(1, weight=1)
        title_column = 0
        if icon_png:
            image_label = add_png(parent, io.BytesIO(icon_png), overlay)
            image_label.grid(row=0, column=0, sticky="w", padx=(0, 6))
            title_column = 1
        ctk.CTkLabel(parent, text=title, font=("Consolas", 18, "bold"), anchor="w").grid(row=0, column=title_column, sticky="we")
        texts = [line.left_text if side == "left" else line.right_text for line in lines]
        yellow = {index for index, line in enumerate(lines) if (line.left_style if side == "left" else line.right_style) == "yellow"}
        # Colour the (+/-N) delta green/red on its own, even on one-sided
        # modifiers whose base text is yellow. The delta direction is carried by
        # the plus/minus style, or read from the embedded "(+" / "(-" for yellow
        # rows that don't set it. textbox raises plus/minus above the yellow tag
        # so only the delta segment recolours.
        colours: dict[int, str] = {}
        for index, text in enumerate(texts):
            style = lines[index].left_style if side == "left" else lines[index].right_style
            if style in {"plus", "minus"}:
                colours[index] = style
            elif "(+" in text:
                colours[index] = "plus"
            elif "(-" in text:
                colours[index] = "minus"
        tags = {index: f"[{line.filter_annotation}]" for index, line in enumerate(lines) if side == "right" and line.filter_annotation}
        height = max(100, int((len(lines) + 2) * 22 * _KNN_CELL_HEIGHT_FACTOR))
        _textbox(parent, texts, yellow, colours, 1, 0, height=height, filter_tags=tags if side == "right" else None, columnspan=2)


def _png_bytes(value):
    return io.BytesIO(value) if value else None


def _plain_comparison_card(card: ComparisonCard) -> dict[str, Any]:
    """Cross-process form of a comparison card; no gui_tk classes cross IPC."""
    return {
        "your_item_name": card.your_item_name,
        "matched_item_name": card.matched_item_name,
        "left_icon_png": card.left_icon_png,
        "right_icon_png": card.right_icon_png,
        "lines": [
            {
                "left_text": line.left_text,
                "right_text": line.right_text,
                "left_style": line.left_style,
                "right_style": line.right_style,
                "filter_annotation": line.filter_annotation,
                "divider": line.divider,
                "comparison_kind": line.comparison_kind,
                "change_kind": line.change_kind,
                "delta": line.delta,
            }
            for line in card.lines
        ],
    }


def _dashboard_model_loading_text(payload: Mapping[str, Any]) -> str:
    """Give the loading cover the useful model result before charts are attached."""
    value = payload.get("display_value")
    if not isinstance(value, (int, float)):
        return "Preparing model result…"
    bucket = str(payload.get("bucket_label") or "").strip()
    category = str(payload.get("category_title") or "item").strip()
    label = f"Model #1 XGB - {_priced_text(value, payload.get('model_conversion'), payload.get('price_display_mode'))}"
    return f"{label}\nRelative {bucket} Value within {category}" if bucket else label


def _render_nearest_dashboard_banner(parent, summary: Mapping[str, Any], detail: str | None):
    """Render the KNN banner with native labels so its text paints immediately.

    CTk's nested grid/pack banner can briefly collapse to its centre while the
    scrollable frame is settling, which leaves only a vertical text slice.
    """
    def price(value: object) -> str | None:
        try:
            return f"{int(round(float(value)))}e"
        except (TypeError, ValueError):
            return None

    median, mean = price(summary.get("median")), price(summary.get("mean"))
    values = ", ".join(part for part in (
        f"{median} (median)" if median else None,
        f"{mean} (mean)" if mean else None,
    ) if part)
    # Place one CTk label directly in the scroll-layout grid. Mixing a native
    # Tk label into a CTkFrame made the child collapse to a thin centre slice
    # while CustomTkinter recalculated the scrollable frame's width.
    text = f"Model #2 \u00b7 Similar Items  |  {values}"
    if detail:
        text += f"  |  {detail}"
    banner = ctk.CTkLabel(
        parent, text=text, fg_color=_BAR_COLOUR, corner_radius=8,
        text_color="white", font=("Segoe UI", 14, "bold"),
        justify="center", anchor="center", height=44,
    )
    banner.pack(fill="x", padx=4, pady=(0, 4))
    return banner


# Per-idle-tick time budget for rendering KNN comparison cards. Rendering runs
# behind the opaque loader cover, so this trades a little UI latency per tick
# for far fewer event-loop round trips than one-card-per-tick.
_CARD_BATCH_BUDGET_S = 0.008


def _present_dashboard_staged_v2(payload: Mapping[str, Any], request_id: int) -> None:
    """Build the result behind a loader.

    Layout: a single fixed header anchors the conversion banner, Model #1
    (XGB), the visualizations, and Model #2 (KNN summary). Only the comparison
    cards live in the scrollable body, so inserting cards can never reflow or
    clip the anchored bands. When viz is disabled the charts row is omitted and
    the header stays compact.
    """
    global overlay, _overlay_loading, _overlay_loading_cover, _overlay_loading_window, _prediction_loader_windows
    if request_id != _prediction_request_id or not root or not root.winfo_exists():
        return
    # Keep one native window for the loader and result. Creating a second
    # top-level during the handoff is what produced the overlapping loader
    # artifacts on Windows/CustomTkinter.
    result = _overlay_loading_window if _overlay_loading_window and _overlay_loading_window.winfo_exists() else overlay
    if result is None or not result.winfo_exists():
        result = _create_prediction_overlay_shell()
    overlay = state.overlay = result
    header = ctk.CTkFrame(result, corner_radius=10)
    header.pack(fill="x", padx=8, pady=(8, 0))
    cards_view = ctk.CTkScrollableFrame(result, corner_radius=10)
    cards_view.pack(fill="both", expand=True, padx=8, pady=8)
    cards_view.grid_columnconfigure((0, 1), weight=1)
    state_data = {"shell": None, "index": 0, "cards": list(payload.get("comparison_cards", []))}

    def alive() -> bool:
        return request_id == _prediction_request_id and result.winfo_exists()

    def set_status(text: str) -> None:
        # Keep the loader copy stable. Reconfiguring a CTk canvas label while
        # cards are being added can leave ghosted, overlapping status text.
        # The indeterminate bar remains the progress signal until reveal.
        del text

    def keep_cover_on_top() -> None:
        # The opaque loader cover and the reflowing CTkScrollableFrame live in
        # the same window. Every time charts/cards are inserted, CTk updates the
        # scroll region and can re-raise its canvas above a cover that was only
        # lifted once. Re-lifting the cover after each build phase guarantees it
        # keeps fully occluding the half-built result until the final reveal.
        cover = _overlay_loading_cover
        if cover is not None and cover.winfo_exists():
            cover.lift()

    def build_header() -> None:
        if not alive(): return
        set_status(_dashboard_model_loading_text(payload))
        score = payload.get("display_value")
        if isinstance(score, (int, float)):
            _bucket_badge(
                header, payload.get("bucket_label"), payload.get("bucket_median"),
                payload.get("bucket_low"), payload.get("bucket_high"), score,
                mode="dataset", category_title=payload.get("category_title"),
                dataset_pred_value=score,
            )
        result.update_idletasks()
        keep_cover_on_top()
        root.after_idle(build_charts)

    def build_charts() -> None:
        if not alive(): return
        set_status("Preparing charts…")
        # Visualizations are anchored in the fixed header, not the scroll body.
        # Many users disable them, so the charts row is only created when at
        # least one chart image is present — no empty gap when viz is off.
        chart_bufs = [
            buf
            for key in ("category_distribution_png", "distribution_png")
            if (buf := _png_bytes(payload.get(key))) is not None
        ]
        if chart_bufs:
            charts_row = ctk.CTkFrame(header, fg_color="transparent")
            charts_row.pack(fill="x", pady=(0, 4))
            for col, buf in enumerate(chart_bufs):
                charts_row.grid_columnconfigure(col, weight=1)
                _scaled_png_percent(charts_row, buf, .98 / len(chart_bufs)).grid(
                    row=0, column=col, sticky="nsew", padx=4, pady=4
                )
        # Model #2 (KNN summary) is also anchored in the header so it can never
        # be reflowed or clipped by comparison cards being inserted below.
        summary = payload.get("price_summary")
        if isinstance(summary, Mapping) and (summary.get("mean") is not None or summary.get("median") is not None):
            _render_nearest_dashboard_banner(header, summary, payload.get("similar_items_summary"))
        keep_cover_on_top()
        root.after_idle(build_card_shell)

    def build_card_shell() -> None:
        if not alive(): return
        set_status("Building comparisons…")
        if state_data["cards"]:
            # cards_view now holds only the scrollable comparison cards; the
            # conversion banner, Model #1, viz, and Model #2 are all anchored in
            # the fixed header above, so the shell starts at row 0.
            shell = ctk.CTkFrame(cards_view, corner_radius=10)
            shell.grid(row=0, column=0, columnspan=2, sticky="nsew")
            shell.columnconfigure((0, 1), weight=1)
            state_data["shell"] = shell
        keep_cover_on_top()
        root.after_idle(build_card_batch)

    def build_card_batch() -> None:
        if not alive(): return
        shell = state_data["shell"]
        cards = state_data["cards"]
        # Render as many cards as fit in a short time budget per idle tick
        # instead of one-per-tick. The opaque cover is up the whole time, so we
        # optimise for total build time while still yielding often enough that
        # the loader's indeterminate progress bar keeps animating.
        if shell is not None:
            deadline = time.perf_counter() + _CARD_BATCH_BUDGET_S
            while state_data["index"] < len(cards):
                idx = state_data["index"]
                _render_prepared_comparison_card(shell, cards[idx], idx)
                state_data["index"] += 1
                if time.perf_counter() >= deadline:
                    break
        # Adding cards grows the scroll region; re-raise the cover on every
        # tick so a mid-build card can never flash above the loader.
        keep_cover_on_top()
        if state_data["index"] < len(cards):
            root.after_idle(build_card_batch)
        else:
            root.after_idle(reveal)

    def reveal() -> None:
        global _overlay_loading, _overlay_loading_cover, _overlay_loading_window, _prediction_loader_windows
        if not alive(): return
        set_status("Finalizing result…")
        # Do the final layout and window resize while the cover is still up and
        # on top, so the geometry change never happens with the result exposed.
        result.update_idletasks()
        keep_cover_on_top()
        # Size/centre against the measured backdrop (handles per-monitor DPI
        # scaling), rather than trusting computed screen coordinates.
        _fit_overlay_over_backdrop(result)
        result.update_idletasks()
        keep_cover_on_top()

        def drop_cover() -> None:
            global _overlay_loading, _overlay_loading_cover, _overlay_loading_window, _prediction_loader_windows
            try:
                if not result.winfo_exists():
                    return
            except tk.TclError:
                return
            # One-window handoff: the completed result is already underneath the
            # opaque loading cover, so removing the cover cannot create a second
            # overlay. Destroy it only after the resize above has settled.
            cover = _overlay_loading_cover
            if cover and cover.winfo_exists(): cover.destroy()
            _overlay_loading_window = None
            _overlay_loading_cover = None
            _prediction_loader_windows = []
            _overlay_loading = False
            try: root.configure(cursor="")
            except Exception: pass
            result.lift()
            _enable_overlay_escape(result)

        root.after_idle(drop_cover)

    root.after_idle(build_header)


_worker_rate_league: str | None = None


def _league_from_disk() -> str:
    """Active league read from the config file, usable in any process.

    The resident worker cannot read the UI's in-memory state, and the config
    is written the moment the setting changes, so disk is the shared source.
    """
    try:
        from poe2trade.app import asset_paths, config_manager
        set_id = str(config_manager.load_config().get("active_model_set") or "").strip()
        meta = asset_paths.model_set_metadata(set_id)
        league = str(meta.get("league") or meta.get("label") or "").strip()
        return league or asset_paths.bundled_set_league()
    except Exception:
        logging.debug("league lookup from disk failed", exc_info=True)
        return ""


def _price_display_mode_from_disk() -> str:
    """The denomination setting, readable from the prediction worker.

    price_display_mode() reads the UI's in-memory state, which the resident
    worker does not have; the payload is built there, so the mode has to come
    off disk like the league does.
    """
    try:
        from poe2trade.app import config_manager
        return str(config_manager.load_config().get("price_display") or "auto").strip().lower()
    except Exception:
        logging.debug("price display lookup from disk failed", exc_info=True)
        return "auto"


def _ensure_conversions_for_league() -> None:
    """Point this process's live rates at the selected league.

    Prediction runs in a resident worker with its own conversion singleton,
    and nothing in that process ever refreshed it. KNN neighbour prices are
    converted to exalt-equivalent through those rates, so without this the
    similar-items prices stay on whichever league the worker booted with even
    though the models beside them switched.
    """
    global _worker_rate_league
    league = _league_from_disk()
    if not league or league == _worker_rate_league:
        return
    try:
        conversion.refresh(league=league)
        _worker_rate_league = league
    except Exception:
        logging.debug("worker rate refresh failed for %s", league, exc_info=True)


def _dashboard_process_entry(text: str, show_viz: bool, result_queue, filters=None, knn_limit=None) -> None:
    """Compute a UI-safe prediction payload in a separate interpreter.

    The process boundary is intentional: this return value is the dashboard
    contract.  It contains ordinary Python values and PNG bytes only; model,
    pandas, Tk, and CustomTkinter objects never cross into the UI process.
    """
    stages = _StageTimings()
    try:
        _ensure_conversions_for_league()
        prepared = prepare_item_features(text)
        stages.stage("parse")
        ml_super: dict = call_super_prepared(prepared) or {}
        model_conversion = None
        if isinstance(ml_super, Mapping):
            model_artifacts = ml_super.get("model_artifacts")
            if isinstance(model_artifacts, Mapping):
                # XGB drives the primary dashboard score; fall back to another
                # model only when XGB was not part of this prediction.
                for model_type in ("xgb", "rf", "gbr"):
                    model_path = model_artifacts.get(model_type)
                    if model_path:
                        model_conversion = conversion.lookup_model_training_snapshot(str(model_path))
                        if model_conversion:
                            break
        # Keep the conversion context visible even when an older model index
        # has no artifact-specific entry. The active runtime snapshot is the
        # safe fallback and preserves the banner across packaged releases.
        if not model_conversion:
            try:
                model_conversion = {
                    "conversions": conversion.snapshot().as_dict(),
                    "is_mock": False,
                    "source": "active-runtime-fallback",
                }
            except Exception:
                model_conversion = None
        cat_norm, seg_norm = _resolve_dashboard_category_segment(
            prepared.model_category or "default_model",
            ml_super.get("segment") if isinstance(ml_super, dict) else prepared.segment,
            prepared.features,
        )
        stages.stage("super")
        try:
            if filters:
                unsuper = (
                    prepared.features,
                    ml_unsuper_utils.call_ml(
                        cat_norm,
                        seg_norm,
                        prepared.features,
                        top=int(knn_limit or 10),
                        where=filters,
                    ),
                )
            else:
                unsuper = call_unsuper_prepared(prepared)
        except FileNotFoundError:
            unsuper = None
        stages.stage("knn")
        (
            display_value, bucket_label, bucket_low, bucket_high, bucket_median,
            _intervals, conf_buf,
        ) = _extract_supervised_values(
            ml_super, cat_norm=cat_norm, seg_norm=seg_norm, build_conf=False
        )
        if not show_viz:
            bucket_median = display_value
            conf_buf = None
        stages.stage("charts")
        unsuper_x, unsuper_df = unsuper if unsuper else (None, None)

        def _plain(value):
            if isinstance(value, (np.generic,)):
                return value.item()
            if isinstance(value, (float,)) and not np.isfinite(value):
                return None
            return value

        def _plain_object(value):
            if isinstance(value, Mapping):
                return {
                    str(key): _plain_object(item)
                    for key, item in value.items()
                    if str(key).lower() not in {"model", "estimator", "pipeline", "shap_model"}
                }
            if isinstance(value, (list, tuple)):
                return [_plain_object(item) for item in value]
            if isinstance(value, (str, int, bool)) or value is None:
                return value
            if isinstance(value, (float, np.generic)):
                return _plain(value)
            return str(value)

        def _records(frame):
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                return []
            return [
                {str(k): _plain(v) for k, v in row.items()}
                for row in frame.to_dict(orient="records")
            ]

        base_record = {}
        display_x = getattr(prepared, "display_features", None)
        base_source = (
            display_x
            if isinstance(display_x, pd.DataFrame) and not display_x.empty
            else unsuper_x
        )
        if isinstance(base_source, pd.DataFrame) and not base_source.empty:
            base_record = {str(k): _plain(v) for k, v in base_source.iloc[0].to_dict().items()}
        item_name = (ml_super.get("item_name") if isinstance(ml_super, dict) else None) or _parse_item(text) or "(Unknown item)"
        knn_snapshot = unsuper_df.attrs.get("training_conversion_snapshot") if isinstance(unsuper_df, pd.DataFrame) else None
        knn_conversion = knn_snapshot if isinstance(knn_snapshot, Mapping) else None
        similar_records = _records(unsuper_df)
        prices = []
        price_labels = []
        for record in similar_records:
            try:
                record_series = pd.Series(record)
                price = (
                    _price_string(record_series, conversions=knn_conversion)
                    if knn_conversion is not None else _price_string(record_series)
                )
                if price:
                    prices.append(float(price[1]))
                # Keep the anchored KNN summary compact; the cards retain the
                # full model-time e/c/d conversion string.
                simple = (
                    f"{float(price[1]):.0f}e"
                    if "price_in_exalts" in record_series or "Price_in_Exalts" in record_series
                    else _price_simple(record_series)
                )
                if simple:
                    price_labels.append(simple)
            except Exception:
                continue
        stages.stage("serialize")
        # Render in the resident prediction worker, alongside the KNN chart.
        # The distribution helper prefers pre-binned profiles and cached PNGs.
        distribution_buf = None
        if show_viz:
            try:
                distribution_buf = _prediction_distribution_buffer(cat_norm, seg_norm, display_value)
            except Exception:
                logging.debug("Category distribution render failed", exc_info=True)
        listing_context_buf = None
        if show_viz and prices:
            try:
                listing_context_buf = generate_prediction_vs_listings_chart(
                    display_value, prices[:10], title="KNN · Similar Item Prices"
                )
            except Exception:
                logging.debug("Comparable listing context render failed", exc_info=True)
        stages.stage("charts")
        comparison_cards = _format_mirror_row_view_models(
            base_record, similar_records, parsed_name := (prepared.raw_parsed.get("Item Name", "(Unknown)") or "(Unknown)"),
            show_defence_mods=str(cat_norm or "").lower() in {"ring", "amulet", "belt"},
            filters=filters,
            price_conversions=knn_conversion,
        )
        stages.stage("cards")
        comparison_icons = _prepare_comparison_icon_pngs(
            [card.your_item_name for card in comparison_cards]
            + [card.matched_item_name for card in comparison_cards]
        )
        for card in comparison_cards:
            card.left_icon_png = comparison_icons.get(card.your_item_name)
            card.right_icon_png = comparison_icons.get(card.matched_item_name)
        stages.stage("icons")
        result_queue.put((
            "ok",
            {
                "raw_parsed": prepared.raw_parsed,
                "model_category": prepared.model_category,
                "segment": prepared.segment,
                "features": {str(k): _plain(v) for k, v in prepared.features.iloc[0].to_dict().items()} if isinstance(prepared.features, pd.DataFrame) and not prepared.features.empty else {},
                "ml_super": _plain_object(ml_super),
                "model_conversion": _plain_object(model_conversion) if model_conversion else None,
                "knn_conversion": _plain_object(knn_conversion) if knn_conversion else None,
                "base_record": base_record,
                "similar_items": similar_records,
                "price_summary": {
                    "mean": float(np.mean(prices)) if prices else None,
                    "median": float(np.median(prices)) if prices else None,
                    "count": len(prices),
                },
                # Keep the nearest listing prices structured for the isolated
                # presenter.  It renders the first ten as compact header chips
                # without reparsing the human-readable summary string.
                "listing_prices": price_labels[:10],
                "similar_items_summary": (
                    f"{len(similar_records)} similar items | prices: {', '.join(price_labels)}"
                    if price_labels else None
                ),
                "comparison_cards": [_plain_comparison_card(card) for card in comparison_cards],
                "item_name": item_name,
                "unsuper_item_name": parsed_name,
                "category_title": (cat_norm or "").replace("_", " ").title(),
                "cat_norm": cat_norm,
                "seg_norm": seg_norm,
                "display_value": display_value,
                # Resolved here because the presenter runs in its own process:
                # without it the overlay rendered exalts whatever the setting
                # said, and format_price was imported but never called.
                "price_display_mode": (
                    _price_display_mode_from_disk()
                    if PREDICTION_PRICE_DISPLAY_ENABLED else "exalted"
                ),
                "bucket_label": bucket_label,
                "bucket_low": bucket_low,
                "bucket_high": bucket_high,
                "bucket_median": bucket_median,
                "conf_png": conf_buf.getvalue() if conf_buf is not None else None,
                "category_distribution_png": (
                    distribution_buf.getvalue() if distribution_buf is not None else None
                ),
                "distribution_png": (
                    listing_context_buf.getvalue()
                    if listing_context_buf is not None
                    else None
                ),
                # Lifted into the worker event's `timings` field and removed
                # before the payload reaches the presenter.
                prediction_worker.STAGE_TIMINGS_KEY: stages.as_dict(),
            },
        ))
    except FileNotFoundError as exc:
        result_queue.put(("missing", str(exc)))
    except Exception as exc:
        result_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _prediction_worker_payload_builder(command: Mapping[str, Any]) -> Mapping[str, Any]:
    """Adapt the established dashboard payload contract for the resident worker."""
    if command.get("kind") == prediction_worker.WARMUP:
        # The worker process is the only one that runs predictions, so this is
        # where the model caches have to live. Warming here is what keeps the
        # first hotkey after launch from paying the sklearn/xgboost import plus
        # a full unpickle of every artifact.
        _ensure_conversions_for_league()
        _warm_model_caches(knn_bundles=True, compact_scoring_jsons=False)
        return {}

    class ResultQueue:
        item = None

        def put(self, value):
            self.item = value

    result_queue = ResultQueue()
    _dashboard_process_entry(
        str(command.get("text") or ""),
        bool(command.get("show_viz", False)),
        result_queue,
        command.get("filters"),
        command.get("knn_limit"),
    )
    status, payload = result_queue.item
    if status == "ok":
        return payload
    if status == "missing":
        raise FileNotFoundError(payload)
    raise RuntimeError(payload)


def _get_prediction_worker() -> prediction_worker.PredictionWorkerManager:
    global _prediction_worker_manager
    if _prediction_worker_manager is None:
        _prediction_worker_manager = prediction_worker.PredictionWorkerManager(
            _prediction_worker_payload_builder,
        )
    return _prediction_worker_manager


def _restart_prediction_worker() -> None:
    """Replace the resident predictor so it picks up the new league.

    Clearing caches in this process does nothing for the worker: it holds its
    own loaded models and its own rate snapshot. The replacement is warmed on
    the Tk loop, so the model reload happens now instead of inside the user's
    next prediction, which otherwise absorbed it.
    """
    try:
        _get_prediction_worker().restart()
    except Exception:
        logging.debug("prediction worker restart failed", exc_info=True)
        return
    _schedule_prediction_worker_rewarm()


def _schedule_prediction_worker_rewarm(delay_ms: int = 400) -> None:
    """Re-warm a recycled worker once the UI has settled.

    Deferred onto the Tk loop so the process spawn never lands on the frame
    that dismisses an overlay. If the user starts a new prediction first, the
    warm simply queues behind it: `warmup()` reuses the running worker, and
    warming an already-warm process is close to free because the model caches
    are mtime-keyed.
    """
    try:
        if root and root.winfo_exists():
            root.after(delay_ms, _prewarm_prediction_worker)
    except Exception:
        logging.debug("Could not schedule prediction worker re-warm", exc_info=True)


def _prewarm_prediction_worker() -> None:
    """Start the resident worker and have it load its model caches.

    `warmup()` starts the process and queues a WARMUP command; the worker runs
    it on its own loop, so this returns immediately and a prediction submitted
    meanwhile simply queues behind the warm.
    """
    try:
        _get_prediction_worker().warmup()
    except Exception:
        logging.debug("Prediction worker prewarm failed", exc_info=True)


def _dashboard_model_payload_in_process(text: str, show_viz: bool, filters=None, knn_limit=None) -> dict:
    """Return a payload from the warm predictor without blocking Tk."""
    worker = _get_prediction_worker()
    request_id = int(time.monotonic_ns())
    worker.submit({
        "request_id": request_id,
        "text": text,
        "show_viz": show_viz,
        "filters": filters,
        "knn_limit": knn_limit,
    })
    while True:
        for event in worker.poll():
            if event.get("request_id") != request_id:
                continue
            if event.get("kind") == "result":
                timings = dict(event.get("timings") or {})
                build_ms = timings.pop("build_ms", None)
                # Costliest stage first, so the bottleneck reads at a glance.
                breakdown = ", ".join(
                    f"{name}={value}ms"
                    for name, value in sorted(
                        timings.items(), key=lambda kv: kv[1], reverse=True
                    )
                )
                logging.info(
                    "Prediction worker completed (request=%s, build_ms=%s)%s",
                    request_id,
                    build_ms,
                    f" {breakdown}" if breakdown else "",
                )
                return event["payload"]
            if event.get("kind") == "error":
                if event.get("category") == "missing":
                    raise FileNotFoundError(event.get("message"))
                raise RuntimeError(event.get("message"))
        if worker.process is None or not worker.process.is_alive():
            raise RuntimeError("Prediction worker exited unexpectedly")
        time.sleep(0.01)


def _score_dashboard_async(text: str, release_lock: threading.Lock | None = None, *, filters=None, knn_limit=None) -> None:
    """
    Run both pipelines (supervised + unsupervised) off the UI thread,
    then hand the finished buffers/data back to the main loop.
    """
    # Claim this request before doing any work.  Every eventual UI callback
    # checks this token, preventing an older worker from reviving an overlay
    # the user closed or replacing a newer prediction.
    global _prediction_request_id, _active_prediction_release_lock
    _prediction_request_id += 1
    request_id = _prediction_request_id
    _active_prediction_release_lock = release_lock
    popup_started = False

    # (a) The presenter owns the whole overlay lifecycle in a separate,
    # DPI-aware process. This keeps the main app's (DPI-unaware) Tk loop free
    # of overlay rendering and preserves smooth cross-monitor dragging.
    try:
        root.configure(cursor="watch")
        popup_started = _launch_prediction_popup(request_id)
        if not popup_started:
            # A packaged/runtime environment may prevent process creation.
            # Preserve a functional in-process overlay as a safe fallback.
            _show_prediction_loading_overlay(request_id)
    except Exception:
        pass

    def work():
        global _active_prediction_release_lock
        timer = _InferenceTimer("dashboard")
        try:
            # Run Python-heavy parsing and both model calls in a separate
            # process. A thread was still able to hold the GIL long enough to
            # freeze the visible loading animation.
            show_viz = _show_viz_enabled(state.config)
            payload = _dashboard_model_payload_in_process(text, show_viz, filters=filters, knn_limit=knn_limit)
            # One mark for the whole worker round-trip: parse, both model
            # calls, charts and serialization all happen inside it. The
            # per-stage split is reported by the worker itself through the
            # result event's `timings` field.
            timer.mark("worker")
            ml_super: dict = payload["ml_super"]

            # Derive category/segment safely here
            # Normalize category using gui_utils to singular internal token
            cat_norm, seg_norm = payload["cat_norm"], payload["seg_norm"]
            display_value = payload["display_value"]
            bucket_label, bucket_low, bucket_high = payload["bucket_label"], payload["bucket_low"], payload["bucket_high"]
            bucket_median_val = payload["bucket_median"]
            timer.mark("display")

            item_name = payload.get("item_name") or "(Unknown item)"

            try:
                log_entry = _build_prediction_log_entry(
                    text=text,
                    ml_super=ml_super if isinstance(ml_super, dict) else {},
                    unsuper_df=pd.DataFrame(payload.get("similar_items", [])),
                    item_name=item_name,
                    category=cat_norm,
                    segment=seg_norm,
                    source="filtered_overlay" if filters else "overlay",
                    filters=filters,
                    knn_limit=knn_limit,
                )
                _append_prediction_log(log_entry)
            except Exception:
                logging.exception("Prediction log append failed")
            timer.mark("log")

            # ---------- UI HANDOFF (Tk main thread only) ----------
            def _show():
                if request_id != _prediction_request_id:
                    return
                if _send_prediction_popup_result(payload, request_id):
                    try:
                        root.configure(cursor="")
                    except Exception:
                        pass
                    return
                # Do not create a second main-process overlay while the warm
                # presenter is still alive. A transient queue/request race is
                # not evidence that the presenter has failed, and falling
                # back here is what produced duplicate popups.
                if (_prediction_popup_process is not None
                        and _prediction_popup_process.is_alive()):
                    logging.warning(
                        "Prediction result handoff deferred: presenter is still alive (request %s)",
                        request_id,
                    )
                    root.after(50, _show)
                    return
                # If the child failed after starting, render locally rather
                # than losing a completed prediction result.
                _show_prediction_loading_overlay(request_id)
                _present_dashboard_staged_v2(payload, request_id)

            root.after(0, _show)
            timer.mark("ui_schedule")

        except FileNotFoundError as exc:
            exc_msg = str(exc) or "Required model assets are missing for this item."
            def _err_missing() -> None:
                if request_id != _prediction_request_id:
                    return
                _destroy_overlay()
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
                if request_id != _prediction_request_id:
                    return
                _destroy_overlay()
                try:
                    root.configure(cursor="")
                except Exception:
                    pass
                messagebox.showerror("StashSage", f"Scoring failed:\n{exc_msg}")

            root.after(0, _err)
        finally:
            timer.finish()
            if release_lock is not None:
                try:
                    release_lock.release()
                except RuntimeError:
                    pass
            if _active_prediction_release_lock is release_lock:
                _active_prediction_release_lock = None

    def launch_work() -> None:
        global _active_prediction_release_lock
        # Let Tk complete at least one paint/animation turn before model code
        # competes for the interpreter. This makes the indeterminate bar
        # visibly start instead of appearing frozen until the result arrives.
        if request_id != _prediction_request_id:
            if release_lock is not None:
                try:
                    release_lock.release()
                except RuntimeError:
                    pass
            if _active_prediction_release_lock is release_lock:
                _active_prediction_release_lock = None
            return
        threading.Thread(target=work, daemon=True).start()

    root.after(90, launch_work)


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


def _handle_hotkey_super(_=None):
    _run_fresh_item_hotkey(
        "super",
        lambda text, lock: _score_dashboard_async(text, release_lock=lock),
    )


def _handle_hotkey_filtered(_=None):
    _run_fresh_item_hotkey(
        "filtered",
        lambda text, lock: _start_filtered_overlay_async(text, release_lock=lock),
    )


def _handle_hotkey_stash_scrape(_=None):
    """Bring the embedded StashScrape workspace to the foreground."""
    try:
        logging.info("Presenter telemetry: stage=ctrl3_stashscrape_requested route=main_workspace")
        _show_stash_scrape_viewer()
    except Exception:
        logging.exception("StashScrape hotkey failed")


def _show_craft_potential_warning(text: str, lock: threading.Lock) -> None:
    """Use the isolated presenter for the hotkey; report a failure instead of hanging."""
    logging.info("Presenter telemetry: stage=ctrl4_craft_requested route=presenter_test")
    if not _launch_craft_potential_popup(text, lock):
        logging.warning("Presenter telemetry: stage=ctrl4_craft_failed route=none")
        try:
            if root is not None and root.winfo_exists():
                root.after(
                    0,
                    lambda: messagebox.showerror(
                        "CraftOracle",
                        "CraftOracle could not start. Try again, or restart the app if this keeps happening.",
                    ),
                )
        finally:
            try:
                lock.release()
            except RuntimeError:
                pass


def _handle_hotkey_craft_potential(_=None):
    _run_fresh_item_hotkey("craft_potential", _show_craft_potential_warning)


def _handle_hotkey_prediction_log(_=None):
    root.after(
        0,
        lambda: _run_with_lock(
            _hotkey_busy["prediction_log"], _show_prediction_log_popup
        ),
    )


def _load_validation_sample_items() -> list[str]:
    """Return uncommented item blocks from the bundled validation fixture."""
    items_path = asset_paths.resolve_asset_file("files", "sample_items.txt")
    raw = items_path.read_text(encoding="utf-8")
    uncommented = re.sub(r"(?m)^\s*#.*$", "", raw)
    return [block.strip() for block in uncommented.split("$$$$") if block.strip()]


def _validation_sample_label(item: str, index: int) -> str:
    """Build a useful, stable picker label from a copied-item text block."""
    lines = [line.strip() for line in item.splitlines() if line.strip()]
    item_class = next(
        (line.partition(":")[2].strip() for line in lines if line.lower().startswith("item class:")),
        "Unknown class",
    )
    rarity_index = next((i for i, line in enumerate(lines) if line.lower().startswith("rarity:")), -1)
    names: list[str] = []
    if rarity_index >= 0:
        for line in lines[rarity_index + 1:]:
            if line.startswith("--------"):
                break
            names.append(line)
    display_name = " — ".join(names[:2]) or f"Sample {index + 1}"
    return f"{index + 1:02d}. {display_name}  [{item_class}]"


def _show_validation_sample_picker(items: list[str], lock: threading.Lock) -> None:
    """Let the user choose a bundled validation item before scoring it."""
    popup = ctk.CTkToplevel(root)
    popup.title("Run validation sample")
    popup.geometry("680x480")
    popup.minsize(480, 320)
    _apply_window_icon(popup)
    try:
        popup.transient(root)
        popup.attributes("-topmost", True)
        popup.lift()
        popup.focus_force()
    except Exception:
        pass

    frame = ctk.CTkFrame(popup)
    frame.pack(fill="both", expand=True, padx=12, pady=12)
    ctk.CTkLabel(
        frame,
        text=(
            "Developer / validation tool (Ctrl+0) - not a normal feature. Runs a "
            "bundled sample item through the parser and scoring dashboard."
        ),
        anchor="w",
        justify="left",
        wraplength=620,
        text_color="#E0A53B",
    ).pack(fill="x", padx=8, pady=(8, 6))
    search = ctk.CTkEntry(frame, placeholder_text="Filter by item name, base, or class…")
    search.pack(fill="x", padx=8, pady=(0, 8))
    listbox = tk.Listbox(frame, activestyle="dotbox", exportselection=False, font=("Segoe UI", 11))
    listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    labels = [_validation_sample_label(item, index) for index, item in enumerate(items)]
    visible_indices: list[int] = []

    def refresh(*_args) -> None:
        query = search.get().strip().lower()
        visible_indices.clear()
        listbox.delete(0, "end")
        for index, label in enumerate(labels):
            if not query or query in label.lower() or query in items[index].lower():
                visible_indices.append(index)
                listbox.insert("end", label)
        if visible_indices:
            listbox.selection_set(0)
            listbox.activate(0)

    closed = False

    def close(*_args) -> None:
        nonlocal closed
        if closed:
            return
        closed = True
        try:
            popup.destroy()
        finally:
            if lock.locked():
                lock.release()

    def run_selected(*_args) -> None:
        nonlocal closed
        selection = listbox.curselection()
        if not selection or not visible_indices:
            return
        item = items[visible_indices[int(selection[0])]]
        closed = True
        popup.destroy()
        _score_dashboard_async(item, release_lock=lock)

    buttons = ctk.CTkFrame(frame, fg_color="transparent")
    buttons.pack(fill="x", padx=8, pady=(0, 8))
    ctk.CTkButton(buttons, text="Run selected", command=run_selected).pack(side="right", padx=(6, 0))
    ctk.CTkButton(buttons, text="Cancel", command=close, fg_color="transparent", border_width=1).pack(side="right")
    search.bind("<KeyRelease>", refresh)
    search.bind("<Down>", lambda _event: (listbox.focus_set(), "break")[1])
    listbox.bind("<Double-Button-1>", run_selected)
    listbox.bind("<Return>", run_selected)
    popup.bind("<Escape>", close)
    popup.protocol("WM_DELETE_WINDOW", close)
    refresh()
    search.focus_set()


def _handle_hotkey_sample_picker(_=None):
    lock = _hotkey_busy["sample"]
    if not lock.acquire(blocking=False):
        return
    try:
        items = _load_validation_sample_items()
    except Exception:
        logging.exception("Could not load validation sample items")
        lock.release()
        return
    if not items:
        lock.release()
        return
    root.after(0, lambda: _show_validation_sample_picker(items, lock))


_MOD_BLOCK_HEADER_RE = re.compile(r"^\{\s*(?P<kind>.*?)\bModifier\b.*\}$")


def _strip_random_explicit_mod(
    text: str, rng: "random.Random | None" = None
) -> "tuple[str, str] | None":
    """Remove one random removable explicit modifier block from advanced item text.

    Returns ``(modified_text, dropped_description)`` or ``None`` when the item
    has no plain (non-implicit, non-fractured, non-desecrated, non-enchant)
    prefix/suffix modifier that could be removed.
    """
    picker = rng or random
    lines = text.splitlines()
    blocks: list[tuple[int, int, str, str]] = []
    i = 0
    while i < len(lines):
        match = _MOD_BLOCK_HEADER_RE.match(lines[i].strip())
        if not match:
            i += 1
            continue
        kind = match.group("kind").strip().lower()
        end = i + 1
        stats: list[str] = []
        while end < len(lines):
            stat_line = lines[end].strip()
            if not stat_line or stat_line.startswith("{") or stat_line.startswith("---"):
                break
            stats.append(stat_line)
            end += 1
        blocks.append((i, end, kind, " / ".join(stats)))
        i = end
    removable = [
        block for block in blocks
        if ("prefix" in block[2] or "suffix" in block[2])
        and not any(tag in block[2] for tag in ("implicit", "fractured", "desecrated", "enchant"))
    ]
    if not removable:
        return None
    start, end, kind, stat = picker.choice(removable)
    modified = "\n".join(lines[:start] + lines[end:])
    return modified, (stat or f"{kind} modifier".strip())


def _build_craft_sample_candidates() -> list[dict]:
    """Sample items seeded for a CraftOracle validation run (one mod removed).

    Reuses the Ctrl+0 sample set; keeps only rare, uncorrupted items that still
    have a removable explicit modifier, and pre-strips a random one so the
    picker label matches exactly what CraftOracle will analyze.
    """
    candidates: list[dict] = []
    for index, item in enumerate(_load_validation_sample_items()):
        if not re.search(r"(?mi)^Rarity:\s*Rare\s*$", item):
            continue
        if re.search(r"(?mi)^Corrupted\s*$", item):
            continue
        stripped = _strip_random_explicit_mod(item)
        if stripped is None:
            continue
        modified_text, dropped = stripped
        base_label = _validation_sample_label(item, index)
        candidates.append(
            {
                "label": f"{base_label}  —  drop: {dropped}",
                "text": modified_text,
                "dropped": dropped,
            }
        )
    return candidates


def _show_craft_sample_picker(candidates: list[dict]) -> None:
    """Dev picker: run CraftOracle on a known item with one explicit mod removed."""
    popup = ctk.CTkToplevel(root)
    popup.title("CraftOracle validation sample")
    popup.geometry("760x520")
    popup.minsize(520, 340)
    _apply_window_icon(popup)
    try:
        popup.transient(root)
        popup.attributes("-topmost", True)
        popup.lift()
        popup.focus_force()
    except Exception:
        pass

    frame = ctk.CTkFrame(popup)
    frame.pack(fill="both", expand=True, padx=12, pady=12)
    ctk.CTkLabel(
        frame,
        text=(
            "Developer / validation tool (Ctrl+Shift+0) - not a normal feature. "
            "Drops one explicit modifier from a known sample item and runs "
            "CraftOracle on the rest, so you can check whether re-adding a "
            "similar modifier ranks near the top."
        ),
        anchor="w",
        justify="left",
        wraplength=700,
        text_color="#E0A53B",
    ).pack(fill="x", padx=8, pady=(8, 6))

    search = ctk.CTkEntry(frame, placeholder_text="Filter by item name, base, class, or dropped mod…")
    search.pack(fill="x", padx=8, pady=(0, 8))
    listbox = tk.Listbox(frame, activestyle="dotbox", exportselection=False, font=("Segoe UI", 11))
    listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    state_box = {"rows": list(candidates)}
    visible_indices: list[int] = []
    status = ctk.CTkLabel(frame, text="", anchor="w", justify="left", text_color="#9AA7B4")
    status.pack(fill="x", padx=8, pady=(0, 6))

    def refresh(*_args) -> None:
        query = search.get().strip().lower()
        rows = state_box["rows"]
        visible_indices.clear()
        listbox.delete(0, "end")
        for index, row in enumerate(rows):
            if not query or query in row["label"].lower() or query in row["text"].lower():
                visible_indices.append(index)
                listbox.insert("end", row["label"])
        if visible_indices:
            listbox.selection_set(0)
            listbox.activate(0)

    def reroll(*_args) -> None:
        state_box["rows"] = _build_craft_sample_candidates()
        refresh()
        status.configure(text="Re-rolled the dropped modifier for every item.")

    def run_selected(*_args) -> None:
        selection = listbox.curselection()
        if not selection or not visible_indices:
            return
        row = state_box["rows"][visible_indices[int(selection[0])]]
        lock = _hotkey_busy["craft_potential"]
        if not lock.acquire(blocking=False):
            status.configure(text="CraftOracle is already running - wait for it to finish.")
            return
        status.configure(text=f"Running CraftOracle. Dropped: {row['dropped']}")
        _show_craft_potential_warning(row["text"], lock)

    buttons = ctk.CTkFrame(frame, fg_color="transparent")
    buttons.pack(fill="x", padx=8, pady=(0, 8))
    ctk.CTkButton(buttons, text="Run selected", command=run_selected).pack(side="right", padx=(6, 0))
    ctk.CTkButton(buttons, text="Re-roll drops", command=reroll, fg_color="#33414E", hover_color="#3F5160").pack(side="right", padx=(6, 0))
    ctk.CTkButton(buttons, text="Close", command=popup.destroy, fg_color="transparent", border_width=1).pack(side="right")
    search.bind("<KeyRelease>", refresh)
    search.bind("<Down>", lambda _event: (listbox.focus_set(), "break")[1])
    listbox.bind("<Double-Button-1>", run_selected)
    listbox.bind("<Return>", run_selected)
    popup.bind("<Escape>", lambda _event: popup.destroy())
    refresh()
    search.focus_set()


def _handle_hotkey_craft_sample(_=None):
    # The lock only debounces the hotkey itself; the picker then runs
    # independently and each "Run selected" guards on the craft_potential lock.
    lock = _hotkey_busy["craft_sample"]
    if not lock.acquire(blocking=False):
        return
    try:
        candidates = _build_craft_sample_candidates()
    except Exception:
        logging.exception("Could not build CraftOracle validation samples")
        return
    finally:
        lock.release()
    if not candidates:
        root.after(0, lambda: messagebox.showinfo(
            "CraftOracle validation",
            "No bundled sample item is a rare with a removable explicit modifier.",
        ))
        return
    root.after(0, lambda: _show_craft_sample_picker(candidates))



# ------------- GUI widgets & helpers (unchanged) ---------
def _browse_for_prediction_log(entry: ctk.CTkEntry) -> None:
    raw = entry.get().strip()
    fallback = str(config_manager.DEFAULT_CONFIG.get("prediction_log_dir", "") or "")
    candidate = Path(raw or fallback)
    opts = {
        "title": "Select prediction log file",
        "defaultextension": ".json",
        "filetypes": [("JSON files", "*.json"), ("All files", "*.*")],
    }
    if candidate:
        if candidate.suffix:
            opts["initialdir"] = str(candidate.parent)
            opts["initialfile"] = candidate.name
        else:
            opts["initialdir"] = str(candidate)
            opts["initialfile"] = "prediction_log.json"
    fpath = filedialog.asksaveasfilename(**opts)
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
            font=_FONT_SECTION_TITLE,
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

# Both live in gui.ui_helpers now so the presenter process can use them too.
_HoverTip = HoverTip
_help_bubble = help_badge


def _entry(
    parent, label, default="", digits_only=False, allow_float=False, help_text=""
) -> ctk.CTkEntry:
    if help_text:
        label_row = ctk.CTkFrame(parent, fg_color="transparent")
        label_row.pack(anchor="w", fill="x", padx=10, pady=(10, 2))
        ctk.CTkLabel(label_row, text=label, font=_FONT_BODY).pack(side="left")
        help_badge = ctk.CTkLabel(
            label_row,
            text="?",
            font=("Segoe UI", 10, "bold"),
            text_color="#0B0E11",
            fg_color="#6E7F8D",
            corner_radius=9,
            width=18,
            height=18,
        )
        help_badge.pack(side="left", padx=(6, 0))
        _HoverTip(help_badge, help_text)
    else:
        ctk.CTkLabel(parent, text=label, font=_FONT_BODY).pack(anchor="w", padx=10, pady=(10, 2))
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

    e = ctk.CTkEntry(parent, corner_radius=6, font=_FONT_BODY)
    vcmd = parent.register(_check)
    e.configure(validate="key", validatecommand=(vcmd, "%P"))
    e.pack(fill="x", padx=10, pady=2, expand=True)
    e.insert(0, default)
    return e


def _file_row(parent, label, default="") -> tuple[ctk.CTkEntry, ctk.CTkButton]:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=10, pady=(10, 2))
    ctk.CTkLabel(frame, text=label, font=_FONT_BODY).pack(anchor="w")
    inner = ctk.CTkFrame(frame, fg_color="transparent")
    inner.pack(fill="x")
    entry = ctk.CTkEntry(inner, corner_radius=6, font=_FONT_BODY)
    entry.pack(side="left", fill="x", expand=True, pady=2)
    btn = ctk.CTkButton(
        inner, text="Browse...", width=90, font=_FONT_BODY, command=lambda e=entry: _browse_for_prediction_log(e)
    )
    btn.pack(side="left", padx=6, pady=2)
    entry.insert(0, default)
    return entry, btn


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
    pf_max_raw = (max_price_filter_entry.get().strip() if max_price_filter_entry else "") or str(DEFAULT_MAX_PRICE_FILTER)
    if not PRICE_FILTER_RE.fullmatch(pf_max_raw):
        messagebox.showerror(
            "Invalid Max Price Filter",
            "Must be a number followed by E, C, or D (e.g. 100d, 500e, 200c)",
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
    state.config.update(
        auction_hotkey=_entry_or_config(auction_hotkey_entry, "auction_hotkey"),
        auction_cut_rule=_entry_or_config(auction_rule_entry, "auction_cut_rule"),
        copy_hotkey=(
            _entry_or_config(copy_hotkey_entry, "copy_hotkey")
            or DEFAULT_COPY_HOTKEY
        ),
        prediction_log_dir=_entry_or_config(prediction_log_entry, "prediction_log_dir"),
        price_mirror_filter=pf_raw,
        price_mirror_max_filter=pf_max_raw,
        knn_filtered_k=knn_filtered_val,
    )
    for entry, key, binder in (
        (custom_hotkey_entry, "custom_hotkey", _bind_overlay_hotkey),
        (filtered_hotkey_entry, "filtered_overlay_hotkey", _bind_filtered_overlay_hotkey),
        (stash_scrape_hotkey_entry, "stash_scrape_hotkey", _bind_stash_scrape_hotkey),
        (craft_potential_hotkey_entry, "craft_potential_hotkey", _bind_craft_potential_hotkey),
    ):
        if not _commit_action_hotkey(entry, key, binder):
            return
    _apply_price_filter(state.config)
    _apply_max_price_filter(state.config)
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
    _bind_price_hotkeys()
    _auto_resize_root()
    messagebox.showinfo(
        "StashSage",
        "Settings updated and reloaded successfully.",
        parent=root if root else None,
    )


# ????????????? main Tk entry-point ???????????????????????
def run_tkinter_app(cfg: Optional[dict] = None) -> None:
    """Launch the CustomTkinter settings window."""
    global root
    global prediction_log_entry, prediction_log_browse_btn
    global price_filter_entry, max_price_filter_entry, knn_filtered_k_entry, copy_hotkey_entry, close_behavior_var, filtered_hotkey_entry
    global custom_hotkey_entry, craft_potential_hotkey_entry, stash_scrape_hotkey_entry
    global _settings_view
    global _exit_watchdog_enabled

    state.update_config(cfg or {})
    _apply_price_filter(state.config)
    _apply_max_price_filter(state.config)

    # ?? NEW: preload the icon lookup once at startup
    try:
        load_base_image_map(str(asset_paths.resolve_asset_file("files", "base_images.json")))
        logging.info("base_images.json loaded (%d entries)", len(state.base_image_map))
    except Exception as exc:
        logging.warning("Could not load base_images.json: %s", exc)

    _configure_default_widget_fonts()
    root = ctk.CTk()
    state.root = root
    root.title(f"StashSage for POE2 (v{__version__} -- {BUILD_DATE})")
    _set_screen_aware_geometry(
        root,
        DEFAULT_WINDOW_WIDTH,
        DEFAULT_WINDOW_HEIGHT,
        MIN_WINDOW_WIDTH,
        MIN_WINDOW_HEIGHT,
    )
    _apply_window_icon(root)
    # Also set a default iconphoto to propagate to child windows where supported
    try:
        png_path = Path(poe2trade_root) / "docs" / "stashsage_logo.png"
        if png_path.is_file():
            _img = tk.PhotoImage(file=str(png_path))
            root.iconphoto(True, _img)
            root._icon_img = _img  # keep a reference
    except Exception:
        pass
    root.protocol("WM_DELETE_WINDOW", _on_root_close)

    for key, binder in (
        ("custom_hotkey", _bind_overlay_hotkey),
        ("filtered_overlay_hotkey", _bind_filtered_overlay_hotkey),
        ("stash_scrape_hotkey", _bind_stash_scrape_hotkey),
        ("craft_potential_hotkey", _bind_craft_potential_hotkey),
    ):
        try:
            binder(state.config.get(key))
        except Exception as exc:
            logging.exception("Stored shortcut %s could not be activated", key)
            messagebox.showerror("Shortcut unavailable", f"{key}: {exc}", parent=root)
    _bind_dev_sample_hotkeys()

    def _set_entry(entry_obj, value: str) -> None:
        if entry_obj is None:
            return
        entry_obj.delete(0, "end")
        entry_obj.insert(0, value)

    def _reset_settings_defaults() -> None:
        defaults = config_manager.DEFAULT_CONFIG
        _set_entry(copy_hotkey_entry, defaults.get("copy_hotkey", DEFAULT_COPY_HOTKEY))
        _set_entry(custom_hotkey_entry, defaults.get("custom_hotkey", ""))
        _set_entry(
            filtered_hotkey_entry,
            defaults.get("filtered_overlay_hotkey", DEFAULT_FILTERED_OVERLAY_HOTKEY),
        )
        _set_entry(
            stash_scrape_hotkey_entry,
            defaults.get("stash_scrape_hotkey", DEFAULT_STASH_SCRAPE_HOTKEY),
        )
        _set_entry(
            craft_potential_hotkey_entry,
            defaults.get("craft_potential_hotkey", DEFAULT_CRAFT_POTENTIAL_HOTKEY),
        )
        if close_behavior_var is not None:
            close_behavior_var.set(
                "Exit application" if _close_behavior(defaults) == "exit" else "Minimize to tray"
            )
        _set_entry(
            knn_filtered_k_entry,
            str(defaults.get("knn_filtered_k", DEFAULT_KNN)),
        )
        _set_entry(
            price_filter_entry,
            str(defaults.get("price_mirror_filter", DEFAULT_PRICE_FILTER)),
        )
        _set_entry(
            max_price_filter_entry,
            str(defaults.get("price_mirror_max_filter", DEFAULT_MAX_PRICE_FILTER)),
        )
        _set_entry(prediction_log_entry, defaults.get("prediction_log_dir", ""))
        # With no Save button, reset must also persist and apply the defaults it
        # just placed into the widgets.
        try:
            if not _reset_action_hotkeys((
                (custom_hotkey_entry, "custom_hotkey", _bind_overlay_hotkey),
                (filtered_hotkey_entry, "filtered_overlay_hotkey", _bind_filtered_overlay_hotkey),
                (stash_scrape_hotkey_entry, "stash_scrape_hotkey", _bind_stash_scrape_hotkey),
                (craft_potential_hotkey_entry, "craft_potential_hotkey", _bind_craft_potential_hotkey),
            )):
                _refresh_hotkey_summary()
                return
            _commit_all_fields()
        except Exception:
            logging.exception("Applying reset defaults failed")

    workspace = _build_app_shell(root)
    main_content = ctk.CTkScrollableFrame(workspace, fg_color="transparent")
    _settings_view = main_content
    _workspace_views["home"] = main_content
    main_content.grid(row=0, column=0, sticky="nsew")
    _show_settings_view()

    header_frame = ctk.CTkFrame(main_content, corner_radius=10, fg_color="#202A33")
    header_frame.pack(fill="x", padx=10, pady=(10, 2))
    header_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        header_frame,
        text="Settings",
        font=_FONT_PAGE_TITLE,
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
    def _hotkey_summary_text() -> str:
        return (
            f"Copy: {(state.config.get('copy_hotkey') or DEFAULT_COPY_HOTKEY)}"
            f" | Overlay: {_action_hotkey_label('_overlay_hotkey_handle')}"
            f" | Filtered: {_action_hotkey_label('_filtered_overlay_hotkey_handle')}"
            f" | StashScrape: {_action_hotkey_label('_stash_scrape_hotkey_handle')}"
            f" | Craft: {_action_hotkey_label('_craft_potential_hotkey_handle')}"
        )

    hotkey_summary_label = ctk.CTkLabel(
        header_frame,
        text=_hotkey_summary_text(),
        text_color="#C8D2DC",
        font=_FONT_MONO,
        anchor="w",
    )
    hotkey_summary_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

    ctk.CTkButton(
        header_frame,
        text="Update Version",
        command=_check_for_updates_clicked,
        corner_radius=8,
        width=140,
    ).grid(row=0, column=1, rowspan=2, sticky="e", padx=12, pady=10)

    def _refresh_hotkey_summary() -> None:
        try:
            hotkey_summary_label.configure(text=_hotkey_summary_text())
        except Exception:
            logging.debug("hotkey summary refresh failed", exc_info=True)

    # Settings persist per-field as they change (see the live-commit wiring
    # below), so there is no global Save button — only version update here.
    ctk.CTkLabel(
        main_content,
        text="Settings save automatically — text fields apply on Enter or when you click away.",
        text_color="#9AA7B4",
        font=_FONT_HELPER,
        anchor="w",
    ).pack(fill="x", padx=12, pady=(0, 4))
    _currency_conversion_banner(main_content)

    # Grouped so the League sits first: it selects which models price every
    # item and which league's rates convert them, so it is the setting most
    # likely to be reached for, and it was previously buried under five hotkey
    # fields. Hotkeys and app plumbing are set once, so they start collapsed.
    league_section = _CollapsibleSection(
        main_content, "League", collapsed=False, on_toggle=_auto_resize_root
    )
    league_section.pack(fill="x", expand=False)

    ctk.CTkLabel(
        league_section.content,
        text="League",
        font=_FONT_BODY,
    ).pack(anchor="w", padx=10, pady=(12, 2))
    model_set_var = tk.StringVar(value=_model_set_label(active_model_set()))
    state.model_set_var = model_set_var
    model_set_menu = ctk.CTkOptionMenu(
        league_section.content,
        values=_model_set_options(),
        variable=model_set_var,
        command=_persist_model_set,
    )
    model_set_menu.pack(anchor="w", padx=10)
    state.model_set_menu = model_set_menu
    ctk.CTkLabel(
        league_section.content,
        text="Which league's models price your items. Each league carries the "
             "currency rates it was trained with, so switching changes both the "
             "predictions and how they convert.",
        text_color="#AAAAAA",
        font=_FONT_HELPER,
        wraplength=520,
        justify="left",
    ).pack(anchor="w", padx=10, pady=(2, 6))

    prediction_section = _CollapsibleSection(
        main_content, "Predictions & Prices", collapsed=False, on_toggle=_auto_resize_root
    )
    prediction_section.pack(fill="x", expand=False)

    if PREDICTION_PRICE_DISPLAY_ENABLED:
        ctk.CTkLabel(
            prediction_section.content,
            text="Prediction Price Display",
            font=_FONT_BODY,
        ).pack(anchor="w", padx=10, pady=(12, 2))
        price_display_var = tk.StringVar(
            value=_PRICE_DISPLAY_VALUES.get(price_display_mode(), "Auto")
        )
        state.price_display_var = price_display_var
        ctk.CTkSegmentedButton(
            prediction_section.content,
            values=["Auto", "Exalts", "Divines", "Chaos"],
            variable=price_display_var,
            command=_persist_price_display,
        ).pack(anchor="w", padx=10)
        ctk.CTkLabel(
            prediction_section.content,
            text="Auto shows exalts until they get unwieldy, then divines. Display only — "
                 "predictions and saved data are unchanged.",
            text_color="#AAAAAA",
            font=_FONT_HELPER,
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 6))


    knn_filtered_k_entry = _entry(
        prediction_section.content,
        "Number of Similar Items Returned",
        str(state.config.get("knn_filtered_k", config_manager.DEFAULT_CONFIG.get("knn_filtered_k", DEFAULT_KNN))),
        digits_only=True,
        help_text="Sets how many similar items the KNN comparison returns.",
    )
    state.knn_filtered_k_entry = knn_filtered_k_entry

    price_filter_entry = _entry(
        prediction_section.content,
        "Nearest Items Min Price Filter (e.g. 40e, 1d, 20c, 10a)",
        str(state.config.get("price_mirror_filter", DEFAULT_PRICE_FILTER)),
        allow_float=True,
        help_text=(
            "Lower price bound for the items KNN compares against - screens out "
            "underpriced dataset listings so they do not drag the estimate down."
        ),
    )
    state.price_filter_entry = price_filter_entry

    max_price_filter_entry = _entry(
        prediction_section.content,
        "Nearest Items Max Price Filter (e.g. 100d, 500e, 200c)",
        str(state.config.get("price_mirror_max_filter", DEFAULT_MAX_PRICE_FILTER)),
        allow_float=True,
        help_text=(
            "Upper price bound for the items KNN compares against - screens out "
            "overpriced dataset outliers so they do not inflate the estimate."
        ),
    )
    state.max_price_filter_entry = max_price_filter_entry

    hotkeys_section = _CollapsibleSection(
        main_content, "Hotkeys", collapsed=True, on_toggle=_auto_resize_root
    )
    hotkeys_section.pack(fill="x", expand=False)

    ctk.CTkLabel(
        hotkeys_section.content,
        text=(
            "Blank uses the default; off disables an action shortcut. "
            "On Windows, digits use the main keyboard; use num1 (e.g. ctrl+num1) "
            "for the keypad. Modifiers must match exactly. "
            "Shortcuts pause while you edit these fields."
        ),
        text_color="#9AA7B4",
        font=_FONT_HELPER,
        justify="left",
        anchor="w",
        wraplength=680,
    ).pack(fill="x", padx=10, pady=(10, 2))

    copy_hotkey_entry = _entry(
        hotkeys_section.content,
        "Native Copy Hotkey (default: ctrl+c; e.g. ctrl+shift+c)",
        (state.config.get("copy_hotkey", DEFAULT_COPY_HOTKEY) or DEFAULT_COPY_HOTKEY).strip(),
        help_text=(
            "Path of Exile's in-game 'copy item to clipboard' keybind. "
            "StashSage uses it to read a hovered item in-game - by default set "
            "to ctrl+c, some operating systems may differ. Set to your "
            "specific keybind."
        ),
    )
    state.copy_hotkey_entry = copy_hotkey_entry

    custom_hotkey_entry = _entry(
        hotkeys_section.content,
        "Overlay Hotkey (e.g. ctrl+1)",
        state.config.get("custom_hotkey", "").strip(),
        help_text=(
            "Hover an item in-game and press this to open the price estimate. "
            "It is scored by two independent models: XGBoost (XGB), which uses "
            "the entire category dataset to determine the incremental value of "
            "each modifier, and k-nearest-neighbors (KNN), which compares "
            "against only the items in the dataset most similar to yours (uses "
            "'Number of Similar Items Returned' below)."
        ),
    )
    state.custom_hotkey_entry = custom_hotkey_entry

    filtered_hotkey_entry = _entry(
        hotkeys_section.content,
        "Filtered Overlay Hotkey (e.g. ctrl+2)",
        (state.config.get("filtered_overlay_hotkey", "") or "").strip()
        or DEFAULT_FILTERED_OVERLAY_HOTKEY,
        help_text=(
            "Same as the Overlay Hotkey, but lets you pin specific mods or "
            "values as fixed requirements so the KNN comparison controls for "
            "those while the rest stay variable. Also uses 'Number of Similar "
            "Items Returned' below. XGB unaffected."
        ),
    )
    state.filtered_hotkey_entry = filtered_hotkey_entry

    stash_scrape_hotkey_entry = _entry(
        hotkeys_section.content,
        "StashScrape Hotkey (e.g. ctrl+3)",
        (state.config.get("stash_scrape_hotkey", "") or "").strip()
        or DEFAULT_STASH_SCRAPE_HOTKEY,
        help_text=(
            "Brings the StashScrape workspace to the front - the tool for "
            "scraping and pricing a whole stash tab at once."
        ),
    )
    state.stash_scrape_hotkey_entry = stash_scrape_hotkey_entry

    craft_potential_hotkey_entry = _entry(
        hotkeys_section.content,
        "CraftOracle Hotkey (e.g. ctrl+4)",
        (state.config.get("craft_potential_hotkey", "") or "").strip()
        or DEFAULT_CRAFT_POTENTIAL_HOTKEY,
        help_text=(
            "Hover an item in-game with an open explicit affix slot and press "
            "this to run CraftOracle. For each modifier the item could still "
            "gain, it adds that mod at the highest eligible roll observed in "
            "the dataset and reports how far the "
            "XGB model's predicted price moves - a ranked view of where the "
            "crafting upside is. It is a model what-if, not a crafting "
            "simulator: no currency costs or odds. This evaluates every "
            "missing explicit modifier at its highest intrinsic catalog roll "
            "and re-predicts the item for each one, but it runs quickly."
        ),
    )
    state.craft_potential_hotkey_entry = craft_potential_hotkey_entry

    app_section = _CollapsibleSection(
        main_content, "Application", collapsed=True, on_toggle=_auto_resize_root
    )
    app_section.pack(fill="x", expand=False)

    ctk.CTkLabel(
        app_section.content,
        text="Window Close Behavior",
        font=_FONT_BODY,
    ).pack(anchor="w", padx=10, pady=(12, 2))
    close_behavior_var = tk.StringVar(
        value="Exit application" if _close_behavior(state.config) == "exit" else "Minimize to tray"
    )
    state.close_behavior_var = close_behavior_var
    ctk.CTkSegmentedButton(
        app_section.content,
        values=["Minimize to tray", "Exit application"],
        variable=close_behavior_var,
        command=_persist_close_behavior,
    ).pack(anchor="w", padx=10)
    ctk.CTkLabel(
        app_section.content,
        text="Tray mode keeps price-check hotkeys available.",
        text_color="#AAAAAA",
        font=_FONT_HELPER,
    ).pack(anchor="w", padx=10, pady=(2, 6))

    prediction_log_entry, prediction_log_browse_btn = _file_row(
        app_section.content,
        "Prediction Log File",
        state.config.get("prediction_log_dir", "") or "",
    )
    state.prediction_log_entry = prediction_log_entry
    state.prediction_log_browse_btn = prediction_log_browse_btn










    # ---- live per-field persistence (replaces the old Save & Reload button) --
    # Toggles/segmented controls save immediately; validated text fields commit
    # on Enter or focus-out and revert to the last good value when invalid.
    def _revert_entry(entry_obj, value: str) -> None:
        if entry_obj is None:
            return
        entry_obj.delete(0, "end")
        entry_obj.insert(0, value)

    def _commit_price_filter() -> bool:
        if price_filter_entry is None:
            return True
        raw = price_filter_entry.get().strip() or str(DEFAULT_PRICE_FILTER)
        if not PRICE_FILTER_RE.fullmatch(raw):
            messagebox.showerror(
                "Invalid Price Filter",
                "Must be a number followed by E, C, or D (e.g. 100e, 50c, 10D)",
                parent=root if root else None,
            )
            _revert_entry(price_filter_entry, str(state.config.get("price_mirror_filter", DEFAULT_PRICE_FILTER)))
            return False
        _revert_entry(price_filter_entry, raw)
        state.config["price_mirror_filter"] = raw
        _apply_price_filter(state.config)
        return _persist_settings_to_disk("price filter")

    def _commit_max_price_filter() -> bool:
        if max_price_filter_entry is None:
            return True
        raw = max_price_filter_entry.get().strip() or str(DEFAULT_MAX_PRICE_FILTER)
        if not PRICE_FILTER_RE.fullmatch(raw):
            messagebox.showerror(
                "Invalid Max Price Filter",
                "Must be a number followed by E, C, or D (e.g. 100d, 500e, 200c)",
                parent=root if root else None,
            )
            _revert_entry(max_price_filter_entry, str(state.config.get("price_mirror_max_filter", DEFAULT_MAX_PRICE_FILTER)))
            return False
        _revert_entry(max_price_filter_entry, raw)
        state.config["price_mirror_max_filter"] = raw
        _apply_max_price_filter(state.config)
        return _persist_settings_to_disk("max price filter")

    def _commit_knn_filtered_k() -> bool:
        if knn_filtered_k_entry is None:
            return True
        raw = knn_filtered_k_entry.get().strip()
        if not raw:
            val = _resolve_knn_filtered_k(config_manager.DEFAULT_CONFIG)
        elif not raw.isdigit() or int(raw) <= 0:
            messagebox.showerror(
                "Invalid Filtered KNN Count",
                "Filtered KNN count must be a whole number of at least 1 (e.g. 3, 10).",
                parent=root if root else None,
            )
            _revert_entry(knn_filtered_k_entry, str(state.config.get("knn_filtered_k", DEFAULT_KNN)))
            return False
        else:
            val = int(raw)
        _revert_entry(knn_filtered_k_entry, str(val))
        state.config["knn_filtered_k"] = val
        _apply_knn_runtime_k(state.config)
        return _persist_settings_to_disk("filtered KNN count")

    def _commit_prediction_log_dir() -> bool:
        if prediction_log_entry is None:
            return True
        state.config["prediction_log_dir"] = prediction_log_entry.get().strip()
        return _persist_settings_to_disk("prediction log dir")

    def _make_hotkey_commit(entry_obj, key: str, rebind):
        def _commit() -> bool:
            ok = _commit_action_hotkey(entry_obj, key, rebind)
            _refresh_hotkey_summary()
            return ok
        return _commit

    _commit_overlay_hotkey = _make_hotkey_commit(custom_hotkey_entry, "custom_hotkey", _bind_overlay_hotkey)
    _commit_filtered_hotkey = _make_hotkey_commit(filtered_hotkey_entry, "filtered_overlay_hotkey", _bind_filtered_overlay_hotkey)
    _commit_stash_scrape_hotkey = _make_hotkey_commit(stash_scrape_hotkey_entry, "stash_scrape_hotkey", _bind_stash_scrape_hotkey)
    _commit_craft_hotkey = _make_hotkey_commit(craft_potential_hotkey_entry, "craft_potential_hotkey", _bind_craft_potential_hotkey)

    def _bind_commit(entry_obj, commit) -> None:
        if entry_obj is None:
            return
        entry_obj.bind("<FocusOut>", lambda _e: commit())
        entry_obj.bind("<Return>", lambda _e: commit())

    _bind_commit(price_filter_entry, _commit_price_filter)
    _bind_commit(max_price_filter_entry, _commit_max_price_filter)
    _bind_commit(knn_filtered_k_entry, _commit_knn_filtered_k)
    _bind_commit(prediction_log_entry, _commit_prediction_log_dir)
    _bind_commit(custom_hotkey_entry, _commit_overlay_hotkey)
    _bind_commit(filtered_hotkey_entry, _commit_filtered_hotkey)
    _bind_commit(stash_scrape_hotkey_entry, _commit_stash_scrape_hotkey)
    _bind_commit(craft_potential_hotkey_entry, _commit_craft_hotkey)

    action_entries = (custom_hotkey_entry, filtered_hotkey_entry,
                      stash_scrape_hotkey_entry, craft_potential_hotkey_entry)

    def _refresh_hotkey_edit_focus(_event=None):
        try:
            focused = root.focus_get()
            # CTkEntry's actual focus target is its internal Tk entry widget.
            keyboard.set_suspended(any(focused in (entry, getattr(entry, "_entry", None))
                                       for entry in action_entries if entry is not None)
                                   if focused is not None else False)
        except Exception:
            keyboard.set_suspended(False)

    for entry in action_entries:
        if entry is not None:
            entry.bind("<FocusIn>", lambda _e: keyboard.set_suspended(True), add=True)
            entry.bind("<FocusOut>", lambda _e: root.after_idle(_refresh_hotkey_edit_focus), add=True)
            entry.bind("<Destroy>", lambda _e: keyboard.set_suspended(False), add=True)


    # Persist the log directory as soon as it is picked via Browse, too.
    if prediction_log_browse_btn is not None:
        prediction_log_browse_btn.configure(
            command=lambda e=prediction_log_entry: (
                _browse_for_prediction_log(e),
                _commit_prediction_log_dir(),
            )
        )

    def _commit_all_fields() -> None:
        _commit_price_filter()
        _commit_max_price_filter()
        _commit_knn_filtered_k()
        _commit_prediction_log_dir()
        _commit_overlay_hotkey()
        _commit_filtered_hotkey()
        _commit_stash_scrape_hotkey()
        _commit_craft_hotkey()
        if close_behavior_var is not None:
            _persist_close_behavior(close_behavior_var.get())

    ctk.CTkButton(
        app_section.content,
        text="Reset Settings",
        command=_reset_settings_defaults,
        corner_radius=8,
    ).pack(anchor="w", padx=10, pady=(4, 10))

    # (Prod) Auction Price Tool section removed; keep in gui_tk_dev only


    # Persistent updater status strip docked at the very bottom of the window,
    # outside the scrollable settings, so update progress/results/actions show
    # inline instead of in floating popups.
    global _update_status_bar
    _update_status_bar = _UpdateStatusBar(root)
    _update_status_bar.frame.grid(row=1, column=0, columnspan=2, sticky="ew")
    # Keep the updater strip out of the layout until it has a real status to
    # show; an idle, empty strip was the unexplained blank bar at the bottom.
    _update_status_bar.frame.grid_remove()

    _bind_price_hotkeys()
    _bind_test_update_hotkey()
    _auto_resize_root()
    _recover_interrupted_update()
    # Discard any per-user override assets a newer bundle has superseded BEFORE
    # the first prediction resolves models, so a stale override (e.g. left by an
    # older install or a prior data snapshot) can never shadow the fresh bundle.
    _reconcile_stale_override_assets()
    # Kick off ML pre-warming shortly after the window is painted so the first
    # prediction isn't stalled by pickle deserialization / JSON compaction.
    root.after(300, _prewarm_prediction_worker)
    # The presenter must be prewarmed independently of model startup. Waiting
    # 350 ms meant a fast first hotkey launched the child during Tk/Windows
    # initialization, which is the one case where foreground focus was flaky.
    root.after(50, _prewarm_prediction_popup)
    # Use a fresh cached rate snapshot at startup when possible. A manual
    # banner refresh always forces a new poe2scout request instead.
    root.after(500, lambda: _refresh_live_prices_async(force=False))
    # Validate StashScrape category IDs once per app launch. The refresh is
    # background-only; scrapes read the resulting local cache and never add a
    # metadata request to every category run.
    root.after(650, _refresh_trade_category_registry_async)
    # If a swap was applied since last launch, confirm the version actually
    # advanced (and blocklist it if not) before the first update check runs.
    _verify_post_swap_update()
    # Check for model/data/app updates shortly after launch (best-effort, off the
    # UI thread). No-op unless auto_update is on and a manifest URL is configured.
    root.after(800, _maybe_start_update_check)
    # A second launch hands off to this instance instead of starting its own.
    root.after(_SHOW_REQUEST_POLL_MS, _poll_show_requests)
    _exit_watchdog_enabled = True
    root.mainloop()


# in-app updater wiring
def _format_download_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes} B"


class _UpdateStatusBar:
    """Inline updater status strip docked at the bottom of the main window.

    Holds its own logical state (``state``/``message``/``action_*``) so the
    update flow is testable without a real Tk window: when constructed without a
    ``parent`` it stays headless (no widgets) and only records what would be
    shown. With a parent it renders a label, an indeterminate progress bar (only
    while checking/downloading) and an optional right-aligned action button
    (e.g. *Restart & Update*).
    """

    def __init__(self, parent=None):
        self.state = "idle"
        self.message = ""
        self.action_text: Optional[str] = None
        self.action_cb: Optional[Callable[[], None]] = None
        self.frame = None
        self.label = None
        self.bar = None
        self.action_btn = None
        self._clear_handle = None
        self.progress_fraction: Optional[float] = None
        if parent is not None:
            self._build(parent)

    @property
    def has_widgets(self) -> bool:
        return self.frame is not None

    def _build(self, parent) -> None:
        self.frame = ctk.CTkFrame(parent, fg_color="#1B1B1B", corner_radius=0, height=30)
        self.action_btn = ctk.CTkButton(
            self.frame, text="", width=150, height=24, corner_radius=8,
            command=self.trigger_action,
        )
        self.bar = ctk.CTkProgressBar(self.frame, mode="indeterminate", width=160, height=10)
        self.label = ctk.CTkLabel(
            self.frame, text="", anchor="w", font=_FONT_MONO, text_color=_STATUS_MUTED
        )
        self.label.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=5)

    def present(
        self,
        state: str,
        message: str,
        *,
        tone: str = "muted",
        action_text: Optional[str] = None,
        action_cb: Optional[Callable[[], None]] = None,
        autoclear_ms: Optional[int] = None,
        progress_fraction: Optional[float] = None,
    ) -> None:
        """Set the strip's state/message and (re)render if widgets exist."""
        self.state = state
        self.message = message or ""
        self.action_text = action_text
        self.action_cb = action_cb
        self.progress_fraction = progress_fraction
        if not self.has_widgets:
            return
        self._cancel_clear()
        if state == "idle" and not self.message:
            self.frame.grid_remove()
            return
        self.frame.grid()
        self.label.configure(text=self.message, text_color=_STATUS_TONES.get(tone, _STATUS_MUTED))
        if state in ("checking", "downloading"):
            if progress_fraction is None:
                self.bar.configure(mode="indeterminate")
            else:
                self.bar.configure(mode="determinate")
                self.bar.set(max(0.0, min(float(progress_fraction), 1.0)))
            self.bar.pack(side="left", padx=(0, 8), pady=8)
            try:
                if progress_fraction is None:
                    self.bar.start()
                else:
                    self.bar.stop()
            except Exception:
                logging.debug("could not start status progress bar", exc_info=True)
        else:
            try:
                self.bar.stop()
            except Exception:
                logging.debug("could not stop status progress bar", exc_info=True)
            self.bar.pack_forget()
        if action_text:
            self.action_btn.configure(text=action_text)
            self.action_btn.pack(side="right", padx=(8, 12), pady=4)
        else:
            self.action_btn.pack_forget()
        if autoclear_ms and root is not None:
            try:
                self._clear_handle = root.after(
                    autoclear_ms, lambda: self.present("idle", "", tone="muted")
                )
            except Exception:
                logging.debug("could not schedule status auto-clear", exc_info=True)

    def set_text(self, message: str) -> None:
        """Cheap label-only update (used for streaming download byte counts)."""
        self.message = message or ""
        if self.has_widgets:
            self.label.configure(text=self.message)

    def set_progress(self, message: str, progress_fraction: Optional[float]) -> None:
        """Update text and progress without changing actions/autoclear state."""
        self.message = message or ""
        self.progress_fraction = progress_fraction
        if not self.has_widgets:
            return
        self.label.configure(text=self.message)
        try:
            if progress_fraction is None:
                self.bar.configure(mode="indeterminate")
                self.bar.start()
            else:
                self.bar.configure(mode="determinate")
                self.bar.stop()
                self.bar.set(max(0.0, min(float(progress_fraction), 1.0)))
        except Exception:
            logging.debug("could not update status progress bar", exc_info=True)

    def trigger_action(self) -> None:
        cb = self.action_cb
        if cb is not None:
            cb()

    def _cancel_clear(self) -> None:
        if self._clear_handle is not None and root is not None:
            try:
                root.after_cancel(self._clear_handle)
            except Exception:
                logging.debug("could not cancel status auto-clear", exc_info=True)
        self._clear_handle = None


def _status() -> "_UpdateStatusBar":
    """Return the docked status strip, lazily creating a headless one if needed.

    The headless fallback keeps the updater flow callable in tests / before the
    main window is built; it simply records state instead of rendering.
    """
    global _update_status_bar
    if _update_status_bar is None:
        _update_status_bar = _UpdateStatusBar()
    return _update_status_bar


def _begin_update_progress() -> None:
    """Show 'checking for updates' in the docked status strip."""
    global _update_progress_bytes, _update_progress_total, _update_progress_kind, _update_progress_version
    _update_progress_bytes = 0
    _update_progress_total = 0
    _update_progress_kind = "download"
    _update_progress_version = None
    _status().present("checking", "Checking for updates...")


def _progress_delta(progress: object) -> int:
    return int(getattr(progress, "delta_bytes", progress) or 0)


def _progress_total(progress: object) -> int:
    return int(getattr(progress, "total_bytes", 0) or 0)


def _progress_message(
    kind: str,
    version: Optional[str],
    num_bytes: int,
    *,
    total_bytes: int = 0,
    phase: str = "download",
) -> str:
    if phase == "verifying":
        return f"Verifying update v{version}..." if kind == "app" and version else "Verifying update..."
    if phase == "verified":
        return f"Update v{version} downloaded & verified." if kind == "app" and version else "Update downloaded & verified."
    if phase == "extracting":
        return f"Preparing update v{version}..." if kind == "app" and version else "Preparing update..."
    size = _format_download_size(num_bytes)
    if total_bytes > 0:
        size = f"{size} of {_format_download_size(total_bytes)}"
    if kind == "app":
        suffix = f" v{version}" if version else ""
        return f"Update found - downloading{suffix}... {size}"
    if kind == "asset":
        return f"Refreshing model data... {size}"
    return f"Downloading verified update... {size}"


def _add_update_progress(progress: object) -> None:
    """Stream download progress into the status strip (Tk thread)."""
    global _update_progress_bytes, _update_progress_total, _update_progress_kind, _update_progress_version
    delta = _progress_delta(progress)
    kind = str(getattr(progress, "kind", "") or _update_progress_kind or "download")
    version = getattr(progress, "version", None) or _update_progress_version
    total = _progress_total(progress)
    phase = str(getattr(progress, "phase", "") or "download")
    if kind != _update_progress_kind or version != _update_progress_version:
        _update_progress_bytes = 0
        _update_progress_total = 0
        _update_progress_kind = kind
        _update_progress_version = version
    if total > 0:
        _update_progress_total = total
    _update_progress_bytes += max(delta, 0)
    text = _progress_message(
        kind,
        version,
        _update_progress_bytes,
        total_bytes=_update_progress_total,
        phase=phase,
    )
    progress_fraction = None
    if _update_progress_total > 0 and phase == "download":
        progress_fraction = min(_update_progress_bytes / _update_progress_total, 1.0)
    elif phase in ("verifying", "verified", "extracting"):
        progress_fraction = 1.0
    bar = _status()
    if bar.state == "downloading":
        bar.set_progress(text, progress_fraction)
    else:
        bar.present("downloading", text, progress_fraction=progress_fraction)


def _queue_update_progress(progress: object) -> None:
    try:
        if root is not None and root.winfo_exists():
            root.after(0, lambda: _add_update_progress(progress))
    except Exception:
        logging.debug("could not schedule update progress", exc_info=True)


def _close_update_progress() -> None:
    """Stop the animated progress bar; the result handler sets the final text."""
    bar = _status()
    if bar.has_widgets and bar.state in ("checking", "downloading"):
        try:
            bar.bar.stop()
        except Exception:
            logging.debug("could not stop status progress bar", exc_info=True)
        bar.bar.pack_forget()


def _invalidate_asset_caches() -> None:
    """Drop cached model/scoring artifacts so refreshed assets take effect.

    The model/stat caches are mtime+path keyed and self-heal after an atomic
    replace, but clearing the gui-level caches makes a mid-session asset refresh
    visible immediately. Runs on the Tk thread (scheduled via root.after).
    """
    global _SCORING_JSON_CACHE, _SCORING_JSON_MTIME
    global _CATEGORY_STATS_CACHE, _CATEGORY_STATS_MTIME
    global _FI_MANIFEST_CACHE, _FI_MANIFEST_MTIME
    global _FI_CHART_CACHE, _FI_CHART_MTIME
    _SCORING_JSON_CACHE = {}
    _SCORING_JSON_MTIME = {}
    _CATEGORY_STATS_CACHE = None
    _CATEGORY_STATS_MTIME = None
    _FI_MANIFEST_CACHE = None
    _FI_MANIFEST_MTIME = None
    _FI_CHART_CACHE = {}
    _FI_CHART_MTIME = None
    # These are mtime-keyed too, but an update can also move the asset search
    # roots, which the keys do not cover.
    _icon_base_map.cache_clear()
    _comparison_icon_candidates.cache_clear()
    _render_icon_png.cache_clear()
    try:
        from poe2trade.utils import ml_super_utils
        ml_super_utils.clear_runtime_caches()
    except Exception:
        logging.debug("supervised model cache clear skipped", exc_info=True)
    try:
        from poe2trade.utils import ml_unsuper_utils
        ml_unsuper_utils.clear_runtime_caches()
    except Exception:
        logging.debug("unsupervised model cache clear skipped", exc_info=True)
    logging.info("Asset caches cleared after update")


def _recover_interrupted_update() -> None:
    """Clean up updater leftovers from a prior interrupted apply attempt."""
    try:
        notes = updater.recover_interrupted_update()
    except Exception:
        logging.debug("update recovery cleanup skipped", exc_info=True)
        return
    for note in notes:
        logging.info("Update recovery: %s", note)


def _record_pending_update(version: Optional[str]) -> None:
    """Record the version we expect to be running after the restart-swap.

    On the next launch :func:`_verify_post_swap_update` checks that the running
    version actually advanced; if it didn't (a stale/mismatched staged zip
    relaunched the same version), that version is blocklisted so the updater
    stops re-staging it on every launch. Best-effort - never blocks the swap.
    """
    try:
        updater.record_pending_update(
            updater.default_update_stage_dir(), str(version or "").strip()
        )
    except Exception:
        logging.debug("could not record pending update sentinel", exc_info=True)


def _reconcile_stale_override_assets() -> None:
    """Clear per-user override model assets a newer bundle has superseded.

    Fixes the case where a freshly installed/built/swapped bundle ships newer
    models + distribution/feature-importance sidecars but an older synced
    override under ``%APPDATA%/StashSage/generated`` keeps shadowing them. Runs
    once at startup, offline-safe, before any model resolution.
    """
    try:
        removed = asset_paths.reconcile_override_with_bundle(
            __version__, build_commit=__build_commit__
        )
    except Exception:
        logging.debug("override reconciliation skipped", exc_info=True)
        return
    if removed:
        logging.warning(
            "Cleared %d stale override asset bucket(s) superseded by bundle v%s: %s",
            len(removed),
            __version__,
            ", ".join(str(p) for p in removed),
        )
        _invalidate_asset_caches()


# How long "Updated to vX" stays in the status strip after a successful update.
_UPDATE_RESULT_NOTICE_MS = 15000


def _verify_post_swap_update() -> None:
    """At startup, report how the last update went and confirm the version advanced.

    The swap helper's result is consumed first: a swap that was refused or failed
    never changed the install, so its pending sentinel is cleared rather than
    read as a bad release (which would blocklist a release that is fine).
    """
    stage_root = updater.default_update_stage_dir()
    try:
        result = updater.consume_apply_result(stage_root)
    except Exception:
        logging.debug("update result check skipped", exc_info=True)
        result = None
    try:
        failed = updater.verify_post_swap_update(stage_root, __version__)
    except Exception:
        logging.debug("post-swap version verification skipped", exc_info=True)
        failed = None
    if failed:
        logging.warning(
            "App update to v%s did not take effect (still running v%s); "
            "it will not be re-staged. A manual reinstall may be needed.",
            failed,
            __version__,
        )
    if result is not None:
        log_fn = logging.info if result.applied and not failed else logging.warning
        log_fn(
            "Last update helper result: status=%s code=%s expected=v%s message=%s (log: %s)",
            result.status,
            result.code,
            result.expected_version,
            result.message,
            stage_root / "apply-update.log",
        )
    _present_update_result(result, failed)


def _present_update_result(result: "Optional[updater.ApplyResult]", failed: Optional[str]) -> None:
    """Tell the user, in the status strip, what the last update attempt did."""
    bar = _status()
    if failed:
        bar.present(
            "warn",
            f"Update to v{failed} didn't take effect; you're still on v{__version__}. "
            "Download the latest from the website.",
            tone="warn",
            action_text="Download",
            action_cb=_open_download_page,
        )
        return
    if result is None:
        return
    if result.applied:
        bar.present(
            "idle",
            f"Updated to v{__version__}.",
            tone="ready",
            autoclear_ms=_UPDATE_RESULT_NOTICE_MS,
        )
        return
    version = f" v{result.expected_version}" if result.expected_version else ""
    reason = result.message or "the update helper stopped before swapping."
    bar.present(
        "warn",
        f"Update{version} wasn't applied: {reason}",
        tone="warn",
        action_text="Try again",
        action_cb=_check_for_updates_clicked,
    )


def _flag_app_update(version: Optional[str]) -> None:
    """Surface an available app update in the window title (non-intrusive)."""
    logging.info("App update available: v%s", version)
    try:
        if root is not None and root.winfo_exists():
            root.title(
                f"StashSage for POE2 (v{__version__} -- {BUILD_DATE})"
                f"  -  update v{version} available"
            )
    except Exception:
        logging.debug("could not update title for app-update flag", exc_info=True)


def _open_download_page() -> None:
    webbrowser.open("https://rheinze08.github.io/StashSage/")


# Long enough for the status strip to paint "closing to apply" before exit.
_APPLY_UPDATE_EXIT_DELAY_MS = 400


def _apply_staged_update(outcome: "updater.UpdateOutcome") -> bool:
    """Apply a verified staged package: launch the swap helper and exit.

    Shared by the manual 'Update App' flow and the auto-check status strip. The
    only remaining hard-stop popup is the rare case where the verified package
    was downloaded but the swap helper could not be launched.

    The staged bundle is re-checked immediately before launching: a check still
    running may be replacing it, and a newer release may have pruned it since
    the button appeared.
    """
    bar = _status()
    if _update_check_in_flight():
        bar.present(
            "checking",
            "The update is still being prepared; try again in a moment.",
            action_text="Restart & Update",
            action_cb=lambda: _apply_staged_update(outcome),
        )
        return False
    problem = updater.staged_bundle_problem(outcome.app_package_dir, outcome.app_version)
    if problem is not None:
        logging.warning("Staged update v%s cannot be applied: %s", outcome.app_version, problem)
        bar.present(
            "warn",
            f"Update v{outcome.app_version} is no longer ready ({problem}). "
            "It will be prepared again on the next check.",
            tone="warn",
            action_text="Check again",
            action_cb=_check_for_updates_clicked,
        )
        return False
    stage_root = updater.default_update_stage_dir()
    try:
        _record_pending_update(outcome.app_version)
        updater.launch_app_update_after_exit(
            outcome.app_package_dir,
            expected_version=outcome.app_version,
            log_path=stage_root / "apply-update.log",
        )
    except Exception:
        logging.exception("failed to launch in-place update")
        # No swap will happen, so the next launch must not read the unchanged
        # version as a failed swap and blocklist this release.
        try:
            updater.clear_pending_update(stage_root)
        except Exception:
            logging.debug("could not clear pending update sentinel", exc_info=True)
        bar.present(
            "warn",
            "Update downloaded, but StashSage couldn't apply it.",
            tone="warn",
        )
        messagebox.showerror(
            "StashSage Updates",
            "The update was downloaded, but StashSage could not apply it.",
        )
        return False
    logging.info("Launched update helper for v%s; closing to apply it", outcome.app_version)
    bar.present("checking", f"Closing StashSage to apply update v{outcome.app_version}…")
    if root is not None:
        try:
            root.after(
                _APPLY_UPDATE_EXIT_DELAY_MS, lambda: _shutdown_app("apply update")
            )
        except Exception:
            logging.debug("could not schedule update shutdown", exc_info=True)
            _shutdown_app("apply update")
    return True


def _show_update_result(outcome: "updater.UpdateOutcome") -> None:
    """Render the result of a manual 'Update App' check in the status strip."""
    _close_update_progress()
    bar = _status()
    if outcome.manifest is None:
        bar.present(
            "warn",
            "Couldn't reach the update server — using the installed version.",
            tone="warn",
            autoclear_ms=8000,
        )
        return
    if outcome.runtime_version_unknown:
        # The running build reports an unknown/0.0.0 version, so every manifest
        # looks newer and auto-staging was suppressed to avoid an update loop.
        bar.present(
            "warn",
            "This build can't report its version; updates can't be applied. "
            "Re-download from the website.",
            tone="warn",
            action_text="Get latest",
            action_cb=_open_download_page,
        )
        return
    asset_note = ""
    if outcome.assets_changed:
        n = len(outcome.sync.downloaded) if outcome.sync else 0
        asset_note = f"Refreshed {n} model/data file(s). "
    if outcome.app_update_available and outcome.app_package_dir is not None:
        bar.present(
            "ready",
            f"{asset_note}Update v{outcome.app_version} downloaded & verified.",
            tone="ready",
            action_text="Restart & Update",
            action_cb=lambda: _apply_staged_update(outcome),
        )
        return
    notice = updater.retirement_notice(outcome)
    if notice is not None:
        bar.present(
            "warn",
            f"{asset_note}{notice.message}",
            tone="warn",
            action_text="Get latest",
            action_cb=_open_download_page,
        )
        return
    if outcome.app_update_available and outcome.manifest and outcome.manifest.app_package_url:
        bar.present(
            "warn",
            f"{asset_note}Update v{outcome.app_version} available "
            "(couldn't stage automatically).",
            tone="warn",
            action_text="Download",
            action_cb=_open_download_page,
        )
        return
    version_note = f" v{outcome.current_version}" if outcome.current_version else ""
    bar.present(
        "idle",
        f"{asset_note}You're up to date{version_note}.".strip(),
        tone="muted",
        autoclear_ms=6000,
    )


def _offer_auto_app_update(outcome: "updater.UpdateOutcome") -> bool:
    """Surface an auto-staged update inline in the status strip (no popup).

    Returns ``True`` when a verified package was staged and the strip now shows
    a *Restart & Update* action; ``False`` when there is nothing to offer (the
    caller then falls back to the title-bar flag).
    """
    if outcome.app_package_dir is None:
        notice = updater.retirement_notice(outcome)
        if notice is not None:
            _status().present(
                "warn",
                notice.message,
                tone="warn",
                action_text="Get latest",
                action_cb=_open_download_page,
            )
            return True
        return False
    _status().present(
        "ready",
        f"Update v{outcome.app_version} downloaded & verified.",
        tone="ready",
        action_text="Restart & Update",
        action_cb=lambda: _apply_staged_update(outcome),
    )
    return True


def _on_update_outcome(outcome: "updater.UpdateOutcome", *, manual: bool) -> None:
    """Updater-thread callback; marshals all UI work onto the Tk thread."""
    global _manual_update_result_requested
    try:
        if root is None or not root.winfo_exists():
            return
    except Exception:
        return
    show_manual_result = manual or _manual_update_result_requested
    if show_manual_result:
        _manual_update_result_requested = False
    if outcome.assets_changed:
        try:
            root.after(0, _invalidate_asset_caches)
        except Exception:
            logging.debug("cache-invalidate schedule failed", exc_info=True)
    if show_manual_result:
        try:
            root.after(0, lambda: _show_update_result(outcome))
        except Exception:
            logging.debug("update-result schedule failed", exc_info=True)
    elif outcome.app_update_available:
        try:
            root.after(
                0,
                lambda: (
                    None
                    if _offer_auto_app_update(outcome)
                    else _flag_app_update(outcome.app_version)
                ),
            )
        except Exception:
            logging.debug("app-update flag schedule failed", exc_info=True)


def _update_check_in_flight() -> bool:
    """True while a background update-check thread is still running."""
    t = _update_check_thread
    return t is not None and t.is_alive()


def _schedule_next_update_check() -> None:
    """Re-arm the periodic background update check on the Tk thread."""
    try:
        if root is not None and root.winfo_exists():
            delay_ms = _UPDATE_RECHECK_INTERVAL_MS + random.randint(0, _UPDATE_RECHECK_JITTER_MS)
            root.after(delay_ms, _maybe_start_update_check)
    except Exception:
        logging.debug("could not schedule next update check", exc_info=True)


def _maybe_start_update_check() -> None:
    """Start the background update check if enabled and configured.

    Always re-arms the next periodic check so toggling ``auto_update`` back on
    (or recovering from a transient failure) is picked up on the next interval.
    """
    global _update_check_thread
    try:
        if (
            str(state.config.get("update_manifest_url") or "").strip()
            and bool(state.config.get("auto_update", True))
            and not _update_check_in_flight()
        ):
            _update_check_thread = updater.run_check_in_background(
                state.config,
                current_version=__version__,
                stage_app_update=True,
                on_complete=lambda o: _on_update_outcome(o, manual=False),
            )
    except Exception:
        logging.debug("update check not started", exc_info=True)
    finally:
        _schedule_next_update_check()


def _test_update_env_enabled() -> bool:
    return str(os.getenv(TEST_UPDATE_ENV_VAR) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


# The local test-update session lives with the headless self-test mode so the
# launcher can use it without importing the GUI.
_LocalTestUpdateResponse = update_self_test.LocalUpdateResponse
_LocalTestUpdateSession = update_self_test.LocalUpdateSession


def _local_test_update_manifest_path() -> Optional[Path]:
    """Return build_app's local updater-test manifest when the app is local."""
    try:
        install = updater.install_root()
    except Exception:
        install = None
    candidates: list[Path] = []
    if install is not None:
        # Running from dist/StashSage.
        candidates.append(install.parent / "updater_selftest" / "update-manifest-local.json")
        # Running from dist/updater_selftest/client/StashSage.
        candidates.append(install.parent.parent / "update-manifest-local.json")
    try:
        candidates.append(Path.cwd() / "dist" / "updater_selftest" / "update-manifest-local.json")
    except OSError:
        pass
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _test_updates_enabled() -> bool:
    # Local artifacts written by build_app.bat are explicitly developer-test
    # artifacts, so make that path work without requiring a separate launcher
    # env var. The hosted test channel still requires TEST_UPDATE_ENV_VAR.
    return _test_update_env_enabled() or _local_test_update_manifest_path() is not None


def _bind_test_update_hotkey() -> None:
    """Bind the hidden updater-test channel hotkey for opted-in dev sessions."""
    global _test_update_hotkey_handle
    if not _test_updates_enabled():
        return
    if _test_update_hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_test_update_hotkey_handle)
        except Exception:
            logging.debug("Previous test update hotkey removal failed", exc_info=True)
        finally:
            _test_update_hotkey_handle = None
    try:
        _test_update_hotkey_handle = keyboard.add_hotkey(
            TEST_UPDATE_HOTKEY, _check_test_updates_clicked, suppress=False
        )
        logging.info(
            "Test update hotkey bound to %s (%s=1)",
            TEST_UPDATE_HOTKEY,
            TEST_UPDATE_ENV_VAR,
        )
    except Exception as exc:
        logging.warning("Could not bind test update hotkey %r: %s", TEST_UPDATE_HOTKEY, exc)
        _test_update_hotkey_handle = None


def _check_test_updates_clicked(_=None) -> None:
    """Run one manual update check against the hidden test-channel manifest."""
    global _update_check_thread, _manual_update_result_requested
    if not _test_updates_enabled():
        logging.info("Ignoring test update hotkey; %s is not enabled", TEST_UPDATE_ENV_VAR)
        return
    # Reuse the same single-flight behavior as the visible Update App button.
    if _update_check_in_flight():
        _manual_update_result_requested = True
        bar = _status()
        if bar.state not in ("checking", "downloading"):
            bar.present("checking", "Checking for updates...")
        return
    local_manifest = _local_test_update_manifest_path()
    cfg = dict(state.config)
    session = None
    force_app_update = False
    if local_manifest is not None:
        cfg["update_manifest_url"] = LOCAL_TEST_UPDATE_MANIFEST_URL
        session = _LocalTestUpdateSession(local_manifest)
        force_app_update = True
        logging.info("Using local updater test manifest: %s", local_manifest)
    else:
        cfg["update_manifest_url"] = TEST_UPDATE_MANIFEST_URL
    _manual_update_result_requested = False
    _begin_update_progress()
    _update_check_thread = updater.run_check_in_background(
        cfg,
        current_version=__version__,
        stage_app_update=True,
        force_app_update=force_app_update,
        session=session,
        progress_cb=_queue_update_progress,
        on_complete=lambda o: _on_update_outcome(o, manual=True),
    )


def _check_for_updates_clicked() -> None:
    """Manual 'Update App' handler.

    When no manifest URL is configured (the default), fall back to opening the
    download site so behaviour is unchanged from before the updater existed.
    """
    global _update_check_thread, _manual_update_result_requested
    if not str(state.config.get("update_manifest_url") or "").strip():
        webbrowser.open("https://rheinze08.github.io/StashSage/")
        return
    # Single-flight: if a check (auto or manual) is already running, just surface
    # the progress dialog instead of starting a second concurrent download.
    if _update_check_in_flight():
        _manual_update_result_requested = True
        bar = _status()
        if bar.state not in ("checking", "downloading"):
            bar.present("checking", "Checking for updates...")
        return
    _manual_update_result_requested = False
    _begin_update_progress()
    _update_check_thread = updater.run_check_in_background(
        state.config,
        current_version=__version__,
        stage_app_update=True,
        progress_cb=_queue_update_progress,
        on_complete=lambda o: _on_update_outcome(o, manual=True),
    )


def _warm_model_caches(*, knn_bundles: bool, compact_scoring_jsons: bool) -> None:
    """Load model artifacts into this process's caches.

    Discovers installed model pickles by glob (no hardcoded category list), so
    it is a no-op when no models are installed. The heavy sklearn/xgboost import
    happens here instead of on the first prediction.

    Both the main process and the resident prediction worker call this, with
    different scopes:

    - `knn_bundles` is worker-only. The bundles carry full overlay DataFrames,
      and `call_ml` runs exclusively inside `_dashboard_process_entry`; loading
      them in the main process would duplicate that memory for no reader.
    - `compact_scoring_jsons` is main-process-only. It rewrites the sidecars on
      disk, so keeping it to one process avoids two writers racing over the
      same files.
    """
    # Matplotlib is imported lazily by chart_utils (keeps startup fast);
    # warm it here so the first overlay render doesn't pay the init cost.
    try:
        from poe2trade.utils.chart_utils import ensure_matplotlib
        ensure_matplotlib()
    except Exception as exc:
        logging.debug("matplotlib prewarm skipped: %s", exc)
    try:
        from poe2trade.utils import ml_super_utils
        super_dirs = [d for d in _super_model_dirs() if d.is_dir()]
        if not super_dirs:
            return
        if compact_scoring_jsons:
            # Compact the large scoring JSON sidecars up front.
            try:
                ml_super_utils._maybe_compact_scoring_jsons()
            except Exception as exc:
                logging.debug("scoring-json compaction skipped: %s", exc)
        # Warm the in-process model cache for every installed model, across
        # the override dir and the bundled fallback (mirrors load resolution).
        for model_dir in super_dirs:
            for pkl in model_dir.glob("*_model.pkl"):
                stem = pkl.name[: -len("_model.pkl")]
                if "_" not in stem:
                    continue
                base_name, mtype = stem.rsplit("_", 1)
                try:
                    ml_super_utils._load_model(model_dir, base_name, mtype)
                except Exception as exc:
                    logging.debug("prewarm skipped %s: %s", pkl.name, exc)
        if knn_bundles:
            try:
                from poe2trade.utils import ml_unsuper_utils as _ml_unsuper_utils
                _ml_unsuper_utils._prewarm_unsuper_bundles()
            except Exception as exc:
                logging.debug("unsuper prewarm skipped: %s", exc)
    except Exception as exc:
        logging.debug("model prewarm failed: %s", exc)


def _spawn_model_prewarm() -> None:
    """Warm the main process's supervised caches on a background thread.

    CraftOracle runs `call_super_prepared` on a thread in this process
    (`_launch_craft_potential_popup`), so the supervised models are needed here
    too. The KNN bundles are not: they are warmed in the prediction worker,
    which is the only process that queries them.
    """
    threading.Thread(
        target=_warm_model_caches,
        kwargs={"knn_bundles": False, "compact_scoring_jsons": True},
        daemon=True,
        name="ModelPrewarm",
    ).start()


# ------------- tray-icon helpers (unchanged) -------------
def _create_image():
    icon_path = Path(__file__).with_name("stashsage_logo.ico")
    if not icon_path.exists():
        raise FileNotFoundError(f"Tray icon not found: {icon_path}")
    return Image.open(icon_path)


def _arm_exit_watchdog(exit_code: int = 0) -> None:
    """Force the process to exit if an orderly shutdown has not finished in time.

    Runs on a daemon thread, which keeps running while the interpreter waits on
    non-daemon children at exit, so it still fires in exactly the hang it
    exists for.
    """
    global _exit_watchdog_armed
    if not _exit_watchdog_enabled or _exit_watchdog_armed:
        return
    _exit_watchdog_armed = True

    def _force_exit() -> None:
        time.sleep(_SHUTDOWN_GRACE_SECONDS)
        logging.warning(
            "Shutdown did not finish within %.0fs; forcing exit", _SHUTDOWN_GRACE_SECONDS
        )
        for handler in logging.getLogger().handlers:
            try:
                handler.flush()
            except Exception:
                pass
        os._exit(exit_code)

    threading.Thread(target=_force_exit, name="StashSageExitWatchdog", daemon=True).start()


def _shutdown_app(reason: str) -> None:
    """Stop everything that can keep the process alive, then end the Tk loop.

    Shared by tray Exit, the window close button (exit mode) and Restart &
    Update. Restart & Update used to only destroy the root window, leaving the
    warm presenter child running; Python then waited on it forever at exit, and
    the update helper waited on this process forever. Must run on the Tk thread.
    """
    global _shutdown_root
    if root is not None and _shutdown_root is root:
        return
    _shutdown_root = root
    logging.info("Application shutdown requested (%s)", reason)
    try:
        keyboard.shutdown()
        for handle in list(_pending_hotkey_cleanup):
            keyboard.remove_hotkey(handle)
            _pending_hotkey_cleanup.remove(handle)
    except Exception:
        logging.exception("Action hotkey shutdown failed")
    _arm_exit_watchdog()
    # Stop the warm Tk presenter before the parent interpreter starts exiting.
    # Without this handshake, Windows can kill it while its queue feeder and
    # CustomTkinter callbacks are still unwinding.
    try:
        _terminate_prediction_popup()
    except Exception:
        logging.debug("Prediction presenter shutdown failed", exc_info=True)
    if _prediction_worker_manager is not None:
        try:
            _prediction_worker_manager.shutdown()
        except Exception:
            logging.debug("Prediction worker shutdown failed", exc_info=True)
    icon = getattr(root, "tray_icon", None) if root is not None else None
    if icon is not None:
        try:
            icon.stop()
        except Exception:
            logging.debug("tray icon stop failed", exc_info=True)
    if root is not None:
        for step in ("quit", "destroy"):
            try:
                getattr(root, step)()
            except Exception:
                logging.debug("root %s failed", step, exc_info=True)


def _on_quit(icon, item):
    """Tray Exit (and the close button in exit mode).

    Tray callbacks run on pystray's thread. Raising SystemExit there never ended
    the process -- it only logged a traceback -- so the shutdown is marshalled
    onto the Tk thread instead. The watchdog is armed first, so an unresponsive
    Tk loop still exits.
    """
    _arm_exit_watchdog()
    if root is None:
        _shutdown_app("tray exit")
        return
    try:
        root.after(0, lambda: _shutdown_app("tray exit"))
    except Exception:
        logging.debug("could not schedule shutdown on the Tk thread", exc_info=True)
        _shutdown_app("tray exit")


def _poll_show_requests() -> None:
    """Bring the window forward when a second launch asked for it."""
    try:
        if single_instance.consume_show_request():
            logging.info("Another launch asked the running instance to show itself")
            _show_app(getattr(root, "tray_icon", None), None)
    except Exception:
        logging.debug("show request poll failed", exc_info=True)
    try:
        if root is not None and root.winfo_exists():
            root.after(_SHOW_REQUEST_POLL_MS, _poll_show_requests)
    except Exception:
        logging.debug("could not re-arm show request poll", exc_info=True)


def _close_behavior(cfg: Mapping[str, Any]) -> str:
    """Return the supported persisted main-window close action."""
    return "exit" if str(cfg.get("close_behavior") or "tray").lower() == "exit" else "tray"


def _persist_settings_to_disk(context: str = "settings") -> bool:
    """Write the live config to disk, surfacing any failure to the user.

    Shared by every self-saving settings control so each field persists the
    moment it changes, with no separate Save button.
    """
    try:
        config_manager.save_config(state.config)
        return True
    except Exception as exc:
        logging.exception("Failed to save %s to disk", context)
        messagebox.showerror(
            "StashSage",
            f"Could not save settings:\n{exc}",
            parent=root if root and root.winfo_exists() else None,
        )
        return False


# Predictions render in exalts for now. A model prices in the economy it was
# trained in, and that drifts from the live one -- Forbidden Rites trained at
# 1d = 111e and now sits near 194e -- so converting a prediction into divines
# with today's rate reads as more precise than it is. There is no sound way to
# reconcile the two from exchange rates alone (the currencies move against each
# other, not just against exalt), so the selector stays hidden until we settle
# on a method. The formatting path is kept and tested; flip this to restore it.
PREDICTION_PRICE_DISPLAY_ENABLED = False

_PRICE_DISPLAY_LABELS = {
    "Auto": "auto",
    "Exalts": "exalted",
    "Divines": "divine",
    "Chaos": "chaos",
}
_PRICE_DISPLAY_VALUES = {v: k for k, v in _PRICE_DISPLAY_LABELS.items()}


def price_display_mode() -> str:
    """The denomination predictions are rendered in, from config."""
    return str(state.config.get("price_display") or "auto").strip().lower()


def _priced_text(value, conversions=None, mode: str | None = None) -> str:
    """Render a price in the chosen denomination, falling back to exalts.

    The in-process overlay is the fallback for the presenter, so it has to
    render the same way; both used to hardcode exalts while format_price sat
    imported and unused.
    """
    resolved = (mode or price_display_mode() or "auto").strip().lower()
    try:
        if resolved == "auto":
            resolved = ("divine" if abs(float(value)) >= AUTO_DIVINE_THRESHOLD_EXALTS
                        else "exalted")
        # Exalts stay whole numbers, auto included; only a chosen denomination
        # changes how these bars have always read.
        if resolved in ("", "exalted"):
            return f"{int(round(float(value))):,}e"
        return helper_format_price(float(value), resolved, conversions=conversions)
    except (TypeError, ValueError, OverflowError):
        return "?e"


def _persist_price_display(selection: str) -> None:
    """Save the denomination as soon as the user changes it, and repaint."""
    state.config["price_display"] = _PRICE_DISPLAY_LABELS.get(selection, "auto")
    _persist_settings_to_disk("price display")
    for callback in list(_PRICE_DISPLAY_LISTENERS):
        try:
            callback()
        except Exception:
            # A stale view must not break the setting for every other one.
            logging.debug("price-display listener failed", exc_info=True)


def _model_set_choices() -> list[tuple[str, str]]:
    """(label, set_id) pairs for the League picker.

    The bundled db/ tree is whatever training last mirrored, so it is normally
    a duplicate of one of the leagues below. Offering it as a separate
    "Default" entry meant two options that predict identically, which reads as
    a broken control -- so it is listed only when no installed league matches
    it, and the stored "default" id then resolves to that league instead.
    """
    choices: list[tuple[str, str]] = []
    try:
        from poe2trade.app import asset_paths
        for set_id in asset_paths.available_model_sets():
            choices.append((asset_paths.model_set_label(set_id), set_id))
        if not asset_paths.default_equivalent_set():
            league = asset_paths.bundled_set_league()
            choices.insert(0, (f"Bundled ({league})" if league else "Bundled", "default"))
    except Exception:
        logging.debug("model set discovery failed", exc_info=True)
    if not choices:
        choices = [("Bundled", "default")]
    # Two sets can carry the same league name; keep the id visible so the
    # picker never offers two entries the user cannot tell apart.
    seen: dict[str, int] = {}
    for label, _set_id in choices:
        seen[label] = seen.get(label, 0) + 1
    return [
        (label if seen[label] == 1 else f"{label} [{set_id}]", set_id)
        for label, set_id in choices
    ]


def _model_set_options() -> list[str]:
    """Selectable leagues."""
    return [label for label, _ in _model_set_choices()]


def active_model_set() -> str:
    return str(state.config.get("active_model_set") or "default").strip()


def _model_set_label(set_id: str) -> str:
    """Picker label for a stored id.

    A stored "default" resolves to whichever league the bundled tree
    duplicates, so the picker shows that league rather than an entry that is
    no longer offered. A stale id falls back to the first available league.
    """
    choices = _model_set_choices()
    for label, candidate in choices:
        if candidate == set_id:
            return label
    if set_id == "default" or not set_id:
        try:
            from poe2trade.app import asset_paths
            equivalent = asset_paths.default_equivalent_set()
        except Exception:
            logging.debug("default set equivalence failed", exc_info=True)
            equivalent = ""
        for label, candidate in choices:
            if candidate == equivalent:
                return label
    return choices[0][0] if choices else "Bundled"


def active_league() -> str:
    """League name behind the selected set, for the live rate lookup.

    Several leagues run at once and each has its own divine and chaos rates,
    so the rates have to be fetched for the league the user picked rather
    than whichever one happened to be cached first.
    """
    try:
        from poe2trade.app import asset_paths
        meta = asset_paths.model_set_metadata(active_model_set())
        league = str(meta.get("league") or meta.get("label") or "").strip()
        return league or asset_paths.bundled_set_league()
    except Exception:
        logging.debug("active league lookup failed", exc_info=True)
        return ""


def _persist_model_set(selection: str) -> None:
    """Switch model sets, then drop cached models so the swap actually takes.

    The loaded-model and bucket-stat caches are keyed by category, not by
    directory, so without clearing them the app keeps scoring with the previous
    set's pickles until restart. Each model's pricing sidecar is resolved next
    to the pickle that was loaded, so the conversions follow the swap.
    """
    chosen = next(
        (set_id for label, set_id in _model_set_choices() if label == selection),
        "default",
    )
    state.config["active_model_set"] = chosen
    _persist_settings_to_disk("model set")
    for module in ("ml_super_utils", "ml_unsuper_utils"):
        try:
            importlib.import_module(f"poe2trade.utils.{module}").clear_runtime_caches()
        except Exception:
            logging.debug("could not clear caches for %s", module, exc_info=True)
    # Each league has its own divine and chaos rates, so the displayed prices
    # are wrong until these are repulled for the league just selected.
    _refresh_live_prices_async(force=True)
    _restart_prediction_worker()


def _persist_close_behavior(selection: str) -> None:
    """Save a close preference as soon as the user changes the setting."""
    behavior = "exit" if selection == "Exit application" else "tray"
    state.config["close_behavior"] = behavior
    _persist_settings_to_disk("close behavior")


def _on_root_close():
    """Apply the user's saved main-window close action without prompting."""
    if root is None:
        return
    if _close_behavior(state.config) == "tray":
        _minimize_to_tray()
    else:
        _on_quit(None, None)


def _show_app(icon, item):
    try:
        icon.visible = False
    except Exception:
        logging.debug("tray visibility update failed", exc_info=True)
    if root is None:
        return
    try:
        def _restore_and_focus():
            root.deiconify()
            try:
                root.state("normal")
            except Exception:
                pass
            try:
                root.lift()
            except Exception:
                pass
            try:
                root.focus_force()
            except Exception:
                pass

        # Tray callbacks run outside Tk's event loop; marshal all window work
        # back onto the GUI thread.
        root.after(0, _restore_and_focus)
        # Restoring must not silently change the meaning of the window close
        # button.  The normal close prompt remains available after every
        # show/hide cycle.
        root.protocol("WM_DELETE_WINDOW", _on_root_close)
    except Exception:
        logging.debug("show from tray failed", exc_info=True)


def _setup_tray_icon():
    icon = pystray.Icon("stashsage")
    icon.icon = _create_image()
    icon.menu = pystray.Menu(
        pystray.MenuItem("Show", _show_app, default=True),
        pystray.MenuItem("Exit", _on_quit),
    )
    return icon


def _minimize_to_tray(_event=None):
    if root is None:
        return
    created_icon = False
    icon = getattr(root, "tray_icon", None)
    if icon is None:
        try:
            icon = _setup_tray_icon()
            root.tray_icon = icon
            created_icon = True
        except Exception:
            logging.exception("Failed to create tray icon")
            return
    try:
        root.withdraw()
        if created_icon:
            threading.Thread(target=icon.run, daemon=True).start()
        else:
            icon.visible = True
    except Exception:
        logging.exception("Failed to minimize to tray")
        try:
            root.deiconify()
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


if __name__ == "__main__":
    run_tkinter_app(config_manager.load_config())
