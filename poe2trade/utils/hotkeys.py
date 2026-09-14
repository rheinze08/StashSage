# hotkeys.py -- cross-platform global hotkey + key-injection backend
#
# On Windows the app uses the `keyboard` package (unchanged behaviour). On
# Linux `keyboard` reads /dev/input directly and therefore refuses to bind
# hotkeys unless the process runs as root ("You must be root to use this
# library on linux"). `pynput` hooks the X11/Wayland layer instead and works
# as an ordinary user, so we route Linux through it.
#
# gui_tk imports this module *as* `keyboard`, so the public surface mirrors the
# subset of the `keyboard` API the app actually relies on:
#     add_hotkey(hotkey, callback, suppress=False) -> handle
#     remove_hotkey(handle)
#     send(combo)
#     write(text)
#     press_and_release(combo)
from __future__ import annotations

import sys
import threading
from typing import Callable, Dict, List

# Modifier aliases, normalised to the names pynput understands. `keyboard`
# accepts a few Windows-flavoured spellings ("win", "super", "windows") that
# pynput exposes as "cmd".
_MODIFIER_ALIASES: Dict[str, str] = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "alt_gr": "alt_gr",
    "altgr": "alt_gr",
    "shift": "shift",
    "cmd": "cmd",
    "win": "cmd",
    "super": "cmd",
    "windows": "cmd",
}

_MODIFIERS = set(_MODIFIER_ALIASES)


def _split_combo(combo: str) -> List[str]:
    """Split a '+'-separated key combo into normalised (lowercase, trimmed)
    tokens, dropping empties."""
    return [p.strip().lower() for p in combo.split("+") if p.strip()]


def _to_pynput_hotkey(hotkey: str) -> str:
    """Convert a `keyboard`-style hotkey ('ctrl+1') into the format
    pynput.keyboard.GlobalHotKeys expects ('<ctrl>+1').

    Named keys and modifiers are wrapped in angle brackets; single printable
    characters (letters, digits) are left bare.
    """
    out: List[str] = []
    for token in _split_combo(hotkey):
        token = _MODIFIER_ALIASES.get(token, token)
        if len(token) == 1 and token.isprintable():
            out.append(token)
        else:
            out.append(f"<{token}>")
    return "+".join(out)


def _single_chord_parts(hotkey: str) -> tuple[list[str], str] | None:
    """Return modifiers and one trigger key for a simple hotkey chord.

    The Windows hook can safely suppress only this final trigger key.  Chords
    with comma-separated steps continue through the upstream implementation,
    whose wider suppression is required to interpret their sequence.
    """
    if "," in hotkey:
        return None
    tokens = _split_combo(hotkey)
    trigger = [token for token in tokens if token not in _MODIFIERS]
    if len(trigger) != 1:
        return None
    return [token for token in tokens if token in _MODIFIERS], trigger[0]


if sys.platform == "win32":
    # ---- Windows: delegate straight to the `keyboard` package -------------
    import keyboard as _kb

    def _windows_modifier_name(token: str) -> str:
        """Map our permissive modifier spellings to keyboard's Windows names."""
        token = token.lower()
        if token in {"win", "super", "windows", "cmd"}:
            return "windows"
        if token == "control":
            return "ctrl"
        return token

    def _add_trigger_only_suppressed_hotkey(hotkey: str, callback: Callable):
        """Suppress the trigger key without delaying a held Ctrl/Shift/Alt.

        ``keyboard.add_hotkey(..., suppress=True)`` suppresses modifiers while
        it decides whether they form a chord.  For Ctrl+1 that can hold Ctrl
        back from the game for its one-second chord timeout.  Keeping modifier
        events native while swallowing only ``1`` preserves instant game
        control input and still prevents the hotkey's action key leaking into
        PoE.
        """
        parts = _single_chord_parts(hotkey)
        if parts is None:
            return _kb.add_hotkey(hotkey, callback, suppress=True)
        modifiers, trigger = parts
        required = [_windows_modifier_name(token) for token in modifiers]
        trigger_down = False

        def handler(event):
            nonlocal trigger_down
            if event.event_type == _kb.KEY_DOWN:
                if trigger_down:
                    return False
                if all(_kb.is_pressed(modifier) for modifier in required):
                    trigger_down = True
                    # keyboard.add_hotkey normally schedules callbacks away
                    # from its low-level suppression hook.  Do the same so
                    # clipboard capture/model startup cannot stall input.
                    threading.Thread(target=callback, daemon=True).start()
                    return False
                return True
            if event.event_type == _kb.KEY_UP and trigger_down:
                trigger_down = False
                return False
            return True

        return _kb.hook_key(trigger, handler, suppress=True)

    def add_hotkey(hotkey: str, callback: Callable, suppress: bool = False):
        if suppress:
            return _add_trigger_only_suppressed_hotkey(hotkey, callback)
        return _kb.add_hotkey(hotkey, callback, suppress=False)

    def remove_hotkey(handle) -> None:
        # Both keyboard.add_hotkey and keyboard.hook_key return no-argument
        # removers. Calling it directly supports either registration style.
        if callable(handle):
            handle()
        else:
            _kb.remove_hotkey(handle)

    def send(combo: str) -> None:
        _kb.send(combo)

    def write(text: str) -> None:
        _kb.write(text)

    def press_and_release(combo: str) -> None:
        _kb.press_and_release(combo)

