"""Saved-watch dashboard with exact check snapshots and explicit settings edits."""
from __future__ import annotations

import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

import customtkinter as ctk

from poe2trade.app.stash_watch import WatchSpec
from poe2trade.app.stash_watch_results import category_label, price_text, previous_price_text, result_csv, CHANGE_LABELS
from poe2trade.app.stash_watch_trade import catalog


INTERVALS = {"15 minutes": 15, "30 minutes": 30, "1 hour": 60, "2 hours": 120}


def interval_label(minutes):
    return next((name for name, value in INTERVALS.items() if value == minutes), f"{minutes} minutes (existing)")


def interval_minutes(label, existing=None):
    if label in INTERVALS:
        return INTERVALS[label]
    if type(existing) is int and 1 <= existing <= 10080 and label == interval_label(existing):
        return existing
    raise ValueError("Choose one of the four check intervals")


def _date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp is not None else "—"


def scope_text(settings):
    scope = "Merchant" if settings["listing_type"] == "merchant" else "All public listings"
    categories = ", ".join(category_label(name) for name in settings["categories"]) or "All categories"
    return f"{settings['account']} · {settings['league']} · {scope} · {categories}"


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


def _table(parent, columns, *, height=8):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(0, weight=1)
    style = ttk.Style(parent)
    style.theme_use("clam")
    style.configure("Watch.Treeview", background="#202A33", foreground="#DCE5EE", fieldbackground="#202A33", rowheight=29)
    style.configure("Watch.Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#2E3A46", foreground="white", padding=(8, 6), relief="flat")
    style.map("Watch.Treeview.Heading", background=[("active", "#3A4A59")])
    style.map("Watch.Treeview", background=[("selected", "#1F6AA5")], foreground=[("selected", "white")])
    tree = ttk.Treeview(frame, columns=[name for name, _, _ in columns], show="headings", height=height,
                        selectmode="browse", style="Watch.Treeview")
    for name, label, width in columns:
        tree.heading(name, text=label)
        tree.column(name, width=width, minwidth=75, stretch=name == "item")
    tree.grid(row=0, column=0, sticky="nsew")
    vertical = ttk.Scrollbar(frame, command=tree.yview)
    horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    tree.tag_configure("missing", foreground="#A9B2BC")
    tree.tag_configure("changed", foreground="#E9BE75")
    tree.tag_configure("unknown", foreground="#C2B3DE")
    return tree


def _sync_table(tree, entries):
    """Keep identities, selection and scroll stable when saved results change."""
    selected, focus, scroll = tree.selection(), tree.focus(), tree.yview()
    keys = {key for key, _, _ in entries}
    for key in tree.get_children():
        if key not in keys:
            tree.delete(key)
    for index, (key, values, tags) in enumerate(entries):
        if tree.exists(key):
            if tuple(tree.item(key, "values")) != tuple(str(value) for value in values) or tuple(tree.item(key, "tags")) != tuple(tags):
                tree.item(key, values=values, tags=tags)
            if tree.index(key) != index:
                tree.move(key, "", index)
        else:
            tree.insert("", index, iid=key, values=values, tags=tags)
    retained = [key for key in selected if key in keys]
    if retained and tuple(retained) != tree.selection():
        tree.selection_set(retained)
    if focus in keys:
        tree.focus(focus)
    if scroll:
        tree.yview_moveto(scroll[0])


