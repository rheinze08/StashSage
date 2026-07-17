# Portable EXE & Release-Pipeline Hardening Plan (Round 2)

Follow-on hardening for the portable one-dir Windows bundle and the
`Update-Release.ps1` build/publish pipeline. This is the **next layer** after
`docs/PORTABLE_UPDATE_HARDENING_PLAN.md` (Phases 0-5), which already shipped:
the swap helper (robocopy mirror + atomic rename + rollback + logging), the
manifest writer/verifier round-trip, and **Phase 5** (version identity,
monotonicity guard, format validation, `0.0.0`-loop guard, post-swap
verification, documented `parse_version` contract, single bump point).

This document is written to be handed to a fresh agent. Read the **Ground
rules** and **Orientation** sections first; they contain everything you need to
build, test, and not break the pipeline.

Status legend: `[ ]` not started, `[~]` in progress, `[x]` done.

---

## Ground rules for the implementing agent

- **Branch.** Develop on a new branch off `main` (e.g.
  `claude/exe-pipeline-hardening-rN`). Never push to `main`. Commit in logical
  chunks; push with `git push -u origin <branch>`.
- **Don't open a PR unless asked.**
- **The version chain is load-bearing and now guarded - don't regress it.**
  `setup.py:8` (`setup(version=...)`) -> `tools/get_version.py` (strict
  `N.N.N[.N]` validation) -> `Update-Release.ps1` (`STASHSAGE_VER`, monotonicity
  guard, identity assertion) -> `tools/write_build_meta.py` (`__build_version__`,
  `__build_date__`) -> `poe2trade/__init__.py` runtime `__version__` -> client
  `updater.is_newer_version`. Tests in `tests/test_updater.py`,
  `tests/test_get_version.py`, `tests/test_bump_version.py` lock the contract.
- **`tools/compare_version.py` intentionally duplicates the `parse_version` /
  `is_newer_version` contract** (it can't import `updater`, which pulls in
  tkinter). `tests/test_updater.py::test_compare_version_tool_matches_updater_semantics`
  keeps the copy in lock-step - if you touch one, keep both and that test green.

### How to run the test suite here (Linux container)

The default interpreter is Python 3.11 **without tkinter**, and `pip install -e .`
fails on the GUI deps under 3.11. Use a 3.12 venv (3.12 has tkinter):

```bash
python3.12 -m venv /tmp/venv && /tmp/venv/bin/pip install -q -e . pytest ruff==0.15.8
xvfb-run -a /tmp/venv/bin/python -m pytest -q      # full suite (needs xvfb for tk imports)
/tmp/venv/bin/ruff check .                          # lint gate: select=["F"], ignore=["F841"]
```

The standalone `tools/*.py` scripts (`get_version`, `bump_version`,
`compare_version`) import nothing from `poe2trade`, so they run under plain
`python` too. Tests load them by path via `tests/conftest.py::load_tool`.

### What CI already covers (`.github/workflows/tests.yml`)

- `lint` (ruff `F`), `pytest` (3.11/3.12/3.13 + xvfb).
- `release-contract-windows`: **parses** `Update-Release.ps1`,
  `tools/Sync-Downstream.ps1`, `build_linux.ps1` with the PowerShell AST parser
  (your only automated PS syntax check - there is no `pwsh` in this container),
  and runs the release-contract pytest files.
- `windows-build-smoke`: runs the real `build_app.bat` on `windows-latest`,
  unzips `docs/StashSageWindows.zip`, and runs the re-extracted
  `StashSage.exe --write-version`, asserting version + non-`dev` build date.
- `linux-build-smoke`: runs `tools/build_linux.sh`.

**There is still no automated coverage of the actual update *swap* (download ->
extract -> robocopy -> rename -> relaunch).** That is the single most valuable
gap below (item 6.3) and the still-open Phase 0 manual check.

### Orientation - the files you'll touch

| Area | File |
| --- | --- |
| Swap helper (generated `.cmd`) + client update logic | `poe2trade/app/updater.py` |
| GUI wiring of the update flow | `poe2trade/app/gui_tk.py` (~5340-5560) |
| Windows build | `build_app.bat` |
| Linux build | `tools/build_linux.sh`, `build_linux.ps1` |
| Release orchestration | `Update-Release.ps1` |
| Build metadata stamp | `tools/write_build_meta.py` |
| Win version resource | `tools/write_pyinstaller_version.py` |
| Manifest write/verify | `tools/write_update_manifest.py`, `tools/verify_update_manifest.py` |
| Pinned build env | `requirements.txt` (e.g. `pyinstaller==6.20.0`) |

---

## Phase 6 - Self-update execution safety (the swap path's runtime gaps)

The swap helper is now atomic/rollback-safe, but its two documented assumptions
are still unenforced, and the path has never run end-to-end in CI.

