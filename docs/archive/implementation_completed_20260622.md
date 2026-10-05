# Completed Implementation Notes - 2026-06-22

These items were moved out of `docs/IMPLEMENTATION_NOTES.md` after the active
backlog was refreshed. They describe completed updater, asset-delivery, and
release-pipeline work that is still useful historical context.

## Self-Update And Asset Delivery

- Generated asset lookup prefers the writable per-user asset directory and
  falls back to bundled package assets.
- The default config points at the GitHub Pages `update-manifest.json`.
- The installer is per-user.
- Release publishing uploads the raw installer executable and the manifest
  consumed by installed clients.
- The release pipeline emits model asset entries into `update-manifest.json`,
  uploads those model files as GitHub release assets, and verifies the published
  asset URLs before the release completes.
- Automatic startup checks can stage a verified newer installer and ask the
  user whether to install it after StashSage exits.
- The background check re-arms itself on a periodic timer, so a long-running
  session eventually notices a new release without a restart. The prompt-once-
  per-version guard still applies.
- The manifest parser enforces a `schema_version` gate: a manifest newer than
  the client understands degrades to "no update" instead of being misread.
- Staging a newer installer prunes older versioned staging dirs so verified
  installers do not accumulate on disk.
- Per-file asset resolution is used for `base_icons` icon lookup and
  `unsuper_models` overlay-column probing. A partial updater override no longer
  hides bundled sibling files.
- Delivered scoring-JSON sidecars are no longer rewritten in place: runtime
  compaction skips the writable override dir, so an updater-delivered file keeps
  the exact bytes the manifest SHA was computed over.
- `download_to` enforces manifest `size` as an upper bound while streaming, so a
  wrong or hostile URL is aborted before it can fill the disk.
- After each check, override files a bucket no longer lists in the manifest are
  pruned. Buckets with no manifest entry are left untouched.
- `write_update_manifest.py` emits verified per-file `assets[]` from a local
  `--assets-root` plus `--assets-base-url`.
- `verify_update_manifest.py` validates asset entries, including bucket
  allow-list, safe relative paths, HTTPS URLs, duplicates, and optional asset
  URL checks.
- `fetch_manifest` and `download_to` have bounded retry/backoff behavior. This
  was previously listed as remaining P2 work.

## Release Pipeline

- `Update-Release.ps1` is the release source of truth.
- The release pipeline builds the installer and ZIP, renders `docs/index.html`,
  writes `update-manifest.json`, uploads installer/model assets, verifies
  uploaded hashes, syncs downstream repositories, and verifies the live manifest.
- `tools/Sync-Downstream.ps1` exports public-safe content to `StashSage` and
  shared ML/runtime assets to `StashSage_Serve`.
- The serve sync validates supervised scoring sidecars and
  `category_segment_stats.json` before pushing model artifacts.

## Release QA

- A checked-in manual release QA checklist exists at
  `docs/RELEASE_QA_CHECKLIST.md`. The remaining active workflow need is
  automated or generated screenshot evidence for the docs/app smoke review.

## Tests

- The promote-then-validate release-gate integration test exists in
  `tests/test_super_artifact_utils.py`.
- Updater tests cover manifest parsing, asset planning, verified downloads,
  staging behavior, schema gating, stale override pruning, and retry behavior.
