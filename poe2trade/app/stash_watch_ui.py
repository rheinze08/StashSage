"""Desktop controls for the same watches exposed to agents and phone browsers."""
from __future__ import annotations

import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser

import customtkinter as ctk

from poe2trade.app.stash_watch import WatchSpec
from poe2trade.app.stash_watch_api import listings_csv
from poe2trade.app.stash_watch_trade import catalog
from poe2trade.app.remote_access_help import read_phone_address, show_remote_access_help


INTERVALS = {"15 minutes": 15, "30 minutes": 30, "1 hour": 60, "2 hours": 120}


def interval_minutes(label, custom):
    if label in INTERVALS:
        return INTERVALS[label]
    try:
        minutes = int(custom)
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter a whole number of minutes for the custom interval") from exc
    if not 1 <= minutes <= 10080:
        raise ValueError("Custom interval must be from 1 to 10080 minutes")
    return minutes


def _date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp is not None else "—"


def event_text(event):
    row = event.get("after") or event.get("before") or {}
    price = lambda item: f"{item.get('price')} {item.get('currency', '')}" if item.get("price") is not None else "unpriced"
    kind = event["type"]
    if kind == "price_changed":
        text = f"price changed {price(event['before'])} → {price(event['after'])}"
    elif kind == "listing_no_longer_observed":
        text = f"no longer observed; last listed at {price(row)} (sale or delisting unknown)"
    elif kind == "listing_reappeared":
        text = f"appeared again at {price(row)}"
    else:
        text = f"listed at {price(row)}"
    return f"{_date(event['observed_at'])} · {row.get('item', event.get('listing_id', ''))} · {text}"


