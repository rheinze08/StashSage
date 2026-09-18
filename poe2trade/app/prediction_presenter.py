"""Small, payload-only presenter used by the isolated prediction process.

This module intentionally does not import :mod:`gui_tk`.  The scoring worker
hands it ordinary mappings and PNG bytes, which keeps the pre-warmed popup
process independent of the main application's pandas/ML/import graph.
"""

from __future__ import annotations

import io
import logging
import re
import time
import tkinter as tk
import tkinter.font as tkfont
import ctypes
import sys
from pathlib import Path
from collections.abc import Mapping
from typing import Any

import customtkinter as ctk
from PIL import Image

from poe2trade.app.gui.constants import BAR_COLOUR, BAR_HEIGHT_PX, BUCKET_COLOURS
from poe2trade.app.popup_escape import coordinator
from poe2trade.utils.craft_display import craft_delta_text, craft_roll_text


_CARD_BATCH_BUDGET_S = 0.008
_CURRENCY_ICONS = {
    "e": "exalted_orb.png",
    "c": "chaos_orb.png",
    "d": "divine_orb.png",
}
_PRICE_PART_RE = re.compile(r"(\d+(?:\.\d+)?)([ecd])", re.I)
_CARD_DELTA_RE = re.compile(r"\(([+-])(\d+(?:\.\d+)?)\)")


def _images(window) -> list:
    images = getattr(window, "images", None)
    if images is None:
        images = []
        window.images = images
    return images


def add_png(parent, buf: io.BytesIO, overlay_window=None):
    image = Image.open(buf)
    rendered = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
    label = ctk.CTkLabel(parent, image=rendered, text="")
    if overlay_window is not None:
        _images(overlay_window).append(rendered)
    return label


def scaled_png_percent(parent, buf: io.BytesIO, pct: float, overlay_window=None):
    image = Image.open(buf)
    width, height = image.size
    target = max(1, int(max(1, width) * max(0.05, min(1.0, float(pct)))))
    rendered = ctk.CTkImage(light_image=image, dark_image=image, size=(target, max(1, int(height * target / max(1, width)))))
    label = ctk.CTkLabel(parent, image=rendered, text="")
    if overlay_window is not None:
        _images(overlay_window).append(rendered)
    return label


def scaled_png_fit(parent, buf: io.BytesIO, max_width: int, max_height: int, overlay_window=None):
    """Render a diagnostic image inside a consistent visual bounding box."""
    image = Image.open(buf)
    width, height = image.size
    scale = min(max_width / max(1, width), max_height / max(1, height))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    rendered = ctk.CTkImage(light_image=image, dark_image=image, size=size)
    label = ctk.CTkLabel(parent, image=rendered, text="")
    if overlay_window is not None:
        _images(overlay_window).append(rendered)
    return label


def _currency_icon(parent, unit: str, overlay_window, *, size: int = 20):
    """Create a small orb icon label, retaining the CTkImage lifetime."""
    filename = _CURRENCY_ICONS.get(str(unit).lower())
    if not filename:
        return None
    cache = getattr(overlay_window, "currency_images", {})
    key = (str(unit).lower(), size)
    rendered = cache.get(key)
    if rendered is None:
        path = Path(__file__).with_name("currency_icons") / filename
        try:
            with Image.open(path) as source:
                image = source.convert("RGBA")
                image.thumbnail((size, size), Image.Resampling.LANCZOS)
                rendered = ctk.CTkImage(light_image=image.copy(), dark_image=image.copy(), size=image.size)
        except (OSError, ValueError):
            return None
        cache[key] = rendered
        overlay_window.currency_images = cache
        _images(overlay_window).append(rendered)
    return ctk.CTkLabel(parent, image=rendered, text="")


def _price_row(parent, text: str, row: int, overlay_window) -> None:
    row_frame = ctk.CTkFrame(parent, fg_color="transparent")
    row_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 0))
    ctk.CTkLabel(row_frame, text="Price:", text_color="#AEBCC9", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 8))
    for index, match in enumerate(_PRICE_PART_RE.finditer(text)):
        if index:
            ctk.CTkLabel(row_frame, text=" · ", text_color="#667582", font=("Segoe UI", 13)).pack(side="left")
        icon = _currency_icon(row_frame, match.group(2), overlay_window, size=20)
        if icon is not None:
            icon.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(row_frame, text=match.group(1), text_color="#BBD8F0", font=("Segoe UI", 14, "bold")).pack(side="left")


def textbox(parent, lines, yellow, colours, row, col, *, height=None, filter_tags=None):
    widget = ctk.CTkTextbox(parent, height=height or max(100, (len(lines) + 2) * 22))
    widget.grid(row=row, column=col, sticky="nsew", columnspan=2)
    widget.tag_config("yellow", foreground="#FFD700")
    widget.tag_config("plus", foreground="#4CAF50")
    widget.tag_config("minus", foreground="#E74C3C")
    widget.tag_config("filter", foreground="#7FBFF6")
    for index, value in enumerate(lines):
        widget.insert("end", f"{value}\n")
        delta_start = value.find("(") if index in colours else -1
        if index in yellow:
            end = delta_start if delta_start >= 0 else len(value)
            widget.tag_add("yellow", f"{index + 1}.0", f"{index + 1}.{end}")
        if delta_start >= 0:
            widget.tag_add(colours[index], f"{index + 1}.{delta_start}", f"{index + 1}.end")
        if filter_tags and index in filter_tags:
            marker = value.rfind(filter_tags[index])
            if marker >= 0:
                widget.tag_add("filter", f"{index + 1}.{marker}", f"{index + 1}.{marker + len(filter_tags[index])}")
    widget.configure(state="disabled")
    return widget


def validate_payload(payload: Mapping[str, Any]) -> bool:
    """Return whether a worker result has the small presenter contract."""
    if not isinstance(payload, Mapping):
        return False
    cards = payload.get("comparison_cards", [])
    return isinstance(cards, (list, tuple)) and all(isinstance(card, Mapping) for card in cards)


def _triple(value: object) -> str:
    try:
        return f"{float(value):,.2f}e"
    except (TypeError, ValueError):
        return "?e"


def _whole_exalts(value: object) -> str:
    """Format a value as a whole exalt count (nearest integer)."""
    try:
        return f"{int(round(float(value))):,}e"
    except (TypeError, ValueError, OverflowError):
        return "?e"


def _priced(value: object, payload: Mapping[str, Any]) -> str:
    """Render a price in the denomination the user chose.

    The overlay is drawn in this process from a payload, so the setting has to
    travel with it; the prediction was formatted as exalts whatever the picker
    said. Falls back to whole exalts when the payload predates the setting or
    the conversions are unusable -- which is what every caller rendered before.
    """
    mode = str(payload.get("price_display_mode") or "auto").strip().lower()
    try:
        from poe2trade.app.gui.ui_helpers import (
            AUTO_DIVINE_THRESHOLD_EXALTS,
            format_price,
        )
    except Exception:
        return _whole_exalts(value)
    if mode == "auto":
        try:
            mode = ("divine" if abs(float(value)) >= AUTO_DIVINE_THRESHOLD_EXALTS
                    else "exalted")
        except (TypeError, ValueError, OverflowError):
            return _whole_exalts(value)
    # Exalts keep their whole-number rendering, auto included: that is what this
    # bar has always shown, and only a deliberately chosen denomination should
    # change it.
    if mode in ("", "exalted"):
        return _whole_exalts(value)
    try:
        return format_price(float(value), mode, conversions=payload.get("model_conversion"))
    except Exception:
        return _whole_exalts(value)


def _craft_roll_text(row: Mapping[str, Any]) -> str:
    """Describe one Craft roll using the shared presentation contract."""
    return craft_roll_text(row)


def _model_conversion_text(snapshot: Mapping[str, Any]) -> str:
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


def _xgb_bar_text(payload: Mapping[str, Any]) -> str:
    label = str(payload.get("bucket_label") or "estimated").strip().capitalize()
    return (
        f"Model #1 - XGB  |  Prediction: {_prediction_prices(payload.get('display_value'), payload.get('model_conversion'))}"
        f"  |  Relative {label} value"
    )


def _knn_bar_text(
    payload: Mapping[str, Any], summary: Mapping[str, Any] | None
) -> str:
    parts = ["Model #2 - KNN"]
    conversion = payload.get("knn_conversion") or payload.get("model_conversion")
    if isinstance(summary, Mapping):
        for key, label in (("median", "Median Prediction"), ("mean", "Mean Prediction")):
            parts.append(f"{label}: {_prediction_prices(summary.get(key), conversion)}")
    prices = payload.get("listing_prices")
    if isinstance(prices, (list, tuple)):
        values = [str(value).strip().removesuffix("e") for value in prices if str(value).strip()]
        if values:
            return "  |  ".join(parts) + f"\n{len(values)} Similar Item Prices {{e}}: [" + ", ".join(values) + "]"
    return "  |  ".join(parts)