- [ ] **6.1 Enforce single-instance before triggering a swap.**
  `write_apply_script`'s docstring (`poe2trade/app/updater.py`, "Single-instance
  assumption") admits the helper waits on exactly one PID; a second window from
  the same install keeps files locked and the swap retries time out and roll
  back. Add a real single-instance lock (a named OS mutex on Windows, or a
  lockfile in the install/stage dir with PID + liveness check) acquired before
  staging/launching the swap. If a second instance is detected, skip auto-stage
  and surface "another StashSage window is open". *Testable: the lockfile
  acquire/release/stale-PID logic is a pure-ish unit; wire the Windows mutex
  behind `supports_app_package_apply()`.*
  **Acceptance:** with two instances running, only one can initiate a swap; the
  other logs and defers.

- [ ] **6.2 Wait on the process handle, not a reused PID.** The helper polls
  `tasklist /FI "PID eq %PID%"` (`write_apply_script`). On Windows a PID can be
  recycled, so the helper could start the swap while a *different* process holds
  the old PID, or proceed early. Pass the exe path and also match the image name
  (`tasklist /FI "IMAGENAME eq StashSage.exe"`), or hand the helper an inherited
  process handle / use `WaitForSingleObject`-style waiting. Carried over from
  Phase 1 ("waiting on the exe handle, not just the PID" - still TODO).
  **Acceptance:** the helper provably waits for the *actual* app process to
  exit, not just for the PID number to disappear.

- [ ] **6.3 Automated swap integration test in Windows CI (highest value).**
  Today `tests/test_updater.py::test_write_apply_script_*` only string-asserts
  the generated `.cmd`; nothing executes it. Add a `windows-latest` job that:
  (1) builds `v_old`; (2) bumps `setup.py` and builds `v_new`; (3) extracts
  `v_old` into a temp "install" dir and launches a dummy long-lived process to
  stand in for the running exe; (4) runs the generated `apply-stashsage-update.cmd`
  pointed at the `v_new` bundle; (5) asserts the install dir was swapped, the
  `.bak` pruned, the helper self-deleted, and the relaunched
  `StashSage.exe --write-version` reports `v_new`. This automates the one
  untested surface and the Phase 0 manual check.
  **Acceptance:** a green CI job proves a real robocopy+rename swap relaunches
  into the new version; a deliberately corrupted `v_new` triggers the rollback
  path and keeps `v_old` runnable.

