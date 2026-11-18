# Release rollback / re-publish runbook

What to do when a published StashSage release is bad — the manifest points at a
broken/missing asset, the packaged app crashes on launch, or a hash no longer
matches. The goal is to stop new clients from adopting the bad build and steer
those already on it to a good one, without a fresh code change if possible.

The in-app updater only *pulls*; clients act on whatever the live
`update-manifest.json` says. So recovery is almost entirely about fixing that
manifest and the assets it references.

## 0. Confirm it's actually broken

```bash
python tools/verify_update_manifest.py \
  --manifest-url https://rheinze08.github.io/StashSage/update-manifest.json \
  --self-check --check-package-url --check-asset-urls --verify-package-hash
```

This is the same check the `verify-live-manifest` scheduled workflow runs. A
non-zero exit tells you *what* drifted (missing URL, hash mismatch, bad
structure). If it passes, the problem is likely in the app binary itself, not
the manifest — go to option B.

## A. The bad version's *assets* are broken (fastest fix)

A release asset was deleted, replaced, or corrupted, but the last-known-good
build is fine.

1. Re-upload the correct assets to the release under the **same tag** (this is
   what `-Republish` is for — it reuses the version and re-uploads assets
   without bumping the exe):
   ```powershell
   .\Update-Release.ps1 -Republish
   ```
   Installed clients only fetch the app *package* for a strictly newer
   `app_version`, so a republish refreshes model/data assets and the manifest
   but does **not** change anyone's exe.
2. Re-run the step-0 self-check until it passes.

## B. The bad version's *app binary* is broken (retire it)

The packaged app itself is bad (crashes, wrong behavior). You cannot un-ship it,
but you can retire it so clients stop trusting it and are told to upgrade, and
you can block the updater from staging it as a target.

1. Cut a **new, strictly-newer** release that is known good, and in the same
   run mark the bad version revoked and/or raise the support floor:
   ```powershell
   .\Update-Release.ps1 -Bump patch `
     -RevokedVersion 0.6.1 `
     -MinSupportedVersion 0.6.0
   ```
   - `-RevokedVersion` adds the bad version to `revoked_versions`. Clients on it
     see "This installed version was retired; install the latest StashSage", and
     the updater refuses to stage that version as an update target.
   - `-MinSupportedVersion` sets the floor below which clients are told they are
     too old. Use it when a whole range is bad.
2. Because the new release is strictly newer, clients auto-stage its package and
   offer **Restart & Update** — the actual remedy.
3. Verify (step 0) against the new live manifest.

## C. Nothing good to ship yet, but stop the bleeding

If you can't produce a good build immediately but must stop new adopters:

1. Roll the live manifest back to the previous good release's `update-manifest.json`
   (re-publish the prior version's manifest to Pages), or
2. Publish a manifest whose `min_supported_version` excludes the bad range so
   clients are steered to "get the latest" (the download page) rather than
   auto-updating into the bad build.

Then follow option B once a good build exists.

## After any recovery

- Run the step-0 self-check and confirm exit 0.
- Trigger the `verify-live-manifest` workflow manually (Actions →
  *Verify live update manifest* → *Run workflow*) to confirm the scheduled gate
  agrees.
- Note the incident: which version, what broke, which option you used.

## Reference

- `-Republish` / `-RevokedVersion` / `-MinSupportedVersion`: `Update-Release.ps1`
  parameter block.
- Client-side handling of revoked/unsupported: `updater.retirement_notice`
  (surfaced in the GUI status strip with a *Get latest* action).
- Manifest schema and the refuse-to-stage-a-revoked-target gate:
  `poe2trade/app/updater.py` (`parse_manifest`, `check_for_updates`).
