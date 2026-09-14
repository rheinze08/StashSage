"""In-app updater for StashSage.

Fetches a small JSON manifest from a configured URL and, when newer assets are
available, downloads them into the writable per-user override dir
(``%APPDATA%/StashSage/generated/<name>``) where :mod:`poe2trade.app.asset_paths`
resolves them ahead of the bundled copies. App-code/exe updates are detected and
the new portable bundle can be downloaded, verified, and swapped over the running
install on restart - no installer and no reinstall.

Design goals
------------
* **Offline-safe** - any network error is swallowed; the app keeps using the
  cached/bundled assets and stays fully functional.
* **Verified** - every download is checked against its manifest SHA-256 before
  it is moved into place.
* **Atomic** - assets are written to a temp file then ``os.replace``'d, so a
  partial download can never be loaded by the running app.
* **No installer** - app upgrades ship as the same portable one-dir bundle that
  is distributed as a ``.zip``. The updater downloads + verifies that zip,
  extracts it, and a small restart helper performs an atomic, rollback-safe swap
  of the new bundle over the current install directory (Windows cannot overwrite
  the running exe, so the swap is deferred until the app exits) and relaunches
  the app. An interrupted or failed swap leaves the previous install intact.
* **Testable** - manifest parsing, version comparison and plan computation are
  pure functions with no network or disk side effects, and all I/O takes an
  injectable ``session`` so tests need no real network.

The manifest schema (all asset fields required unless noted)::

    {
      "schema_version": 1,                                       # optional
      "app_version": "0.6.0",
      "app_package_url": "https://.../StashSageWindows.zip",     # optional
      "app_package_sha256": "...",                               # optional*
      "assets": [
        {"name": "super_models", "path": "body_armour_xgb_model.pkl",
         "sha256": "<hex>", "size": 1234, "url": "https://.../file.pkl"}
      ]
    }

All ``url`` fields must be ``https://`` (non-https entries are dropped). The
downloaded package is extracted and swapped over the install in place, so
``app_package_sha256`` is required to stage it: without a verified SHA the
package is never fetched (``optional*`` above means the field may be omitted,
but then no app update is staged).

``name`` is the ``db/<name>`` bucket; ``path`` is the file's location within that
bucket. The local target is ``generated_root/name/path``.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional
from urllib.parse import urlparse
from uuid import uuid4

from poe2trade.app import asset_paths

log = logging.getLogger(__name__)

# Default per-download / per-request timeouts (seconds).
_MANIFEST_TIMEOUT = 10
_DOWNLOAD_TIMEOUT = 300
_MANIFEST_RETRIES = 2
_DOWNLOAD_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 1.0
# "model_sets" is the only nested bucket: its paths are
# ``<set id>/<super_models|unsuper_models>/<file>`` rather than a bare
# filename. asset_target, the download writer and the orphan prune all work
# from the relative path already, so nesting needs no special handling --
# only the traversal guard in _is_unsafe_relpath, which allows subdirectories
# but still rejects "..", absolute paths and drive letters.
ALLOWED_ASSET_BUCKETS = frozenset(
    {"super_models", "unsuper_models", "files", "base_icons", "model_sets"}
)

# Highest manifest ``schema_version`` this client understands. A newer manifest
# (schema_version greater than this) is treated as "no update available" so an
# older client can never misread a future, restructured manifest.
SUPPORTED_SCHEMA_VERSION = 2


class UpdaterError(Exception):
    """Raised for malformed manifests or failed integrity checks."""


# data model
@dataclass(frozen=True)
class Asset:
    name: str  # db/<name> bucket, e.g. "super_models"
    path: str  # relative path within the bucket, e.g. "body_armour_xgb_model.pkl"
    sha256: str
    url: str
    size: int = 0


@dataclass(frozen=True)
class Manifest:
    app_version: str
    assets: tuple[Asset, ...] = ()
    app_package_url: Optional[str] = None
    app_package_sha256: Optional[str] = None
    revoked_versions: tuple[str, ...] = ()
    min_supported_version: Optional[str] = None


@dataclass
class SyncResult:
    downloaded: list[Asset] = field(default_factory=list)
    failed: list[tuple[Asset, str]] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.downloaded)


@dataclass(frozen=True)
class DownloadProgress:
    """Progress event for updater downloads.

    ``kind`` is ``"asset"`` for model/data assets and ``"app"`` for the
    portable app package. ``delta_bytes`` is the number of bytes just streamed.
    ``total_bytes`` is best-effort and may be zero when the server did not give
    a size. ``phase`` is one of ``download``, ``verifying``, ``verified`` or
    ``extracting``.
    """

    delta_bytes: int
    kind: str = "download"
    label: str = ""
    version: Optional[str] = None
    total_bytes: int = 0
    phase: str = "download"


@dataclass(frozen=True)
class UpdateOutcome:
    manifest: Optional[Manifest]
    assets_changed: bool
    app_update_available: bool
    app_version: Optional[str]
    sync: Optional[SyncResult] = None
    app_package_dir: Optional[Path] = None
    # True when the *running* version is the unknown/0.0.0 fallback, so an app
    # update looks available against everything but auto-staging was suppressed
    # to avoid an update loop. The GUI surfaces a "reinstall" hint in this case.
    runtime_version_unknown: bool = False
    # True when the live manifest says the running build should not be used.
    # The GUI surfaces a repair/re-download hint if the updater cannot stage a
    # replacement automatically.
    runtime_version_revoked: bool = False
    runtime_version_unsupported: bool = False
    current_version: str = ""
    app_update_reason: str = ""


# pure helpers (no network / no disk)
#
# Version contract (load-bearing - the whole self-update decision rests on it):
#   * Only **numeric, dot-separated** versions are supported (``"0.6.0"``,
#     ``"0.6.0.1"``). This mirrors the strict ``N.N.N[.N]`` shape the release
#     pipeline enforces at the source (``tools/get_version.py``).
#   * ``parse_version`` extracts the run of integers and **ignores all
#     non-numeric text**, so a pre-release/build suffix is silently dropped:
#     ``"0.6.0-rc1"`` parses to ``(0, 6, 0, 1)`` (the ``1`` from ``rc1``) and
#     ``"0.6.0-beta"`` to ``(0, 6, 0)`` == ``"0.6.0"``. Suffixes therefore must
#     never be published - the pipeline rejects them rather than relying on this
#     parser to compare them sanely.
#   * ``is_newer_version`` is **strict-greater** after zero-padding both tuples
#     to equal width, so ``"0.6"`` == ``"0.6.0"`` (no update) and ``"0.6.0.1"``
#     > ``"0.6.0"`` (a 4th-part bump is newer). Equal versions are *not* newer,
#     which is what stops a re-published, non-advancing release from updating.
def parse_version(value: str) -> tuple[int, ...]:
    """Parse a dotted version string into a comparable int tuple.

    Non-numeric junk is ignored; an empty/garbage version becomes ``(0,)``. See
    the module-level version contract above for the supported shapes and the
    suffix-stripping caveat.
    """
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(p) for p in parts) if parts else (0,)


def is_newer_version(candidate: str, current: str) -> bool:
    """True if ``candidate`` is a strictly newer version than ``current``.

    Comparison is strict-greater on the zero-padded numeric tuples, so equal
    versions return ``False`` (no update). See the module-level version contract.
    """
    cand = parse_version(candidate)
    cur = parse_version(current)
    width = max(len(cand), len(cur))
    cand += (0,) * (width - len(cand))
    cur += (0,) * (width - len(cur))
    return cand > cur


def is_unknown_version(version: str) -> bool:
    """True when a runtime version is the unknown/fallback sentinel.

    The frozen app resolves ``__version__`` from ``_build_meta`` (stamped from
    ``setup.py`` at build time). If that file is missing from the bundle the
    chain falls through to ``importlib.metadata`` and finally the literal
    ``"0.0.0"`` (see ``poe2trade/__init__.py``). A ``0.0.0``/empty/garbage
    runtime version parses to an all-zero tuple, which compares *older* than
    every real manifest version - so an unguarded check would treat **every**
    manifest as newer and re-stage the same package on every launch. Callers use
    this to suppress auto-staging and surface a reinstall hint instead of
    update-looping.
    """
    return set(parse_version(version)) == {0}


def _is_unsafe_relpath(rel: str) -> bool:
    """Reject absolute paths and any ``..`` traversal in a manifest path."""
    norm = str(rel).replace("\\", "/")
    if not norm:
        return True
    if norm.startswith("/"):
        return True
    if len(norm) >= 2 and norm[1] == ":":  # Windows drive (e.g. C:)
        return True
    # Reject empty segments, parent traversal, and bare "." segments.
    return any(seg in ("", ".", "..") for seg in norm.split("/"))


def _is_unsafe_bucket(name: str) -> bool:
    return name not in ALLOWED_ASSET_BUCKETS


def _is_https_url(url: str) -> bool:
    """Only https downloads are trusted (blocks http/file/ftp downgrades)."""
    return str(url).strip().lower().startswith("https://")


def _is_zip_url(url: str) -> bool:
    """True for portable-bundle ``.zip`` URLs the apply helper can swap in."""
    path = urlparse(str(url or "")).path.lower()
    return path.endswith(".zip")


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


def supports_app_package_apply() -> bool:
    """Whether this runtime can apply the portable-package manifest entry.

    Windows and Linux ship an in-place restart-swap helper (a generated ``.cmd``
    /``.ps1`` on Windows, a ``.sh`` on Linux). macOS still syncs data/model
    assets but is not offered an app-binary update. The swap is additionally
    gated on running frozen from a writable install dir (see
    :func:`install_dir_is_writable`), so a source/dev run is never clobbered.
    """
    return sys.platform == "win32" or _is_linux()


def install_root() -> Optional[Path]:
    """Directory of the running frozen app (the one-dir bundle root).

    ``None`` when not running as a PyInstaller-frozen build (e.g. a dev/source
    run), so the swap path is skipped instead of clobbering a source checkout.
    """
    if not getattr(sys, "frozen", False):
        return None
    try:
        return Path(sys.executable).resolve().parent
    except (OSError, ValueError):
        return None


def install_dir_is_writable(target: Optional[Path] = None) -> bool:
    """Best-effort check that the install dir can be replaced without elevation.

    A portable bundle extracted into a read-only location (e.g. Program Files
    without admin) cannot self-update; the GUI falls back to the download page.
    """
    target = target if target is not None else install_root()
    if target is None:
        return False
    try:
        probe = target / f".stashsage-write-probe-{uuid4().hex}"
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


def _safe_package_filename(raw: str) -> str:
    """Sanitize a package name taken from a URL into a safe local filename.

    The name is interpolated into a generated ``.cmd`` apply helper, so it must
    never carry shell metacharacters; restrict it to a conservative charset.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(raw or "")).strip("._")
    return cleaned or "StashSageWindows.zip"