- [ ] **6.4 Bundle self-integrity manifest + fast startup check (optional).**
  After a swap, nothing detects a partially-mirrored install at startup (a
  half-copied `_internal\` would crash deep in import). Ship a
  `bundle.sha256`/file-list inside the zip (written by `build_app.bat` /
  `build_linux.sh`) and add a *cheap* startup check (count + a couple of
  critical files, not every byte) that surfaces "install looks incomplete -
  please re-download" instead of a stack trace. Keep it opt-in/fast so it
  doesn't regress cold start.
  **Acceptance:** deleting/truncating a bundled file yields a clear startup
  message, not a raw exception.

---

## Phase 7 - Build provenance & supply-chain

Make a binary traceable to its source and its build environment reproducible.

- [ ] **7.1 Hash-locked dependency install.** `requirements.txt` pins versions
  (`pyinstaller==6.20.0`, ...) but carries **no hashes**, so `build_app.bat`'s
  `pip install -r requirements.txt` trusts whatever the index serves. Generate a
  fully hashed lock (`pip-compile --generate-hashes` or `pip hash`) and install
  with `--require-hashes`. Gate the build on it. *Linux-testable: a CI step that
  installs the lock with `--require-hashes` in a clean venv.*
  **Acceptance:** a tampered/substituted wheel fails the build.

- [ ] **7.2 Stamp the git commit into build metadata.** `tools/write_build_meta.py`
  writes only `__build_date__` + `__build_version__`. Add `__build_commit__`
  (short SHA, resolved via `git rev-parse --short HEAD`, falling back to an env
  var / `"unknown"` outside a checkout). Surface it in `--write-version` output
  and the title bar so a shipped binary is traceable to exact source. *Testable
  in `tests/test_write_build_meta.py`.*
  **Acceptance:** `StashSage.exe --write-version` (or `--version`) can report the
  commit it was built from.

- [ ] **7.3 Assert the embedded Windows file-version resource.**
  `tools/write_pyinstaller_version.py` bakes `FileVersion`/`ProductVersion` from
  `--version`, but nothing verifies the *frozen exe's* resource matches
  `STASHSAGE_VER`. After the build, assert
  `(Get-Item exe).VersionInfo.FileVersion` equals the expected
  `_version_tuple(STASHSAGE_VER)` (in `build_app.bat` near the existing runtime
  check at ~`build_app.bat:321`, and/or in the `windows-build-smoke` CI job).
  **Acceptance:** a drift between the embedded resource and `STASHSAGE_VER` fails
  the build.

- [ ] **7.4 Reproducibility pass + provenance doc.** Set `SOURCE_DATE_EPOCH` and
  audit `build_app.bat` / `tools/curate_stage.py` for nondeterminism (mtimes,
  `__pycache__`, dict ordering) so two builds of the same commit produce
  byte-stable (or at least hash-stable-modulo-known-fields) zips. Document the
  toolchain (Python minor, PyInstaller, OS) required to reproduce a release.
  **Acceptance:** documented, repeatable build inputs; ideally identical zip
  hashes across two runs of one commit.

---

## Phase 8 - Release operability & recovery

The pipeline can publish safely; it can't yet *recover* from a bad release.

- [ ] **8.1 Manifest revocation / minimum-supported-version.** A bad release
  currently can't be yanked: clients only move *forward* (`is_newer_version`
  strict) and there's no way to tell them "don't run / leave 0.6.3". Extend the
  manifest schema (bump `schema_version`, keep back-compat in
  `updater.parse_manifest`) with an optional `revoked_versions` list and/or
  `min_supported_version`; the client refuses to keep a revoked version (prompts
  re-download) and the updater treats a revoked staged version as stale (reuse
  the Phase 5 blocklist). Update `tools/write_update_manifest.py` +
  `tools/verify_update_manifest.py`. *Linux-testable end to end.*
  **Acceptance:** publishing a manifest that revokes `X` makes installed `X`
  clients prompt to re-download instead of sitting on a broken build.

- [ ] **8.2 Scheduled live-manifest verify workflow.** Carried from Phase 3 /
  `docs/IMPLEMENTATION_NOTES.md` (P2). A standalone scheduled GitHub Action that
  runs `tools/verify_update_manifest.py` against the live Pages manifest so a
  broken/stale manifest is caught *between* releases, not only during one.
  **Acceptance:** a cron job alerts on a manifest that fails the live contract.

- [ ] **8.3 Rollback / re-publish runbook.** Document the recovery procedure:
  when to use `Update-Release.ps1 -Republish` (re-upload fixed assets under the
  same tag) vs cutting a new patch via `-Bump patch`, how to revoke (8.1), and
  how the monotonicity guard interacts with each. Add to
  `docs/RELEASE_QA_CHECKLIST.md` or a new `docs/RELEASE_RUNBOOK.md`.
  **Acceptance:** an on-call operator can recover a bad release without reading
  the PowerShell source.

- [ ] **8.4 Linux self-apply.** Carried from Phase 4:
  `supports_app_package_apply()` is win32-only (`poe2trade/app/updater.py`); the
  mirror+rename+relaunch concept ports cleanly to a POSIX shell helper. Gate it
  the same way (writable install, single instance, post-swap verify).
  **Acceptance:** the Linux bundle can self-update in place, with the same
  rollback + post-swap-version guarantees as Windows.

---

## Phase 9 - Carry-overs from the first plan (still open)

Track these here so nothing is lost; details live in
`docs/PORTABLE_UPDATE_HARDENING_PLAN.md`:

- [ ] **Phase 0 manual end-to-end on real Windows** - the human-in-the-loop swap
  pass; superseded in practice by **6.3** once that lands.
- [ ] **Code signing (Phase 2)** - Authenticode cert + sign `StashSage.exe` in
  `build_app.bat`; biggest trust/AV win, needs budget.
- [ ] **Writable-install-location strategy (Phase 2)** - the download-and-run UX
  when extracted somewhere read-only (`install_dir_is_writable`).
- [ ] **Legacy-install migration (Phase 2)** - old Inno-era clients reading
  `app_installer_url`.
- [ ] **Decide the manifest `platforms` block's fate (Phase 3)** - document a
  consumer or drop it.
- [ ] **First-run / on-demand asset-bootstrap UX (Phase 4)**.
- [ ] **Update telemetry (Phase 4)** - staged/applied/failed outcomes in the log
  + title-bar flag.

---

## Suggested order

Start with **6.3** (automated swap test - it de-risks everything else and
finally exercises the untested surface), then **7.2 + 7.3** (cheap, high-signal
provenance, mostly Linux-testable), then **6.1/6.2** (swap-safety), then **8.1**
(revocation - the missing recovery primitive). **7.1**, **8.2**, **8.3** are
independent and can slot in any time. **8.4** and the Phase 9 carry-overs are
larger and lower-urgency.

Dependencies: **6.4** and **8.1** both build on the Phase 5 stale-version
blocklist (`updater.add_stale_update_version` / `read_stale_update_versions`).
**6.3** is a prerequisite for trusting **6.1/6.2** changes.
