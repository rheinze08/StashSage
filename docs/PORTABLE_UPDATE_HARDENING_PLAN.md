# Portable EXE + Self-Update Hardening Plan

Hardening plan for the portable one-dir bundle and its in-place self-update
("apply and restart") path, organized by priority. It is grounded in the
shipped code (`build_app.bat`, `poe2trade/app/updater.py`,
`tools/write_update_manifest.py`, `tools/verify_update_manifest.py`,
`Update-Release.ps1`) and calls out the specific gaps in the Update-Release
chain.

Priority/sequencing: **Phase 0 -> 1 -> 2 (signing) -> 3 -> 5** before relying on
self-update for a public release; **Phase 4** after. Phase 5 (version identity &
monotonicity) is a correctness gate: without it the pipeline can silently ship a
non-newer or mismatched version that the client either ignores or update-loops
on. **Phase 5 is now implemented** (monotonicity guard, format validation,
end-to-end identity assertion, client `0.0.0`-loop guard, post-swap
verification, documented `parse_version` contract + edge tests, and a single
bump point) - the only remaining release blockers are the manual Windows
end-to-end pass in Phase 0 and the signing/install-location work in Phase 2.

Status legend: `[ ]` not started, `[~]` in progress, `[x]` done.

---

## Phase 0 - Prove it on real Windows (release blocker)

The entire swap path has never executed on Windows; this is the one untested
surface.

- [ ] **Manual end-to-end once (requires a human + real Windows).** Run
  `build_app.bat` -> unzip `StashSageWindows.zip` -> run `StashSage.exe` ->
  point a test `update-manifest.json` at a newer version's zip -> confirm
  download, verify, extract, robocopy swap on exit, and relaunch all work, and
  that the version bumped after restart. *Cannot run in the Linux CI container;
  must be done interactively on Windows.*
- [x] **CI coverage.** Add a `windows-latest` job that drives `build_app.bat`,
  extracts the produced `docs/StashSageWindows.zip`, runs
  `StashSage.exe --write-version`, and asserts the runtime version and build
  date. Today CI only builds the Linux bundle, so the Windows package is
  otherwise unverified.

**Acceptance:** a fresh unzip launches (now proven automatically by CI); an
in-app update applies without a reinstall and relaunches into the new version
(still needs the manual Windows pass above).

---

## Phase 1 - Harden the swap helper (`write_apply_script`)

The generated `.cmd` is the riskiest, least-tested piece
(`poe2trade/app/updater.py:684`).

- [x] **Check robocopy's exit code.** `/MIR` returns 0-7 = success, >=8 =
  failure; the script currently ignores it and relaunches even on a
  half-mirrored (broken) install. Add `if %ERRORLEVEL% GEQ 8` -> log + abort +
  relaunch the old exe. *Done in `write_apply_script`: robocopy now mirrors into
  a sibling `.new`, and `>= 8` discards it and relaunches the untouched
  install.*
- [x] **Make the swap atomic with rollback.** `/MIR` mutates the live dir in
  place; an interruption leaves a corrupt install. Switch to: mirror into
  `install\.new`, rename `install`->`install\.bak` (or sibling), rename
  `.new`->`install`, then relaunch; restore `.bak` on failure. Prune `.bak` on
  next successful launch. *Done: same-volume sibling `.new`/`.bak` renames with
  a `:move_retry` loop; the `.bak` is rolled back into place if installing the
  new bundle fails, pruned on success, and any stale `.new`/`.bak` is cleared at
  the start of the next run.*
- [x] **Log the helper run** to a file in the stage dir (`apply-update.log`) so
  failures are diagnosable - right now they're invisible. *Done: every step
  (start, exit, mirror, each failure/rollback, success) is appended to
  `apply-update.log` beside the staged bundle.*
- [~] **Lock/AV resilience.** Keep the `/R:3 /W:2` retries, but widen for AV
  scans; consider waiting on the exe handle, not just the PID via `tasklist`.
  *Partly done: kept `/R:3 /W:2` and added a 5x retry-with-backoff `:move_retry`
  loop around the swap renames to ride out brief AV/file locks. Waiting on the
  exe handle (vs. the PID) is still TODO.*
