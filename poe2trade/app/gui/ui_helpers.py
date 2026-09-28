"""Reusable UI helpers for the CustomTkinter front-end."""
from __future__ import annotations

import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Iterable, Mapping, Optional

import tkinter
import customtkinter as ctk
import pandas as pd
from PIL import Image

from poe2trade.pricing import conversion
from poe2trade.app import asset_paths

from .state import GuiState


_CATEGORY_WORD_MAP = {
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
    "boots": "Boots",
    "greaves": "Boots",
    "sabatons": "Boots",
    "shoes": "Boots",
    "leggings": "Boots",
    "sandals": "Boots",
    "gloves": "Gloves",
    "gauntlets": "Gloves",
    "bracers": "Gloves",
    "mitts": "Gloves",
    "cuffs": "Gloves",
    "wraps": "Gloves",
    # Focus
    "focus": "Focus",
    # Shields
    "shield": "Shield",
    "buckler": "Buckler",
    "helm": "Helmet",
    "helmet": "Helmet",
    "mask": "Helmet",
    "crown": "Helmet",
    "cap": "Helmet",
    "greathelm": "Helmet",
    "tiara": "Helmet",
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


def load_base_image_map(state: GuiState, path: str | os.PathLike[str]) -> None:
    """Populate ``state.base_image_map`` from the packaged JSON manifest."""

    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    mapping: dict[str, dict[str, str]] = {}
    for item in data:
        base = item.get("baseType")
        if not base:
            continue
        key = " ".join(str(base).split()[-2:]).lower()
        mapping[key] = {
            "path": item.get("icon", ""),
            "category": item.get("category", ""),
            "baseType": base,
        }
    state.base_image_map = mapping


def find_local_image(state: GuiState, item_name: str, root: str | os.PathLike[str]) -> Optional[str]:
    """Return a local icon path for ``item_name`` if one can be resolved."""

    words = item_name.strip().split()
    if not words:
        return None

    root_path = Path(root)

    for span in (2, 1):
        key = " ".join(words[-span:]).lower()
        entry = state.base_image_map.get(key)
        if not entry:
            continue
        category = entry.get("category") or ""
        base_type = entry.get("baseType", "")
        safe = "".join(c for c in base_type if c.isalnum() or c in (" ", "-", "_"))
        candidate = root_path / category / f"{safe}.png"
        if candidate.exists():
            return str(candidate)
        fallback = root_path / category / "default.png"
        if fallback.exists():
            return str(fallback)

    last = re.sub(r"[^A-Za-z]", "", words[-1]).lower()
    category = _CATEGORY_WORD_MAP.get(last)
    if category:
        fallback = Path(root) / category / "default.png"
        if fallback.exists():
            return str(fallback)
    return None


def _ensure_overlay_image_list(overlay_window: Optional[ctk.CTkToplevel]) -> list[ctk.CTkImage]:
    if overlay_window is None:
        return []
    images = getattr(overlay_window, "images", None)
    if images is None:
        images = []
        overlay_window.images = images  # type: ignore[attr-defined]
    return images


def scaled_png(
    parent: ctk.CTkBaseClass,
    buf: io.BytesIO,
    target_width: int,
    overlay_window: Optional[ctk.CTkToplevel] = None,
) -> ctk.CTkLabel:
    """Render a PNG into a ``CTkLabel`` scaled to ``target_width`` pixels."""

    pil = Image.open(buf)
    width, height = pil.size
    width = max(width, 1)
    scale = target_width / float(width)
    size = (target_width, int(height * scale))
    image = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
    label = ctk.CTkLabel(parent, image=image, text="")
    images = _ensure_overlay_image_list(overlay_window)
    images.append(image)
    return label


def scaled_png_percent(
    parent: ctk.CTkBaseClass,
    buf: io.BytesIO,
    pct: float,
    overlay_window: Optional[ctk.CTkToplevel] = None,
) -> ctk.CTkLabel:
    """Scale a PNG relative to its native width."""

    pil = Image.open(buf)
    width, _ = pil.size
    width = max(width, 1)
    target = max(1, int(width * max(0.05, min(1.0, float(pct)))))
    return scaled_png(parent, io.BytesIO(buf.getvalue()), target, overlay_window)


def add_png(
    parent: ctk.CTkBaseClass,
    buf: io.BytesIO,
    overlay_window: Optional[ctk.CTkToplevel] = None,
) -> ctk.CTkLabel:
    """Attach a PNG at its native size to ``parent``."""

    pil = Image.open(buf)
    image = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
    label = ctk.CTkLabel(parent, image=image, text="")
    images = _ensure_overlay_image_list(overlay_window)
    images.append(image)
    return label


def icon_label(
    state: GuiState,
    parent: ctk.CTkBaseClass,
    item_name: str,
    *,
    target_w: int = 36,
    target_h: int | None = None,
    overlay_window: Optional[ctk.CTkToplevel] = None,
) -> Optional[ctk.CTkLabel]:
    """Render the icon that best matches ``item_name`` if available."""

    # Resolve per file across the writable override dir and the bundled dir.
    # ``active_asset_dir`` would return the override dir wholesale once it
    # exists, hiding every bundled icon the updater has not (yet) delivered;
    # searching both dirs keeps partial overrides additive.
    search_dirs = asset_paths.asset_search_dirs("base_icons")
    candidates: list[str] = []
    for root_dir in search_dirs:
        resolved = find_local_image(state, item_name, root_dir)
        if resolved:
            candidates.append(resolved)
    for category in ("Body_Armour", "Helmet", "Boots", "Gloves", "Focus", "Shield", "Buckler", "Ring", "Amulet", "Belt", "Wand", "Sceptre", "Staff", "Quiver", "Tablet", "Waystone", "Bow"):
        for root_dir in search_dirs:
            candidates.append(str(root_dir / category / "default.png"))

    for path in candidates:
        fp = Path(path)
        if not fp.exists():
            continue
        try:
            with fp.open("rb") as handle:
                buffer = io.BytesIO(handle.read())
            label = scaled_png(parent, buffer, target_w, overlay_window)
            if target_h is not None:
                try:
                    label.configure(height=target_h)
                except Exception:
                    pass
            return label
        except Exception as exc:
            logging.warning("Icon load failed for %s: %s", fp, exc)
            continue
    return None


_CURRENCY_ICON_FILES = {
    "e": "exalted_orb.png",
    "c": "chaos_orb.png",
    "d": "divine_orb.png",
}


def currency_orb_label(
    parent: ctk.CTkBaseClass,
    unit: str,
    *,
    size: int = 20,
) -> Optional[ctk.CTkLabel]:
    """Return a retained orb-icon label for compact price/conversion displays."""

    filename = _CURRENCY_ICON_FILES.get(str(unit).lower())
    if not filename:
        return None
    window = parent.winfo_toplevel()
    cache = getattr(window, "currency_images", {})
    key = (str(unit).lower(), int(size))
    image = cache.get(key)
    if image is None:
        path = Path(__file__).resolve().parents[1] / "currency_icons" / filename
        try:
            with Image.open(path) as source:
                rendered = source.convert("RGBA")
                rendered.thumbnail((size, size), Image.Resampling.LANCZOS)
                image = ctk.CTkImage(
                    light_image=rendered.copy(),
                    dark_image=rendered.copy(),
                    size=rendered.size,
                )
        except (OSError, ValueError):
            return None
        cache[key] = image
        window.currency_images = cache
    return ctk.CTkLabel(parent, image=image, text="")


_MOD_SORT_EPS = 1e-6


def is_zeroish(value: float) -> bool:
    return abs(value) <= _MOD_SORT_EPS


def is_positiveish(value: float) -> bool:
    return value > _MOD_SORT_EPS


def mod_sort_bucket(base_value: float, neighbour_value: float) -> int:
    """Return an ordering bucket used for mirror-row grouping."""

    if is_positiveish(base_value) and is_positiveish(neighbour_value):
        return 0
    if is_zeroish(base_value) and is_positiveish(neighbour_value):
        return 1
    if is_positiveish(base_value) and is_zeroish(neighbour_value):
        return 2
    return 3


def textbox(
    parent: ctk.CTkBaseClass,
    lines: Iterable[str],
    yellow: Iterable[int],
    colours: dict[int, str],
    row: int,
    col: int,
    *,
    height: int | None = None,
    filter_tags: dict[int, str] | None = None,
    columnspan: int = 1,
) -> ctk.CTkTextbox:
    """Create a read-only textbox with coloured rows."""

    lines = list(lines)
    if height is None:
        base = max(100, int((len(lines) + 1) * 26))
        height = max(20, base)

    widget = ctk.CTkTextbox(
        parent,
        wrap="word",
        font=("Consolas", 15),
        border_width=1,
        border_color="#3A3A3A",
        height=height,
    )
    widget.tag_config("yellow", foreground="#FFD700")
    widget.tag_config("plus", foreground="#4CAF50")
    widget.tag_config("minus", foreground="#E74C3C")
    widget.tag_config("filter", foreground="#7FBFF6")

    yellow = set(yellow)
    colours = colours or {}
    filter_tags = filter_tags or {}

    for idx, line in enumerate(lines):
        widget.insert("end", line + "\n")
        # Locate the (+/-N) delta so a one-sided modifier's yellow base text can
        # stop right before it, leaving the delta free to read green/red. This
        # avoids overlapping tags entirely, so no tag-priority juggling.
        delta_start = line.find("(") if idx in colours else -1
        if idx in yellow:
            end = f"{idx+1}.{delta_start}" if delta_start != -1 else f"{idx+1}.end"
            widget.tag_add("yellow", f"{idx+1}.0", end)
        if delta_start != -1:
            widget.tag_add(colours[idx], f"{idx+1}.{delta_start}", f"{idx+1}.end")
        tag_text = filter_tags.get(idx)
        if tag_text:
            start = line.rfind(tag_text)
            if start != -1:
                widget.tag_add(
                    "filter",
                    f"{idx+1}.{start}",
                    f"{idx+1}.{start + len(tag_text)}",
                )

    widget.configure(state="disabled")
    widget.grid(
        row=row,
        column=col,
        columnspan=columnspan,
        sticky="nsew",
        padx=(6, 0) if col == 0 else (0, 0),
        pady=4,
    )
    return widget


def _conversion_rates(conversions=None) -> tuple[float, float]:
    values = conversions.get("conversions") if isinstance(conversions, Mapping) else None
    if not isinstance(values, Mapping):
        return float(conversion.chaos), float(conversion.divine)
    try:
        return (
            float(values.get("chaos", conversion.chaos)),
            float(values.get("divine", conversion.divine)),
        )
    except (TypeError, ValueError):
        return float(conversion.chaos), float(conversion.divine)


def price_to_exalt(price: float, currency: str | None, *, conversions=None) -> float:
    chaos_rate, divine_rate = _conversion_rates(conversions)
    currency = (currency or "").lower()
    if currency in {"e", "exa", "exalt", "exalts"}:
        return float(price)
    if currency in {"c", "chaos"}:
        return float(price) * chaos_rate
    if currency in {"d", "div", "divine"}:
        return float(price) * divine_rate
    return float(price)


def price_string(row: pd.Series, *, conversions=None) -> tuple[str, float] | None:
    """Return (display_string, exalts_float) if pricing information exists."""

    e_value: float | None = None
    if "Price_in_Exalts" in row and pd.notna(row.get("Price_in_Exalts")):
        e_value = float(row["Price_in_Exalts"])  # type: ignore[index]
    elif "price_in_exalts" in row and pd.notna(row.get("price_in_exalts")):
        e_value = float(row["price_in_exalts"])  # type: ignore[index]
    elif {"Price", "Currency"}.issubset(row.index) and pd.notna(row.get("Price")):
        e_value = price_to_exalt(row["Price"], row["Currency"], conversions=conversions)  # type: ignore[index]
    elif {"price", "currency"}.issubset(row.index) and pd.notna(row.get("price")):
        e_value = price_to_exalt(row["price"], row["currency"], conversions=conversions)  # type: ignore[index]
    if e_value is None:
        return None
    try:
        exalt = int(round(float(e_value)))
        chaos_rate, divine_rate = _conversion_rates(conversions)
        chaos = round(float(e_value) / max(chaos_rate, 1e-9), 1)
        divine = float(e_value) / max(divine_rate, 1e-9)
    except Exception:
        return None
    divine_text = f"{divine:.2f}".rstrip("0").rstrip(".")
    return (f"{exalt}e/{chaos:.1f}c/{divine_text}d", float(e_value))


def price_simple(row: pd.Series) -> Optional[str]:
    if {"Price", "Currency"}.issubset(row.index) and pd.notna(row.get("Price")):
        return f"{int(round(float(row['Price'])))}{str(row['Currency']).lower()[:1]}"
    if {"price", "currency"}.issubset(row.index) and pd.notna(row.get("price")):
        return f"{int(round(float(row['price'])))}{str(row['currency']).lower()[:1]}"
    if "Price_in_Exalts" in row and pd.notna(row.get("Price_in_Exalts")):
        return f"{int(round(float(row['Price_in_Exalts'])))}e"
    return None


# Above this many exalts, auto mode switches to divine. A prediction of
# 1,200,000e is not readable; 10801d is. Below it exalts stay the unit players
# actually quote in, so a 40e item is not re-expressed as 6.4c.
AUTO_DIVINE_THRESHOLD_EXALTS = 1000.0

PRICE_DISPLAY_MODES = ("auto", "exalted", "divine", "chaos")


def _fmt_number(value: float) -> str:
    """Whole numbers for anything countable, two decimals for fractions.

    A non-zero value never renders as a bare "0": in an explicit denomination a
    cheap item can be a tiny fraction of a divine, and showing 0 would read as
    worthless rather than as below the resolution of that unit.
    """
    if abs(value) >= 100:
        return f"{value:,.0f}"
    if value and abs(value) < 0.01:
        return "<0.01" if value > 0 else ">-0.01"
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def format_price(price_in_exalts: float, mode: str = "auto", *, conversions=None) -> str:
    """One denomination instead of the three-way string.

    `triple()` renders every currency at once, which is unreadable at the
    magnitudes predictions actually reach. This picks a single unit: `auto`
    keeps exalts until they stop being scannable and then switches to divine;
    the explicit modes always win so a chosen unit is never overridden.
    """
    try:
        value = float(price_in_exalts)
    except (TypeError, ValueError):
        return "-"
    chaos_rate, divine_rate = _conversion_rates(conversions)
    mode = (mode or "auto").lower()
    if mode not in PRICE_DISPLAY_MODES:
        mode = "auto"
    if mode == "auto":
        mode = "divine" if abs(value) >= AUTO_DIVINE_THRESHOLD_EXALTS else "exalted"
    if mode == "divine":
        return f"{_fmt_number(value / max(divine_rate, 1e-9))}d"
    if mode == "chaos":
        return f"{_fmt_number(value / max(chaos_rate, 1e-9))}c"
    return f"{_fmt_number(value)}e"


def triple(price_in_exalts: float, *, conversions=None) -> str:
    try:
        exalt = int(round(float(price_in_exalts)))
        chaos_rate, divine_rate = _conversion_rates(conversions)
        chaos = round(float(price_in_exalts) / max(chaos_rate, 1e-9), 1)
        divine = float(price_in_exalts) / max(divine_rate, 1e-9)
        divine_text = f"{divine:.2f}".rstrip("0").rstrip(".")
        return f"{exalt}e/{chaos:.1f}c/{divine_text}d"
    except Exception:
        return f"{price_in_exalts:.0f}e"


# Shared so the prediction presenter, which runs in its own process and
# cannot import gui_tk, can offer the same "?" affordance as the settings.
class HoverTip:
    """Lightweight hover tooltip anchored above a widget (e.g. a ``?`` badge)."""

    def __init__(self, widget, text: str, *, wraplength: int = 300) -> None:
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tip: tkinter.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.tip is not None or not self.text:
            return
        try:
            anchor_x = self.widget.winfo_rootx()
            anchor_y = self.widget.winfo_rooty()
        except tkinter.TclError:
            return
        self.tip = tkinter.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        try:
            self.tip.attributes("-topmost", True)
        except tkinter.TclError:
            pass
        tkinter.Label(
            self.tip,
            text=self.text,
            justify="left",
            wraplength=self.wraplength,
            background="#1F262C",
            foreground="#E6EDF3",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 10),
            padx=8,
            pady=6,
        ).pack()
        self.tip.update_idletasks()
        tip_h = self.tip.winfo_height()
        y = anchor_y - tip_h - 6
        if y < 0:
            y = anchor_y + self.widget.winfo_height() + 6
        self.tip.wm_geometry(f"+{anchor_x}+{y}")

    def _hide(self, _event=None) -> None:
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tkinter.TclError:
                pass
            self.tip = None


def help_badge(parent, help_text: str) -> ctk.CTkLabel:
    """Create a small "?" badge with a hover tip, matching the Home tab style."""
    badge = ctk.CTkLabel(
        parent,
        text="?",
        font=("Segoe UI", 10, "bold"),
        text_color="#0B0E11",
        fg_color="#6E7F8D",
        corner_radius=9,
        width=18,
        height=18,
    )
    HoverTip(badge, help_text)
    return badge