class WatchEditor(ctk.CTkToplevel):
    def __init__(self, parent, runtime, on_saved, watch_id=None):
        super().__init__(parent)
        self.runtime, self.on_saved, self.watch_id = runtime, on_saved, watch_id
        self.original = runtime.manager.store.get(watch_id) if watch_id else None
        self.title("Edit watch" if watch_id else "New watch")
        self.geometry("650x650")
        self.minsize(520, 480)
        self.transient(parent.winfo_toplevel())
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        form = ctk.CTkScrollableFrame(self)
        form.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        form.grid_columnconfigure(1, weight=1)
        values = self.original["settings"] if self.original else {}
        options = catalog()

        def field(label, widget, index):
            ctk.CTkLabel(form, text=label).grid(row=index, column=0, sticky="w", padx=10, pady=8)
            widget.grid(row=index, column=1, sticky="ew", padx=10, pady=8)
            return widget

        self.account = field("Account", ctk.CTkEntry(form, placeholder_text="Player#1234"), 0)
        self.account.insert(0, values.get("account", runtime.config.get("stash_scrape_username", "")))
        self.league = field("League", ctk.CTkComboBox(form, values=options["leagues"] or ["Enter trade league name"]), 1)
        self.league.set(values.get("league", options["leagues"][0] if options["leagues"] else ""))
        self.scope = field("Listings to watch", ctk.CTkOptionMenu(form, values=["Merchant", "All public listings"]), 2)
        self.scope.set("All public listings" if values.get("listing_type") == "all" else "Merchant")
        self.existing_interval = values.get("interval_minutes")
        intervals = list(INTERVALS)
        if self.existing_interval and self.existing_interval not in INTERVALS.values():
            intervals.append(interval_label(self.existing_interval))
        self.interval = field("Check every", ctk.CTkOptionMenu(form, values=intervals), 3)
        self.interval.set(interval_label(values.get("interval_minutes", 30)))
        self.all_categories = tk.BooleanVar(value=not values.get("categories"))
        ctk.CTkCheckBox(form, text="All categories", variable=self.all_categories,
                        command=self._categories_changed).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=12)
        category_frame = ctk.CTkFrame(form, fg_color="transparent")
        category_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=4)
        self.category_vars = {}
        names = list(dict.fromkeys([*options["categories"], *values.get("categories", [])]))
        for index, name in enumerate(names):
            variable = tk.BooleanVar(value=name in values.get("categories", []))
            self.category_vars[name] = variable
            ctk.CTkCheckBox(category_frame, text=category_label(name), variable=variable,
                            command=lambda: self.all_categories.set(False)).grid(row=index // 2, column=index % 2, sticky="w", padx=8, pady=5)
        ctk.CTkLabel(form, text="Changing account, league, listing scope or categories begins a new baseline. Earlier checks stay in history. Changing only the interval keeps the baseline.",
                     justify="left", wraplength=520, text_color="#9AA7B4").grid(row=6, column=0, columnspan=2, sticky="w", padx=10, pady=12)
        if not self.original:
            ctk.CTkLabel(form, text="Create saves a paused watch. Use Check now once, or Start watching for repeated checks.",
                         justify="left", wraplength=520).grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        self.message = ctk.CTkLabel(self, text="", text_color="#E9BE75", wraplength=600)
        self.message.grid(row=1, column=0, sticky="ew", padx=12)
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(buttons, text="Save changes" if watch_id else "Create watch", command=self._save).pack(side="right")
        ctk.CTkButton(buttons, text="Cancel", command=self.destroy, fg_color="#354350").pack(side="right", padx=8)
        self.bind("<Escape>", lambda _event: self.destroy())

    def _categories_changed(self):
        if self.all_categories.get():
            for variable in self.category_vars.values():
                variable.set(False)

    def _spec(self):
        categories = () if self.all_categories.get() else tuple(name for name, variable in self.category_vars.items() if variable.get())
        if not self.all_categories.get() and not categories:
            raise ValueError("Choose categories or select All categories")
        return WatchSpec(account=self.account.get(), league=self.league.get(),
                         listing_type="merchant" if self.scope.get() == "Merchant" else "all",
                         categories=categories, interval_minutes=interval_minutes(self.interval.get(), self.existing_interval))

    def _save(self):
        try:
            spec = self._spec()
            if not self.original and any(WatchSpec(**watch["settings"]).scope == spec.scope
                                         for watch in self.runtime.manager.store.watches()):
                raise ValueError("A watch for these settings already exists. Select it or use Edit watch.")
            if self.original and spec == WatchSpec(**self.original["settings"]):
                current = self.runtime.manager.store.get(self.watch_id)
                if current["settings_version"] != self.original["settings_version"]:
                    raise ValueError("Watch settings changed; reopen Edit watch")
                watch = current
            else:
                watch = self.runtime.manager.save(spec, watch_id=self.watch_id,
                                                  expected_version=self.original["settings_version"] if self.original else None)
            self.on_saved(watch["id"])
            self.destroy()
        except (ValueError, KeyError, OSError) as exc:
            self.message.configure(text=str(exc))


class StashWatchView(ctk.CTkFrame):
    PAGE_SIZE = 100

    def __init__(self, parent, runtime):
        super().__init__(parent, fg_color="transparent")
        self.runtime, self.manager = runtime, runtime.manager
        self.watch_id = None
        self._names, self._run_names, self._rows = {}, {}, {}
        self._selected_run = None
        self._offset = 0
        self._sort, self._descending = "item", False
        self._checks_before, self._activity_before = None, None
        self._check_pages, self._activity_pages = [], []
        self._checks_page, self._activity_page = [], []
        self._history_before, self._history_pages = None, []
        self._history_key = None
        self._history_visible = False
        self._stopping = None
        self._editor = None
        self._after_id = None
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        header = ctk.CTkFrame(self, corner_radius=10, fg_color="#202A33")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        ctk.CTkLabel(header, text="StashWatch", font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(header, text="Follow your listings over time", text_color="#9AA7B4").pack(anchor="w", padx=12, pady=(0, 10))
        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        selector.grid_columnconfigure(0, weight=1)
        self.saved = ctk.CTkOptionMenu(selector, values=["No saved watches"], command=self._choose, dynamic_resizing=False)
        self.saved.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.new_button = ctk.CTkButton(selector, text="New watch", width=110, command=lambda: self._guard(self._new_watch))
        self.new_button.grid(row=0, column=1, padx=(0, 8))
        self.edit_button = ctk.CTkButton(selector, text="Edit watch", width=110, command=lambda: self._guard(self._edit_watch))
        self.edit_button.grid(row=0, column=2)
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=12, pady=4)
        controls.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(controls, text="", anchor="w", justify="left", wraplength=510)
        self.status.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.watch_button = ctk.CTkButton(controls, text="Start watching", width=140, command=lambda: self._guard(self._toggle_watching))
        self.watch_button.grid(row=0, column=1, padx=(0, 8))
        self.check_button = ctk.CTkButton(controls, text="Check now", width=110, command=lambda: self._guard(self._check))
        self.check_button.grid(row=0, column=2)
        self.timing = ctk.CTkLabel(self, text="", anchor="w", text_color="#9AA7B4")
        self.timing.grid(row=3, column=0, sticky="ew", padx=12)
        self.message = ctk.CTkLabel(self, text="", anchor="w", text_color="#E9BE75", wraplength=820, justify="left", height=20)
        self.message.grid(row=4, column=0, sticky="ew", padx=12)
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=5, column=0, sticky="nsew", padx=12, pady=(0, 12))
        listings, checks, activity = (self.tabs.add(name) for name in ("Listings", "Checks", "Activity"))
        listings.grid_columnconfigure(0, weight=1)
        listings.grid_rowconfigure(3, weight=1)
        toolbar = ctk.CTkFrame(listings, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=4)
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(toolbar, text="Check:").grid(row=0, column=0, padx=(0, 8))
        self.run_selector = ctk.CTkOptionMenu(toolbar, values=["Latest captured result"], command=self._choose_run, dynamic_resizing=False)
        self.run_selector.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.export_button = ctk.CTkButton(toolbar, text="Export CSV", width=110, command=lambda: self._guard(self._export))
        self.export_button.grid(row=0, column=2)
        filters = ctk.CTkFrame(listings, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", pady=4)
        filters.grid_columnconfigure(0, weight=1)
        self.search = ctk.CTkEntry(filters, placeholder_text="Search item, stash or category")
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search.bind("<KeyRelease>", lambda _event: self._filter_changed())
        self.filter = ctk.CTkOptionMenu(filters, values=["All", "Still listed", "No longer observed", "Changed", "Unknown"], command=lambda _value: self._filter_changed(), width=170)
        self.filter.grid(row=0, column=1)
        self.result_status = ctk.CTkLabel(listings, text="", anchor="w", justify="left", wraplength=820)
        self.result_status.grid(row=2, column=0, sticky="ew", pady=4)
        table = ctk.CTkFrame(listings, fg_color="transparent")
        table.grid(row=3, column=0, sticky="nsew")
        columns = [("item", "Item", 230), ("remaining", "Still listed?", 95), ("previous_price", "Previous price", 120),
                   ("price", "Last listed price", 120), ("change", "Change", 155), ("stash_name", "Stash", 120)]
        self.tree = _table(table, columns)
        for name, label, _ in columns:
            self.tree.heading(name, text=label, command=lambda name=name: self._sort_by(name))
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._listing_selected())
        self.page_label, self.previous_button, self.next_button = self._pager(listings, self._page, grid_row=4)
        self.history_toggle = ctk.CTkButton(self.page_label.master, text="Show history", width=110, command=self._toggle_history)
        self.history_toggle.pack(side="right", padx=8)
        self.detail = ctk.CTkLabel(listings, text="Select a listing to review its history. No longer observed does not confirm a sale.",
                                  anchor="w", justify="left", wraplength=820, text_color="#9AA7B4")
        self.detail.grid(row=5, column=0, sticky="ew", pady=4)
        self.history_panel = ctk.CTkFrame(listings, fg_color="transparent", height=100)
        self.history_panel.grid(row=6, column=0, sticky="ew")
        self.history = _table(self.history_panel, [("time", "Observation time", 170), ("price", "Listed price", 130),
                                       ("coverage", "Check coverage", 150)], height=3)
        self.history_label, self.history_previous, self.history_next = self._pager(listings, self._history_page, grid_row=7)
        self.history_panel.grid_remove()
        self.history_label.master.grid_remove()
        self.checks = _table(checks, [("time", "Time", 170), ("outcome", "Outcome", 135), ("captured", "Captured", 80),
                                    ("new", "New", 75), ("price_changed", "Price changed", 105), ("no_longer_observed", "No longer observed", 145), ("scope", "Scope", 300)])
        self.checks.bind("<Double-1>", lambda _event: self._open_check())
        self.checks.bind("<Return>", lambda _event: self._open_check())
        ctk.CTkButton(checks, text="View selected check", command=lambda: self._guard(self._open_check), width=170).pack(anchor="w", pady=4)
        self.checks_label, self.checks_previous, self.checks_next = self._pager(checks, self._checks_paginate)
        self.activity = _table(activity, [("time", "Time", 170), ("item", "Item", 220), ("change", "Change", 170),
                                         ("before", "Before price", 120), ("after", "After price", 120)])
        self.activity.bind("<<TreeviewSelect>>", lambda _event: self._activity_selected())
        self.activity_detail = ctk.CTkLabel(activity, text="", anchor="w", justify="left", wraplength=820, text_color="#9AA7B4")
        self.activity_detail.pack(fill="x", pady=4)
        self.activity_label, self.activity_previous, self.activity_next = self._pager(activity, self._activity_paginate)
        self._activity_rows = {}
        self.bind("<Configure>", self._layout_changed)
        self._load_watches()
        self._refresh()

    def _pager(self, parent, action, grid_row=None):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        if grid_row is None:
            bar.pack(fill="x", pady=4)
        else:
            bar.grid(row=grid_row, column=0, sticky="ew", pady=4)
        label = ctk.CTkLabel(bar, text="", anchor="w")
        label.pack(side="left")
        next_button = ctk.CTkButton(bar, text="Older" if grid_row != 4 else "Next", width=80, command=lambda: action(1))
        next_button.pack(side="right")
        previous = ctk.CTkButton(bar, text="Newer" if grid_row != 4 else "Previous", width=80, command=lambda: action(-1))
        previous.pack(side="right", padx=8)
        return label, previous, next_button

    def _guard(self, action):
        try:
            self.message.configure(text="")
            return action()
        except (ValueError, KeyError, OSError) as exc:
            self.message.configure(text=str(exc))

    def _load_watches(self, selected=None):
        watches = self.manager.store.watches()
        self._names = {scope_text(watch["settings"]): watch["id"] for watch in watches}
        self.saved.configure(values=list(self._names) or ["No saved watches"], state="normal" if watches else "disabled")
        selected = selected or self.watch_id or (watches[0]["id"] if watches else None)
        label = next((name for name, key in self._names.items() if key == selected), "No saved watches")
        self.saved.set(label)
        if selected != self.watch_id:
            self._choose(label)

    def _choose(self, name):
        self.watch_id = self._names.get(name)
        self._selected_run, self._offset = None, 0
        self._checks_before, self._activity_before = None, None
        self._check_pages, self._activity_pages = [], []
        self._history_key = None
        self._refresh_data()

    def _open_editor(self, watch_id=None):
        if self._editor is not None and self._editor.winfo_exists():
            self._editor.lift()
            return self._editor
        self._editor = WatchEditor(self, self.runtime, self._saved_watch, watch_id)
        return self._editor

    def _new_watch(self):
        return self._open_editor()

    def _edit_watch(self):
        if not self.watch_id:
            raise ValueError("Create a watch first")
        return self._open_editor(self.watch_id)

    def _saved_watch(self, watch_id):
        self._selected_run, self._offset = None, 0
        self._load_watches(watch_id)
        self._refresh_data()

    def _start(self):
        if not self.watch_id:
            raise ValueError("Create a watch first")
        self.manager.start(self.watch_id)
        self.manager.tick()
        self._refresh_data()

    def _pause(self):
        if self.watch_id:
            active = self.manager.active_run()
            self.manager.pause(self.watch_id)
            if active and active["watch_id"] == self.watch_id:
                self._stopping = active["id"]
            self._refresh_data()

    def _toggle_watching(self):
        if not self.watch_id:
            return
        watch, active = self.manager.store.get(self.watch_id), self.manager.active_run()
        if watch["enabled"] or (active and active["watch_id"] == self.watch_id):
            self._pause()
        else:
            self._start()

    def _check(self):
        if not self.watch_id:
            raise ValueError("Create a watch first")
        self.manager.check_now(self.watch_id)
        self._refresh_data()

    def _choose_run(self, name):
        self._select_run(self._run_names.get(name))

    def _select_run(self, run_id):
        self._selected_run, self._offset = run_id, 0
        self._history_key = None
        self.tabs.set("Listings")
        self._refresh_data()

    def _filter_changed(self):
        self._offset = 0
        self._refresh_data()

    def _sort_by(self, name):
        self._descending = not self._descending if self._sort == name else False
        self._sort = name
        self._refresh_data()

    def _page(self, direction):
        self._offset = max(0, self._offset + direction * self.PAGE_SIZE)
        self._refresh_data()

    def _query_result(self, *, offset=None, run_id=None, limit=None):
        return self.manager.store.desktop_result(self.watch_id, run_id=self._selected_run if run_id is None else run_id,
                                                 limit=limit or self.PAGE_SIZE, offset=self._offset if offset is None else offset,
                                                 search=self.search.get(), status=self.filter.get(), sort=self._sort, descending=self._descending)

    def _refresh_data(self):
        active = self.manager.active_run()
        busy = active is not None
        self.new_button.configure(state="disabled" if busy else "normal")
        self.edit_button.configure(state="normal" if self.watch_id and not busy else "disabled")
        self.check_button.configure(state="normal" if self.watch_id and not busy else "disabled")
        if not self.watch_id:
            self.status.configure(text="Create a paused watch to get started.")
            self.watch_button.configure(state="disabled", text="Start watching")
            self.export_button.configure(state="disabled")
            self.result_status.configure(text="No checks yet. Create a watch, then use Check now or Start watching.")
            return
        watch = self.manager.store.get(self.watch_id)
        own_active = active and active["watch_id"] == self.watch_id
        stopping = own_active and (active["id"] == self._stopping or active["cancelling"])
        if not own_active:
            self._stopping = None
        label = "Stopping…" if stopping else "Pause watching" if watch["enabled"] else "Stop check" if own_active else "Start watching"
        self.watch_button.configure(text=label, state="disabled" if stopping or (busy and not own_active) else "normal")
        state = "Stopping" if stopping else "Checking" if own_active else "Watching" if watch["enabled"] else "Paused"
        self.status.configure(text=f"{state} · Every {watch['settings']['interval_minutes']} minutes")
        self.timing.configure(text=f"Last complete: {_date(watch['last_complete_at'])}   ·   Next check: {_date(watch['next_check'])}")
        result = self._query_result()
        if self._offset and self._offset >= result["total"]:
            self._offset = max(0, (result["total"] - 1) // self.PAGE_SIZE * self.PAGE_SIZE)
            result = self._query_result()
        self._result = result
        run = result["run"]
        latest = result["watch"]["last_run"]
        if result["captured"]:
            counts = result["counts"]
            absence = counts["no_longer_observed"] if counts["no_longer_observed"] is not None else "unverified"
            prefix = "Baseline · " if run["baseline"] else ""
            summary = f"{prefix}{_date(run['observed_at'])} · {run['status'].capitalize()} · Captured {counts['captured']} · New {counts['new']} · Price changed {counts['price_changed']} · No longer observed {absence}"
            if not self._selected_run and latest and latest["id"] != run["id"]:
                summary += f"\nLatest attempt {latest['status']} at {_date(latest['started_at'])}; showing the preceding captured check."
            if run.get("error"):
                summary += f"\n{run['error']}"
            if self._selected_run:
                summary += f"\nScope: {scope_text(result['scope'])}"
        elif run:
            summary = f"{_date(run['started_at'])} · {run['status'].capitalize()} · No snapshot available for this check."
            if run.get("error"):
                summary += f"\n{run['error']}"
        elif result["total"]:
            summary = "Last-known legacy records · Exact check snapshots and change counts are unavailable for older checks."
        else:
            summary = "No captured check in this scope yet. Use Check now to capture listings."
        if not run and latest and latest["revision"] == watch["revision"]:
            summary += f"\nLatest attempt {latest['status']} at {_date(latest['started_at'])}."
            if latest.get("error"):
                summary += f" {latest['error']}"
        self.result_status.configure(text=summary)
        self.export_button.configure(state="normal" if result["captured"] or result["total"] else "disabled")
        self._rows = {row["listing_id"]: row for row in result["rows"]}
        entries = []
        for row in result["rows"]:
            tag = "unknown" if row["remaining"] == "Unknown" else "missing" if row["remaining"] == "No" else "changed" if row["change"] in ("New", "Price changed", "Appeared again") else ""
            entries.append((row["listing_id"], (row.get("item", row["listing_id"]), row["remaining"], previous_price_text(row),
                                                price_text(row.get("price"), row.get("currency", "")), row["change"], row.get("stash_name", "")), (tag,) if tag else ()))
        _sync_table(self.tree, entries)
        self.page_label.configure(text=f"{self._offset + 1 if result['total'] else 0}–{min(self._offset + self.PAGE_SIZE, result['total'])} of {result['total']} listings")
        self.previous_button.configure(state="normal" if self._offset else "disabled")
        self.next_button.configure(state="normal" if self._offset + self.PAGE_SIZE < result["total"] else "disabled")
        self._refresh_ledgers()
        self._listing_selected()

    @staticmethod
    def _count(value):
        return value if value is not None else "—"

    def _refresh_ledgers(self):
        store = self.manager.store
        runs = store.recent_runs(self.watch_id, limit=self.PAGE_SIZE, before=self._checks_before)
        self._checks_page = runs
        entries = []
        for run in runs:
            settings = run["settings"]
            counts = run["counts"]
            outcome = "Baseline" if run["baseline"] and run["status"] == "complete" else run["status"].capitalize()
            entries.append((run["id"], (_date(run["started_at"]), outcome, self._count(counts["captured"]), self._count(counts["new"]),
                                         self._count(counts["price_changed"]), self._count(counts["no_longer_observed"]), scope_text(settings) if settings else "Legacy · scope unavailable"), ()))
        _sync_table(self.checks, entries)
        self.checks_label.configure(text=f"Checks · page {len(self._check_pages) + 1} · Enter or View selected check to review")
        self.checks_previous.configure(state="normal" if self._check_pages else "disabled")
        self.checks_next.configure(state="normal" if len(runs) == self.PAGE_SIZE else "disabled")
        self._run_names = {f"{_date(run['started_at'])} · {run['status']} · Captured {self._count(run['counts']['captured'])} · Check {run['cursor']}": run["id"] for run in runs}
        if self._selected_run and self._selected_run not in self._run_names.values():
            selected = store.run(self._selected_run)
            self._run_names[f"{_date(selected['started_at'])} · {selected['status']} · Selected check"] = self._selected_run
        self.run_selector.configure(values=["Latest captured result", *self._run_names])
        self.run_selector.set(next((name for name, key in self._run_names.items() if key == self._selected_run), "Latest captured result"))
        events = store.recent_events(self.watch_id, limit=self.PAGE_SIZE, before=self._activity_before)
        self._activity_page = events
        self._activity_rows = {str(event["id"]): event for event in events}
        entries = []
        for event in events:
            before, after = event["before"], event["after"]
            row = after or before or {}
            change = "Baseline" if event["baseline"] else CHANGE_LABELS.get(event["type"], event["type"])
            entries.append((str(event["id"]), (_date(event["observed_at"]), row.get("item", event["listing_id"]), change,
                                              price_text(before.get("price"), before.get("currency", "")) if before else "—",
                                              price_text(after.get("price"), after.get("currency", "")) if after else "—"), ()))
        _sync_table(self.activity, entries)
        self.activity_label.configure(text=f"Activity · page {len(self._activity_pages) + 1} · No longer observed does not confirm a sale.")
        self.activity_previous.configure(state="normal" if self._activity_pages else "disabled")
        self.activity_next.configure(state="normal" if len(events) == self.PAGE_SIZE else "disabled")
        self._activity_selected()

    def _checks_paginate(self, direction):
        if direction > 0 and self._checks_page:
            self._check_pages.append(self._checks_before)
            self._checks_before = self._checks_page[-1]["cursor"]
        elif direction < 0 and self._check_pages:
            self._checks_before = self._check_pages.pop()
        self._refresh_data()

    def _activity_paginate(self, direction):
        if direction > 0 and self._activity_page:
            self._activity_pages.append(self._activity_before)
            self._activity_before = self._activity_page[-1]["id"]
        elif direction < 0 and self._activity_pages:
            self._activity_before = self._activity_pages.pop()
        self._refresh_data()

    def _open_check(self):
        selected = self.checks.selection()
        if selected:
            self._select_run(selected[0])

    def _activity_selected(self):
        selected = self.activity.selection()
        event = self._activity_rows.get(selected[0]) if selected else None
        self.activity_detail.configure(text=f"{scope_text(event['settings'])}\n{event_text(event)}" if event else "Select an event to see its recorded scope.")

    def _listing_selected(self):
        selected = self.tree.selection()
        row = self._rows.get(selected[0]) if selected else None
        if not row:
            self.history_toggle.configure(state="disabled")
            self.history_panel.grid_remove()
            self.history_label.master.grid_remove()
            self.detail.configure(text="Select a listing to review its history. No longer observed does not confirm a sale.")
            _sync_table(self.history, [])
            self.history_label.configure(text="Observation history")
            self.history_previous.configure(state="disabled")
            self.history_next.configure(state="disabled")
            self._history_key = None
            return
        self.history_toggle.configure(state="normal")
        if self._history_visible:
            self.history_panel.grid()
            self.history_label.master.grid()
        run = self._result["run"] or {}
        revision = run.get("revision") or self._result["watch"]["revision"]
        key = (self.watch_id, revision, row["listing_id"])
        if key != self._history_key:
            self._history_key, self._history_before, self._history_pages = key, None, []
        self.detail.configure(text=f"Listing ID: {row['listing_id']} · First seen: {_date(row.get('first_seen_at'))} · Last seen: {_date(row.get('last_seen_at'))}\n"
                                  f"Absence observed: {_date(row.get('absent_at'))} · Still listed? {row['remaining']} · No means absent from a complete check; a sale is unconfirmed.")
        observations = self.manager.store.listing_history(key[0], key[2], revision=key[1], limit=30, before=self._history_before)
        self._history_observations = observations
        entries = []
        for observation in observations:
            coverage = observation["status"] or "Legacy · unavailable"
            entries.append((str(observation["id"]), (_date(observation["observed_at"]), price_text(observation.get("price"), observation.get("currency", "")), coverage), ()))
        _sync_table(self.history, entries)
        self.history_label.configure(text=f"Observation history · page {len(self._history_pages) + 1}")
        self.history_previous.configure(state="normal" if self._history_pages else "disabled")
        self.history_next.configure(state="normal" if len(observations) == 30 else "disabled")

    def _toggle_history(self):
        self._history_visible = not self._history_visible
        self.history_toggle.configure(text="Hide history" if self._history_visible else "Show history")
        if self._history_visible:
            self._listing_selected()
        else:
            self.history_panel.grid_remove()
            self.history_label.master.grid_remove()

    def _layout_changed(self, event):
        if event.widget not in (self, self._canvas):
            return
        for label in (self.message, self.result_status, self.detail, self.activity_detail):
            label.configure(wraplength=max(300, event.width - 48))
        if event.height < 820 and self._history_visible:
            self._toggle_history()

    def _history_page(self, direction):
        if direction > 0 and self._history_observations:
            self._history_pages.append(self._history_before)
            self._history_before = self._history_observations[-1]["id"]
        elif direction < 0 and self._history_pages:
            self._history_before = self._history_pages.pop()
        self._listing_selected()

    def _export(self):
        if not self.watch_id:
            raise ValueError("Create a watch first")
        first = self.manager.store.desktop_export(self.watch_id, self._selected_run, search=self.search.get(),
                                                  status=self.filter.get(), sort=self._sort, descending=self._descending)
        if not first["captured"] and not first["total"]:
            raise ValueError("No snapshot is available to export")
        filename = filedialog.asksaveasfilename(parent=self, title="Export selected check", defaultextension=".csv",
                                               initialfile=f"stashwatch-{(first['run'] or {}).get('id', 'legacy')}.csv", filetypes=[("CSV", "*.csv")])
        if not filename:
            return
        Path(filename).write_text(result_csv(first), encoding="utf-8", newline="")
        self.message.configure(text=f"Exported {len(first['rows'])} matching listings from the selected check.")

    def _refresh(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._guard(self._load_watches)
        self._guard(self._refresh_data)
        self._after_id = self.after(3000, self._refresh)

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        if self._editor is not None and self._editor.winfo_exists():
            self._editor.destroy()
        super().destroy()