- [x] **Self-clean** the helper `.cmd` + extracted bundle after a successful
  swap (in addition to the existing stale-version prune). *Done: the helper
  removes the staged bundle (`%SRC%`) and self-deletes via
  `(goto) 2>nul & del "%~f0"` after a successful swap.*
- [x] **Multiple instances.** The helper waits on one PID; document/guard the
  "two windows open" case. *Documented in `write_apply_script`'s docstring: the
  helper waits on exactly one PID; a second instance from the same install would
  keep files locked and the swap retries would time out and roll back, so the
  caller must ensure a single instance triggers the update.*

---

## Phase 2 - Install location & trust (the "download-and-run" UX)

- [ ] **Writable-location strategy.** In-place swap needs a writable folder;
  today it silently falls back to the download page
  (`install_dir_is_writable`, `poe2trade/app/updater.py:198`). Pick one:
  (a) first-run hint to extract somewhere writable, or (b) opt-in relocate into
  `%LOCALAPPDATA%\StashSage` + create shortcuts. Biggest remaining UX gap.
- [ ] **Code signing.** The portable exe is unsigned -> SmartScreen/Defender
  warnings on first run and possible mid-swap AV locks. Budget for an
  Authenticode cert; sign `StashSage.exe` in `build_app.bat`. Highest-leverage
  trust fix.
- [ ] **Legacy-install migration.** Existing Inno-era users get a manifest with
  `app_package_url` but their old client only reads `app_installer_url` -> they
  keep syncing models but never auto-migrate to the portable app. Decide: one
  final transitional installer release that points them to the portable zip, or
  accept a one-time manual re-download (and document it).

---

## Phase 3 - Update-Release alignment & guardrails

The happy path is aligned (build -> `StashSageWindows.zip` -> manifest
`app_package_url` -> upload -> Sync-Downstream/site -> live verify). Gaps to
close:

- [x] **Round-trip contract test in CI.** Build a real zip ->
  `write_update_manifest.py` -> `updater.parse_manifest` ->
  `verify_update_manifest.validate_manifest`, asserting the package URL/sha and
  that `parse_manifest` keeps the `.zip`. Catches field-name drift between
  writer/verifier/client. *Done:
  `test_real_zip_package_fields_round_trips_through_client_and_verifier` in
  `tests/test_write_update_manifest.py` builds a real bundle zip, runs the
  writer, and asserts the package URL/sha survive `parse_manifest`'s
  `_is_zip_url` gate and that the verifier agrees on the same contract. Runs in
  the existing CI `tests` job.*
- [x] **Extract-and-run smoke of the zipped (not just freshly-built) exe.**
  `Assert-ZipContainsEntry` only checks the entry exists, not that the
  re-extracted app launches. *Covered by the Phase 0 `windows-build-smoke` CI
  job, which unzips `docs/StashSageWindows.zip` and runs the re-extracted
  `StashSage.exe --write-version`, asserting the runtime version/build date.*
- [ ] **Decide the fate of the manifest `platforms` block** - the client
  ignores it and the site doesn't read it; either document a consumer or drop
  it to avoid drift.
- [ ] **Scheduled live-manifest verify workflow** (standalone from the full
  release) so a broken Pages manifest is caught between releases - already a P2
  in `docs/IMPLEMENTATION_NOTES.md`.

---

## Phase 4 - Cross-platform & polish

- [ ] **Linux self-apply** (`supports_app_package_apply` is win32-only,
  `poe2trade/app/updater.py:175`); the swap helper concept ports cleanly to a
  shell script.
- [ ] **First-run / on-demand asset-bootstrap UX** (existing P1) - matters more
  now that the portable zip could ship thin.
- [ ] **Update telemetry.** Surface staged/applied/failed outcomes in the app
  log and the title-bar flag, and verify the declined-version + progress
  dialogs still read well with the new "apply and restart" wording.