def _prediction_prices(value: object, conversions=None) -> str:
    """Keep each prediction in its own model's training economy."""
    from poe2trade.app.gui.ui_helpers import format_price

    try:
        value = float(value)
        return _whole_exalts(value) + "   " + "   ".join(
            format_price(value, mode, conversions=conversions)
            for mode in ("chaos", "divine")
        )
    except (TypeError, ValueError, OverflowError):
        return "?e   ?c   ?d"


def _model_price_bar(parent, text: str, overlay_window, *, colour: str, text_colour="white"):
    """Embed the same orb labels as item cards, wrapping long KNN summaries."""
    bar = ctk.CTkFrame(parent, fg_color=colour, corner_radius=8)
    font = ("Segoe UI", -15, "bold")
    content = tk.Text(
        bar, height=1, width=1, wrap="word", borderwidth=0, highlightthickness=0,
        background=colour, foreground=text_colour, font=font,
        cursor="arrow", takefocus=False, padx=0, pady=0,
    )
    content.place(x=8, rely=0.5, anchor="w", relwidth=1, width=-16, height=1)
    content.tag_configure("center", justify="center")
    tokens = re.compile(r"([<>]?-?[\d,]+(?:\.\d+)?|\?)([ecd])\b|\{([ecd])\}")
    end = 0
    for match in tokens.finditer(text):
        content.insert("end", text[end:match.start()])
        unit = match.group(2) or match.group(3)
        # Keep an orb and its value together when the text wraps.
        group = tk.Frame(content, background=colour)
        icon = _currency_icon(group, unit, overlay_window, size=20)
        if icon is not None:
            icon.pack(side="left", padx=(0, 2))
            if match.group(1):
                tk.Label(
                    group, text=match.group(1), font=font, background=colour,
                    foreground=text_colour, borderwidth=0, padx=0, pady=0,
                ).pack(side="left")
            content.window_create("end", window=group, padx=2, align="center")
        else:
            group.destroy()
            content.insert("end", (match.group(1) or "") + unit)
        end = match.end()
    content.insert("end", text[end:])
    content.tag_add("center", "1.0", "end")
    content.configure(state="disabled")
    line_height = tkfont.Font(font=font).metrics("linespace")

    def fit(_event=None):
        if content.winfo_exists():
            # Embedded orb widgets can be taller than a normal text line.
            pixels = content.count("1.0", "end", "update", "ypixels")
            height = max(line_height, pixels or 0)
            if content.winfo_height() != height:
                content.place_configure(height=height)
                # Native Text sizes are pixels; CTk frame heights are scaled.
                # Exact sizing avoids a spare partial line below the text.
                bar.configure(height=height / bar._get_widget_scaling() + 12)

    content.bind("<Configure>", fit, add="+")
    content.after_idle(fit)
    return bar


def _png(value: object) -> io.BytesIO | None:
    return io.BytesIO(value) if isinstance(value, (bytes, bytearray)) and value else None


def _line(card: Mapping[str, Any], side: str) -> tuple[list[str], set[int], dict[int, str], dict[int, str]]:
    texts: list[str] = []
    yellow: set[int] = set()
    colours: dict[int, str] = {}
    tags: dict[int, str] = {}
    for index, raw in enumerate(card.get("lines", [])):
        if not isinstance(raw, Mapping):
            continue
        text = str(raw.get("left_text" if side == "left" else "right_text") or "")
        texts.append(text)
        style = raw.get("left_style" if side == "left" else "right_style")
        if style == "yellow":
            yellow.add(index)
        if style in {"plus", "minus"}:
            colours[index] = str(style)
        elif "(+" in text:
            colours[index] = "plus"
        elif "(-" in text:
            colours[index] = "minus"
        annotation = raw.get("filter_annotation")
        if side == "right" and annotation:
            tags[index] = f"[{annotation}]"
    return texts, yellow, colours, tags