def parse_manifest(data: Mapping) -> Manifest:
    """Validate and parse a manifest mapping. Skips malformed/unsafe assets."""
    if not isinstance(data, Mapping):
        raise UpdaterError("manifest is not a JSON object")
    # Schema-version gate: an absent/garbage value is treated as the current
    # schema (back-compat with v1 manifests that predate the field), but a
    # value the client is too old to understand is rejected up front.
    raw_schema = data.get("schema_version", SUPPORTED_SCHEMA_VERSION)
    try:
        schema_version = int(raw_schema)
    except (TypeError, ValueError):
        schema_version = SUPPORTED_SCHEMA_VERSION
    if schema_version > SUPPORTED_SCHEMA_VERSION:
        raise UpdaterError(
            f"unsupported manifest schema_version {schema_version} "
            f"(client supports up to {SUPPORTED_SCHEMA_VERSION})"
        )
    app_version = str(data.get("app_version") or "").strip()
    if not app_version:
        raise UpdaterError("manifest missing 'app_version'")

    assets: list[Asset] = []
    for raw in data.get("assets") or []:
        if not isinstance(raw, Mapping):
            log.warning("updater: skipping non-object asset entry: %r", raw)
            continue
        name = str(raw.get("name") or "").strip()
        path = str(raw.get("path") or "").strip()
        sha = str(raw.get("sha256") or "").strip()
        url = str(raw.get("url") or "").strip()
        if not (name and path and sha and url):
            log.warning("updater: skipping incomplete asset entry: %r", raw)
            continue
        if _is_unsafe_bucket(name) or _is_unsafe_relpath(path):
            log.warning("updater: skipping unsafe asset path: %r", raw)
            continue
        if not _is_https_url(url):
            log.warning("updater: skipping non-https asset url: %r", raw)
            continue
        try:
            size = int(raw.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        assets.append(Asset(name=name, path=path, sha256=sha, url=url, size=size))

    package_url = str(data.get("app_package_url") or "").strip() or None
    package_sha = str(data.get("app_package_sha256") or "").strip() or None
    # The top-level app_package_url is the Windows bundle. On Linux, resolve the
    # platform-specific package from the manifest's platforms.linux block (same
    # url/sha the release already publishes) so the in-place swap fetches the
    # Linux bundle, not the Windows one. Production manifests always carry that
    # block; if it is somehow absent we leave the top-level value untouched
    # (back-compat). Windows resolution is unchanged.
    if _is_linux():
        platforms = data.get("platforms")
        linux_plat = platforms.get("linux") if isinstance(platforms, Mapping) else None
        if isinstance(linux_plat, Mapping):
            linux_url = str(linux_plat.get("url") or "").strip()
            if linux_url:
                package_url = linux_url
                package_sha = str(linux_plat.get("sha256") or "").strip() or None
    if package_url and not _is_https_url(package_url):
        log.warning("updater: ignoring non-https app_package_url: %r", package_url)
        package_url = None
        package_sha = None
    if package_url and not _is_zip_url(package_url):
        log.warning("updater: ignoring unsupported app_package_url: %r", package_url)
        package_url = None
        package_sha = None
    revoked: list[str] = []
    for raw_version in data.get("revoked_versions") or []:
        version = str(raw_version or "").strip().lstrip("v")
        if version:
            revoked.append(version)
    min_supported = str(data.get("min_supported_version") or "").strip().lstrip("v") or None
    return Manifest(
        app_version=app_version,
        assets=tuple(assets),
        app_package_url=package_url,
        app_package_sha256=package_sha,
        revoked_versions=tuple(dict.fromkeys(revoked)),
        min_supported_version=min_supported,
    )


def app_update_available(manifest: Manifest, current_version: str) -> bool:
    return is_newer_version(manifest.app_version, current_version)


def version_is_revoked(manifest: Manifest, version: str) -> bool:
    """True when ``version`` appears in the manifest revocation list."""
    normalized = str(version or "").strip().lstrip("v")
    return bool(normalized and normalized in manifest.revoked_versions)


def version_is_supported(manifest: Manifest, version: str) -> bool:
    """True when ``version`` is not below the manifest's support floor."""
    if not manifest.min_supported_version:
        return True
    return not is_newer_version(manifest.min_supported_version, version)


@dataclass(frozen=True)
class RetirementNotice:
    """A user-facing notice that the running build should be replaced.

    ``kind`` is ``"revoked"`` (the manifest retired this exact version) or
    ``"unsupported"`` (it is below the manifest's minimum-supported floor).
    """

    kind: str
    message: str


def retirement_notice(outcome: "UpdateOutcome") -> Optional[RetirementNotice]:
    """Single source of truth for the 'this install is retired/too old' notice.

    Returns ``None`` when the running version is fine. ``unsupported`` (below the
    support floor) takes precedence over ``revoked`` in the message — it is the
    strongest reason to act — matching the prior inline GUI logic exactly.
    """
    if outcome.runtime_version_unsupported:
        reason = "This installed version is too old"
        kind = "unsupported"
    elif outcome.runtime_version_revoked:
        reason = "This installed version was retired"
        kind = "revoked"
    else:
        return None
    return RetirementNotice(kind=kind, message=f"{reason}; install the latest StashSage.")


# disk helpers
def sha256_file(path: os.PathLike | str, *, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk_size), b""):
            h.update(block)
    return h.hexdigest()


