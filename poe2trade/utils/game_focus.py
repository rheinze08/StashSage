"""Foreground identity checks for game-facing shortcuts; never activate on doubt."""
from __future__ import annotations

import logging
import os
import sys
import threading


_CLIENTS = frozenset({
    "pathofexile.exe", "pathofexile_x64.exe", "pathofexilesteam.exe",
    "pathofexile_x64steam.exe", "pathofexile2.exe", "pathofexile2steam.exe",
    "pathofexile2_x64.exe", "pathofexile2_x64steam.exe",
    "pathofexile", "pathofexile2",
})
_X11_CLASSES = _CLIENTS | {"steam_app_238960", "steam_app_2694490"}
_xdisplay = None
_lock = threading.Lock()
_warned = False


def _windows_client() -> str:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value.replace("\\", "/").rsplit("/", 1)[-1].lower()
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _x11_is_poe() -> bool:
    # XWayland cannot establish whether a native Wayland window has focus.
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
        raise RuntimeError("Automatic game shortcuts require X11; native Wayland detection is unavailable")
    from Xlib import X, display

    global _xdisplay
    with _lock:
        try:
            if _xdisplay is None:
                _xdisplay = display.Display()
            root = _xdisplay.screen().root
            active = root.get_full_property(_xdisplay.intern_atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
            if active is None or not len(active.value) or not active.value[0]:
                return False
            window = _xdisplay.create_resource_object("window", int(active.value[0]))
            return any(name.lower() in _X11_CLASSES for name in (window.get_wm_class() or ()))
        except Exception:
            if _xdisplay is not None:
                try:
                    _xdisplay.close()
                except Exception:
                    pass
                _xdisplay = None
            raise


def is_poe_foreground() -> bool:
    global _warned
    try:
        if sys.platform == "win32":
            return _windows_client() in _CLIENTS
        if sys.platform.startswith("linux"):
            return _x11_is_poe()
        return False
    except Exception:
        if not _warned:
            logging.warning("Game shortcuts inactive: foreground detection unavailable", exc_info=True)
            _warned = True
        return False