class StashWatchView(ctk.CTkScrollableFrame):
    def __init__(self, parent, runtime):
        super().__init__(parent, fg_color="transparent")
        self.runtime, self.manager = runtime, runtime.manager
        self.watch_id = None
        self._names = {}
        self._after_id = None
        self._cursor, self._events = 0, []
        self.pack(fill="both", expand=True)
        ctk.CTkLabel(self, text="StashWatch", font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(self, text="Track your public listings, price changes and disappearances.", wraplength=650,
                     justify="left").pack(anchor="w", padx=12, pady=(0, 12))
        self.saved = ctk.CTkOptionMenu(self, values=["New watch"], command=self._choose, width=420)
        self.saved.pack(anchor="w", padx=12, pady=5)
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=12, pady=8)
        form.grid_columnconfigure(1, weight=1)

        def field(label, widget, index):
            ctk.CTkLabel(form, text=label).grid(row=index, column=0, padx=12, pady=6, sticky="w")
            widget.grid(row=index, column=1, padx=12, pady=6, sticky="ew")
            return widget

        self.account = field("Account", ctk.CTkEntry(form, placeholder_text="Player#1234"), 0)
        self.account.insert(0, runtime.config.get("stash_scrape_username", ""))
        options = catalog()
        self.league = field("League", ctk.CTkComboBox(form, values=options["leagues"] or ["Enter trade league name"]), 1)
        self.league.set(options["leagues"][0] if options["leagues"] else "")
        self.scope = field("Listings to watch", ctk.CTkOptionMenu(form, values=["Merchant", "All public listings"]), 2)
        self.interval = field("Check every", ctk.CTkOptionMenu(form, values=[*INTERVALS, "Custom"], command=self._interval_changed), 3)
        self.interval.set("30 minutes")
        self.custom = field("Custom minutes", ctk.CTkEntry(form), 4)
        self.custom.insert(0, "30")
        self.custom.configure(state="disabled")
        categories = ctk.CTkFrame(self)
        categories.pack(fill="x", padx=12, pady=4)
        self.all_categories = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(categories, text="All categories", variable=self.all_categories,
                        command=self._categories_changed).pack(anchor="w", padx=12, pady=8)
        category_list = ctk.CTkScrollableFrame(categories, height=130)
        category_list.pack(fill="x", padx=8, pady=(0, 8))
        self.category_vars = {}
        for index, name in enumerate(options["categories"]):
            var = tk.BooleanVar(value=False)
            self.category_vars[name] = var
            box = ctk.CTkCheckBox(category_list, text=name.replace("_", " "), variable=var,
                                 command=lambda: self.all_categories.set(False))
            box.grid(row=index // 3, column=index % 3, padx=8, pady=5, sticky="w")
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=12, pady=8)
        for index, (label, action) in enumerate([("Save settings", self._save), ("Start watching", self._start),
                                               ("Pause", self._pause), ("Check now", self._check)]):
            ctk.CTkButton(controls, text=label, width=130, command=lambda fn=action: self._guard(fn)).grid(row=0, column=index, padx=(0, 8))
        self.status = ctk.CTkLabel(self, text="No baseline yet", justify="left", wraplength=680, anchor="w")
        self.status.pack(fill="x", padx=12, pady=5)
        self.message = ctk.CTkLabel(self, text="", text_color="#E9BE75", justify="left", wraplength=680, anchor="w")
        self.message.pack(fill="x", padx=12)
        remote = ctk.CTkFrame(self)
        remote.pack(fill="x", padx=12, pady=10)
        self.remote_enabled = tk.BooleanVar(value=runtime.server is not None)
        ctk.CTkCheckBox(remote, text="Allow phones and agents to connect", variable=self.remote_enabled,
                        command=self._toggle_api).pack(anchor="w", padx=12, pady=10)
        self.remote_status = ctk.CTkLabel(remote, text="", anchor="w", justify="left", wraplength=650)
        self.remote_status.pack(fill="x", padx=12)
        self.advanced = ctk.CTkFrame(remote, fg_color="transparent")
        ctk.CTkLabel(self.advanced, text="Service port (5006 recommended)").pack(side="left", padx=(0, 8))
        self.api_port = ctk.CTkEntry(self.advanced, width=100)
        self.api_port.insert(0, str(runtime.config.get("stash_watch_api_port", 5006)))
        self.api_port.pack(side="left")
        ctk.CTkButton(remote, text="Advanced settings", width=140, command=self._toggle_advanced).pack(anchor="w", padx=12, pady=5)
        remote_buttons = ctk.CTkFrame(remote, fg_color="transparent")
        remote_buttons.pack(anchor="w", padx=12, pady=(0, 8))
        for index, (label, action) in enumerate([
            ("Open web page on this PC", self._open_web), ("Copy access token", self._copy_token),
            ("Phone & agent setup", lambda: show_remote_access_help(self, self.runtime.config.get("stash_watch_api_port", 5006))),
            ("Copy phone link", self._copy_phone_link),
        ]):
            ctk.CTkButton(remote_buttons, text=label, width=190, command=lambda action=action: self._guard(action)).grid(
                row=index // 2, column=index % 2, padx=(0, 8), pady=4)
        ctk.CTkLabel(remote, text="Desktop use needs no remote setup. For a phone or agent, start with Phone & agent setup.\n"
                     "Android can also run checks on This phone without a PC, Tailscale or token.",
                     justify="left", wraplength=650).pack(anchor="w", padx=12, pady=(0, 10))
        tabs = ctk.CTkTabview(self, height=320)
        tabs.pack(fill="both", expand=True, padx=12, pady=8)
        current, activity = tabs.add("Current Listings"), tabs.add("Activity")
        ctk.CTkButton(current, text="Export CSV", command=lambda: self._guard(self._export), width=120).pack(anchor="w", pady=5)
        table = ctk.CTkFrame(current)
        table.pack(fill="both", expand=True)
        columns = ("item", "price", "stash", "last_seen")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=9)
        for name, title, width in zip(columns, ("Item", "Listed price", "Stash", "Last seen"), (230, 130, 150, 165)):
            self.tree.heading(name, text=title)
            self.tree.column(name, width=width, minwidth=80)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(table, command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)
        self.activity = ctk.CTkTextbox(activity, height=250, wrap="word")
        self.activity.pack(fill="both", expand=True)
        self.activity.configure(state="disabled")
        self._load_watches()
        if self._names:
            self.saved.set(next(iter(self._names)))
            self._choose(self.saved.get())
        self._remote_status()
        self._refresh()

    def _guard(self, fn):
        try:
            self.message.configure(text="")
            fn()
        except (ValueError, KeyError, OSError) as exc:
            self.message.configure(text=str(exc))

    def _load_watches(self):
        self._names = {f"{w['settings']['account']} · {w['settings']['league']} · {w['settings']['listing_type']} · {w['id'][:6]}": w["id"]
                       for w in self.manager.store.watches()}
        self.saved.configure(values=["New watch", *self._names])

    def _choose(self, name):
        self.watch_id = self._names.get(name)
        self._cursor, self._events = 0, []
        if self.watch_id:
            settings = self.manager.store.get(self.watch_id)["settings"]
            self.account.delete(0, "end")
            self.account.insert(0, settings["account"])
            self.league.set(settings["league"])
            self.scope.set("Merchant" if settings["listing_type"] == "merchant" else "All public listings")
            self.interval.set(next((label for label, minutes in INTERVALS.items() if minutes == settings["interval_minutes"]), "Custom"))
            self.custom.configure(state="normal")
            self.custom.delete(0, "end")
            self.custom.insert(0, str(settings["interval_minutes"]))
            self._interval_changed(self.interval.get())
            self.all_categories.set(not settings["categories"])
            for category, var in self.category_vars.items():
                var.set(category in settings["categories"])
        self._refresh_data()

    def _interval_changed(self, value):
        self.custom.configure(state="normal" if value == "Custom" else "disabled")

    def _categories_changed(self):
        if self.all_categories.get():
            for var in self.category_vars.values():
                var.set(False)

    def _spec(self):
        categories = () if self.all_categories.get() else tuple(name for name, var in self.category_vars.items() if var.get())
        if not self.all_categories.get() and not categories:
            raise ValueError("Choose categories or select All categories")
        return WatchSpec(account=self.account.get(), league=self.league.get(),
                         listing_type="merchant" if self.scope.get() == "Merchant" else "all",
                         categories=categories, interval_minutes=interval_minutes(self.interval.get(), self.custom.get()))

    def _save(self):
        spec = self._spec()
        if self.watch_id and spec == WatchSpec(**self.manager.store.get(self.watch_id)["settings"]):
            return
        watch = self.manager.save(spec, watch_id=self.watch_id)
        self.watch_id = watch["id"]
        self._load_watches()
        self.saved.set(next(name for name, key in self._names.items() if key == self.watch_id))
        self._cursor, self._events = 0, []
        self._refresh_data()

    def _start(self):
        self._save()
        self.manager.start(self.watch_id)
        self.manager.tick()
        self._refresh_data()

    def _pause(self):
        if self.watch_id:
            self.manager.pause(self.watch_id)
            self._refresh_data()

    def _check(self):
        self._save()
        self.manager.check_now(self.watch_id)
        self._refresh_data()

    def _toggle_api(self):
        try:
            if self.remote_enabled.get():
                self.runtime.config["stash_watch_api_port"] = int(self.api_port.get())
            self.runtime.enable_api(self.remote_enabled.get())
        except (ValueError, OSError) as exc:
            self.message.configure(text=str(exc))
        self.remote_enabled.set(self.runtime.server is not None)
        self._remote_status()

    def _remote_status(self):
        port = self.runtime.config.get("stash_watch_api_port", 5006)
        self.api_port.configure(state="disabled" if self.runtime.server else "normal")
        self.remote_status.configure(text=f"Ready on this PC at http://127.0.0.1:{port}/. For your phone, use the Tailscale phone link." if self.runtime.server else
                                     (self.runtime.api_error or "Remote access is off. Desktop checks work normally; enable only for a phone or agent."))

    def _toggle_advanced(self):
        if self.advanced.winfo_manager():
            self.advanced.pack_forget()
        else:
            self.advanced.pack(anchor="w", padx=12, pady=5)

    def _copy_phone_link(self):
        if not self.runtime.server:
            raise ValueError("Turn on Allow phones and agents to connect first.")
        address = read_phone_address(self.runtime.config.get("stash_watch_api_port", 5006))
        self.clipboard_clear()
        self.clipboard_append(address)
        self.message.configure(text="Phone link copied. Open it in your phone browser with Tailscale connected, or paste it into Android's HTTPS desktop URL field. Then use Copy access token to connect.")

    def _open_web(self):
        if not self.runtime.server:
            raise ValueError("Enable HTTP access first")
        webbrowser.open(f"http://127.0.0.1:{self.runtime.config['stash_watch_api_port']}/")

    def _copy_token(self):
        if not self.runtime.server:
            raise ValueError("Enable HTTP access first")
        self.clipboard_clear()
        self.clipboard_append(self.runtime.config["stash_watch_api_token"])
        self.message.configure(text="Access token copied. Paste into Desktop access token on the phone web page or Android desktop connection, then Connect or Test and save. For an agent, use its secure connection settings with your phone link.")

    def _export(self):
        if not self.watch_id:
            raise ValueError("Select a watch first")
        path = filedialog.asksaveasfilename(parent=self.winfo_toplevel(), defaultextension=".csv",
                                          initialfile="stashwatch.csv", filetypes=[("CSV", "*.csv")])
        if path:
            Path(path).write_text(listings_csv(self.manager.store.listings(self.watch_id)), encoding="utf-8", newline="")

    def _refresh_data(self):
        self.tree.delete(*self.tree.get_children())
        if self.watch_id:
            watch = self.manager.store.get(self.watch_id)
            mode = "Checking" if watch["last_run"] and watch["last_run"]["status"] == "running" else "Watching" if watch["enabled"] else "Paused"
            coverage = "No baseline yet" if watch["last_complete"] is None else "Complete" if watch["last_complete"] else "Incomplete; unseen listings retained"
            self.status.configure(text=f"{mode} · {coverage}\nLast checked: {_date(watch['last_check'])} · Next check: {_date(watch['next_check'])}")
            if watch["last_error"]:
                self.message.configure(text=watch["last_error"])
            for row in self.manager.store.listings(self.watch_id):
                price = f"{row.get('price')} {row.get('currency', '')}" if row.get("price") is not None else "Unpriced"
                self.tree.insert("", "end", values=(row.get("item", ""), price, row.get("stash_name", ""), _date(row["last_seen_at"])))
            events = self.manager.store.events(self.watch_id, after=self._cursor)
            if events:
                self._cursor = events[-1]["id"]
                self._events = (self._events + events)[-100:]
        else:
            self.status.configure(text="Save a watch to establish its first baseline.")
        self.activity.configure(state="normal")
        self.activity.delete("1.0", "end")
        self.activity.insert("end", "\n\n".join(event_text(event) for event in reversed(self._events)))
        self.activity.configure(state="disabled")

    def _refresh(self):
        self._guard(self._refresh_data)
        self._load_watches()
        self._after_id = self.after(3000, self._refresh)

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        super().destroy()