def asset_target(generated_root: os.PathLike | str, asset: Asset) -> Path:
    return Path(generated_root) / asset.name / asset.path


def default_update_stage_dir() -> Path:
    """Writable directory used for staged app installers."""
    return asset_paths.generated_assets_root().parent / "updates"


# post-swap version verification
#
# The restart-swap helper relaunches the freshly-installed exe but cannot itself
# confirm the new build's version actually advanced (a stale/mismatched staged
# zip would relaunch the *same* version and re-trigger the update every launch).
# To close that loop the GUI records the version it expects to be running after
# the swap, then verifies it on the next startup:
#   * before launching the helper -> ``record_pending_update(stage, version)``
#   * on next startup -> ``read_pending_update`` + ``post_swap_version_ok``; if
#     the running version did not reach the expected one, the version is added to
#     a stale-version blocklist so the updater stops re-staging it.
# All of these are best-effort JSON file helpers that never raise.
_PENDING_UPDATE_FILE = "pending_update.json"
_STALE_VERSIONS_FILE = "stale_update_versions.json"


def _pending_update_path(stage_root: os.PathLike | str) -> Path:
    return Path(stage_root) / _PENDING_UPDATE_FILE


def _stale_versions_path(stage_root: os.PathLike | str) -> Path:
    return Path(stage_root) / _STALE_VERSIONS_FILE


def record_pending_update(stage_root: os.PathLike | str, expected_version: str) -> None:
    """Record the version expected to be running after a restart-swap.

    Best-effort: any failure (read-only dir, etc.) is swallowed - a missing
    sentinel simply means the post-swap check is skipped, never that the app
    breaks.
    """
    import json

    try:
        path = _pending_update_path(stage_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"expected_version": str(expected_version or "").strip()}),
            encoding="utf-8",
        )
    except OSError:
        log.debug("updater: could not record pending update sentinel", exc_info=True)


