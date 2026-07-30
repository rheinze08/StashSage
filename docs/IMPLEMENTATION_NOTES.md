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
