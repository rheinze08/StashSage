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
    steam_entry: Optional[ctk.CTkEntry] = None
    ggg_entry: Optional[ctk.CTkEntry] = None
    steam_browse_btn: Optional[ctk.CTkButton] = None
    ggg_browse_btn: Optional[ctk.CTkButton] = None
    prediction_log_entry: Optional[ctk.CTkEntry] = None
    prediction_log_browse_btn: Optional[ctk.CTkButton] = None
    discord_id_entry: Optional[ctk.CTkEntry] = None
    discord_token_entry: Optional[ctk.CTkEntry] = None
    price_filter_entry: Optional[ctk.CTkEntry] = None
    knn_filtered_k_entry: Optional[ctk.CTkEntry] = None
    show_viz_var: Optional[ctk.BooleanVar] = None
    custom_hotkey_entry: Optional[ctk.CTkEntry] = None
    filtered_hotkey_entry: Optional[ctk.CTkEntry] = None
    prediction_log_hotkey_entry: Optional[ctk.CTkEntry] = None
    client_choice: Optional[ctk.StringVar] = None
    log_files: list[str] = field(default_factory=list)
    services_started: bool = False
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
