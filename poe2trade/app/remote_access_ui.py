"""Shared connection controls in Help → Setups; feature views stay local."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
import webbrowser

import customtkinter as ctk

from poe2trade.app.remote_access_help import _port, read_phone_address, tailscale_serve_command


SETUPS = (
    ("Desktop", "Use the overlay, prediction history, StashScrape and StashWatch on this PC. No connection setup is needed."),
    ("Android · This phone", "Price a stash and watch listings on the phone with bundled models. This phone's watches and files stay separate from the desktop."),
    ("Phone + desktop via Tailscale", "Keep StashSage running and the PC awake. Android or a phone browser can control the desktop's watches and share their listing snapshots and monitoring history. Desktop tools remain available."),
    ("Agent + desktop via Tailscale", "Connect the agent's tool runner, such as Muse, to the same Tailscale network. It can request desktop listing snapshots and control watches with the desktop URL and token."),
)


class RemoteAccessSetupView(ctk.CTkFrame):
    def __init__(self, parent, runtime):
        super().__init__(parent, fg_color="transparent")
        self.runtime = runtime
        self._after_id = None
        self._queue = queue.Queue()
        self._discovering = False
        self._connection_state = None
        self.pack(fill="both", expand=True)
        self._paragraph("Choose your setup", heading=True)
        for title, description in SETUPS:
            card = ctk.CTkFrame(self, corner_radius=8)
            card.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=12, pady=(8, 2))
            ctk.CTkLabel(card, text=description, justify="left", anchor="w", wraplength=600).pack(fill="x", padx=12, pady=(0, 10))
        self._paragraph("Desktop connections share StashWatch records. They do not remotely run the desktop StashScrape pricing pipeline, merge phone-local files, or expose overlay prediction history. The hosted single-item pricing API is a separate service.")
        self._paragraph("Connect to this desktop", heading=True)
        self.remote_enabled = tk.BooleanVar(value=runtime.server is not None)
        ctk.CTkCheckBox(self, text="Allow phones and agents to connect", variable=self.remote_enabled,
                        command=lambda: self._guard(self._toggle_api)).pack(anchor="w", padx=12, pady=8)
        self.remote_status = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=620)
        self.remote_status.pack(fill="x", padx=12, pady=4)
        self.advanced = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.advanced, text="Service port (5006 recommended)").pack(side="left", padx=(0, 8))
        self.api_port = ctk.CTkEntry(self.advanced, width=90)
        self.api_port.insert(0, str(runtime.config.get("stash_watch_api_port", 5006)))
        self.api_port.pack(side="left")
        self.api_port.bind("<FocusOut>", lambda _event: self._guard(self._update_command))
        ctk.CTkButton(self, text="Advanced settings", width=140, command=self._toggle_advanced).pack(anchor="w", padx=12, pady=4)
        self._paragraph("1. Enable the switch above. Install Tailscale on this PC and the phone or agent's tool runner. Connect them to the same Tailscale network.")
        links = ctk.CTkFrame(self, fg_color="transparent")
        links.pack(anchor="w", padx=12, pady=4)
        for label, url in (("Get Tailscale", "https://tailscale.com/download"),
                           ("Serve instructions", "https://tailscale.com/docs/features/tailscale-serve")):
            ctk.CTkButton(links, text=label, width=140, command=lambda url=url: webbrowser.open(url)).pack(side="left", padx=(0, 8))
        self._paragraph("2. Run this command in PowerShell or Terminal on the desktop. If Tailscale asks you to enable HTTPS, follow its link, then run the command again.")
        self.command = ctk.CTkEntry(self)
        self.command.pack(fill="x", padx=12, pady=4)
        self._update_command()
        ctk.CTkButton(self, text="Copy setup command", command=lambda: self._guard(self._copy_command)).pack(anchor="w", padx=12, pady=4)
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=12, pady=8)
        for index, (label, action) in enumerate((("Copy phone link", self._copy_phone_link),
                                                ("Copy access token", self._copy_token),
                                                ("Open web page on this PC", self._open_web))):
            ctk.CTkButton(buttons, text=label, width=170, command=lambda action=action: self._guard(action)).grid(row=index // 2, column=index % 2, padx=(0, 8), pady=4)
        self.message = ctk.CTkLabel(self, text="", text_color="#E9BE75", anchor="w", justify="left", wraplength=620)
        self.message.pack(fill="x", padx=12, pady=4)
        self._paragraph("3. Android: choose Desktop via Tailscale → Add desktop connection. Paste the phone link into HTTPS desktop URL and the token into Desktop access token; Test and save. Phone browser (including iPhone): open the link with Tailscale connected, paste the token and press Connect.")
        self._paragraph("Agent: save the same HTTPS URL and token in its secure tool connection. A paused watch plus Check now makes a one-off snapshot; Start watching enables repeated checks. Connecting only a phone does not connect a cloud agent.")
        self._paragraph("The token is this desktop's private access password, separate from Tailscale login and the hosted pricing API key. Keep it out of URLs and public messages. The web page forgets it when closed.")
        self._paragraph("Stop remote access", heading=True)
        self._paragraph("Turn off the switch or exit StashSage. To remove this Tailscale service, run: tailscale serve --https=10000 off. Pause watching stops checks; it does not turn off the connection.")
        self.refresh()
        self._poll()

    def _paragraph(self, text, heading=False):
        ctk.CTkLabel(self, text=text, justify="left", anchor="w", wraplength=620,
                     font=("Segoe UI", 17 if heading else 13, "bold" if heading else "normal")).pack(
                         fill="x", padx=12, pady=(12 if heading else 4, 4))

    def _guard(self, action):
        try:
            self.message.configure(text="")
            action()
        except (ValueError, OSError) as exc:
            self.message.configure(text=str(exc))
        self.refresh()

    def refresh(self):
        enabled = self.runtime.server is not None
        self.remote_enabled.set(enabled)
        port = self.runtime.config.get("stash_watch_api_port", 5006)
        state = (enabled, port, self.runtime.api_error)
        if self._connection_state == state:
            return
        self._connection_state = state
        self.api_port.configure(state="disabled" if enabled else "normal")
        self.remote_status.configure(text=f"Ready on this PC at http://127.0.0.1:{port}/. Use the Tailscale HTTPS link on another device." if enabled else
                                     (self.runtime.api_error or "Remote access is off. Desktop tools and phone-local checks work independently."))

    def _toggle_advanced(self):
        if self.advanced.winfo_manager():
            self.advanced.pack_forget()
        else:
            self.advanced.pack(anchor="w", padx=12, pady=4, after=self.remote_status)

    def _toggle_api(self):
        old_port = self.runtime.config.get("stash_watch_api_port", 5006)
        try:
            if self.remote_enabled.get():
                self.runtime.config["stash_watch_api_port"] = _port(self.api_port.get())
            self.runtime.enable_api(self.remote_enabled.get())
        except (ValueError, OSError):
            self.runtime.config["stash_watch_api_port"] = old_port
            raise
        finally:
            self.refresh()
        self._update_command()

    def _require_connection(self):
        if not self.runtime.server:
            raise ValueError("Turn on Allow phones and agents to connect first.")

    def _copy(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)

    def _update_command(self):
        text = tailscale_serve_command(self.api_port.get())
        self.command.configure(state="normal")
        self.command.delete(0, "end")
        self.command.insert(0, text)
        self.command.configure(state="readonly")

    def _copy_command(self):
        self._update_command()
        self._copy(self.command.get())
        self.message.configure(text="Setup command copied. Run it on this PC.")

    def _copy_phone_link(self):
        self._require_connection()
        if self._discovering:
            return
        self._discovering = True
        port = self.runtime.config.get("stash_watch_api_port", 5006)
        self.message.configure(text="Reading this desktop's Tailscale link…")

        def discover():
            try:
                self._queue.put((read_phone_address(port), None))
            except (ValueError, OSError) as exc:
                self._queue.put((None, str(exc)))

        threading.Thread(target=discover, name="StashSage phone link", daemon=True).start()

    def _poll(self):
        try:
            address, error = self._queue.get_nowait()
            self._discovering = False
            if not self.runtime.server:
                error = "Remote access was turned off. Enable it before copying the phone link."
            if error:
                self.message.configure(text=error)
            else:
                self._copy(address)
                self.message.configure(text="Phone link copied. Use it as the HTTPS desktop URL, then copy the access token.")
        except queue.Empty:
            pass
        self.refresh()
        self._after_id = self.after(150 if self._discovering else 1000, self._poll)

    def _open_web(self):
        self._require_connection()
        webbrowser.open(f"http://127.0.0.1:{self.runtime.config.get('stash_watch_api_port', 5006)}/")

    def _copy_token(self):
        self._require_connection()
        self._copy(self.runtime.config["stash_watch_api_token"])
        self.message.configure(text="Desktop access token copied. Paste it into your device's connection settings.")

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        super().destroy()
