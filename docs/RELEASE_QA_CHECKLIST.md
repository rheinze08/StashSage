# Release QA Checklist

Use this checklist before publishing a StashSage release. It covers the manual
P0 checks that cannot be trusted to unit tests alone.

## Build Inputs

- Confirm the release version and tag are correct.
- Confirm `python -m poe2trade.db validate --tests` passes on the release
  workspace.
- Confirm `python tools\validate_super_model_artifacts.py` passes.
- Confirm the generated supervised and unsupervised model artifacts are the
  intended release payload.

## Desktop App Smoke

- Start the desktop app from the release build.
- Confirm startup succeeds with the network disabled or unreachable.
- Paste representative copied item text for armour, jewellery, simple weapon,
  quiver, and jewel categories.
- Confirm parsed item name, base, category, and segment are correct.
- Confirm supervised prediction appears with the expected bucket styling.
- Confirm KNN or nearest-item overlay opens and uses the configured item count.
- Confirm settings can be saved and reloaded without restarting.
- Run the manual "Update App" check.
- Confirm a no-update, asset-update, or offline result is understandable and
  does not block normal app use.

## Generated Docs Page

- Run the normal release build path that renders `docs/index.html` from
  `index.html.j2`.
- Open `docs/index.html` at a desktop width.
- Open `docs/index.html` at a mobile width.
- Confirm the first viewport presents StashSage clearly and the next section is
  visible without awkward overlap.
- Confirm download links point at the intended GitHub release assets.
- Confirm the update manifest link points at the public GitHub Pages manifest.

## Release Manifest

- Confirm `Update-Release.ps1` verifies the live manifest before completion.
- Confirm the live `update-manifest.json` has the release `app_version`.
- Confirm `app_package_url` points at the `StashSageWindows.zip` release asset.
- Confirm `app_package_sha256` matches the uploaded portable ZIP.
- Confirm every listed model/data asset resolves and has the expected SHA-256.

## Downstream Repositories

- Confirm `StashSage` received the rendered public docs and public-safe runtime
  files.
- Confirm `StashSage_Serve` received shared runtime files and model artifacts.
- Confirm the serve deployment completed or is intentionally deferred.

## After Publishing

- Unzip and run the published portable bundle on a clean user profile when
  practical, and exercise the in-app "Update App" check / restart-swap.
- Launch the portable app and repeat one representative copied-item prediction.
- Confirm the app can still start after deleting the generated asset directory,
  proving bundled fallback remains usable.
