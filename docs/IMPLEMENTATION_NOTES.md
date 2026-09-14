# Implementation Notes

This document is the active implementation backlog. Completed release/updater
notes are archived under `docs/archive/` so this file stays focused on work that
still needs a decision, implementation, or release proof.

Priority legend:

- P0: release blocker or must-keep safety guard.
- P1: required before relying on self-update or remote asset delivery.
- P2: useful support, security, maintenance, or size improvement.
- P3: conditional work that should wait for evidence.

## Release QA

- P0: Run a live desktop UI release review with representative copied item data.
  Cover startup, item paste/parse, supervised prediction, KNN overlay, settings
  save/reload, manual update check, and no-network startup.
- P0: Review the generated docs page in desktop and mobile widths after the
  normal release build. Verify the public download links, update manifest link,
  and first-viewport layout before publishing.
- P1: Add generated screenshots or another workflow artifact for the docs page
  and desktop smoke review. The checked-in manual release checklist exists at
  `docs/RELEASE_QA_CHECKLIST.md`.

## Self-Update And Asset Delivery

Current baseline:

- The app ships as a **portable one-dir bundle** (no installer):
  `build_app.bat` zips `dist/StashSage` into `docs/StashSageWindows.zip`
  (top-level `StashSage/` with `StashSage.exe` + `_internal/`). Users unzip and
  run the exe.
- Generated asset lookup prefers the writable per-user asset directory and
  falls back to bundled package assets. The bundle still ships `files`,
  `base_icons`, `super_models`, and `unsuper_models`.
- Release publishing emits `update-manifest.json`, uploads the portable
  Windows/Linux ZIPs and model assets, verifies hashes, and checks published
  asset URLs.
- Startup and manual update checks can sync verified assets. Windows can stage a
  verified newer **portable ZIP**, extract it, and on restart a `robocopy /MIR`
  helper swaps the new bundle over the running install in place and relaunches —
  no installer and no reinstall. The swap is skipped (with a download-page
  fallback) when the install dir is not writable.
- The updater is offline-safe, schema-gated, retry/backoff-capable, size-bounded
  while streaming downloads, zip-slip-guarded on extract, and prunes stale
  override/staged files.

Remaining work:

- P0: Keep release publishing verification green. The live
  `https://rheinze08.github.io/StashSage/update-manifest.json` endpoint must
  serve the current release manifest, and its `app_package_url` must point at
  the `StashSageWindows.zip` release asset with the matching SHA-256.
- P0: Keep bundled model/data payloads until first-run asset fetch UX is live
  and at least one public release has proven model delivery from
  `update-manifest.json`.
- P1: Surface the legal notice (`installer/legal_notice.txt`, formerly the
  installer license page) on the download site or inside the portable bundle now
  that there is no installer wizard to display it.
- P1: Add first-run and on-demand UX for generated asset bootstrap. The UI
  should make it clear when assets are bundled-only, when generated assets are
  current, when a sync is running, and when a sync failed but bundled fallback is
  still usable.
- P1: Add automated or semi-automated update smoke coverage for an empty
  generated asset directory, an already-current generated directory, a bundled
  copy that already matches the manifest, and a partial remote sync failure.
- P2: Cache an asset-state file with manifest version plus per-file
  size/mtime/SHA so the periodic update check does not re-hash every bundled
  model on each timer fire.
- P2: Add a scheduled or manually dispatched workflow that verifies the live
  GitHub Pages update manifest outside the full release script.
- P2: After updater bootstrap is live and proven, introduce an optional thin
  bundle build mode that omits heavy model/data `--add-data` entries. Make it
  non-default first, compare bundle size and startup behavior, then decide
  whether to flip the default.
- P2: Decide how to guide users who unzip the portable bundle into a
  non-writable location (e.g. `Program Files`). The in-place swap is skipped
  there with a download-page fallback; consider a first-run hint to extract
  somewhere writable, or an opt-in relocate-to-`%LOCALAPPDATA%` step.
- P2: Budget for code signing and manifest integrity if self-update becomes a
  primary distribution path. Package SHA-256 verification exists, but the
  manifest itself is not separately signed, and the portable exe is unsigned.
