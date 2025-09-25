"""Reusable UI helpers for the CustomTkinter front-end."""
from __future__ import annotations

import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Iterable, Optional

import customtkinter as ctk
import pandas as pd
from PIL import Image

from poe2trade import chaos_exalt, divine_exalt, poe2trade_root

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
    "quiver": "Quiver",
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

    root_dir = Path(poe2trade_root) / "db" / "base_icons"
    candidates: list[str] = []
    resolved = find_local_image(state, item_name, root_dir)
    if resolved:
        candidates.append(resolved)
    for category in ("Body_Armour", "Helmet", "Boots", "Gloves", "Ring", "Amulet", "Belt", "Wand", "Sceptre", "Quiver"):
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
        if idx in yellow:
            widget.tag_add("yellow", f"{idx+1}.0", f"{idx+1}.end")
        if idx in colours:
            start = line.find("(")
            if start != -1:
                widget.tag_add(colours[idx], f"{idx+1}.{start}", f"{idx+1}.end")
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
    widget.grid(row=row, column=col, sticky="nsew", padx=(6, 0) if col == 0 else (0, 0), pady=4)
    return widget


def price_to_exalt(price: float, currency: str | None) -> float:
    currency = (currency or "").lower()
    if currency in {"e", "exa", "exalt", "exalts"}:
        return float(price)
    if currency in {"c", "chaos"}:
        return float(price) * chaos_exalt
    if currency in {"d", "div", "divine"}:
        return float(price) * divine_exalt
    return float(price)


def price_string(row: pd.Series) -> tuple[str, float] | None:
    """Return (display_string, exalts_float) if pricing information exists."""

    e_value: float | None = None
    if {"Price", "Currency"}.issubset(row.index) and pd.notna(row.get("Price")):
        e_value = price_to_exalt(row["Price"], row["Currency"])  # type: ignore[index]
    elif {"price", "currency"}.issubset(row.index) and pd.notna(row.get("price")):
        e_value = price_to_exalt(row["price"], row["currency"])  # type: ignore[index]
    elif "Price_in_Exalts" in row and pd.notna(row.get("Price_in_Exalts")):
        e_value = float(row["Price_in_Exalts"])  # type: ignore[index]
    if e_value is None:
        return None
    try:
        exalt = int(round(float(e_value)))
        chaos = int(round(float(e_value) / max(chaos_exalt, 1e-9)))
        divine = int(round(float(e_value) / max(divine_exalt, 1e-9)))
    except Exception:
        return None
    return (f"{exalt}e/{chaos}c/{divine}d", float(e_value))


def price_simple(row: pd.Series) -> Optional[str]:
    if {"Price", "Currency"}.issubset(row.index) and pd.notna(row.get("Price")):
        return f"{int(round(float(row['Price'])))}{str(row['Currency']).lower()[:1]}"
    if {"price", "currency"}.issubset(row.index) and pd.notna(row.get("price")):
        return f"{int(round(float(row['price'])))}{str(row['currency']).lower()[:1]}"
    if "Price_in_Exalts" in row and pd.notna(row.get("Price_in_Exalts")):
        return f"{int(round(float(row['Price_in_Exalts'])))}e"
    return None


def triple(price_in_exalts: float) -> str:
    try:
        exalt = int(round(float(price_in_exalts)))
        chaos = int(round(float(price_in_exalts) / max(chaos_exalt, 1e-9)))
        divine = int(round(float(price_in_exalts) / max(divine_exalt, 1e-9)))
        return f"{exalt}e/{chaos}c/{divine}d"
    except Exception:
        return f"{price_in_exalts:.0f}e"
