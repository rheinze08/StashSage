# hotkeys.py -- cross-platform global hotkey + key-injection backend
#
# On Windows action shortcuts use a native hook; key injection uses keyboard. On
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
import logging
import time
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
_MODIFIERS.update(f"{side} {name}" for side in ("left", "right")
                  for name in ("ctrl", "control", "shift", "alt", "windows", "win"))
_suspended = False
_injecting = 0


def _normal_modifier(token):
    words = token.split()
    base = _MODIFIER_ALIASES.get(words[-1], words[-1])
    base = {"cmd": "windows", "alt_gr": "altgr"}.get(base, base)
    return " ".join(words[:-1] + [base])


def _matches_modifiers(required, actual):
    covered = set()
    for name in required:
        matches = {key for key in actual if key == name or key.endswith(" " + name)}
        if not matches:
            return False
        covered.update(matches)
    # Right Alt often generates a synthetic Ctrl. Reserve this combination
    # for AltGr rather than accidentally running Ctrl+Alt shortcuts.
    if "right alt" in actual and any(key.endswith("ctrl") for key in actual):
        return False
    return covered == set(actual)


def _modifiers_overlap(first, second):
    import itertools
    keys = ("left ctrl", "right ctrl", "left shift", "right shift",
            "left alt", "right alt", "left windows", "right windows")
    return any(_matches_modifiers(first, actual) and _matches_modifiers(second, actual)
               for count in range(9) for actual in itertools.combinations(keys, count))


def set_suspended(value: bool) -> None:
    """Let shortcut editors receive input without launching an action."""
    global _suspended
    _suspended = value


def action_shortcut(value: str | None, default: str) -> str:
    value = (value or "").strip().lower()
    value = value or default
    return "+".join(token.strip() for token in value.split("+"))