- P3: `update_channel` config is currently unused and `parse_version` ignores
  pre-release suffixes (`1.0.0-rc1` == `1.0.0`). Only wire this up if a
  non-`stable` channel or pre-release tags are introduced.
- P3: Linux has no self-apply path (`supports_app_package_apply` is win32
  only). Linux users get asset sync but are not offered an app binary update.

## Low Priority Performance

- P3: Consider moving `load_base_image_map()` until after the initial Tk window
  is created. This is only a perceived-startup improvement and touches the large
  GUI startup path, so keep it low priority unless startup profiling shows it is
  user-visible again.

## Consolidated Release And Updater Follow-Ups

These are the unresolved decisions retained from the two completed portable
update hardening plans. Their implementation history and original acceptance
criteria remain under `docs/archive/`.

- P0: Complete and record one human-driven, end-to-end update swap using two
  real Windows builds. Verify download, shutdown, swap, relaunch, cleanup,
  rollback behavior, and the case where another StashSage process is open.
- P1: Enforce single-instance ownership before applying an update so two running
  copies cannot race over the install directory.
- P1: Make the Windows swap helper wait on a process handle or another
  non-reusable identity rather than relying only on PID polling.
- P1: Add a Windows CI integration test that installs an old portable build,
  stages a newer archive, runs the real apply helper, and proves version advance
  plus `.new`, `.bak`, and staging cleanup.
- P1: Decide the writable-install-location experience. Options include keeping
  the current portable-folder warning or offering an opt-in relocation to
  `%LOCALAPPDATA%\StashSage` with shortcuts.
- P1: Finish first-run and on-demand asset-bootstrap UX before considering a
  default thin bundle without bundled models.
- P2: Plan Authenticode signing and manifest signing if self-update becomes the
  primary distribution path.
- P2: Decide whether legacy installer-era users need an explicit migration path
  to the portable update layout.
- P2: Document and either retain or remove the manifest `platforms` compatibility
  block; do not leave it as an accidental second source of package metadata.
- P2: Extend update telemetry/logging to distinguish staged, applied, rolled
  back, and failed outcomes without making telemetry mandatory.
- P2: Design Linux self-apply separately; Linux currently receives asset sync
  but not an in-place application update.
- P3: Consider a bundle self-integrity inventory only if partial-install or
  antivirus-removal incidents are observed. Avoid hashing the entire multi-GB
  install on every startup.
- P3: Pursue reproducible-build controls only after the release timing and cache
  work in [the update-release optimization review](../update_release_optimize_20260903.md)
  is measured.

## Consolidated Product And Model Follow-Ups

These are the unresolved or evidence-gated findings from the archived product
gaps audit.

- P0, retrain required: Correct weapon quality/rune deflation so local physical
  increases stack additively rather than multiplicatively. Keep offline matrix,
  runtime parsing, CraftOracle simulation, and documentation in parity.
- P2, retrain required: Decide whether corrupted, fractured, and sanctified item
  status flags should become model features. They are parsed today but excluded
  from the trained feature surface.
- P3: Add a measured outlier policy for CraftOracle catalog roll ceilings only
  if observed training data demonstrates that malformed or extreme rolls are
  influencing recommendations.
- P3: Verify Merchant search sale-type and price-sort behavior against the live
  trade API before changing query semantics.
- P3: Continue treating weapon categories as explicitly distinct feature
  branches; do not generalize the bow algorithm without parity tests for the
  target weapon type.

## Conditional Investigations

- P3: Use `STASHSAGE_PROFILE=1` before changing model formats or supervised
  inference mechanics.
- P3: Evaluate direct/native XGBoost inference or more compact model artifacts
  only if profiling shows supervised prediction dominates overlay latency.

## Archive

- Completed updater/release work moved to
  `docs/archive/implementation_completed_20260622.md`.
- Completed release QA checklist work moved to
  `docs/archive/implementation_completed_20260622.md`.
- Portable updater hardening history moved to
  `docs/archive/PORTABLE_UPDATE_HARDENING_PLAN.md`.
- Second-round executable/release hardening history moved to
  `docs/archive/EXE_PIPELINE_HARDENING_PLAN.md`.
- Resolved product-gap findings and their evidence moved to
  `docs/archive/PRODUCT_GAPS_AUDIT.md`.
