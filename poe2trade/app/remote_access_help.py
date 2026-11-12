"""Shared phone setup guidance and discovery of this app's Tailscale link."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import customtkinter as ctk


def _port(value):
    if isinstance(value, bool) or not str(value).isdigit() or not 1 <= int(value) <= 65535:
        raise ValueError("Use a whole service port from 1 to 65535; 5006 is recommended.")
    return int(value)


def tailscale_serve_command(port=5006):
    return f"tailscale serve --bg --https=10000 http://127.0.0.1:{_port(port)}"


def phone_address_from_status(status, port=5006):
    target = f"http://127.0.0.1:{_port(port)}"
    for address, service in status.get("Web", {}).items():
        if service.get("Handlers", {}).get("/", {}).get("Proxy", "").rstrip("/") == target:
            return f"https://{address}/"
    raise ValueError("Open Help → Setups and run its setup command on this PC, then copy the phone link again.")


def read_phone_address(port=5006):
    executable = shutil.which("tailscale")
    fallback = Path("C:/Program Files/Tailscale/tailscale.exe")
    if not executable and fallback.is_file():
        executable = str(fallback)
    if not executable:
        raise ValueError("Install Tailscale on this PC using the link in Help → Setups.")
    try:
        # The packaged app has no console, so without this flag Windows flashes one.
        result = subprocess.run([executable, "serve", "status", "--json"], capture_output=True, text=True, timeout=5,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise ValueError("Connect Tailscale on this PC, then run the setup command in Help → Setups.")
        return phone_address_from_status(json.loads(result.stdout), port)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise ValueError("Could not read the phone link. Use the HTTPS address printed by the setup command.") from exc


def add_remote_access_help(parent, port=5006):
    """Compatibility entry point using the same setup controls as Help."""
    from poe2trade.app.remote_access_ui import RemoteAccessSetupView
    from poe2trade.app.stash_watch_runtime import get_runtime
    return RemoteAccessSetupView(parent, get_runtime())


def show_remote_access_help(parent, port=5006):
    window = ctk.CTkToplevel(parent)
    window.title("Setups")
    window.geometry("740x680")
    window.transient(parent.winfo_toplevel())
    scroll = ctk.CTkScrollableFrame(window)
    scroll.pack(fill="both", expand=True, padx=12, pady=12)
    add_remote_access_help(scroll, port)
    ctk.CTkButton(window, text="Close", command=window.destroy).pack(pady=(0, 12))
    window.bind("<Escape>", lambda _event: window.destroy())
    return window
