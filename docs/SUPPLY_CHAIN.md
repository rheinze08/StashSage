# Supply-chain hardening: hashed dependency locking

`requirements.txt` pins exact versions, but a version pin alone still trusts
whatever bytes PyPI serves for that version. A compromised or typosquatted
release could be installed into a bundle we ship to every client. Enforcing
hashes closes that gap: pip refuses any dependency whose downloaded bytes do not
match a hash recorded in the lock.

## Status: opt-in, wired but not yet enabled

The builds (`build_app.bat`, `tools/build_linux.sh`) already **prefer a
`requirements.lock` and install it with `--require-hashes` when it exists**.
Until that lock is generated, validated, and committed, the builds fall back to
`requirements.txt` exactly as before — so nothing changes yet.

Enabling it is a deliberate, validated step (below) because `--require-hashes`
is all-or-nothing: every requirement, including transitive ones, must be pinned
and hashed or the install hard-fails.

## Generating the lock

Use `pip-compile` (from `pip-tools`) with `--generate-hashes`. It resolves the
full transitive tree, pins every package, and records hashes for **all** of each
version's distributions (so a single lock covers Windows and Linux wheels):

```bash
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
```

Then validate the shape before trusting it:

```bash
python tools/check_requirements_lock.py requirements.lock
```

This confirms every requirement is pinned (`==`) and carries at least one
`--hash=`. It checks shape only — pip verifies the hashes against real bytes at
install time.

## Validating before you commit it

Because resolution can be platform-sensitive (environment markers, OS-only
wheels), **build on the real targets before committing the lock**:

1. Generate `requirements.lock`.
2. Run `tools/check_requirements_lock.py` — must pass.
3. Do a full Windows build (`build_app.bat`) and a Linux build
   (`tools/build_linux.sh`) with the lock in place. A missing transitive hash
   surfaces here as a pip `--require-hashes` failure.
4. Run the app / updater self-test to confirm the pinned set still works.
5. Only then commit `requirements.lock`.

Regenerate and re-validate the lock whenever `requirements.txt` changes.

## Rolling back

Delete (or rename) `requirements.lock` — the builds immediately revert to
`requirements.txt` with no other change. That is the escape hatch if a lock ever
blocks a legitimate build.
