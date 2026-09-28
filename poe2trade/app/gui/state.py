"""Shared GUI state used across the CustomTkinter front-end."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import customtkinter as ctk


@dataclass
class GuiState:
    """Container for mutable GUI objects and configuration."""

    root: Optional[ctk.CTk] = None
    overlay: Optional[ctk.CTkToplevel] = None
    config: dict[str, Any] = field(default_factory=dict)
    prediction_log_entry: Optional[ctk.CTkEntry] = None
    prediction_log_browse_btn: Optional[ctk.CTkButton] = None
    price_filter_entry: Optional[ctk.CTkEntry] = None
    max_price_filter_entry: Optional[ctk.CTkEntry] = None
    knn_filtered_k_entry: Optional[ctk.CTkEntry] = None
    copy_hotkey_entry: Optional[ctk.CTkEntry] = None
    custom_hotkey_entry: Optional[ctk.CTkEntry] = None
    filtered_hotkey_entry: Optional[ctk.CTkEntry] = None
    craft_potential_hotkey_entry: Optional[ctk.CTkEntry] = None
    stash_scrape_hotkey_entry: Optional[ctk.CTkEntry] = None
    client_day_filter: int = 30
    filter_entry_memory: dict[str, list[str]] = field(default_factory=dict)
    base_image_map: dict[str, dict[str, Any]] = field(default_factory=dict)
    overlay_hotkey_handle: Any = None
    filtered_overlay_hotkey_handle: Any = None

    def reset_overlay(self) -> None:
        """Clear overlay reference after the window has been destroyed."""
        self.overlay = None

    def update_config(self, new_cfg: dict[str, Any]) -> None:
        """Replace the in-memory configuration snapshot."""
        self.config = new_cfg


state = GuiState()