---

## Phase 5 - Version identity, comparison & monotonicity (pipeline-owned)

The version a release advertises, the version it bundles, and the version the
running app reports must be one value, and each release must be strictly newer
than the last - otherwise the client (which only updates on a *strictly* newer
manifest version, `is_newer_version`, `poe2trade/app/updater.py:137`) either
silently ignores the release or update-loops on it. Today the chain is
single-sourced from `setup.py` (`setup(version=...)`, `setup.py:8`) through
`tools/get_version.py` -> `Update-Release.ps1` (`$Version`/`$relTag`/
`STASHSAGE_VER`/manifest `--version`, `Update-Release.ps1:247-264,300,322`) ->
`tools/write_build_meta.py` (`__build_version__`, `write_build_meta.py:84`) ->
runtime `__version__` (`poe2trade/__init__.py:24-38`), but nothing *enforces*
that single value or guards against a re-released / non-advancing version.

- [x] **Monotonicity guard (release blocker).** `Update-Release.ps1` resolves
  the version from `setup.py` but never checks it is strictly newer than the
  last release. Re-running with an un-bumped `setup.py` re-publishes the same
  version with `--clobber` (`Update-Release.ps1:379-383`); clients compare
  strictly-newer so they never see it - a silent no-op release, or new bytes
  shipped under an already-installed version. Add a pre-publish check: the
  resolved `$Version` must be strictly greater than both the latest `v*` git tag
  and the live manifest's `app_version` (reuse `is_newer_version` semantics via
  a tiny Python helper), failing the release otherwise unless an explicit
  `-Republish`/`-Force` switch is passed. *Done: `tools/compare_version.py`
  reimplements the `parse_version`/`is_newer_version` contract (it can't import
  `updater`, which pulls in tkinter; `tests/test_updater.py`'s
  `test_compare_version_tool_matches_updater_semantics` keeps the copy in
  lock-step). `Update-Release.ps1`'s `Assert-VersionIsNewer` calls it with the
  resolved version against every existing `v*` tag (`Get-LatestVersionTags`) and
  the live manifest's `app_version` (`Get-LiveManifestVersion`), failing the
  release unless `-Republish` is passed.*
- [x] **Version-format validation at the source.** `get_version.py` and the
  release script accept any string, but `parse_version`
  (`poe2trade/app/updater.py:128`) strips non-digits, so `0.6.0-rc1` compares
  *equal* to `0.6.0` and a `v0.6.0-beta` tag would ship a manifest version
  clients treat as the GA release. Enforce a strict numeric `N.N.N[.N]` shape in
  `get_version.py` (and assert it in `Update-Release.ps1`) so a pre-release or
  typo'd version can never be published. *Done: `get_version.py` adds
  `VERSION_RE`/`is_valid_version` and its `main` now exits non-zero on anything
  that isn't a strict `N.N.N[.N]` (rejecting `-rc1`/`-beta`/2-part/typo'd
  versions); `Update-Release.ps1`'s `Assert-VersionFormat` re-checks the
  resolved version so the explicit `-Version` override path is held to the same
  shape. Covered by `tests/test_get_version.py`.*
- [x] **End-to-end version-identity assertion.** `build_app.bat:321` already
  fails the build when the frozen exe's `--write-version` output disagrees with
  `STASHSAGE_VER` (exit 4) or the build date is `dev`/missing (exit 5). Extend
  the chain so the *manifest's* `app_version` is asserted equal to the
  re-extracted exe's reported version (in `Update-Release.ps1` after the build,
  and/or in the Phase 0 `windows-build-smoke` CI job) - closing the last drift
  gap between what the manifest advertises and what actually runs. *Done:
  `Update-Release.ps1`'s `Assert-PackagedExeVersionMatchesManifest` extracts the
  built `StashSageWindows.zip` exactly as a user would, runs the re-extracted
  `StashSage.exe --write-version`, and fails the release if the reported version
  differs from the manifest's `app_version`. Runs right after the manifest is
  written, before any upload.*