def read_pending_update(stage_root: os.PathLike | str) -> Optional[str]:
    """Return the recorded post-swap expected version, or ``None``."""
    import json

    try:
        data = json.loads(_pending_update_path(stage_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = str((data or {}).get("expected_version") or "").strip()
    return version or None


def clear_pending_update(stage_root: os.PathLike | str) -> None:
    """Delete the post-swap sentinel (best-effort)."""
    try:
        _pending_update_path(stage_root).unlink()
    except OSError:
        pass


def post_swap_version_ok(expected_version: str, current_version: str) -> bool:
    """True when the running version reached (or passed) the expected one.

    A swap that relaunched a stale/older build leaves ``current_version`` short
    of ``expected_version``; that is the only failure we flag.
    """
    return not is_newer_version(expected_version, current_version)


def read_stale_update_versions(stage_root: os.PathLike | str) -> set[str]:
    """Return versions a prior swap failed to apply (do not re-stage them)."""
    import json

    try:
        data = json.loads(_stale_versions_path(stage_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(data, list):
        return set()
    return {str(v).strip() for v in data if str(v).strip()}


def add_stale_update_version(stage_root: os.PathLike | str, version: str) -> None:
    """Mark a version as failed-to-apply so the updater stops re-staging it."""
    import json

    version = str(version or "").strip()
    if not version:
        return
    versions = read_stale_update_versions(stage_root)
    if version in versions:
        return
    versions.add(version)
    try:
        path = _stale_versions_path(stage_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sorted(versions)), encoding="utf-8")
    except OSError:
        log.debug("updater: could not record stale update version", exc_info=True)


def verify_post_swap_update(stage_root: os.PathLike | str, current_version: str) -> Optional[str]:
    """Check a pending post-swap sentinel against the running version.

    Returns the version that **failed** to apply (so the caller can warn/flag),
    or ``None`` when there was no pending swap or it succeeded. A failed version
    is added to the stale-version blocklist; the sentinel is always cleared so
    the check runs once per swap.
    """
    expected = read_pending_update(stage_root)
    if expected is None:
        return None
    clear_pending_update(stage_root)
    if post_swap_version_ok(expected, current_version):
        return None
    add_stale_update_version(stage_root, expected)
    log.warning(
        "updater: post-swap version did not advance (expected %s, running %s); "
        "blocking re-staging of that version",
        expected,
        current_version,
    )
    return expected


def _asset_file_matches(path: Path, expected_sha: str) -> bool:
    try:
        return path.is_file() and sha256_file(path).lower() == expected_sha.lower()
    except OSError:
        return False


def compute_asset_plan(
    manifest: Manifest,
    generated_root: os.PathLike | str,
    *,
    bundled_resolver: Optional[Callable[[str], Path]] = None,
) -> list[Asset]:
    """Return the assets whose active local copy is missing or out of date."""
    plan: list[Asset] = []
    for asset in manifest.assets:
        target = asset_target(generated_root, asset)
        if target.is_file():
            if _asset_file_matches(target, asset.sha256):
                continue
            # A stale override shadows the bundled copy at runtime, so refresh it
            # even when the bundle already carries the expected bytes.
            plan.append(asset)
            continue
        if bundled_resolver is not None:
            bundled = bundled_resolver(asset.name) / asset.path
            if _asset_file_matches(bundled, asset.sha256):
                continue
        plan.append(asset)
    return plan


# network I/O (injectable session)
def _session(session=None):
    if session is not None:
        return session
    import requests  # local import keeps module import cheap / offline-importable

    return requests


def _retry_delay(attempt: int, base_delay: float) -> float:
    return max(float(base_delay), 0.0) * (2 ** max(attempt - 1, 0))


def _response_content_length(resp: object) -> int:
    """Return Content-Length from a requests-like response, or 0 when absent."""
    headers = getattr(resp, "headers", {}) or {}
    try:
        value = headers.get("content-length") or headers.get("Content-Length")
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def fetch_manifest(
    url: str,
    *,
    session=None,
    timeout: int = _MANIFEST_TIMEOUT,
    retries: int = _MANIFEST_RETRIES,
    retry_backoff: float = _RETRY_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Optional[dict]:
    """Fetch and JSON-decode the manifest. Returns ``None`` on any failure."""
    if not url:
        return None
    attempts = max(int(retries), 0) + 1
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            resp = _session(session).get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # offline, 404, bad JSON, ... all non-fatal
            last_exc = exc
            if attempt < attempts:
                try:
                    sleep_fn(_retry_delay(attempt, retry_backoff))
                except Exception:
                    log.debug("updater: retry sleep failed", exc_info=True)
    log.info("updater: manifest fetch failed (%s): %s", url, last_exc)
    return None


def download_to(
    url: str,
    dest: os.PathLike | str,
    expected_sha: Optional[str],
    *,
    session=None,
    timeout: int = _DOWNLOAD_TIMEOUT,
    progress_cb: Optional[Callable[[object], None]] = None,
    expected_size: Optional[int] = None,
    retries: int = _DOWNLOAD_RETRIES,
    retry_backoff: float = _RETRY_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
    progress_kind: Optional[str] = None,
    progress_label: str = "",
    progress_version: Optional[str] = None,
) -> None:
    """Stream ``url`` to ``dest`` atomically, verifying ``expected_sha``.

    Writes to a sibling temp file, hashes while streaming, and only
    ``os.replace``'s into place once the digest matches. When ``expected_size``
    is a positive integer the stream is aborted as soon as it exceeds that
    many bytes, so a wrong or hostile URL cannot fill the disk before the
    final SHA-256 check would have rejected it.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    size_cap = int(expected_size) if expected_size and expected_size > 0 else None
    attempts = max(int(retries), 0) + 1
    for attempt in range(1, attempts + 1):
        tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}-{uuid4().hex}")
        digest = hashlib.sha256()
        written = 0
        try:
            with _session(session).get(url, stream=True, timeout=timeout) as resp:
                resp.raise_for_status()
                total_bytes = size_cap or _response_content_length(resp)
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 16):
                        if not chunk:
                            continue
                        written += len(chunk)
                        if size_cap is not None and written > size_cap:
                            raise UpdaterError(
                                f"download for {url} exceeded expected size "
                                f"({size_cap} bytes)"
                            )
                        fh.write(chunk)
                        digest.update(chunk)
                        if progress_cb is not None:
                            if progress_kind:
                                progress_cb(
                                    DownloadProgress(
                                        delta_bytes=len(chunk),
                                        kind=progress_kind,
                                        label=progress_label,
                                        version=progress_version,
                                        total_bytes=total_bytes,
                                    )
                                )
                            else:
                                progress_cb(len(chunk))
            actual = digest.hexdigest()
            if progress_cb is not None and progress_kind:
                progress_cb(
                    DownloadProgress(
                        delta_bytes=0,
                        kind=progress_kind,
                        label=progress_label,
                        version=progress_version,
                        total_bytes=total_bytes,
                        phase="verifying",
                    )
                )
            if expected_sha and actual.lower() != expected_sha.lower():
                raise UpdaterError(
                    f"sha256 mismatch for {url}: expected {expected_sha}, got {actual}"
                )
            os.replace(tmp, dest)
            if progress_cb is not None and progress_kind:
                progress_cb(
                    DownloadProgress(
                        delta_bytes=0,
                        kind=progress_kind,
                        label=progress_label,
                        version=progress_version,
                        total_bytes=total_bytes,
                        phase="verified",
                    )
                )
            return
        except Exception:
            if attempt >= attempts:
                raise
            try:
                sleep_fn(_retry_delay(attempt, retry_backoff))
            except Exception:
                log.debug("updater: retry sleep failed", exc_info=True)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass


def sync_assets(
    manifest: Manifest,
    generated_root: os.PathLike | str,
    *,
    session=None,
    timeout: int = _DOWNLOAD_TIMEOUT,
    progress_cb: Optional[Callable[[object], None]] = None,
    bundled_resolver: Optional[Callable[[str], Path]] = None,
    retries: int = _DOWNLOAD_RETRIES,
) -> SyncResult:
    """Download every out-of-date asset into ``generated_root``."""
    result = SyncResult()
    for asset in compute_asset_plan(
        manifest, generated_root, bundled_resolver=bundled_resolver
    ):
        try:
            download_to(
                asset.url,
                asset_target(generated_root, asset),
                asset.sha256,
                session=session,
                timeout=timeout,
                progress_cb=progress_cb,
                expected_size=asset.size,
                retries=retries,
                progress_kind="asset",
                progress_label=f"{asset.name}/{asset.path}",
                progress_version=manifest.app_version,
            )
            result.downloaded.append(asset)
        except Exception as exc:
            log.warning("updater: asset download failed %s/%s: %s", asset.name, asset.path, exc)
            result.failed.append((asset, str(exc)))
    return result


# Buckets whose assets form a co-versioned set (models + their scoring,
# distribution and feature-importance sidecars). A partial sync of one of these
# buckets leaves a mixed-vintage override (new model, old stats), so a failure
# touching any of them rolls the whole run's bucket downloads back to the prior
# coherent state rather than serving a mismatched set.
CONSISTENCY_BUCKETS = frozenset({"super_models", "unsuper_models"})


def rollback_synced_assets(
    generated_root: os.PathLike | str, assets: list[Asset]
) -> list[Path]:
    """Delete the override files written for ``assets`` (best-effort).

    Used to undo a partially-applied co-versioned bucket sync so the override
    reverts to its previous coherent state (or empty, letting the bundled set
    resurface). Never raises.
    """
    removed: list[Path] = []
    for asset in assets:
        target = asset_target(generated_root, asset)
        try:
            target.unlink()
            removed.append(target)
        except OSError:
            log.debug("updater: could not roll back synced asset %s", target, exc_info=True)
    return removed


def prune_orphan_override_assets(
    manifest: Manifest, generated_root: os.PathLike | str
) -> list[Path]:
    """Delete override files a bucket no longer lists in the manifest.

    The override copy under ``generated_root/<bucket>`` always wins over the
    bundled package copy (see :mod:`poe2trade.app.asset_paths`). Without cleanup,
    an asset that a later manifest renames or drops would keep shadowing the
    fresh bundled file after an app upgrade. For every bucket that the manifest
    *does* list assets for, any override file not in that listing is removed so
    the bundled copy resurfaces.

    Buckets with no manifest entry are left untouched: an empty ``assets`` list
    must never wipe a working override directory. Best-effort and never raises.
    """
    listed: dict[str, set[str]] = {}
    for asset in manifest.assets:
        norm = str(asset.path).replace("\\", "/")
        listed.setdefault(asset.name, set()).add(norm)

    removed: list[Path] = []
    root = Path(generated_root)
    for bucket, keep in listed.items():
        bucket_dir = root / bucket
        if not bucket_dir.is_dir():
            continue
        for path in bucket_dir.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(bucket_dir).as_posix()
            if rel in keep:
                continue
            try:
                path.unlink()
                removed.append(path)
            except OSError:
                log.debug("updater: could not prune orphan override %s", path, exc_info=True)

        # Pruning a retired league empties its directories but leaves them
        # behind, and a set whose bucket still exists reads as installed. Walk
        # deepest-first so a league directory goes once its buckets have.
        for path in sorted(bucket_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if not path.is_dir():
                continue
            try:
                if not any(path.iterdir()):
                    path.rmdir()
            except OSError:
                log.debug("updater: could not prune empty override dir %s", path, exc_info=True)

    if removed:
        log.info("updater: pruned %d orphan override asset(s)", len(removed))
    return removed


def download_app_package(
    manifest: Manifest,
    dest_dir: os.PathLike | str,
    *,
    session=None,
    timeout: int = _DOWNLOAD_TIMEOUT,
    progress_cb: Optional[Callable[[object], None]] = None,
    retries: int = _DOWNLOAD_RETRIES,
) -> Optional[Path]:
    """Download the portable app package ``.zip`` into ``dest_dir``.

    Returns the path to the verified zip. Windows cannot overwrite the running
    exe in place, so applying the update is deferred to a restart helper (see
    :func:`launch_app_update_after_exit`); this only fetches + verifies the
    bytes. A verified ``app_package_sha256`` is mandatory: the package is
    extracted and executed, so an unverified archive is never downloaded.
    """
    if not manifest.app_package_url:
        return None
    if not supports_app_package_apply():
        log.info("updater: app package staging is not supported on %s", sys.platform)
        return None
    if not manifest.app_package_sha256:
        log.warning(
            "updater: refusing to stage package without a verified app_package_sha256"
        )
        return None
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    raw_name = manifest.app_package_url.rstrip("/").split("/")[-1]
    name = _safe_package_filename(raw_name)
    dest = dest_dir / name
    if dest.is_file() and manifest.app_package_sha256:
        try:
            if sha256_file(dest).lower() == manifest.app_package_sha256.lower():
                return dest
        except OSError:
            pass
    download_to(
        manifest.app_package_url,
        dest,
        manifest.app_package_sha256,
        session=session,
        timeout=timeout,
        progress_cb=progress_cb,
        retries=retries,
        progress_kind="app",
        progress_label="StashSageWindows.zip",
        progress_version=manifest.app_version,
    )
    return dest


def post_update_download_metric(
    config: Optional[Mapping],
    version: str,
    *,
    session=None,
    timeout: int = 10,
) -> bool:
    """Best-effort telemetry that a verified app update was downloaded.

    This is intentionally opt-in: without ``metrics_api_base``/``api_base_url``
    in config, nothing is sent. Failures are logged at debug level and never
    affect update staging.
    """
    cfg = config or {}
    base = str(
        cfg.get("metrics_api_base")
        or cfg.get("api_base_url")
        or cfg.get("api_base")
        or ""
    ).strip()
    if not base:
        return False
    endpoint = base.rstrip("/") + "/metrics/update-download"
    client_id = str(
        cfg.get("installation_id")
        or cfg.get("client_id")
        or ""
    ).strip()
    payload = {
        "installation_id": client_id,
        "client_id": client_id,
        "version": str(version or "").strip(),
        "source": "cdn",
        "action": "update_download",
    }
    headers = {}
    api_key = str(cfg.get("metrics_api_key") or cfg.get("api_key") or "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = _session(session).post(endpoint, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return True
    except Exception:
        log.debug("updater: update-download metric post failed", exc_info=True)
        return False


def _zip_is_safe(zf: zipfile.ZipFile, dest_dir: Path) -> bool:
    """Reject archives whose members would escape ``dest_dir`` (zip-slip)."""
    dest_root = dest_dir.resolve()
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or (len(name) >= 2 and name[1] == ":"):
            return False
        target = (dest_dir / name).resolve()
        try:
            target.relative_to(dest_root)
        except ValueError:
            return False
    return True


def extract_app_package(zip_path: os.PathLike | str, dest_dir: os.PathLike | str) -> Path:
    """Extract a verified package zip into ``dest_dir`` and return the bundle root.

    The release zip wraps the one-dir bundle under a top-level ``StashSage/``
    directory (matching the Windows/Linux build output). The returned path is the
    directory whose contents should be mirrored over the install dir.
    """
    zip_path = Path(zip_path)
    dest_dir = Path(dest_dir)
    # Re-extract from scratch so a previous partial extract can't leave stale
    # files that would be mirrored over the install.
    if dest_dir.exists():
        shutil.rmtree(dest_dir, ignore_errors=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        if not _zip_is_safe(zf, dest_dir):
            raise UpdaterError(f"refusing to extract unsafe package archive: {zip_path}")
        zf.extractall(dest_dir)
    # A single top-level dir (the bundle folder) is the swap source; otherwise the
    # extract dir itself holds the bundle.
    entries = [p for p in dest_dir.iterdir() if p.name not in {"__MACOSX"}]
    dirs = [p for p in entries if p.is_dir()]
    files = [p for p in entries if p.is_file()]
    if len(dirs) == 1 and not files:
        return dirs[0]
    return dest_dir


def _safe_version_dir(app_version: str) -> str:
    """Filesystem-safe per-version subdirectory name for a staged package."""
    version_dir = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(app_version or "")).strip("._")
    return version_dir or "latest"


def prune_stale_staged_packages(stage_root: os.PathLike | str, keep_version: str) -> None:
    """Delete staged-package dirs for any version other than ``keep_version``.

    Each staged package lives in ``stage_root/<version>/`` and holds the
    downloaded zip plus its extracted bundle (hundreds of MB). Without cleanup
    every release a user passes through accumulates forever. Best-effort: any
    error (missing dir, locked file, ...) is swallowed so this can never break
    the update check.
    """
    keep = _safe_version_dir(keep_version)
    root = Path(stage_root)
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.name == keep:
            continue
        try:
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            log.debug("updater: could not prune staged package dir %s", entry, exc_info=True)


def remove_staged_package(stage_root: os.PathLike | str, version: str) -> None:
    """Delete the staged package directory for ``version`` if it exists."""
    target = Path(stage_root) / _safe_version_dir(version)
    try:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
    except OSError:
        log.debug("updater: could not remove staged package dir %s", target, exc_info=True)


def recover_interrupted_update(
    *,
    install_dir: os.PathLike | str | None = None,
    stage_root: os.PathLike | str | None = None,
) -> list[str]:
    """Best-effort cleanup for leftovers from an interrupted app update.

    The apply helper is rollback-safe, but power loss or process termination can
    still leave sibling ``.new``/``.bak`` directories or stale staged packages.
    On a healthy startup this removes those leftovers. If the live install dir is
    missing but ``.bak`` exists, it restores the backup. Any failure is logged and
    returned as a note; this function never raises.
    """
    notes: list[str] = []
    target = Path(install_dir).resolve() if install_dir is not None else install_root()
    if target is not None:
        target = Path(target).resolve()
        new_dir = target.with_name(target.name + ".new")
        bak_dir = target.with_name(target.name + ".bak")
        try:
            if not target.exists() and bak_dir.is_dir():
                bak_dir.rename(target)
                notes.append(f"restored backup install from {bak_dir}")
        except OSError as exc:
            notes.append(f"could not restore backup install: {exc}")
            log.warning("updater: could not restore backup install %s", bak_dir, exc_info=True)
        if target.exists():
            for leftover, label in ((new_dir, "partial install"), (bak_dir, "backup install")):
                try:
                    if leftover.is_dir():
                        shutil.rmtree(leftover, ignore_errors=True)
                        notes.append(f"removed stale {label} at {leftover}")
                except OSError as exc:
                    notes.append(f"could not remove stale {label}: {exc}")
                    log.debug("updater: could not remove stale update dir %s", leftover, exc_info=True)
    root = Path(stage_root) if stage_root is not None else default_update_stage_dir()
    for version in read_stale_update_versions(root):
        before = root / _safe_version_dir(version)
        if before.exists():
            remove_staged_package(root, version)
            notes.append(f"removed staged package for blocked version {version}")
    return notes


def stage_app_package(
    manifest: Manifest,
    stage_root: os.PathLike | str,
    *,
    session=None,
    timeout: int = _DOWNLOAD_TIMEOUT,
    progress_cb: Optional[Callable[[object], None]] = None,
    retries: int = _DOWNLOAD_RETRIES,
) -> Optional[Path]:
    """Download + extract a newer app package into a versioned staging directory.

    Returns the extracted bundle root (the directory whose contents are mirrored
    over the install on restart), or ``None`` when nothing is staged. Older
    versioned staging dirs are pruned so stale packages don't pile up.
    """
    version_dir = _safe_version_dir(manifest.app_version)
    prune_stale_staged_packages(stage_root, manifest.app_version)
    dest_dir = Path(stage_root) / version_dir
    zip_path = download_app_package(
        manifest,
        dest_dir,
        session=session,
        timeout=timeout,
        progress_cb=progress_cb,
        retries=retries,
    )
    if zip_path is None:
        return None
    if progress_cb is not None:
        progress_cb(
            DownloadProgress(
                delta_bytes=0,
                kind="app",
                label="StashSageWindows.zip",
                version=manifest.app_version,
                phase="extracting",
            )
        )
    return extract_app_package(zip_path, dest_dir / "bundle")


def _ps_single_quoted(value: os.PathLike | str) -> str:
    """Return a PowerShell single-quoted string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def _sh_single_quoted(value: os.PathLike | str) -> str:
    """Return a POSIX-shell single-quoted string literal.

    A single quote inside the value is emitted as ``'\\''`` (close, escaped
    quote, reopen), the standard way to embed one in a single-quoted shell word.
    """
    return "'" + str(value).replace("'", "'\\''") + "'"


def write_apply_script(
    source_dir: os.PathLike | str,
    *,
    install_dir: os.PathLike | str | None = None,
    wait_for_pid: Optional[int] = None,
) -> Path:
    """Write a Windows cmd helper that swaps ``source_dir`` over the install dir.

    The helper waits for the current app process to exit, then performs an
    **atomic, rollback-safe** swap of the freshly extracted bundle over the
    running install directory:

    1. Mirror the new bundle into a sibling ``<install>.new`` with
       ``robocopy /MIR`` and check its exit code (``>= 8`` is a real failure -
       robocopy reports success as ``0-7``). On failure the half-mirrored
       ``.new`` is discarded and the *current* install is relaunched untouched.
    2. Rename the live install to ``<install>.bak`` and ``<install>.new`` into
       place. Each rename retries to ride out brief AV / file-lock windows. If
       the second rename fails the first is rolled back so the user is never
       left without a working install.
    3. Relaunch the swapped exe, prune the ``.bak`` and the staged bundle, and
       self-delete the helper.

    Every step is appended to ``apply-update.log`` beside the staged bundle so a
    failed swap is diagnosable instead of silent. This avoids overwriting files
    while the frozen app is still running, and needs no installer.

    The helper waits on the original process handle rather than repeatedly
    polling a reusable PID. It also refuses to swap while another StashSage
    process is active, because a second copy running from the same install dir
    could keep files locked and force rollback.
    """
    source = Path(source_dir).resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    target = Path(install_dir).resolve() if install_dir is not None else install_root()
    if target is None:
        raise UpdaterError("cannot resolve install directory for in-place update")
    target = Path(target).resolve()
    exe_name = Path(sys.executable).name if getattr(sys, "frozen", False) else "StashSage.exe"
    # The helper must not live inside the install dir: it renames the install dir
    # out of the way, so a helper inside it would vanish mid-run. Keep it (and the
    # log) beside the staged source instead.
    script = source.parent / "apply-stashsage-update.cmd"
    ps_script = source.parent / "apply-stashsage-update.ps1"
    # ``.new``/``.bak`` are siblings of the install dir so the final swap is a
    # same-volume rename (atomic + instant), not a cross-volume copy.
    new_dir = target.with_name(target.name + ".new")
    bak_dir = target.with_name(target.name + ".bak")
    log_path = source.parent / "apply-update.log"
    pid = int(wait_for_pid if wait_for_pid is not None else os.getpid())
    ps_script.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                f"$ParentPid = {pid}",
                f"$Source = {_ps_single_quoted(source)}",
                f"$Target = {_ps_single_quoted(target)}",
                f"$NewDir = {_ps_single_quoted(new_dir)}",
                f"$BakDir = {_ps_single_quoted(bak_dir)}",
                f"$Exe = {_ps_single_quoted(target / exe_name)}",
                f"$LogPath = {_ps_single_quoted(log_path)}",
                "",
                "function Write-ApplyLog([string]$Message) {",
                "  $line = ('{0} {1}' -f (Get-Date -Format o), $Message)",
                "  Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value $line",
                "}",
                "",
                "function Invoke-MoveRetry([string]$From, [string]$To) {",
                "  for ($i = 0; $i -lt 5; $i++) {",
                "    try {",
                "      Move-Item -LiteralPath $From -Destination $To -ErrorAction Stop",
                "      return $true",
                "    } catch {",
                "      Start-Sleep -Seconds 1",
                "    }",
                "  }",
                "  return $false",
                "}",
                "",
                "function Start-CurrentExe {",
                "  if (Test-Path -LiteralPath $Exe) {",
                "    Start-Process -FilePath $Exe",
                "  }",
                "}",
                "",
                "try {",
                "  Write-ApplyLog ('helper started; parent pid=' + $ParentPid)",
                "  $parent = Get-Process -Id $ParentPid -ErrorAction SilentlyContinue",
                "  if ($null -ne $parent) {",
                "    try {",
                "      Write-ApplyLog ('waiting for parent process handle ' + $ParentPid)",
                "      $parent.WaitForExit()",
                "    } finally {",
                "      $parent.Dispose()",
                "    }",
                "  } else {",
                "    Write-ApplyLog ('parent process already exited: ' + $ParentPid)",
                "  }",
                "",
                "  $otherInstances = @(",
                "    Get-Process -Name 'StashSage' -ErrorAction SilentlyContinue |",
                "      Where-Object { $_.Id -ne $ParentPid }",
                "  )",
                "  if ($otherInstances.Count -gt 0) {",
                "    $ids = ($otherInstances | ForEach-Object { $_.Id }) -join ','",
                "    Write-ApplyLog ('refusing to apply update; other StashSage process ids=' + $ids)",
                "    exit 20",
                "  }",
                "",
                "  Write-ApplyLog 'app exited; staging mirror'",
                "  if (Test-Path -LiteralPath $NewDir) { Remove-Item -LiteralPath $NewDir -Recurse -Force }",
                "  if (Test-Path -LiteralPath $BakDir) { Remove-Item -LiteralPath $BakDir -Recurse -Force }",
                "  & robocopy $Source $NewDir /MIR /MT:8 /R:3 /W:2 /NFL /NDL /NP |",
                "    Add-Content -LiteralPath $LogPath -Encoding UTF8",
                "  $robocopyExit = $LASTEXITCODE",
                "  if ($robocopyExit -ge 8) {",
                "    Write-ApplyLog ('ERROR robocopy failed exit=' + $robocopyExit + '; keeping current install')",
                "    if (Test-Path -LiteralPath $NewDir) { Remove-Item -LiteralPath $NewDir -Recurse -Force }",
                "    Start-CurrentExe",
                "    exit 1",
                "  }",
                "",
                "  if (-not (Invoke-MoveRetry $Target $BakDir)) {",
                "    Write-ApplyLog 'ERROR could not move install aside; keeping current install'",
                "    if (Test-Path -LiteralPath $NewDir) { Remove-Item -LiteralPath $NewDir -Recurse -Force }",
                "    Start-CurrentExe",
                "    exit 1",
                "  }",
                "  if (-not (Invoke-MoveRetry $NewDir $Target)) {",
                "    Write-ApplyLog 'ERROR could not install new bundle; rolling back'",
                "    Invoke-MoveRetry $BakDir $Target | Out-Null",
                "    Start-CurrentExe",
                "    exit 1",
                "  }",
                "",
                "  Write-ApplyLog 'swap complete; relaunching'",
                "  Start-Process -FilePath $Exe",
                "  if (Test-Path -LiteralPath $BakDir) { Remove-Item -LiteralPath $BakDir -Recurse -Force }",
                "  if (Test-Path -LiteralPath $Source) { Remove-Item -LiteralPath $Source -Recurse -Force }",
                "  exit 0",
                "} catch {",
                "  Write-ApplyLog ('apply helper failed: ' + $_.Exception.Message)",
                "  exit 1",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    script.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal",
                f"set \"APPLY_PS1={ps_script}\"",
                "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%APPLY_PS1%\"",
                "set \"APPLY_EXIT=%ERRORLEVEL%\"",
                "if \"%APPLY_EXIT%\"==\"0\" del \"%APPLY_PS1%\" >nul 2>&1",
                "if \"%APPLY_EXIT%\"==\"0\" (goto) 2>nul & del \"%~f0\"",
                "exit /b %APPLY_EXIT%",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return script


def write_apply_script_posix(
    source_dir: os.PathLike | str,
    *,
    install_dir: os.PathLike | str | None = None,
    wait_for_pid: Optional[int] = None,
) -> Path:
    """Write a Linux ``.sh`` helper that swaps ``source_dir`` over the install dir.

    Mirrors the Windows helper's atomic, rollback-safe design (see
    :func:`write_apply_script`), using shell primitives:

    1. Wait for the current app process to exit (bounded ``kill -0`` poll) and
       refuse to swap while another StashSage instance is running.
    2. Mirror the new bundle into a sibling ``<install>.new`` with ``cp -a``
       (preserving the executable bit). On failure the half-mirror is discarded
       and the current install is relaunched untouched.
    3. ``mv`` the live install to ``<install>.bak`` and ``<install>.new`` into
       place (same-volume, atomic). If the second move fails the first is rolled
       back so the user is never left without a working install.
    4. Relaunch the swapped binary, prune the ``.bak`` + staged bundle, and
       self-delete the helper. Every step is appended to ``apply-update.log``
       beside the staged bundle.

    The helper lives beside the staged bundle, never inside the install dir it
    renames aside.
    """
    source = Path(source_dir).resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    target = Path(install_dir).resolve() if install_dir is not None else install_root()
    if target is None:
        raise UpdaterError("cannot resolve install directory for in-place update")
    target = Path(target).resolve()
    exe_name = Path(sys.executable).name if getattr(sys, "frozen", False) else "StashSage"
    script = source.parent / "apply-stashsage-update.sh"
    new_dir = target.with_name(target.name + ".new")
    bak_dir = target.with_name(target.name + ".bak")
    log_path = source.parent / "apply-update.log"
    pid = int(wait_for_pid if wait_for_pid is not None else os.getpid())
    q = _sh_single_quoted
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -u",
                f"ParentPid={pid}",
                f"Source={q(source)}",
                f"Target={q(target)}",
                f"NewDir={q(new_dir)}",
                f"BakDir={q(bak_dir)}",
                f"Exe={q(target / exe_name)}",
                f"LogPath={q(log_path)}",
                "",
                "log() { printf '%s %s\\n' \"$(date -Iseconds 2>/dev/null || date)\" \"$1\" >> \"$LogPath\"; }",
                "start_current() { if [ -x \"$Exe\" ]; then (\"$Exe\" >/dev/null 2>&1 &) ; fi; }",
                "",
                "log \"helper started; parent pid=$ParentPid\"",
                "i=0",
                "while kill -0 \"$ParentPid\" 2>/dev/null; do",
                "  i=$((i+1))",
                "  if [ \"$i\" -ge 600 ]; then log 'parent still alive after wait; proceeding'; break; fi",
                "  sleep 1",
                "done",
                "",
                "others=$(pgrep -x StashSage 2>/dev/null | grep -v \"^$ParentPid$\" || true)",
                "if [ -n \"$others\" ]; then",
                "  log \"refusing to apply update; other StashSage pids=$others\"",
                "  exit 20",
                "fi",
                "",
                "log 'app exited; staging mirror'",
                "rm -rf \"$NewDir\" \"$BakDir\"",
                "if ! cp -a \"$Source\" \"$NewDir\"; then",
                "  log 'ERROR mirror copy failed; keeping current install'",
                "  rm -rf \"$NewDir\"; start_current; exit 1",
                "fi",
                "if ! mv \"$Target\" \"$BakDir\"; then",
                "  log 'ERROR could not move install aside; keeping current install'",
                "  rm -rf \"$NewDir\"; start_current; exit 1",
                "fi",
                "if ! mv \"$NewDir\" \"$Target\"; then",
                "  log 'ERROR could not install new bundle; rolling back'",
                "  mv \"$BakDir\" \"$Target\" 2>/dev/null || true",
                "  start_current; exit 1",
                "fi",
                "",
                "log 'swap complete; relaunching'",
                "rm -rf \"$BakDir\"",
                "start_current",
                "rm -rf \"$Source\"",
                "rm -f \"$0\"",
                "exit 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    try:
        script.chmod(0o755)
    except OSError:
        pass
    return script


def launch_app_update_after_exit(
    source_dir: os.PathLike | str,
    *,
    install_dir: os.PathLike | str | None = None,
    wait_for_pid: Optional[int] = None,
) -> subprocess.Popen:
    """Launch the in-place swap helper and return the helper process."""
    if not supports_app_package_apply():
        raise UpdaterError(f"app package apply is not supported on {sys.platform}")
    if sys.platform == "win32":
        script = write_apply_script(
            source_dir, install_dir=install_dir, wait_for_pid=wait_for_pid
        )
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.Popen(
            ["cmd", "/c", str(script)],
            cwd=str(script.parent),
            creationflags=creationflags,
        )
    # Linux: a detached bash helper that survives the app exiting.
    script = write_apply_script_posix(
        source_dir, install_dir=install_dir, wait_for_pid=wait_for_pid
    )
    return subprocess.Popen(
        ["/bin/bash", str(script)],
        cwd=str(script.parent),
        start_new_session=True,
    )


# orchestration
def check_for_updates(
    config: Optional[Mapping],
    *,
    current_version: str,
    generated_root: os.PathLike | str | None = None,
    update_stage_dir: os.PathLike | str | None = None,
    stage_app_update: bool = False,
    force_app_update: bool = False,
    session=None,
    manifest_timeout: int = _MANIFEST_TIMEOUT,
    download_timeout: int = _DOWNLOAD_TIMEOUT,
    manifest_retries: int = _MANIFEST_RETRIES,
    download_retries: int = _DOWNLOAD_RETRIES,
    progress_cb: Optional[Callable[[object], None]] = None,
) -> UpdateOutcome:
    """Fetch the manifest, sync assets, and report whether an app update exists.

    A blank/absent ``update_manifest_url`` is a no-op, and any network failure
    degrades gracefully to the locally cached assets.
    """
    url = str((config or {}).get("update_manifest_url") or "").strip()
    if not url:
        return UpdateOutcome(None, False, False, None, current_version=str(current_version or ""))

    raw = fetch_manifest(
        url,
        session=session,
        timeout=manifest_timeout,
        retries=manifest_retries,
    )
    if raw is None:
        return UpdateOutcome(None, False, False, None, current_version=str(current_version or ""))
    try:
        manifest = parse_manifest(raw)
    except UpdaterError as exc:
        log.warning("updater: %s", exc)
        return UpdateOutcome(None, False, False, None, current_version=str(current_version or ""))

    if generated_root is None:
        generated_root = asset_paths.generated_assets_root()

    sync = sync_assets(
        manifest,
        generated_root,
        session=session,
        timeout=download_timeout,
        progress_cb=progress_cb,
        bundled_resolver=asset_paths.bundled_db_dir,
        retries=download_retries,
    )

    # Co-versioned bucket consistency gate: if any model-bucket asset failed to
    # download, roll back this run's downloads for those buckets so the override
    # cannot serve a mixed-vintage set (new model + stale stats). The override
    # reverts to its prior coherent state and the next check retries.
    failed_consistency_buckets = {
        asset.name for asset, _ in sync.failed if asset.name in CONSISTENCY_BUCKETS
    }
    consistency_ok = not failed_consistency_buckets
    if not consistency_ok:
        rolled_back = [a for a in sync.downloaded if a.name in failed_consistency_buckets]
        if rolled_back:
            rollback_synced_assets(generated_root, rolled_back)
            sync.downloaded = [a for a in sync.downloaded if a not in rolled_back]
        log.warning(
            "updater: rolled back partial sync of co-versioned bucket(s) %s to "
            "avoid serving mismatched assets",
            ", ".join(sorted(failed_consistency_buckets)),
        )

    try:
        prune_orphan_override_assets(manifest, generated_root)
    except Exception:
        log.debug("updater: orphan override prune failed", exc_info=True)

    # Stamp the override with the version/commit it now reflects so a later
    # bundle upgrade can detect and discard a superseded override (see
    # asset_paths.reconcile_override_with_bundle). Only stamp when the synced
    # model buckets are internally consistent.
    if consistency_ok:
        try:
            from poe2trade import __build_commit__

            asset_paths.write_override_provenance(
                manifest.app_version, __build_commit__, root=Path(generated_root)
            )
        except Exception:
            log.debug("updater: could not stamp override provenance", exc_info=True)
    if update_stage_dir is None:
        update_stage_dir = default_update_stage_dir()

    current_revoked = version_is_revoked(manifest, current_version)
    current_unsupported = not version_is_supported(manifest, current_version)
    manifest_version_revoked = version_is_revoked(manifest, manifest.app_version)
    for revoked_version in manifest.revoked_versions:
        add_stale_update_version(update_stage_dir, revoked_version)
        remove_staged_package(update_stage_dir, revoked_version)

    app_version_newer = app_update_available(manifest, current_version)
    newer_app = (
        bool(force_app_update)
        or app_version_newer
        or current_revoked
        or current_unsupported
    )
    app_update_reason = ""
    if force_app_update:
        app_update_reason = "forced"
    elif app_version_newer:
        app_update_reason = "newer_version"
    elif current_revoked:
        app_update_reason = "revoked_runtime"
    elif current_unsupported:
        app_update_reason = "unsupported_runtime"
    log.info(
        "updater: manifest v%s checked against running v%s "
        "(newer_app=%s, reason=%s, assets_downloaded=%d, assets_failed=%d)",
        manifest.app_version,
        current_version,
        newer_app,
        app_update_reason or "none",
        len(sync.downloaded),
        len(sync.failed),
    )
    if manifest_version_revoked and newer_app:
        log.warning(
            "updater: manifest app_version %s is revoked; refusing to stage it",
            manifest.app_version,
        )

    # Loop guards: never auto-stage when (a) the running version is the
    # unknown/0.0.0 fallback (every manifest looks newer -> perpetual re-stage),
    # or (b) this exact version already failed to apply on a previous swap.
    unknown_runtime = is_unknown_version(current_version)
    stale_versions = read_stale_update_versions(update_stage_dir)
    version_is_stale = str(manifest.app_version or "").strip() in stale_versions
    if newer_app and unknown_runtime:
        log.warning(
            "updater: runtime version %r is the unknown/fallback sentinel; "
            "suppressing auto-staging to avoid an update loop (reinstall recommended)",
            current_version,
        )
    elif newer_app and version_is_stale:
        log.warning(
            "updater: version %s previously failed to apply on swap; "
            "not re-staging it",
            manifest.app_version,
        )

    app_package_dir: Optional[Path] = None
    if (
        stage_app_update
        and newer_app
        and not unknown_runtime
        and not version_is_stale
        and not manifest_version_revoked
        and manifest.app_package_url
        and supports_app_package_apply()
        and install_dir_is_writable()
    ):
        try:
            app_package_dir = stage_app_package(
                manifest,
                update_stage_dir,
                session=session,
                timeout=download_timeout,
                progress_cb=progress_cb,
                retries=download_retries,
            )
            if app_package_dir is not None:
                post_update_download_metric(config, manifest.app_version, session=session)
        except Exception as exc:
            log.warning("updater: app package staging failed: %s", exc)
    return UpdateOutcome(
        manifest=manifest,
        assets_changed=sync.changed,
        app_update_available=newer_app,
        app_version=manifest.app_version,
        sync=sync,
        app_package_dir=app_package_dir,
        runtime_version_unknown=unknown_runtime and newer_app,
        runtime_version_revoked=current_revoked,
        runtime_version_unsupported=current_unsupported,
        current_version=str(current_version or ""),
        app_update_reason=app_update_reason,
    )


def run_check_in_background(
    config: Optional[Mapping],
    *,
    current_version: str,
    on_complete: Optional[Callable[[UpdateOutcome], None]] = None,
    generated_root: os.PathLike | str | None = None,
    update_stage_dir: os.PathLike | str | None = None,
    stage_app_update: bool = False,
    force_app_update: bool = False,
    session=None,
    progress_cb: Optional[Callable[[object], None]] = None,
) -> threading.Thread:
    """Run :func:`check_for_updates` on a daemon thread; never raises."""

    def _work() -> None:
        try:
            outcome = check_for_updates(
                config,
                current_version=current_version,
                generated_root=generated_root,
                update_stage_dir=update_stage_dir,
                stage_app_update=stage_app_update,
                force_app_update=force_app_update,
                session=session,
                progress_cb=progress_cb,
            )
        except Exception:
            log.exception("updater: background check failed")
            outcome = UpdateOutcome(None, False, False, None)
        if on_complete is not None:
            try:
                on_complete(outcome)
            except Exception:
                log.exception("updater: on_complete callback failed")

    thread = threading.Thread(target=_work, name="StashSageUpdater", daemon=True)
    thread.start()
    return thread