class _TriggerDispatcher:
    """Own each physical press once, including releases after a rebind."""

    def __init__(self, modifiers, physical_down, dispatch):
        self.modifiers = modifiers
        self.physical_down = physical_down
        self.dispatch = dispatch
        self.bindings = {}
        self.pressed = {}
        self.lock = threading.RLock()

    def handle(self, event):
        identity = (event.scan_code, bool(event.is_keypad))
        with self.lock:
            try:
                if event.event_type == "up":
                    previous = self.pressed.pop(identity, None)
                    return not (previous and previous[0])
                if event.event_type != "down":
                    return True
                if identity in self.pressed:
                    suppressed = self.pressed[identity][0]
                    self.pressed[identity] = (suppressed, time.monotonic())
                    return not suppressed
                matches = [(chord, callback) for chord, callback in self.bindings.items()
                           if identity[0] in chord[0] and identity[1] == chord[1]]
                if not matches:
                    return True
                callback = next((callback for chord, callback in matches
                                 if _matches_modifiers(chord[2], self.modifiers())), None)
                suppress = callback is not None and not _suspended and not _injecting
                self.pressed[identity] = (suppress, time.monotonic())
                if suppress:
                    self.dispatch(callback)
                return not suppress
            except Exception:
                self.pressed.pop(identity, None)
                logging.exception("Hotkey dispatch failed; passing input through")
                return True

    def reconcile(self):
        with self.lock:
            try:
                for identity, (suppressed, since) in list(self.pressed.items()):
                    # Query after Windows applies its current event; age alone
                    # must never expire a genuinely held key.
                    age = time.monotonic() - since
                    down = self.physical_down(identity)
                    if age > 0.1 and down is False:
                        del self.pressed[identity]
                        logging.debug("Hotkey released-state reconciliation")
                    elif suppressed and down is None and age > 2 and not self.modifiers():
                        # Suppressed triggers have no usable Windows async
                        # state. After modifiers are released AND repeats have
                        # stopped, recover pass-through but keep a tombstone
                        # until key-up. A possibly-held key must not fire again.
                        self.pressed[identity] = (False, since)
                        logging.debug("Inactive shortcut recovered to pass-through")
            except Exception:
                self.pressed.clear()
                logging.exception("Hotkey reconciliation failed; cleared suppression state")


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

    The Windows action hook suppresses only this final trigger key. Multi-step
    action shortcuts are rejected rather than reverting to modifier suppression.
    """
    if "," in hotkey:
        return None
    tokens = _split_combo(hotkey)
    trigger = [token for token in tokens if token not in _MODIFIERS]
    if len(trigger) != 1:
        return None
    return [token for token in tokens if token in _MODIFIERS], trigger[0]


if sys.platform == "win32":
    # ---- Windows: native action hook, keyboard name mapping/injection ------
    import keyboard as _kb

    from poe2trade.utils._windows_hotkey_hook import WindowsHook

    _native = None
    _dispatcher = None
    _registration_lock = threading.RLock()
    _injection_lock = threading.RLock()
    _legacy_handles = []
    _legacy_chords = {}

    def _conflicts(first, second):
        return (bool(set(first[0]) & set(second[0]))
                and (first[1] is None or second[1] is None or first[1] == second[1])
                and _modifiers_overlap(first[2], second[2]))

    def _dispatch(callback):
        def run():
            try:
                callback()
            except Exception:
                logging.exception("Hotkey action failed")
        threading.Thread(target=run, name="HotkeyAction", daemon=True).start()

    def _ensure_dispatcher():
        global _native, _dispatcher
        if _native is None or _native.stopped.is_set():
            candidate = _dispatcher or _TriggerDispatcher(
                lambda: _native.modifiers(), lambda key: _native.physical_down(key), _dispatch,
            )
            with candidate.lock:
                candidate.pressed.clear()
            native = WindowsHook(candidate.handle, candidate.reconcile)
            _native = native
            _dispatcher = candidate
            native.start()
            logging.info("Action hotkey backend: native Windows hook")
        return _dispatcher

    def _resolve_chord(hotkey):
        if any(not token.strip() for token in hotkey.split("+")):
            raise ValueError("Shortcut contains an empty key name")
        parts = _single_chord_parts(hotkey)
        if parts is None:
            raise ValueError("Use modifiers and one trigger key for an action shortcut")
        modifiers, trigger = parts
        required = frozenset(_normal_modifier(token) for token in modifiers)
        if "altgr" in required:
            raise ValueError("AltGr shortcuts are not supported; choose another modifier")
        keypad = trigger.startswith("num") and len(trigger) == 4 and trigger[-1].isdigit()
        if keypad:
            # Physical keypad layout is fixed by Windows; ordinary digits
            # below still use the installed keyboard layout's name mapping.
            codes = ({"0": 82, "1": 79, "2": 80, "3": 81, "4": 75,
                      "5": 76, "6": 77, "7": 71, "8": 72, "9": 73}[trigger[-1]],)
        else:
            codes = tuple(sorted(set(_kb.key_to_scan_codes(trigger))))
            if len(trigger) == 1 and trigger.isdigit():
                codes = tuple(code for code in codes if code not in (71, 72, 73, 75, 76, 77, 79, 80, 81, 82))
        if not codes or any(code <= 0 for code in codes):
            raise ValueError("No main-keyboard key found for this shortcut")
        return (codes, keypad, required)

    def validate_hotkey(hotkey):
        if hotkey != "off":
            _resolve_chord(hotkey)

    def _add_trigger_only_suppressed_hotkey(hotkey: str, callback: Callable):
        chord = _resolve_chord(hotkey)
        with _registration_lock:
            dispatcher = _ensure_dispatcher()
            with dispatcher.lock:
                for existing in list(dispatcher.bindings) + list(_legacy_chords.values()):
                    if _conflicts(existing, chord):
                        raise ValueError("This shortcut conflicts with another active action")
                dispatcher.bindings[chord] = callback
            logging.info("Action shortcut registered: %s (keypad=%s)", hotkey, chord[1])

        removed = False

        def remove():
            nonlocal removed
            with dispatcher.lock:
                if removed:
                    return
                dispatcher.bindings.pop(chord, None)
                removed = True
                # Held presses remain owned until release/reconciliation.
            logging.info("Action shortcut removed: %s", hotkey)
        return remove

    def add_hotkey(hotkey: str, callback: Callable, suppress: bool = False):
        if suppress:
            return _add_trigger_only_suppressed_hotkey(hotkey, callback)
        chord = _resolve_chord(hotkey) if _single_chord_parts(hotkey) else None
        if chord is not None:
            trigger = _single_chord_parts(hotkey)[1]
            # Upstream non-suppressed bindings still alias keypad scan codes.
            chord = (tuple(_kb.key_to_scan_codes(trigger)), None, chord[2])
        if chord is not None and _dispatcher is not None:
            with _dispatcher.lock:
                if any(_conflicts(existing, chord) for existing in _dispatcher.bindings):
                    raise ValueError("This shortcut conflicts with an active action")
        handle = _kb.add_hotkey(hotkey, lambda: None if _suspended else callback(), suppress=False)
        _legacy_handles.append(handle)
        if chord is not None:
            _legacy_chords[handle] = chord
        return handle

    def remove_hotkey(handle) -> None:
        if callable(handle):
            handle()
        else:
            _kb.remove_hotkey(handle)
        if handle in _legacy_handles:
            _legacy_handles.remove(handle)
            _legacy_chords.pop(handle, None)

    def shutdown() -> None:
        global _native, _dispatcher
        set_suspended(False)
        with _registration_lock:
            if _native is not None:
                _native.stop()
                _native = None
                _dispatcher = None
            for handle in list(_legacy_handles):
                remove_hotkey(handle)

    def _inject(function, value):
        global _injecting
        with _injection_lock:
            _injecting += 1
            try:
                function(value)
            finally:
                _injecting -= 1

    def send(combo: str) -> None:
        def emit(value):
            parts = _single_chord_parts(value)
            if _native is not None and parts is not None:
                modifiers, trigger = parts
                actual = _native.modifiers()
                # Do not synthesize a release for a Ctrl the user still owns.
                # A real release during copying stays native; never restore a
                # saved modifier snapshot after the user has let go.
                missing = [name for name in modifiers if not any(
                    key == _normal_modifier(name) or key.endswith(" " + _normal_modifier(name))
                    for key in actual
                )]
                value = "+".join(missing + [trigger])
            _kb.send(value)
        _inject(emit, combo)

    def write(text: str) -> None:
        _inject(_kb.write, text)

    def press_and_release(combo: str) -> None:
        send(combo)

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
                if key in self._bindings:
                    raise ValueError("This shortcut is already active")
                wrapped = lambda: None if _suspended else callback()
                self._bindings[key] = wrapped
                try:
                    self._rebuild_listener()
                except Exception:
                    del self._bindings[key]
                    raise
            removed = False

            def remove():
                nonlocal removed
                with self._lock:
                    if not removed:
                        if self._bindings.get(key) is wrapped:
                            self.remove_hotkey(key)
                        removed = True
            return remove

        def remove_hotkey(self, handle) -> None:
            if callable(handle):
                handle()
                return
            with self._lock:
                previous = dict(self._bindings)
                # handle is normally the value returned by add_hotkey, but be
                # forgiving and also accept a raw keyboard-style hotkey string.
                if handle in self._bindings:
                    del self._bindings[handle]
                else:
                    self._bindings.pop(_to_pynput_hotkey(str(handle)), None)
                try:
                    self._rebuild_listener()
                except Exception:
                    self._bindings = previous
                    raise

        def _rebuild_listener(self) -> None:
            from pynput.keyboard import GlobalHotKeys

            listener = GlobalHotKeys(dict(self._bindings)) if self._bindings else None
            if listener is not None:
                listener.start()
            if self._listener is not None:
                try:
                    self._listener.stop()
                except Exception:
                    if listener is not None:
                        listener.stop()
                    raise
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

    def validate_hotkey(hotkey):
        if hotkey != "off":
            from pynput.keyboard import HotKey
            HotKey.parse(_to_pynput_hotkey(hotkey))

    def shutdown() -> None:
        set_suspended(False)
        with _backend._lock:
            _backend._bindings.clear()
            _backend._rebuild_listener()

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