- [x] **Client fallback guard against update loops.** If `_build_meta` is absent
  from the frozen bundle, `__version__` falls through to the `setup.py` parse
  (gone when frozen) -> `importlib.metadata` -> `"0.0.0"`
  (`poe2trade/__init__.py:33-38`). A `0.0.0` runtime treats *every* manifest as
  newer -> perpetual update prompt / re-stage loop. Guard the update check: when
  the runtime version is the unknown/`0.0.0` fallback (or `__build_date__` is
  `"dev"` in a frozen build), suppress auto-staging and surface a "reinstall"
  hint instead of looping. *Done: `updater.is_unknown_version` flags an all-zero
  runtime version; `check_for_updates` suppresses auto-staging for it (and never
  fetches the package), reports it via the new `UpdateOutcome.runtime_version_unknown`
  field, and the GUI shows a "re-download" warning instead of looping
  (`_show_update_result`). The `dev`-build case is already covered because a
  non-frozen/source run fails the existing `install_root`/`install_dir_is_writable`
  frozen gate and never stages. Covered by `tests/test_updater.py`.*
- [x] **Post-swap version verification.** The swap helper relaunches the new exe
  but never confirms its `__build_version__` actually advanced to the manifest's
  `app_version`; a stale or mismatched staged zip would relaunch the *same*
  version and re-trigger the update every launch. Record the expected
  post-swap version (e.g. a sentinel beside the install) before launching the
  helper and, on next startup, confirm `__version__` advanced; if not, stop
  re-staging that version and log/flag it. *Done: `updater` gains
  `record_pending_update`/`read_pending_update`/`clear_pending_update`,
  `post_swap_version_ok`, a stale-version blocklist
  (`add_stale_update_version`/`read_stale_update_versions`), and
  `verify_post_swap_update` which ties them together. The GUI records the
  expected version before launching the swap (`_record_pending_update`) and
  verifies it at startup (`_verify_post_swap_update`); a version that failed to
  advance is blocklisted and `check_for_updates` refuses to re-stage it. Covered
  by `tests/test_updater.py`.*
- [x] **Lock down `parse_version`/`is_newer_version` with a documented contract
  + edge tests.** Document that only numeric dotted versions are supported and
  that comparison is strict-greater with zero-padding, then audit/extend the
  unit tests to cover the load-bearing edges: equal versions (no update),
  suffix-stripping (`0.6.0` vs `0.6.0-rc1`), trailing-zero padding (`0.6` vs
  `0.6.0`), and 4-part bumps (`0.6.0` vs `0.6.0.1`). *Done: a module-level
  version-contract comment in `updater.py` documents the numeric-only,
  zero-padded, strict-greater semantics and the suffix-stripping caveat (incl.
  the `-rc1` footgun where the trailing digit leaks in as a 4th component);
  `tests/test_updater.py` extends the `parse_version`/`is_newer_version`
  parametrize blocks to cover equal versions, pure-text vs digit-bearing
  suffixes, trailing-zero padding (both directions), and 4-part bumps.*
- [x] **Single bump point / optional auto-bump.** Document that `setup.py:8` is
  the one place a version is bumped and that a release *requires* bumping it
  first; optionally add a `tools/bump_version.py` (or a `-BumpPatch`/`-BumpMinor`
  switch) so the pipeline bumps + commits `setup.py` atomically with the tag,
  removing the "forgot to bump" failure mode the monotonicity guard above only
  *detects*. *Done: `tools/bump_version.py` reads/validates/rewrites the single
  `setup.py` version (`--part patch|minor|major`, `--set X.Y.Z`, `--show`,
  `--commit`), reusing `get_version`'s AST reader + strict validator;
  `Update-Release.ps1` gains a `-Bump patch|minor|major` switch that rewrites
  `setup.py` (and `--commit`s it, atomic with the release, unless `-DryRun`)
  before resolving the version. Covered by `tests/test_bump_version.py`.*
</content>
</invoke>
