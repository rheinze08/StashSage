"""Keep one StashSage running per user session.

A second copy binds every global hotkey a second time, and while it runs from
the same install dir it holds the files a self-update has to replace -- which
made the swap helper refuse to apply an update and leave the user with no app.

The first instance holds a named mutex (Windows) or an exclusive lock file
(POSIX) for its lifetime; the OS releases either when the process exits, so a
crash or forced exit can never leave the lock stuck. A later launch cannot
acquire it, drops a small request file the running instance polls, and exits.
The running instance then brings its window forward.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

MUTEX_NAME = "Local\\StashSage.SingleInstance"
LOCK_FILE = "instance.lock"
SHOW_REQUEST_FILE = "show_request.flag"
# Escape hatch for development: running two copies side by side on purpose.
ALLOW_MULTIPLE_ENV = "STASHSAGE_ALLOW_MULTIPLE_INSTANCES"

_ERROR_ALREADY_EXISTS = 183

# The mutex handle or locked file object, kept referenced for the process
# lifetime. Releasing it early would let a second copy start.
_held: object = None


def _state_dir() -> Path:
    from poe2trade.app import config_manager

    return config_manager._user_config_dir()


def show_request_path(state_dir: Optional[Path] = None) -> Path:
    return (state_dir if state_dir is not None else _state_dir()) / SHOW_REQUEST_FILE


def _multiple_instances_allowed() -> bool:
    return str(os.getenv(ALLOW_MULTIPLE_ENV) or "").strip().lower() in {"1", "true", "yes", "on"}


def _acquire_windows_mutex(name: str) -> Optional[bool]:
    """True when acquired, False when held elsewhere, None when unavailable."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, name)
    error = ctypes.get_last_error()
    if not handle:
        log.warning("single instance: CreateMutexW failed (error %s); allowing launch", error)
        return None
    if error == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    global _held
    _held = (kernel32, handle)
    return True


def _acquire_lock_file(path: Path) -> Optional[bool]:
    """True when acquired, False when held elsewhere, None when unavailable."""
    try:
        import fcntl
    except ImportError:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(path, "a+")
    except OSError:
        log.warning("single instance: cannot open %s; allowing launch", path, exc_info=True)
        return None
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return False
    global _held
    _held = handle
    return True


def acquire(*, state_dir: Optional[Path] = None, mutex_name: str = MUTEX_NAME) -> bool:
    """Claim the single-instance lock; ``False`` when another copy holds it.

    Fails open: if the platform lock cannot be created at all, the launch is
    allowed rather than refusing to start the app.
    """
    if _held is not None or _multiple_instances_allowed():
        return True
    if sys.platform == "win32":
        acquired = _acquire_windows_mutex(mutex_name)
    else:
        root = state_dir if state_dir is not None else _state_dir()
        acquired = _acquire_lock_file(root / LOCK_FILE)
    if acquired is False:
        return False
    # A request left by a launch that raced a previous instance's exit is stale.
    consume_show_request(state_dir)
    return True


def release() -> None:
    """Drop the lock early (tests, or a process about to replace itself)."""
    global _held
    held, _held = _held, None
    if held is None:
        return
    try:
        if isinstance(held, tuple):
            kernel32, handle = held
            kernel32.CloseHandle(handle)
        else:
            held.close()
    except Exception:
        log.debug("single instance: release failed", exc_info=True)


def request_show_existing(
    state_dir: Optional[Path] = None,
    *,
    wait_seconds: float = 4.0,
    poll_seconds: float = 0.1,
) -> bool:
    """Ask the running instance to show its window.

    Returns ``True`` once that instance picked the request up, ``False`` when it
    did not within ``wait_seconds`` (it is hung, or still starting up).
    """
    path = show_request_path(state_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        log.warning("single instance: could not write show request %s", path, exc_info=True)
        return False
    deadline = time.monotonic() + max(wait_seconds, 0.0)
    while time.monotonic() < deadline:
        if not path.exists():
            return True
        time.sleep(poll_seconds)
    if not path.exists():
        return True
    # Leave nothing behind for an instance that was not listening.
    try:
        path.unlink()
    except OSError:
        pass
    return False


def consume_show_request(state_dir: Optional[Path] = None) -> bool:
    """``True`` (and clear it) when another launch asked this instance to show."""
    try:
        show_request_path(state_dir).unlink()
        return True
    except OSError:
        return False