class PredictionPresenter:
    """Own the popup's root, overlay lifecycle, and dashboard widgets."""

    def __init__(self, root: ctk.CTk, request_id: int, on_close, monitor_rect=None) -> None:
        self.root = root
        self.request_id = request_id
        self.on_close = on_close
        self.monitor_rect = self._physical_monitor_rect(monitor_rect)
        self.overlay: ctk.CTkToplevel | None = None
        self.loading_overlay: ctk.CTkToplevel | None = None
        self.result_overlay: ctk.CTkToplevel | None = None
        self.backdrop: tk.Toplevel | None = None
        self.cover: ctk.CTkFrame | None = None
        self.loading_progress: ctk.CTkProgressBar | None = None
        self.loading_status_label = None
        self._loading_rotation_after = None
        self._backdrop_click_pending = False
        self._backdrop_click_action = None
        # The window (normally PoE) that was foreground before this presenter
        # took keyboard focus; focus is handed back to it on close.
        self._return_hwnd: int | None = None
        self.closed = False

    def _physical_monitor_rect(self, rect):
        """Return the native-pixel desktop rectangle supplied by the parent.

        ``gui_tk`` normalizes Windows game rectangles before process handoff.
        They must remain intact here: scaling a global X/Y coordinate using
        this process's primary-screen scale moves secondary-monitor overlays
        to the wrong virtual-desktop position.
        """
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        try:
            scale = float(self.root._get_window_scaling())
        except Exception:
            scale = 1.0
        physical_w, physical_h = round(screen_w * scale), round(screen_h * scale)
        if not rect or len(rect) != 4:
            return 0, 0, physical_w, physical_h
        return tuple(int(value) for value in rect)

    def _close(self, *_event) -> None:
        if self.closed:
            return
        self.closed = True
        logging.info("Prediction presenter close requested (request=%s)", self.request_id)
        # Withdrawing native toplevels is effectively instantaneous, whereas
        # tearing down several CTk surfaces can briefly block on Windows.  Do
        # this first so a click-out feels immediate; the normal destruction
        # below still performs the complete resource cleanup.
        self._restore_focus()
        self._withdraw_windows()
        for window in (self.cover, self.loading_overlay, self.result_overlay, self.overlay, self.backdrop):
            try:
                if window is not None and window.winfo_exists():
                    window.destroy()
            except tk.TclError:
                pass
        self.cover = None
        self.loading_progress = None
        self.loading_status_label = None
        self.overlay = None
        self.loading_overlay = None
        self.result_overlay = None
        self.backdrop = None
        self.on_close()

    def hide(self) -> None:
        """Hide the current overlay while keeping the presenter process warm."""
        self._restore_focus()
        self._withdraw_windows()
        for window in (self.cover, self.loading_overlay, self.result_overlay, self.overlay, self.backdrop):
            try:
                if window is not None and window.winfo_exists():
                    window.destroy()
            except tk.TclError:
                pass
        self.cover = None
        self.loading_progress = None
        self.loading_status_label = None
        self.overlay = None
        self.loading_overlay = None
        self.result_overlay = None
        self.backdrop = None

    def _withdraw_windows(self) -> None:
        """Remove top-level windows from the screen before expensive cleanup."""
        escape = getattr(self.root, "_popup_escape", None)
        if escape is not None:
            escape.unregister(getattr(self, "_escape_token", None))
        try:
            if self._loading_rotation_after is not None:
                self.root.after_cancel(self._loading_rotation_after)
        except tk.TclError:
            pass
        self._loading_rotation_after = None
        self._backdrop_click_pending = False
        self._backdrop_click_action = None
        try:
            if self.backdrop is not None and self.backdrop.winfo_exists():
                self.backdrop.grab_release()
        except tk.TclError:
            pass
        withdrawn: set[int] = set()
        for window in (self.loading_overlay, self.result_overlay, self.overlay, self.backdrop):
            try:
                if window is not None and id(window) not in withdrawn and window.winfo_exists():
                    window.withdraw()
                    withdrawn.add(id(window))
            except tk.TclError:
                pass

    def _shell(self, *, hidden: bool = False) -> ctk.CTkToplevel:
        # The presenter runs in its own process and therefore does not inherit
        # the main application's appearance setting.  Force the dashboard's
        # dark palette instead of accepting the host compositor's light theme.
        ctk.set_appearance_mode("dark")
        # Ctrl+2's legacy editor imports gui_tk, which disables CTk's automatic
        # DPI awareness at module import time. Reassert the presenter policy
        # before every warm-host window so Ctrl+2 cannot affect later hotkeys.
        try:
            from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker
            ScalingTracker.deactivate_automatic_dpi_awareness = False
        except Exception:
            pass
        mon_x, mon_y, mon_w, mon_h = self.monitor_rect
        self.backdrop = tk.Toplevel(self.root)
        self.backdrop.overrideredirect(True)
        self.backdrop.configure(background="#000000")
        self.backdrop.attributes("-alpha", 0.0)
        self.backdrop.attributes("-topmost", True)
        if sys.platform.startswith("linux"):
            # X11 window managers commonly keep splash windows out of normal
            # activation/task-switch handling. Wayland may ignore this hint,
            # but the full-screen native backdrop still consumes the click.
            try:
                self.backdrop.wm_attributes("-type", "splash")
            except tk.TclError:
                pass
        self.backdrop.geometry(f"{mon_w}x{mon_h}+{mon_x}+{mon_y}")
        self.backdrop.bind("<Button-1>", self._consume_backdrop_click)
        self.backdrop.update_idletasks()
        self._make_nonactivating(self.backdrop)
        self.overlay = ctk.CTkToplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        # Keep the provisional geometry invisible.  Windows can paint a
        # deiconified toplevel before _fit_overlay() applies the DPI-correct
        # size and centered position, which otherwise produces a visible
        # smaller/up-left jump on every popup.
        self.overlay.attributes("-alpha", 0.0)
        self.overlay.withdraw()
        self.overlay.geometry(f"{min(int(mon_w * .8), 1600)}x{min(int(mon_h * .88), 1000)}+{mon_x}+{mon_y}")
        self._responsive_minsize(self.overlay)
        self.overlay.images = []
        self.overlay.protocol("WM_DELETE_WINDOW", self._close)
        self._bind_escape(self.overlay)
        self._add_close_control(self.overlay)
        self.overlay.deiconify()
        self.overlay.update_idletasks()
        self._fit_overlay()
        self.overlay.update_idletasks()
        if not hidden:
            self.overlay.attributes("-alpha", 1.0)
            self.overlay.lift()
            self._enable_escape(self.overlay)
            self._take_focus(self.overlay)
        self._fade_backdrop()
        return self.overlay

    def _hidden_result_shell(self) -> ctk.CTkToplevel:
        """Create a complete-but-invisible result surface for an atomic swap."""
        mon_x, mon_y, mon_w, mon_h = self.monitor_rect
        result = ctk.CTkToplevel(self.root)
        result.overrideredirect(True)
        result.attributes("-topmost", True)
        result.attributes("-alpha", 0.0)
        result.geometry(
            f"{min(int(mon_w * .8), 1600)}x{min(int(mon_h * .88), 1000)}+{mon_x}+{mon_y}"
        )
        self._responsive_minsize(result)
        result.images = []
        result.protocol("WM_DELETE_WINDOW", self._close)
        self._bind_escape(result)
        self._add_close_control(result)
        # An alpha-zero deiconified window can finish native layout, scrolling,
        # and image creation without being visible to the user.
        result.deiconify()
        result.update_idletasks()
        self._fit_overlay(result)
        result.update_idletasks()
        return result

    def _enable_escape(self, window) -> None:
        self._escape_token = coordinator(self.root).register(
            window, self._close, getattr(self, "_escape_token", None),
        )
        if sys.platform != "win32":
            window.focus_force()

    def reveal_overlay(self, window=None) -> bool:
        """Reveal a window owned by this host without changing the backdrop.

        Craft, filter, and prediction views all use this one transition point.
        In particular, a view must never create a second backdrop or native
        click target merely to replace its content.
        """
        target = window or self.overlay
        if target is None:
            return False
        try:
            if not target.winfo_exists():
                return False
            target.update_idletasks()
            target.attributes("-alpha", 1.0)
            target.lift()
            self._enable_escape(target)
            close_control = getattr(target, "_presenter_close_control", None)
            if close_control is not None:
                close_control.lift()
            self._take_focus(target)
            return True
        except tk.TclError:
            return False

    def _consume_backdrop_click(self, _event=None):
        """Claim both halves of a click before removing the backdrop.

        Closing during ButtonPress exposes the game beneath the still-held
        mouse button.  In an inventory that can complete the same item pickup
        the user meant to dismiss, so retain a native grab until ButtonRelease.
        """
        self._arm_close_click(self._close)
        return "break"

    def _arm_close_click(self, action) -> bool:
        """Retain the backdrop until a close-button click has fully released.

        A CTk button normally invokes its command on button release.  Keeping
        the native backdrop grabbed until then prevents that release from
        reaching PoE if the action removes the presenter immediately.  This
        is deliberately limited to dismissing actions; it is not a global
        mouse hook and therefore adds no hotkey or pointer latency.
        """
        if self.closed or self.backdrop is None or self._backdrop_click_pending:
            return False
        try:
            self.backdrop.bind("<ButtonRelease-1>", self._finish_backdrop_click)
            self.backdrop.grab_set_global()
        except tk.TclError:
            return False
        self._backdrop_click_pending = True
        self._backdrop_click_action = action
        return True

    def protect_close_button(self, button, action) -> None:
        """Make a mouse-activated close/action consume its own release."""
        def arm(_event=None):
            if self._arm_close_click(action):
                return "break"
            return None

        button.bind("<ButtonPress-1>", arm, add="+")

    def _finish_backdrop_click(self, _event=None):
        """Release the native mouse grab and dismiss after ButtonRelease."""
        if not self._backdrop_click_pending:
            return "break"
        self._backdrop_click_pending = False
        action = self._backdrop_click_action or self._close
        self._backdrop_click_action = None
        try:
            if self.backdrop is not None and self.backdrop.winfo_exists():
                self.backdrop.grab_release()
        except tk.TclError:
            pass
        try:
            self.root.after_idle(action)
        except tk.TclError:
            action()
        return "break"

    def _bind_escape(self, window) -> None:
        """Close on Escape while this overlay has keyboard focus.

        A toplevel binding (not ``bind_all``) fires for every child widget of
        the focused panel, but never once the user has focused another
        application. Clicking the panel re-activates it; the backdrop stays
        non-activating so a click there simply closes.

        Closing waits for the physical key release. Focus is handed back to
        PoE on close, so closing on the press would deliver the rest of the
        keystroke (auto-repeat or the release) to the game and could toggle
        its Escape menu. A release whose press didn't land on this panel,
        e.g. Escape pressed in-game as the overlay appeared, is ignored.
        """
        pressed = False

        def on_press(_event=None):
            nonlocal pressed
            pressed = True
            return "break"

        def close_when_released() -> None:
            if self.closed:
                return
            if sys.platform == "win32":
                try:
                    if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:  # VK_ESCAPE
                        # Tk synthesizes a release before each auto-repeat.
                        window.after(15, close_when_released)
                        return
                except (AttributeError, OSError, tk.TclError):
                    pass
            self._close()

        def on_release(_event=None):
            if pressed:
                close_when_released()
            return "break"

        window.bind("<KeyPress-Escape>", on_press)
        window.bind("<KeyRelease-Escape>", on_release)

    @staticmethod
    def _user32_focus_api():
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
        user32.AttachThreadInput.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_bool]
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        user32.BringWindowToTop.argtypes = [ctypes.c_void_p]
        user32.IsWindow.argtypes = [ctypes.c_void_p]
        return user32, kernel32

    def _take_focus(self, window) -> None:
        """Give a revealed overlay keyboard focus so Escape reaches it.

        The hotkey fires while PoE is foreground, and a background process may
        not simply call SetForegroundWindow, so briefly attach to the
        foreground thread's input queue.  A couple of short retries cover the
        hotkey's own key release racing activation; retries stop as soon as
        the user has moved to some other window.
        """
        def attempt(retries_left: int) -> None:
            if self.closed:
                return
            try:
                if not window.winfo_exists():
                    return
            except tk.TclError:
                return
            if sys.platform == "win32":
                try:
                    user32, kernel32 = self._user32_focus_api()
                    current_thread = int(kernel32.GetCurrentThreadId())
                    foreground = int(user32.GetForegroundWindow() or 0)
                    foreground_thread = (
                        int(user32.GetWindowThreadProcessId(foreground, None)) if foreground else 0
                    )
                    if foreground_thread != current_thread:
                        if self._return_hwnd is None:
                            self._return_hwnd = foreground or None
                        elif foreground and foreground != self._return_hwnd:
                            return  # the user focused another application
                        hwnd = int(user32.GetAncestor(int(window.winfo_id()), 2) or 0)  # GA_ROOT
                        attached = bool(
                            foreground_thread
                            and user32.AttachThreadInput(current_thread, foreground_thread, True)
                        )
                        try:
                            user32.BringWindowToTop(hwnd)
                            user32.SetForegroundWindow(hwnd)
                        finally:
                            if attached:
                                user32.AttachThreadInput(current_thread, foreground_thread, False)
                except (AttributeError, OSError, TypeError, ValueError):
                    logging.debug("Could not foreground presenter overlay", exc_info=True)
            try:
                window.focus_force()
            except tk.TclError:
                return
            if retries_left > 0:
                try:
                    window.after(80, lambda: attempt(retries_left - 1))
                except tk.TclError:
                    pass

        attempt(2)

    def _restore_focus(self) -> None:
        """Hand keyboard focus back to the game if this overlay still holds it."""
        target, self._return_hwnd = self._return_hwnd, None
        if sys.platform != "win32" or not target:
            return
        try:
            user32, kernel32 = self._user32_focus_api()
            foreground = int(user32.GetForegroundWindow() or 0)
            if not foreground or int(user32.GetWindowThreadProcessId(foreground, None)) != int(
                kernel32.GetCurrentThreadId()
            ):
                return  # focus already moved elsewhere; leave it there
            if user32.IsWindow(target):
                user32.SetForegroundWindow(target)
        except (AttributeError, OSError, TypeError, ValueError):
            logging.debug("Could not restore game focus", exc_info=True)

    def _make_nonactivating(self, window) -> None:
        """Stop a click on the dimmed backdrop from activating it."""
        if sys.platform != "win32" or window is None:
            return
        try:
            hwnd = int(window.winfo_id())
            user32 = ctypes.windll.user32
            is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
            get_proc = user32.GetWindowLongPtrW if is_64bit else user32.GetWindowLongW
            set_proc = user32.SetWindowLongPtrW if is_64bit else user32.SetWindowLongW
            long_type = ctypes.c_ssize_t if is_64bit else ctypes.c_long
            get_proc.argtypes = [ctypes.c_void_p, ctypes.c_int]
            get_proc.restype = long_type
            set_proc.argtypes = [ctypes.c_void_p, ctypes.c_int, long_type]
            set_proc.restype = long_type
            ex_style = int(get_proc(hwnd, -20))  # GWL_EXSTYLE
            set_proc(hwnd, -20, long_type(ex_style | 0x08000000))  # WS_EX_NOACTIVATE
        except (AttributeError, OSError, TypeError, ValueError):
            logging.debug("Could not make presenter surface non-activating", exc_info=True)

    def _add_close_control(self, window) -> None:
        control = ctk.CTkButton(
            window,
            text="Close",
            command=self._close,
            width=58,
            height=26,
            fg_color="#303940",
            hover_color="#414C54",
            font=("Segoe UI", 11, "bold"),
        )
        control.place(relx=1.0, rely=0.0, anchor="ne", x=-12, y=12)
        self.protect_close_button(control, self._close)
        window._presenter_close_control = control

    def _fade_backdrop(self, alpha: float = 0.0) -> None:
        try:
            if self.backdrop is None or not self.backdrop.winfo_exists():
                return
            next_alpha = min(0.48, alpha + 0.08)
            self.backdrop.attributes("-alpha", next_alpha)
            if self.overlay is not None and self.overlay.winfo_exists():
                self.overlay.lift()
            if next_alpha < 0.48:
                self.backdrop.after(20, lambda: self._fade_backdrop(next_alpha))
        except tk.TclError:
            return

    def _fit_overlay(self, window=None) -> None:
        """Fit in physical pixels, compensating for CTk's DPI scaling."""
        target = window or self.overlay
        if target is None:
            return
        try:
            if not target.winfo_exists():
                return
            mon_x, mon_y, mon_w, mon_h = self.monitor_rect
            target_w = min(int(mon_w * 0.80), 1600)
            target_h = min(int(mon_h * 0.88), 1000)
            scale = float(target._get_window_scaling())
        except (tk.TclError, AttributeError):
            scale = 1.0
        scale = scale if scale > 0 else 1.0
        try:
            target.geometry(f"{max(1, round(target_w / scale))}x{max(1, round(target_h / scale))}")
            target.update()
            actual_w, actual_h = int(target.winfo_width()), int(target.winfo_height())
            if actual_w <= 1 or actual_h <= 1:
                actual_w, actual_h = target_w, target_h
            target.geometry(f"+{mon_x + (mon_w - actual_w) // 2}+{mon_y + (mon_h - actual_h) // 2}")
        except tk.TclError:
            # Craft progress can race a close/reset; its next command will
            # create a fresh surface, so a stale native handle is harmless.
            return

    def _responsive_minsize(self, window) -> None:
        """Keep the dashboard usable without forcing it beyond small screens."""
        _mon_x, _mon_y, mon_w, mon_h = self.monitor_rect
        try:
            scale = max(1.0, float(window._get_window_scaling()))
        except Exception:
            scale = 1.0
        target_w = max(1, round(min(int(mon_w * 0.80), 1600) / scale))
        target_h = max(1, round(min(int(mon_h * 0.88), 1000) / scale))
        min_w = min(target_w, max(560, round(mon_w * 0.55 / scale)))
        min_h = min(target_h, max(420, round(mon_h * 0.55 / scale)))
        window.minsize(min_w, min_h)

    def show_loading(
        self,
        *,
        title: str = "Pricing item...",
        detail: str = "Checking model estimates and comparable listings.",
        hint: str = "Press Esc or click outside the panel to close",
        reuse_shell: bool = False,
    ) -> None:
        shell = self.overlay if reuse_shell and self.overlay is not None else self._shell()
        panel = ctk.CTkFrame(shell, corner_radius=0, fg_color="#1E1E1E")
        self.loading_overlay = self.overlay
        panel.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.cover = panel
        ctk.CTkLabel(panel, text=title, font=("Segoe UI", 20, "bold")).pack(pady=(28, 8))
        self.loading_status_label = ctk.CTkLabel(panel, text=detail, text_color="#AEBCC9")
        self.loading_status_label.pack(pady=(0, 20))
        try:
            logo_path = Path(__file__).with_name("sidebar_icons") / "sage_logo_v11.png"
            with Image.open(logo_path) as source:
                logo = source.convert("RGBA")
                logo.thumbnail((128, 128), Image.Resampling.LANCZOS)
            rendered_logo = ctk.CTkImage(light_image=logo, dark_image=logo, size=logo.size)
            _images(self.overlay).append(rendered_logo)
            ctk.CTkLabel(panel, image=rendered_logo, text="").pack(pady=(0, 12))
        except Exception:
            logging.debug("Could not load prediction loading logo", exc_info=True)
        progress = ctk.CTkProgressBar(panel, mode="indeterminate", indeterminate_speed=1, width=300, height=14)
        self.loading_progress = progress
        progress.pack(pady=(0, 12))
        progress.start()
        ctk.CTkLabel(panel, text=hint, text_color="#7E8C99").pack()
        self.overlay.update_idletasks()
        messages = (
            detail,
            "Estimating value across the trained models.",
            "Preparing comparison cards and price context.",
            "Finalizing the complete result view.",
        )

        def rotate(index: int = 1) -> None:
            if self.closed or self.loading_status_label is None:
                return
            try:
                if not self.loading_status_label.winfo_exists():
                    return
                self.loading_status_label.configure(text=messages[index % len(messages)])
                self._loading_rotation_after = self.overlay.after(1100, lambda: rotate(index + 1))
            except tk.TclError:
                return

        self._loading_rotation_after = self.overlay.after(1100, rotate)

    def update_loading_detail(self, detail: str) -> None:
        try:
            if self.loading_status_label is not None and self.loading_status_label.winfo_exists():
                self.loading_status_label.configure(text=detail)
        except tk.TclError:
            pass

    def _banner(self, parent, summary: Mapping[str, Any], detail: object) -> None:
        values = []
        for key, label in (("median", "median"), ("mean", "mean")):
            try:
                if summary.get(key) is not None:
                    values.append(f"{int(round(float(summary[key])))}e ({label})")
            except (TypeError, ValueError):
                pass
        count = summary.get("count")
        count_text = f"{int(count)} comparable listings" if isinstance(count, (int, float)) else "Comparable listings"
        text = f"Model #2 Similar Items  ·  {', '.join(values)}"
        text += f"\n{count_text}"
        ctk.CTkLabel(
            parent, text=text, fg_color=BAR_COLOUR, corner_radius=8,
            text_color="white", font=("Segoe UI", 22, "bold"),
            justify="center", wraplength=1200, height=BAR_HEIGHT_PX,
        ).pack(fill="x", padx=4, pady=(0, 4))

    def _conversion_banner(self, parent, snapshot: Mapping[str, Any]) -> None:
        values = snapshot.get("conversions") if isinstance(snapshot, Mapping) else None
        if not isinstance(values, Mapping):
            return
        is_mock = bool(snapshot.get("is_mock", False))
        frame = ctk.CTkFrame(parent, fg_color="#34495E", corner_radius=8)
        frame.pack(fill="x", padx=4, pady=(0, 3))
        heading = "Model training conversions (demo)" if is_mock else "Model training conversions"
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(anchor="center", padx=8, pady=5)
        ctk.CTkLabel(
            row,
            text=heading,
            font=("Segoe UI", 13, "bold"),
            text_color="#E0A53B" if is_mock else "#BBD8F0",
        ).pack(side="left")
        # Same "?" affordance the settings use, so the reader can find out why
        # these numbers are not the live ones without leaving the overlay.
        try:
            from poe2trade.app.gui.ui_helpers import help_badge

            help_badge(
                row,
                "These are the currency rates when this model was trained. "
                "The prediction is expressed in that economy, not today's. "
                "If the market has moved a lot since, treat the number as a "
                "guide and adjust.",
            ).pack(side="left", padx=(6, 0))
        except Exception:
            logging.debug("Could not attach the training-rates help badge", exc_info=True)
        ctk.CTkLabel(
            row, text="  |  ", font=("Segoe UI", 13, "bold"), text_color="#90A6B5"
        ).pack(side="left")

        names = {"d": "divine", "c": "chaos"}
        for index, unit in enumerate(("d", "c")):
            if index:
                ctk.CTkLabel(
                    row, text="  ·  ", font=("Segoe UI", 13), text_color="#90A6B5"
                ).pack(side="left")
            source_icon = _currency_icon(row, unit, self.overlay, size=20)
            if source_icon is not None:
                source_icon.pack(side="left", padx=(0, 3))
            ctk.CTkLabel(
                row, text="=", font=("Segoe UI", 13, "bold"), text_color="white"
            ).pack(side="left", padx=(0, 3))
            try:
                value: object = int(round(float(values.get(names[unit]))))
            except (TypeError, ValueError, OverflowError):
                value = "?"
            ctk.CTkLabel(
                row, text=str(value), font=("Segoe UI", 13, "bold"), text_color="white"
            ).pack(side="left", padx=(0, 2))
            exalt_icon = _currency_icon(row, "e", self.overlay, size=20)
            if exalt_icon is not None:
                exalt_icon.pack(side="left")

    def _band(self, parent, payload: Mapping[str, Any]) -> None:
        label = str(payload.get("bucket_label") or "").capitalize()
        colour = BUCKET_COLOURS.get(label.lower(), BAR_COLOUR)
        frame = ctk.CTkFrame(parent, fg_color=colour, corner_radius=8, height=44)
        frame.pack(fill="x", padx=4, pady=(0, 4))
        ctk.CTkLabel(
            frame,
            text=_xgb_bar_text(payload),
            font=("Segoe UI", 15, "bold"),
            text_color="white",
            anchor="center",
            justify="center",
        ).pack(fill="x", padx=8, pady=6)

    def _model_summary_row(
        self,
        parent,
        payload: Mapping[str, Any],
        summary: Mapping[str, Any] | None,
        conversion: Mapping[str, Any] | None,
    ) -> None:
        """Frame Model #1 with the StashSage crest above Model #2 context."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.pack(fill="x", padx=4, pady=(0, 6))
        layout.grid_columnconfigure(0, weight=0, minsize=150)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_columnconfigure(2, weight=0, minsize=150)

        def brand_crest(column: int) -> None:
            """Use the loader crest as a deliberate frame, not item art."""
            try:
                logo_path = Path(__file__).with_name("sidebar_icons") / "sage_logo_v11.png"
                with Image.open(logo_path) as source:
                    logo = source.convert("RGBA")
                    logo.thumbnail((130, 130), Image.Resampling.LANCZOS)
                rendered_logo = ctk.CTkImage(light_image=logo, dark_image=logo, size=logo.size)
                _images(self.overlay).append(rendered_logo)
                ctk.CTkLabel(layout, image=rendered_logo, text="").grid(
                    row=0, column=column, rowspan=3, sticky="ns", pady=4
                )
            except Exception:
                logging.debug("Could not load prediction header crest", exc_info=True)

        brand_crest(0)
        brand_crest(2)
        label = str(payload.get("bucket_label") or "").capitalize()
        colour = BUCKET_COLOURS.get(label.lower(), BAR_COLOUR)
        model_one = _model_price_bar(layout, _xgb_bar_text(payload), self.overlay, colour=colour)
        model_one.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        model_two = _model_price_bar(
            layout, _knn_bar_text(payload, summary), self.overlay,
            colour="#294354", text_colour="#E3F2FA",
        )
        model_two.grid(row=2, column=1, sticky="ew", padx=8, pady=(4, 0))

    def _card(self, body, card: Mapping[str, Any], index: int) -> None:
        for column, side in enumerate(("left", "right")):
            frame_colour = "#252A30" if side == "left" else "#232D35"
            frame = ctk.CTkFrame(body, fg_color=frame_colour, corner_radius=8)
            frame.grid(row=index, column=column, sticky="nsew", padx=(6, 4) if column == 0 else (4, 6), pady=4)
            frame.columnconfigure(1, weight=1)
            icon = _png(card.get("left_icon_png" if side == "left" else "right_icon_png"))
            title = card.get("your_item_name" if side == "left" else "matched_item_name") or "Similar Item"
            col = 0
            if icon:
                frame.columnconfigure(0, minsize=52)
                add_png(frame, icon, self.overlay).grid(
                    row=0, column=0, rowspan=2, sticky="", padx=(2, 6), pady=(2, 0)
                )
                col = 1
            ctk.CTkLabel(
                frame,
                text=f"{title} (Your Item)" if side == "left" else str(title),
                font=("Consolas", 17, "bold"),
                text_color="#E8EEF4" if side == "left" else "#C8DCEB",
                anchor="w",
            ).grid(row=0, column=col, sticky="we", padx=(0, 6))
            if side == "right":
                replacements, roll_differences, higher_rolls = self._card_modifier_summary(card)
                parts = []
                if replacements:
                    parts.append(f"{replacements} replaced affix{'es' if replacements != 1 else ''}")
                if roll_differences:
                    parts.append(f"{roll_differences} roll difference{'s' if roll_differences != 1 else ''}")
                if higher_rolls:
                    parts.append(f"{higher_rolls} higher roll{'s' if higher_rolls != 1 else ''}")
                summary_text = "  ·  ".join(parts) or "Same compared modifier rolls"
                summary_colour = "#77C9A5" if higher_rolls else "#9AA7B4"
            else:
                summary_text = "Baseline modifier rolls"
                summary_colour = "#9AA7B4"
            ctk.CTkLabel(
                frame,
                text=summary_text,
                font=("Segoe UI", 11),
                text_color=summary_colour,
                anchor="w",
            ).grid(row=1, column=col, sticky="we", padx=(0, 6), pady=(0, 2))
            texts, yellow, colours, tags = _line(card, side)
            price_text = next((value for value in texts if value.lower().startswith("price:")), None)
            if price_text is not None:
                price_index = texts.index(price_text)
                texts.pop(price_index)
                yellow.discard(price_index)
                colours.pop(price_index, None)
                tags.pop(price_index, None)
            # Most comparisons contain only a few meaningful differences. Do
            # not reserve the old 96px minimum for a one-line card; longer
            # modifier lists still grow naturally and remain scrollable.
            height = max(52, min(260, int((len(texts) + 1) * 21)))
            textbox(frame, texts, yellow, colours, 2, 0, height=height, filter_tags=tags if side == "right" else None)
            if price_text is not None:
                _price_row(frame, price_text, 3, self.overlay)

    @staticmethod
    def _card_price(card: Mapping[str, Any]) -> float:
        for raw in card.get("lines", []):
            if not isinstance(raw, Mapping):
                continue
            text = str(raw.get("right_text") or "")
            if text.lower().startswith("price:"):
                match = _PRICE_PART_RE.search(text)
                if match and match.group(2).lower() == "e":
                    try:
                        return float(match.group(1))
                    except ValueError:
                        pass
        return float("inf")

    @staticmethod
    def _card_modifier_summary(card: Mapping[str, Any]) -> tuple[int, int, int]:
        """Return explicit-affix replacements, roll differences, and higher rolls.

        Price, core-stat, divider, and extra-status rows are intentionally not
        affix changes. Older payloads fall back to their rendered delta text.
        """
        replacements = roll_differences = higher_rolls = 0
        for raw in card.get("lines", []):
            if not isinstance(raw, Mapping):
                continue
            kind = str(raw.get("comparison_kind") or "explicit")
            if kind != "explicit":
                continue
            change_kind = raw.get("change_kind")
            delta = raw.get("delta")
            if change_kind == "replacement":
                replacements += 1
                continue
            if change_kind == "roll":
                roll_differences += 1
                try:
                    higher_rolls += int(float(delta) > 0)
                except (TypeError, ValueError):
                    pass
                continue
            # Compatibility for payloads produced by an older worker.
            text = str(raw.get("right_text") or "")
            matches = _CARD_DELTA_RE.findall(text)
            if matches:
                roll_differences += 1
                try:
                    higher_rolls += int(any(sign == "+" and float(value) > 0 for sign, value in matches))
                except ValueError:
                    pass
        return replacements, roll_differences, higher_rolls

    @staticmethod
    def _card_difference_score(card: Mapping[str, Any]) -> tuple[int, float]:
        """Lower values mean a closer modifier match."""
        count, magnitude = 0, 0.0
        for raw in card.get("lines", []):
            if not isinstance(raw, Mapping):
                continue
            if str(raw.get("comparison_kind") or "explicit") != "explicit":
                continue
            text = str(raw.get("right_text") or "")
            style = str(raw.get("right_style") or "")
            for sign, value in _CARD_DELTA_RE.findall(text):
                count += 1
                try:
                    magnitude += abs(float(value))
                except ValueError:
                    pass
            if style in {"plus", "minus"} and not _CARD_DELTA_RE.search(text):
                count += 1
        return count, magnitude

    @staticmethod
    def _card_has_positive_change(card: Mapping[str, Any]) -> bool:
        return PredictionPresenter._card_modifier_summary(card)[2] > 0

    @staticmethod
    def _card_has_filter_annotation(card: Mapping[str, Any]) -> bool:
        return any(
            isinstance(raw, Mapping) and raw.get("filter_annotation")
            for raw in card.get("lines", [])
        )

    def present(self, payload: Mapping[str, Any]) -> bool:
        if self.closed or not validate_payload(payload) or self.overlay is None:
            return False
        logging.info(
            "Prediction presenter staging result (request=%s, cards=%s)",
            self.request_id,
            len(payload.get("comparison_cards", [])),
        )
        # Keep the loading window visible.  Every final widget is built in a
        # separate alpha-zero native window, then that finished window replaces
        # the loader in one swap.
        loading_overlay = self.loading_overlay or self.overlay
        result_overlay = self._hidden_result_shell()
        self.result_overlay = result_overlay
        self.overlay = result_overlay
        header = ctk.CTkFrame(self.overlay, corner_radius=10, fg_color="#20262C")
        header.pack(fill="x", padx=8, pady=(8, 0))
        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="x", padx=8, pady=6)
        # Keep one scroll region visible and empty while the card widgets are
        # constructed. Tk will paint it after this callback returns, so users
        # see the blank region followed by the complete card set rather than
        # two stacked scroll frames or a partially populated dashboard.
        body = ctk.CTkScrollableFrame(self.overlay, corner_radius=10, fg_color="#191D21")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        body.grid_columnconfigure((0, 1), weight=1)
        summary = payload.get("price_summary")
        cards = list(payload.get("comparison_cards", []))
        conversion = payload.get("model_conversion")
        self._model_summary_row(
            header_content,
            payload,
            summary if isinstance(summary, Mapping) else None,
            conversion if isinstance(conversion, Mapping) else None,
        )

        card_controls = ctk.CTkFrame(header_content, fg_color="transparent")
        card_controls.pack(fill="x", padx=4, pady=(2, 5))
        ctk.CTkLabel(card_controls, text="Comparisons", font=("Segoe UI", 13, "bold"), text_color="#B9CEDA").pack(side="left", padx=(0, 8))
        diagnostics_toggle = ctk.CTkButton(
            card_controls,
            text="Show Model #1 diagnostics",
            height=28,
            fg_color="#26323A",
            hover_color="#33434E",
            font=("Segoe UI", 13),
        )
        diagnostics_toggle.pack(side="right", padx=(0, 6))
        diagnostics = ctk.CTkFrame(header_content, fg_color="#171B1F", corner_radius=8)

        # The rates the model was trained in, on the same show/hide mechanic as
        # the diagnostics. A prediction is denominated in the economy it
        # learned, and that drifts from the live one -- Forbidden Rites trained
        # at 1d = 111e and is 194e now -- so the reader needs to be able to see
        # which economy the number is expressed in, without it always taking
        # header space.
        rates_panel = ctk.CTkFrame(header_content, fg_color="#171B1F", corner_radius=8)
        if isinstance(conversion, Mapping):
            rates_toggle = ctk.CTkButton(
                card_controls,
                text="Show training rates",
                height=28,
                fg_color="#26323A",
                hover_color="#33434E",
                font=("Segoe UI", 13),
            )
            rates_toggle.pack(side="right", padx=(0, 6))
            self._conversion_banner(rates_panel, conversion)

            def _toggle_rates() -> None:
                if rates_panel.winfo_manager():
                    rates_panel.pack_forget()
                    rates_toggle.configure(text="Show training rates")
                else:
                    rates_panel.pack(fill="x", padx=4, pady=(0, 4))
                    rates_toggle.configure(text="Hide training rates")
                try:
                    result_overlay.update_idletasks()
                except tk.TclError:
                    pass

            rates_toggle.configure(command=_toggle_rates)

        def _toggle_diagnostics() -> None:
            if diagnostics.winfo_manager():
                diagnostics.pack_forget()
                diagnostics_toggle.configure(text="Show Model #1 diagnostics")
            else:
                diagnostics.pack(fill="x", padx=4, pady=(0, 4))
                diagnostics_toggle.configure(text="Hide Model #1 diagnostics")
            try:
                result_overlay.update_idletasks()
            except tk.TclError:
                pass

        diagnostics_toggle.configure(command=_toggle_diagnostics)
        diagnostics_charts = ctk.CTkFrame(diagnostics, fg_color="transparent")
        diagnostics_charts.pack(fill="x", padx=4, pady=4)
        charts = [
            chart
            for key in ("category_distribution_png", "distribution_png")
            if (chart := _png(payload.get(key))) is not None
        ]
        for col, chart in enumerate(charts):
            diagnostics_charts.grid_columnconfigure(col, weight=1)
            scaled_png_fit(diagnostics_charts, chart, 1300 // len(charts), 300, self.overlay).grid(
                row=0, column=col, sticky="nsew", padx=4, pady=2
            )
        staged_cards = ctk.CTkFrame(body, fg_color="transparent")
        staged_cards.grid_columnconfigure((0, 1), weight=1)
        next_card = 0

        def _retire_loader() -> None:
            if self.loading_progress is not None:
                try:
                    self.loading_progress.stop()
                except tk.TclError:
                    pass
            try:
                if self.cover is not None and self.cover.winfo_exists():
                    self.cover.destroy()
            except tk.TclError:
                pass
            self.cover = None
            self.loading_progress = None
            try:
                if loading_overlay is not None and loading_overlay.winfo_exists():
                    loading_overlay.destroy()
            except tk.TclError:
                pass
            if self.loading_overlay is loading_overlay:
                self.loading_overlay = None

        def _swap_completed_result() -> None:
            if self.closed or self.overlay is not result_overlay or not result_overlay.winfo_exists():
                return
            try:
                result_overlay.update_idletasks()
                # All child widgets and image layouts are now complete in the
                # hidden surface. Begin a subtle completed-view reveal before
                # retiring the loader.
                result_overlay.attributes("-alpha", 0.0)
            except tk.TclError:
                return
            result_overlay.lift()
            close_control = getattr(result_overlay, "_presenter_close_control", None)
            if close_control is not None:
                close_control.lift()
            # The loader that held focus is about to be destroyed.
            self._take_focus(result_overlay)
            def _reveal(alpha: float = 0.0) -> None:
                if self.closed or not result_overlay.winfo_exists():
                    return
                next_alpha = min(1.0, alpha + (1.0 / 8.0))
                try:
                    result_overlay.attributes("-alpha", next_alpha)
                    if alpha == 0.0:
                        self._enable_escape(result_overlay)
                except tk.TclError:
                    return
                if next_alpha < 1.0:
                    result_overlay.after(15, lambda: _reveal(next_alpha))
                else:
                    logging.info("Prediction presenter result swap completed (request=%s)", self.request_id)
                    _retire_loader()

            _reveal()

        def _render_card_batch() -> None:
            nonlocal next_card
            try:
                if (
                    self.closed
                    or self.overlay is not result_overlay
                    or not result_overlay.winfo_exists()
                    or not staged_cards.winfo_exists()
                ):
                    return
                # Yield often enough for the visible loading progress bar to
                # keep moving. A close can still arrive between these checks
                # and CTk's native textbox setup, so Tcl teardown is treated
                # as normal cancellation rather than an uncaught callback.
                deadline = time.perf_counter() + _CARD_BATCH_BUDGET_S
                while next_card < len(cards):
                    self._card(staged_cards, cards[next_card], next_card)
                    next_card += 1
                    if time.perf_counter() >= deadline:
                        break
                if next_card < len(cards):
                    result_overlay.after(1, _render_card_batch)
                    return
                staged_cards.grid(row=0, column=0, columnspan=2, sticky="nsew")
                result_overlay.after_idle(_swap_completed_result)
            except tk.TclError:
                logging.debug("Prediction card staging cancelled by window teardown")
                return

        result_overlay.after_idle(_render_card_batch)
        return True


class CraftPresenter:
    """Craft Potential UI; calculation remains in the main app process."""

    def __init__(self, root, monitor_rect, event_queue, on_closed, session_id: int = 0) -> None:
        def host_closed():
            # A late progress/result command must not rebuild a dismissed view.
            self.phase = "closed"
            on_closed()

        self.host = PredictionPresenter(root, 0, host_closed, monitor_rect)
        self.event_queue = event_queue
        self.session_id = int(session_id)
        self.window = None
        self.content = None
        self.status_label = None
        self.progress = None
        self.phase = "confirm"

    def _fit_compact(self, window, *, width: int, height: int) -> None:
        """Fit a CraftOracle panel to its content instead of the dashboard canvas."""
        mon_x, mon_y, mon_w, mon_h = self.host.monitor_rect
        try:
            scale = max(1.0, float(window._get_window_scaling()))
        except Exception:
            scale = 1.0
        physical_w, physical_h = min(width, int(mon_w * .78)), min(height, int(mon_h * .78))
        try:
            window.minsize(1, 1)
            window.geometry(f"{max(1, round(physical_w / scale))}x{max(1, round(physical_h / scale))}")
            window.update_idletasks()
            actual_w, actual_h = int(window.winfo_width()), int(window.winfo_height())
            window.geometry(f"+{mon_x + (mon_w - actual_w) // 2}+{mon_y + (mon_h - actual_h) // 2}")
            close_control = getattr(window, "_presenter_close_control", None)
            if close_control is not None:
                close_control.lift()
        except tk.TclError:
            return

    def _panel(self, window, title: str):
        self.content = ctk.CTkFrame(window)
        self.content.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(self.content, text=title, font=("Segoe UI", 20, "bold")).pack(anchor="w")

    def _reset(self, title: str = "CraftOracle") -> None:
        self.host.hide()
        self.window = self.host._shell(hidden=True)
        self._panel(self.window, title)

    def _replace_panel(self, title: str) -> bool:
        """Replace Craft content inside its existing shared overlay window.

        Keeping the same native window means confirmation, progress, and the
        result all retain the one backdrop/click shield.  Creating a hidden
        replacement toplevel for each phase looked atomic in code but caused
        visible flashing and inconsistent click routing on Windows.
        """
        try:
            if self.content is not None and self.content.winfo_exists():
                self.content.destroy()
        except tk.TclError:
            return False
        self.content = None
        self.status_label = None
        self.progress = None
        if self.window is None:
            return False
        self._panel(self.window, title)
        return True

    def _close(self) -> None:
        self.phase = "closed"
        self.host.hide()
        try:
            self.event_queue.put(("craft_cancel", {"session_id": self.session_id}))
        except Exception:
            pass

    def show_confirm(self) -> None:
        self.phase = "confirm"
        self._reset()
        ctk.CTkLabel(
            self.content,
            text=("This evaluates every missing explicit modifier at its highest target-eligible "
                  "observed tier, applies this item's local magnitude effects, and re-predicts "
                  "the item for each one. It can take a long time."),
            wraplength=520, justify="left",
        ).pack(anchor="w", pady=12)
        buttons = ctk.CTkFrame(self.content, fg_color="transparent")
        buttons.pack(fill="x")
        def start() -> None:
            if self.phase != "confirm":
                return
            self.phase = "starting"
            self.event_queue.put(("craft_start", {"session_id": self.session_id}))

        ctk.CTkButton(buttons, text="Start", command=start).pack(side="left", expand=True, fill="x", padx=(0, 6))
        cancel = ctk.CTkButton(buttons, text="Cancel", command=self._close)
        cancel.pack(side="left", expand=True, fill="x")
        self.host.protect_close_button(cancel, self._close)
        self._fit_compact(self.window, width=720, height=260)
        self.host.reveal_overlay(self.window)

    def show_progress(self, done: int | None = None, total: int | None = None) -> None:
        if self.phase in {"result", "error", "closed"}:
            return
        text = "Predicting possible modifier outcomes. This may take a while."
        if done is not None and total is not None:
            text = f"Predicting modifier {done} of {total}..."
        if self.phase == "predicting" and self.status_label is not None:
            try:
                if self.status_label.winfo_exists():
                    self.status_label.configure(text=text)
                    return
            except tk.TclError:
                pass
        self.phase = "predicting"
        # The confirmation frame is an earlier child of the same native
        # window. Remove it before the shared loader is placed; otherwise the
        # later result only removes the loader cover and exposes confirmation
        # content beneath it.
        try:
            if self.content is not None and self.content.winfo_exists():
                self.content.destroy()
        except tk.TclError:
            return
        self.content = None
        # Reuse the same loader that protects the prediction-result handoff.
        # It replaces the confirmation content in-place, stays animated for the
        # entire CraftOracle calculation, and is then replaced by the result.
        self.host.show_loading(
            title="Predicting Craft Potential...",
            detail=text,
            hint="Press Esc or click outside the panel to cancel",
            reuse_shell=True,
        )
        self.window = self.host.overlay
        self.content = self.host.cover
        self.status_label = self.host.loading_status_label
        self.progress = self.host.loading_progress
        self._fit_compact(self.window, width=720, height=410)

    def show_result(self, payload: Mapping[str, Any]) -> None:
        if self.phase == "closed":
            return
        self.phase = "result"
        if self.progress is not None:
            try:
                self.progress.stop()
            except tk.TclError:
                pass
        if not self._replace_panel("CraftOracle"):
            return
        item_name = str(payload.get("item_name") or "CraftOracle")
        item_header = ctk.CTkFrame(self.content, fg_color="transparent")
        item_header.pack(fill="x")
        icon = _png(payload.get("icon_png"))
        if icon:
            add_png(item_header, icon, self.host.overlay).pack(side="left", padx=(0, 10))
        item_copy = ctk.CTkFrame(item_header, fg_color="transparent")
        item_copy.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(item_copy, text=item_name, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ctk.CTkLabel(item_copy, text=(
            f"Baseline prediction: {_triple(payload.get('baseline_prediction'))} | "
            f"{payload.get('explicit_count', 0)} explicit modifier(s) | "
            f"{len(payload.get('rows', []))} simulations"
        )).pack(anchor="w", pady=(2, 10))
        rows = [row for row in payload.get("rows", []) if isinstance(row, Mapping)]
        best = max(rows, key=lambda row: float(row.get("delta", 0) or 0), default=None)
        if best is not None:
            delta = float(best.get("delta", 0) or 0)
            summary = ctk.CTkFrame(self.content, fg_color="#1F3A35" if delta > 0 else "#2A3036", corner_radius=8)
            summary.pack(fill="x", pady=(0, 10))
            label = "Best projected improvement" if delta > 0 else "Best projected outcome"
            ctk.CTkLabel(summary, text=label, font=("Segoe UI", 12, "bold"), text_color="#93D5B8").pack(anchor="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(
                summary,
                text=f"{_craft_roll_text(best)}  ·  {_triple(best.get('prediction'))}  ·  {craft_delta_text(delta)}",
                font=("Segoe UI", 14, "bold"),
            ).pack(anchor="w", padx=12, pady=(1, 8))
        table = ctk.CTkScrollableFrame(self.content, width=760, height=440)
        table.pack(fill="both", expand=True)
        for rank, row in enumerate(rows, start=1):
            delta = float(row.get("delta", 0) or 0)
            colour = "#4CC2A0" if delta > 0 else ("#D26A6A" if delta < 0 else "#C8D2DC")
            line = (
                f"{rank}. {_craft_roll_text(row)}    {_triple(row.get('prediction'))}    "
                f"{craft_delta_text(delta, row.get('delta_percent'))}"
            )
            ctk.CTkLabel(table, text=line, anchor="w", text_color=colour).pack(fill="x", pady=2)
        close = ctk.CTkButton(self.content, text="Close", command=self._close)
        close.pack(pady=(10, 0))
        self.host.protect_close_button(close, self._close)
        self._fit_compact(self.window, width=860, height=650)

    def show_error(self, message: str) -> None:
        if self.phase == "closed":
            return
        self.phase = "error"
        if not self._replace_panel("CraftOracle"):
            return
        ctk.CTkLabel(self.content, text=message, wraplength=560, justify="left").pack(pady=(0, 12))
        close = ctk.CTkButton(self.content, text="Close", command=self._close)
        close.pack()
        self.host.protect_close_button(close, self._close)
        self._fit_compact(self.window, width=680, height=260)


class FilterPresenter:
    """Small payload-only Ctrl+2 editor for the resident presenter."""

    def __init__(self, root, payload: Mapping[str, Any], event_queue) -> None:
        self.host = PredictionPresenter(root, 0, lambda: self._cancel(), payload.get("monitor_rect"))
        self.payload = payload
        self.event_queue = event_queue
        self.entries: list[tuple[Mapping[str, Any], Any]] = []
        self.uses_scrollbar = False
        self.action_bar = None
        self.action_buttons: list[Any] = []

    @staticmethod
    def _parse(raw: str, base: float) -> tuple[str, object]:
        value = raw.strip()
        if not value:
            raise ValueError("Empty filter value")
        if value.endswith("%"):
            try:
                span = abs(float(base)) * float(value[:-1].strip()) / 100.0
            except ValueError as exc:
                raise ValueError(f"Invalid percentage: {raw}") from exc
            return "between", tuple(sorted((float(round(base - span)), float(round(base + span)))))
        if value.endswith(("+", "=")):
            try:
                number = float(value[:-1].strip())
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value: {raw}") from exc
            return (">=" if value[-1] == "+" else "=="), number
        try:
            return ">=", float(value)
        except ValueError as exc:
            raise ValueError(f"Invalid numeric value: {raw}") from exc

    def _reset(self) -> None:
        self.host.hide()
        # Build the compact form in the same alpha-zero host used by Craft and
        # the completed dashboard.  Mapping the shared shell first exposes its
        # dashboard-sized provisional geometry before these fields exist.
        window = self.host._shell(hidden=True)
        frame = ctk.CTkFrame(window)
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(frame, text="Filtered Mods for Nearest Items", font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 8))
        identity = ctk.CTkFrame(frame, fg_color="transparent")
        identity.pack(fill="x", anchor="w")
        icon = _png(self.payload.get("icon_png"))
        if icon:
            add_png(identity, icon, self.host.overlay).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(identity, text=str(self.payload.get("item_name") or "Your Item"), font=("Consolas", 17, "bold")).pack(side="left", anchor="w")
        ctk.CTkLabel(frame, text="Enter filters like 35+ (at least 35), 35= (exact), or 35% (+/-35%).", wraplength=600, justify="left").pack(anchor="w", pady=(4, 8))
        rows = [row for row in self.payload.get("rows", []) if isinstance(row, Mapping)]
        # A short modifier list is a compact form, not a scrollable workspace.
        # Keep scrolling for genuinely long lists only, otherwise the permanent
        # scrollbar wastes space and can crowd the action row out of view.
        scroll_height = min(440, max(112, len(rows) * 43 + 18))
        self.uses_scrollbar = len(rows) > 7
        if self.uses_scrollbar:
            scroll = ctk.CTkScrollableFrame(frame, height=scroll_height, width=620)
            scroll.pack(fill="both", expand=True, pady=8)
        else:
            scroll = ctk.CTkFrame(frame, fg_color="transparent")
            scroll.pack(fill="x", pady=8)
        self.entries = []
        previous = self.payload.get("snapshot") or []
        for index, row in enumerate(rows):
            line = ctk.CTkFrame(scroll, fg_color="transparent")
            line.pack(fill="x", pady=3)
            line.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(line, text=f"{row.get('label', row.get('key'))}: {row.get('display', '-')}", anchor="w").grid(row=0, column=0, sticky="ew", padx=(0, 12))
            entry = ctk.CTkEntry(line, width=120)
            entry.grid(row=0, column=1, sticky="e")
            if index < len(previous) and previous[index]:
                entry.insert(0, str(previous[index]))
            self.entries.append((row, entry))
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))
        self.action_bar = buttons
        primary_actions = ctk.CTkFrame(buttons, fg_color="transparent")
        primary_actions.pack(fill="x", pady=(0, 5))
        secondary_actions = ctk.CTkFrame(buttons, fg_color="transparent")
        secondary_actions.pack(fill="x")

        def action(parent, text, command, *, padx=(0, 0), primary=False, subdued=False, consumes_click=False):
            colours = {}
            if primary:
                colours = {"fg_color": "#2B7DB8", "hover_color": "#3793D0"}
            elif subdued:
                colours = {"fg_color": "#3A424A", "hover_color": "#4B555E"}
            button = ctk.CTkButton(parent, text=text, command=command, **colours)
            button.pack(side="left", expand=True, fill="x", padx=padx)
            if consumes_click:
                self.host.protect_close_button(button, command)
            self.action_buttons.append(button)

        # Two balanced rows keep every action readable on a 760px compact
        # form; the former one-line arrangement clipped Cancel at 125% DPI.
        action(primary_actions, "Match Existing", lambda: self._fill("1+"), padx=(0, 3))
        action(primary_actions, "Match Current or Better", self._fill_current, padx=(3, 0))
        action(secondary_actions, "Clear", lambda: self._fill(""), padx=(0, 3), subdued=True)
        action(secondary_actions, "Apply", self._apply, padx=3, primary=True, consumes_click=True)
        action(secondary_actions, "Cancel", self._cancel, padx=(3, 0), subdued=True, consumes_click=True)
        mon_x, mon_y, mon_w, mon_h = self.host.monitor_rect
        try:
            scale = max(1.0, float(window._get_window_scaling()))
        except Exception:
            scale = 1.0
        physical_w = min(760, int(mon_w * .78))
        try:
            window.minsize(1, 1)
            # Measure the completed form before choosing its native geometry.
            # The fixed header/action row is taller than a simple row-count
            # estimate at Windows 125% scaling, which previously clipped every
            # action button below the panel.
            window.update_idletasks()
            physical_h = min(
                max(300, scroll_height + 250, int(frame.winfo_reqheight()) + 32),
                int(mon_h * .78),
            )
            window.geometry(f"{max(1, round(physical_w / scale))}x{max(1, round(physical_h / scale))}")
            window.update_idletasks()
            actual_w, actual_h = int(window.winfo_width()), int(window.winfo_height())
            # CTk/Tk report requested child sizes in a different coordinate
            # space on some Windows DPI combinations.  Measure the completed
            # action bar after applying geometry and grow only if it would be
            # clipped; this keeps long forms compact everywhere else.
            action_bottom = buttons.winfo_rooty() + buttons.winfo_height() + 16
            window_bottom = window.winfo_rooty() + actual_h
            overflow = max(0, action_bottom - window_bottom)
            if overflow:
                window.geometry(f"{actual_w}x{actual_h + overflow}")
                window.update_idletasks()
                actual_w, actual_h = int(window.winfo_width()), int(window.winfo_height())
            window.geometry(f"+{mon_x + (mon_w - actual_w) // 2}+{mon_y + (mon_h - actual_h) // 2}")
            window.update_idletasks()
            self.host.reveal_overlay(window)
        except tk.TclError:
            return

    def _fill(self, value: str) -> None:
        for _row, entry in self.entries:
            entry.delete(0, "end")
            if value:
                entry.insert(0, value)

    def _fill_current(self) -> None:
        for row, entry in self.entries:
            entry.delete(0, "end")
            display = str(row.get("display") or "")
            if display and display != "-":
                entry.insert(0, f"{display}+")

    def _apply(self) -> None:
        filters: dict[str, tuple[str, object]] = {}
        snapshot: list[str] = []
        try:
            for row, entry in self.entries:
                raw = entry.get().strip()
                snapshot.append(raw)
                if raw:
                    filters[str(row.get("key"))] = self._parse(raw, float(row.get("raw", 0) or 0))
        except ValueError as exc:
            ctk.CTkLabel(self.host.overlay, text=str(exc), text_color="#E07A7A").pack(pady=4)
            return
        self.event_queue.put(("filtered_apply", {"filters": filters, "snapshot": snapshot}))

    def _cancel(self) -> None:
        self.host.hide()
        try:
            self.event_queue.put(("filtered_cancel", None))
        except Exception:
            pass

    def show(self) -> None:
        self._reset()
