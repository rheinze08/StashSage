# Implementation Notes

This document is the single backlog for implementation notes that are still
relevant after the older root-level tracker files were consolidated.

## Release QA

- Review the desktop UI in a live app session with representative copied item
  data.
- Review the generated docs page in desktop and mobile widths after the normal
  release build.

## Self-Update And Asset Delivery

The local app-side updater foundation exists: generated asset lookup prefers
the writable per-user asset directory, update checks are disabled until a
manifest URL is configured, the installer is per-user, and release publishing
uploads the raw installer executable for the updater.

Remaining work:

- Add the server-side manifest endpoint, for example
  `GET /assets/manifest.json`, in the serving repo.
- Generate manifest entries from the verified model/data artifacts synced into
  the serving repo.
- Host large model and installer bytes on GitHub release assets, object
  storage, or a CDN rather than PythonAnywhere.
- Point manifest app updates at the raw `StashSageInstaller.exe` release asset.
- Keep bundled model/data payloads until the manifest endpoint and first-run
  asset fetch UX are live.
- After updater bootstrap is live, remove the heavy model/data `--add-data`
  bundle entries from installer builds.
- Add first-run and on-demand UX for an empty generated asset directory.
- Decide whether to handle migration from legacy admin installs in Program
  Files. Current per-user installs upgrade cleanly; old admin installs may need
  manual uninstall unless an elevated cross-hive migration step is added.
- Budget for code signing and manifest integrity if self-update becomes a
  primary distribution path.

## Low Priority Performance

- Consider moving `load_base_image_map()` until after the initial Tk window is
  created. This is only a perceived-startup improvement and touches the large
  GUI startup path, so keep it low priority unless startup profiling shows it is
  user-visible again.

## Conditional Investigations

- Use `STASHSAGE_PROFILE=1` before changing model formats or supervised
  inference mechanics.
- Evaluate direct/native XGBoost inference or more compact model artifacts only
  if profiling shows supervised prediction dominates overlay latency.

## Test Backlog

- Consider one Python-level integration test for the promote-then-validate
  release gate: create minimal consistent generated supervised artifacts,
  promote them with `promote_super_scoring_artifacts()`, then validate the
  destination with `validate_super_model_artifacts.validate()`.