else:
    # ---- Linux / other: drive global hotkeys + injection via pynput -------
    # pynput is imported lazily so this module (and its pure helpers) import
    # cleanly on machines/CI where pynput is not installed.

    def _resolve_key(name: str):
        """Map a token to a pynput key object (named keys) or a bare character."""
        from pynput.keyboard import Key

        name = _MODIFIER_ALIASES.get(name, name)
        if len(name) == 1:
            return name
        if name in ("return", "enter"):
            return Key.enter
        if name in ("esc", "escape"):
            return Key.esc
        if name in ("del", "delete"):
            return Key.delete
        # f1..f12, space, tab, backspace, ctrl, alt, shift, cmd, ...
        return getattr(Key, name, name)

    class _LinuxHotkeys:
        """Maintains the active hotkey bindings behind a single
        pynput GlobalHotKeys listener, rebuilt whenever bindings change."""

        def __init__(self) -> None:
            self._lock = threading.RLock()
            self._bindings: Dict[str, Callable] = {}
            self._listener = None
            self._controller = None

        # -- global hotkeys --------------------------------------------------
        def add_hotkey(self, hotkey: str, callback: Callable, suppress: bool = False):
            key = _to_pynput_hotkey(hotkey)
            with self._lock:
                self._bindings[key] = callback
                self._rebuild_listener()
            return key

        def remove_hotkey(self, handle) -> None:
            with self._lock:
                # handle is normally the value returned by add_hotkey, but be
                # forgiving and also accept a raw keyboard-style hotkey string.
                if handle in self._bindings:
                    del self._bindings[handle]
                else:
                    self._bindings.pop(_to_pynput_hotkey(str(handle)), None)
                self._rebuild_listener()

        def _rebuild_listener(self) -> None:
            from pynput.keyboard import GlobalHotKeys

            if self._listener is not None:
                try:
                    self._listener.stop()
                except Exception:
                    pass
                self._listener = None
            if not self._bindings:
                return
            listener = GlobalHotKeys(dict(self._bindings))
            listener.daemon = True
            listener.start()
            self._listener = listener

        # -- key injection ---------------------------------------------------
        def _ctrl(self):
            if self._controller is None:
                from pynput.keyboard import Controller

                self._controller = Controller()
            return self._controller

        def send(self, combo: str) -> None:
            keys = [_resolve_key(t) for t in _split_combo(combo)]
            if not keys:
                return
            controller = self._ctrl()
            held, tap = keys[:-1], keys[-1]
            for key in held:
                controller.press(key)
            try:
                controller.press(tap)
                controller.release(tap)
            finally:
                for key in reversed(held):
                    controller.release(key)

        def write(self, text: str) -> None:
            self._ctrl().type(text)

    _backend = _LinuxHotkeys()

    def add_hotkey(hotkey: str, callback: Callable, suppress: bool = False):
        return _backend.add_hotkey(hotkey, callback, suppress=suppress)

    def remove_hotkey(handle) -> None:
        _backend.remove_hotkey(handle)

    def send(combo: str) -> None:
        _backend.send(combo)

    def write(text: str) -> None:
        _backend.write(text)

    def press_and_release(combo: str) -> None:
        _backend.send(combo)
