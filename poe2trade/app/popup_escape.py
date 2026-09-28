"""Root-owned popup dismissal, with a focus-independent presenter input path."""
from __future__ import annotations

import logging
import queue
import sys
import tkinter as tk


class EscapeSequence:
    """Capture one popup on press; consume repeats and release before closing."""

    def __init__(self, pending):
        self.pending = pending
        self.target = None
        self.held = False

    def handle(self, event, target):
        if event.scan_code != 1 or event.is_keypad:
            return True
        if event.event_type == "down":
            if not self.held:
                self.held = True
                self.target = target
            return self.target is None
        captured = self.target
        self.held = False
        self.target = None
        if captured is not None:
            self.pending.put(captured)
        return captured is None


class PopupEscape:
    def __init__(self, root):
        self.root = root
        self.entries = {}
        self.active = None
        self.pending = queue.SimpleQueue()
        self.sequence = EscapeSequence(self.pending)
        self.hook = None
        self.timer = None
        self.local_release = None
        self.closed = False
        root.bind("<Destroy>", self._destroyed, add="+")
        self._poll()

    def start_native(self):
        if sys.platform != "win32" or self.hook is not None:
            return
        from poe2trade.utils._windows_hotkey_hook import WindowsHook

        hook = WindowsHook(lambda event: self.sequence.handle(event, self.active), lambda: None)
        self.sequence.held = hook.down(0x1B)
        try:
            hook.start()
        except Exception:
            logging.exception("Could not start popup Escape interception")
            hook.stop()
            return
        self.hook = hook

    def register(self, window, close, token=None):
        token = token if token in self.entries else object()
        # A new registration invalidates any pending press for the old view.
        for old, (registered, _) in list(self.entries.items()):
            if registered is window:
                self.entries.pop(old)
        self.entries[token] = (window, close)

        def local(event):
            self.refresh()
            target = self.active
            # Native interception owns real Windows events in the presenter.
            # This binding also supports focused dialogs and synthetic Tk input.
            from types import SimpleNamespace
            key = SimpleNamespace(
                scan_code=1, is_keypad=False,
                event_type="up" if event.type == tk.EventType.KeyRelease else "down",
            )
            if self.local_release is not None:
                self.root.after_cancel(self.local_release)
                self.local_release = None
            if key.event_type == "up" and self.sequence.target is not None:
                # X11 autorepeat can emit a release immediately followed by a
                # press. Wait one idle turn so that pair cannot close a popup.
                def release():
                    self.local_release = None
                    self.sequence.handle(key, target)
                    self._drain()

                self.local_release = self.root.after_idle(release)
                return "break"
            accepted = self.sequence.handle(key, target)
            if not accepted:
                self._drain()
                return "break"
            return None

        window.bind("<KeyPress-Escape>", local)
        window.bind("<KeyRelease-Escape>", local)
        window.bind("<Destroy>", lambda event: self.unregister(token)
                    if event.widget is window and self.entries.get(token, (None,))[0] is window else None, add="+")
        self.refresh()
        return token

    def unregister(self, token):
        self.entries.pop(token, None)
        self.refresh()

    def refresh(self):
        active = None
        try:
            grab = self.root.grab_current()
            stacking = self.root.tk.call("wm", "stackorder", self.root._w)
            rank = {str(path): index for index, path in enumerate(stacking)}
            ordered = sorted(self.entries.items(), key=lambda entry: rank.get(str(entry[1][0]), -1))
            for token, (window, _) in reversed(ordered):
                if not window.winfo_exists():
                    self.entries.pop(token, None)
                    continue
                if not window.winfo_viewable() or float(window.attributes("-alpha")) == 0:
                    continue
                # A native modal dialog owns Escape until it closes. A mouse
                # grab on the presenter's backdrop also takes precedence.
                if grab is not None and grab.winfo_toplevel() is not window:
                    continue
                active = token
                break
        except (tk.TclError, KeyError):
            # Tk cannot resolve some native dialog grab paths to Python widgets.
            active = None
        self.active = active

    def _drain(self):
        while not self.pending.empty():
            token = self.pending.get_nowait()
            self.refresh()
            if token is self.active and token in self.entries:
                try:
                    self.entries[token][1]()
                except Exception:
                    logging.exception("Popup Escape cancellation failed")

    def _poll(self):
        if self.closed:
            return
        self.refresh()
        self._drain()
        self.timer = self.root.after(10, self._poll)

    def _destroyed(self, event):
        if event.widget is self.root:
            self.stop()

    def stop(self):
        if self.closed:
            return
        self.closed = True
        self.active = None
        self.entries.clear()
        if self.timer is not None:
            try:
                self.root.after_cancel(self.timer)
            except tk.TclError:
                pass
        if self.local_release is not None:
            try:
                self.root.after_cancel(self.local_release)
            except tk.TclError:
                pass
        if self.hook is not None:
            self.hook.stop()


def coordinator(root):
    current = getattr(root, "_popup_escape", None)
    if current is None:
        current = root._popup_escape = PopupEscape(root)
    return current


def register_popup(root, window, close):
    return coordinator(root).register(window, close)
