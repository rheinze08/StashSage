"""Shared phone setup guidance and discovery of this app's Tailscale link."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import webbrowser

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
    raise ValueError("Open Phone & agent setup and run its setup command on this PC, then copy the phone link again.")


def read_phone_address(port=5006):
    executable = shutil.which("tailscale")
    fallback = Path("C:/Program Files/Tailscale/tailscale.exe")
    if not executable and fallback.is_file():
        executable = str(fallback)
    if not executable:
        raise ValueError("Install Tailscale on this PC using the link in Phone & agent setup.")
    try:
        result = subprocess.run([executable, "serve", "status", "--json"], capture_output=True, text=True, timeout=5)
        if result.returncode:
            raise ValueError("Connect Tailscale on this PC, then run the setup command in Phone & agent setup.")
        return phone_address_from_status(json.loads(result.stdout), port)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise ValueError("Could not read the phone link. Use the HTTPS address printed by the setup command.") from exc


def add_remote_access_help(parent, port=5006):
    def paragraph(text, heading=False):
        ctk.CTkLabel(parent, text=text, justify="left", anchor="w", wraplength=620,
                     font=("Segoe UI", 16 if heading else 13, "bold" if heading else "normal")).pack(
                         fill="x", padx=16, pady=(12 if heading else 4, 4))

    paragraph("Choose where your checks run", True)
    paragraph("Desktop: StashScrape prices listings and StashWatch tracks changes on this PC. No Tailscale or token is needed for desktop use.")
    paragraph("Android, This phone: StashScrape prices locally with bundled models; StashWatch checks run on your phone. No PC, Tailscale or token is needed.")
    paragraph("Phone browser (including iPhone), Android Desktop via Tailscale, or agent: control this PC's StashWatch and request listing snapshots. Keep StashSage running and the PC awake. Remote snapshots contain asking prices and history, not StashScrape model valuations.")
    paragraph("Connect a phone to this PC", True)
    paragraph("1. In desktop StashWatch, turn on Allow phones and agents to connect. Leave the recommended service port at 5006; Advanced settings is only for a port conflict.")
    paragraph("2. Install Tailscale on this PC and your phone. Sign in to the same Tailscale account and connect both devices.")
    links = ctk.CTkFrame(parent, fg_color="transparent")
    links.pack(anchor="w", padx=16, pady=4)
    for label, url in [("Get Tailscale", "https://tailscale.com/download"),
                       ("Tailscale Serve instructions", "https://tailscale.com/docs/features/tailscale-serve")]:
        ctk.CTkButton(links, text=label, command=lambda url=url: webbrowser.open(url)).pack(side="left", padx=(0, 8))
    paragraph("3. On this PC, open PowerShell (Windows) or Terminal (Linux) and paste this command. If Tailscale asks you to enable HTTPS, follow its link and run the command again.")
    command = tailscale_serve_command(port)
    entry = ctk.CTkEntry(parent)
    entry.pack(fill="x", padx=16, pady=4)
    entry.insert(0, command)
    entry.configure(state="readonly")
    copied = ctk.CTkLabel(parent, text="", wraplength=620)

    def copy():
        parent.clipboard_clear()
        parent.clipboard_append(command)
        copied.configure(text="Setup command copied. Paste it into PowerShell or Terminal on this PC.")

    ctk.CTkButton(parent, text="Copy setup command", command=copy).pack(anchor="w", padx=16, pady=4)
    copied.pack(fill="x", padx=16)
    paragraph("4. In StashWatch, Copy phone link copies the HTTPS address after setup. You can also copy the address Tailscale prints, including :10000, for example https://your-pc.your-tailnet.ts.net:10000/. Transfer this link to your phone.")
    paragraph("5. Phone browser: connect Tailscale on your phone, open that link, then paste the desktop's Copy access token into Desktop access token and press Connect. The page controls the PC; it forgets the token when closed.")
    paragraph("Android app instead: choose Desktop via Tailscale, then Add desktop connection. Paste the phone link into HTTPS desktop URL and the copied token into Desktop access token. Press Test and save.")
    paragraph("What the buttons and token mean", True)
    paragraph("Open web page on this PC previews the same page in this PC's browser. It does not open your phone or set up Tailscale. Copy phone link is the address to open on your phone.")
    paragraph("Copy access token copies StashSage's private access password. Paste it only into the browser's Desktop access token field, the Android connection's Desktop access token field, or your agent's secure connection settings. It is not a Tailscale login key or hosted pricing API key. Do not put it in a URL or public message.")
    paragraph("Agent: its tool runner must also be connected to your Tailscale network. Give that connection the HTTPS phone link and token; connecting only your phone does not give a cloud agent access. Use a paused watch plus Check now for a one-off snapshot; Start watching enables repeated checks.")
    paragraph("In v0.5.24, the switch is Enable HTTP access for phones and agents, Copy access token is Copy API token, and Open web page on this PC is Open phone view. Their functions are the same.")
    paragraph("Stop remote access", True)
    paragraph("Turn off the connection switch or exit StashSage. To remove this Tailscale service, run: tailscale serve --https=10000 off. Pause stops a watch's checks.")


def show_remote_access_help(parent, port=5006):
    window = ctk.CTkToplevel(parent)
    window.title("Phone & agent setup")
    window.geometry("740x680")
    window.transient(parent.winfo_toplevel())
    scroll = ctk.CTkScrollableFrame(window)
    scroll.pack(fill="both", expand=True, padx=12, pady=12)
    add_remote_access_help(scroll, port)
    ctk.CTkButton(window, text="Close", command=window.destroy).pack(pady=(0, 12))
    window.bind("<Escape>", lambda _event: window.destroy())
    return window
