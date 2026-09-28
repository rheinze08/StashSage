"""Headless in-app update, for testing a real frozen build end to end.

``StashSage.exe --self-test-update <manifest.json>`` runs the same staging and
swap-helper path as Restart & Update -- verified download, atomic stage, the
generated helper, the swap and the relaunch -- without starting the GUI. The
manifest and package are read from local disk: URLs on the reserved
``local.stashsage.test`` host resolve to files beside the manifest, so nothing
touches the network. CI uses it to prove a packaged exe can update itself; the
app's hidden test-update hotkey uses the same local session.

The staged version may equal the running one (the staging is forced), so a test
can re-apply the build it just made. ``--relaunch-write-version <path>`` makes
the relaunched exe write its version there and exit instead of opening the GUI.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlparse

from poe2trade.app import updater

log = logging.getLogger(__name__)

LOCAL_UPDATE_HOST = "local.stashsage.test"

# Exit codes for the self-test mode (0 = helper launched).
EXIT_BAD_ARGUMENTS = 2
EXIT_NOT_STAGED = 3


class LocalUpdateResponse:
    """Just enough of a ``requests`` response for the updater, backed by a file."""

    def __init__(self, path: Path):
        self.path = path
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        if not self.path.is_file():
            raise FileNotFoundError(self.path)

    def json(self) -> dict:
        self.raise_for_status()
        # utf-8-sig so a BOM-prefixed manifest (PowerShell's Set-Content default
        # on Windows) still parses; plain utf-8 would choke on the leading BOM.
        return json.loads(self.path.read_text(encoding="utf-8-sig"))

    def __enter__(self):
        self.raise_for_status()
        return self

    def __exit__(self, *_exc):
        return False

    def iter_content(self, chunk_size: int = 1 << 16):
        self.raise_for_status()
        with self.path.open("rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                yield chunk


class LocalUpdateSession:
    """Requests-like session serving a local manifest and the files beside it."""

    def __init__(self, manifest_path: Path):
        self.manifest_path = Path(manifest_path)
        self.root = self.manifest_path.parent

    def get(self, url: str, **_kwargs):
        parsed = urlparse(str(url))
        if parsed.netloc.lower() != LOCAL_UPDATE_HOST:
            raise ValueError(f"unsupported local test update URL: {url}")
        name = Path(parsed.path).name
        if name == self.manifest_path.name:
            return LocalUpdateResponse(self.manifest_path)
        return LocalUpdateResponse(self.root / name)

    def post(self, *_args, **_kwargs):
        raise ValueError("the local update session does not send telemetry")


def _report(message: str, *, error: bool = False) -> None:
    # A windowed frozen exe has no stdout; the log is where CI reads the outcome.
    (log.error if error else log.info)("self-test update: %s", message)
    print(message)


def run_self_test_update(
    manifest_path: Path,
    *,
    stage_dir: Optional[Path] = None,
    relaunch_args: Sequence[str] = (),
    current_version: Optional[str] = None,
) -> int:
    """Stage the local package and launch the swap helper; return an exit code.

    The caller must exit right after this returns 0: the helper waits for this
    process to end before it swaps the install.
    """
    from poe2trade import __version__

    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_file():
        _report(f"manifest not found: {manifest_path}", error=True)
        return EXIT_BAD_ARGUMENTS
    if updater.install_root() is None:
        _report("--self-test-update needs a frozen build; nothing to swap", error=True)
        return EXIT_BAD_ARGUMENTS
    stage_root = Path(stage_dir).resolve() if stage_dir is not None else updater.default_update_stage_dir()
    with tempfile.TemporaryDirectory(prefix="stashsage-selftest-generated-") as generated:
        outcome = updater.check_for_updates(
            {"update_manifest_url": f"https://{LOCAL_UPDATE_HOST}/{manifest_path.name}"},
            current_version=current_version or __version__,
            generated_root=generated,
            update_stage_dir=stage_root,
            stage_app_update=True,
            force_app_update=True,
            session=LocalUpdateSession(manifest_path),
        )
    if outcome.manifest is None:
        _report(f"could not read manifest {manifest_path}", error=True)
        return EXIT_NOT_STAGED
    problem = updater.staged_bundle_problem(outcome.app_package_dir, outcome.app_version)
    if problem is not None:
        _report(f"update v{outcome.app_version} was not staged: {problem}", error=True)
        return EXIT_NOT_STAGED
    log_path = stage_root / "apply-update.log"
    updater.record_pending_update(stage_root, outcome.app_version or "")
    updater.launch_app_update_after_exit(
        outcome.app_package_dir,
        expected_version=outcome.app_version,
        log_path=log_path,
        relaunch_args=relaunch_args,
    )
    _report(f"staged v{outcome.app_version}; swap helper launched (log: {log_path})")
    return 0
