"""Small native adapter for action shortcuts; callbacks must never block.

Owning this hook lets us see real releases even while keyboard.send() bypasses
that library's listener. Injected copy input is passed through without becoming
physical shortcut state. This module is imported only on Windows.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import threading
from types import SimpleNamespace


def _physical_event(data, message):
    if data.flags & 0x10:  # LLKHF_INJECTED
        return None
    extended = bool(data.flags & 1)
    keypad = (0x60 <= data.vkCode <= 0x6F or
              (not extended and data.scanCode in
               (71, 72, 73, 75, 76, 77, 79, 80, 81, 82, 83)) or
              (extended and data.vkCode == 0x0D))
    return SimpleNamespace(scan_code=data.scanCode, is_keypad=keypad,
                           event_type="down" if message in (0x100, 0x104) else "up")


class WindowsHook:
    def __init__(self, handle, reconcile):
        self.handle = handle
        self.reconcile = reconcile
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        self.user32.MapVirtualKeyW.restype = wintypes.UINT
        self.vks = {}
        self.suppressed = set()
        self.ready = threading.Event()
        self.stopped = threading.Event()
        self.error = None
        self.thread_id = None
        self.thread = threading.Thread(target=self._run, name="ActionHotkeys", daemon=True)

    def start(self):
        self.thread.start()
        if not self.ready.wait(5):
            raise RuntimeError("Timed out starting Windows action hotkeys")
        if self.error:
            raise RuntimeError("Could not install Windows action hotkeys") from self.error

    def down(self, vk):
        return bool(self.user32.GetAsyncKeyState(vk) & 0x8000)

    def modifiers(self):
        # Side-specific state also distinguishes Right Alt / AltGr. It must
        # not accidentally satisfy an ordinary Ctrl+Alt shortcut.
        return frozenset(name for name, vk in (
            ("left ctrl", 0xA2), ("right ctrl", 0xA3),
            ("left shift", 0xA0), ("right shift", 0xA1),
            ("left alt", 0xA4), ("right alt", 0xA5),
            ("left windows", 0x5B), ("right windows", 0x5C),
        ) if self.down(vk))

    def physical_down(self, identity):
        if identity in self.suppressed:
            # Windows does not update asynchronous state for swallowed input.
            # False would incorrectly expire a genuinely held trigger.
            return None
        vk = self.vks.get(identity)
        if vk is None:
            return False
        # Num Lock can change the VK associated with a still-held keypad key.
        # Conservatively retain state if either interpretation is down.
        if identity[1]:
            scan = identity[0]
            alternate = self.user32.MapVirtualKeyW(scan, 1)
            return self.down(vk) or bool(alternate and self.down(alternate))
        return self.down(vk)

    def stop(self):
        if self.stopped.is_set():
            return
        if self.thread_id is not None:
            if not self.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0):
                raise ctypes.WinError(ctypes.get_last_error())
            self.thread.join(2)
            if self.thread.is_alive():
                raise RuntimeError("Windows action hotkey thread did not stop")

    def _run(self):
        hook = None
        timer = None
        try:
            ULONG_PTR = ctypes.c_size_t
            LRESULT = ctypes.c_ssize_t

            class KeyData(ctypes.Structure):
                _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                            ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                            ("dwExtraInfo", ULONG_PTR)]

            callback_type = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
            self.user32.SetWindowsHookExW.argtypes = [ctypes.c_int, callback_type, wintypes.HINSTANCE, wintypes.DWORD]
            self.user32.SetWindowsHookExW.restype = wintypes.HANDLE
            self.user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
            self.user32.CallNextHookEx.restype = LRESULT
            self.user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
            self.user32.SetTimer.argtypes = [wintypes.HWND, ULONG_PTR, wintypes.UINT, ctypes.c_void_p]
            self.user32.SetTimer.restype = ULONG_PTR
            self.user32.KillTimer.argtypes = [wintypes.HWND, ULONG_PTR]
            self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE

            def callback(code, message, pointer):
                if code >= 0 and message in (0x100, 0x101, 0x104, 0x105):
                    try:
                        data = ctypes.cast(pointer, ctypes.POINTER(KeyData)).contents
                        event = _physical_event(data, message)
                        if event is not None:
                            identity = (event.scan_code, event.is_keypad)
                            self.vks[identity] = data.vkCode
                            accepted = self.handle(event)
                            if event.event_type == "up":
                                self.suppressed.discard(identity)
                            elif not accepted:
                                self.suppressed.add(identity)
                            if not accepted:
                                return 1
                    except Exception:
                        logging.exception("Windows hotkey event failed; passing input through")
                return self.user32.CallNextHookEx(None, code, message, pointer)

            native_callback = callback_type(callback)
            self.thread_id = self.kernel32.GetCurrentThreadId()
            # Create the message queue before publishing readiness to stop().
            msg = wintypes.MSG()
            self.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
            hook = self.user32.SetWindowsHookExW(
                13, native_callback, self.kernel32.GetModuleHandleW(None), 0,
            )
            if not hook:
                raise ctypes.WinError(ctypes.get_last_error())
            timer = self.user32.SetTimer(None, 0, 100, None)
            if not timer:
                raise ctypes.WinError(ctypes.get_last_error())
            self.ready.set()
            while True:
                result = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == 0:
                    break
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if msg.message == 0x113:
                    self.reconcile()
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as exc:
            self.error = exc
            logging.exception("Windows action hotkey hook stopped")
        finally:
            if timer:
                self.user32.KillTimer(None, timer)
            if hook:
                self.user32.UnhookWindowsHookEx(hook)
            self.ready.set()
            self.stopped.set()
