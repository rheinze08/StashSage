# Release-Readiness Environment

`python -m poe2trade.db test` is the release-readiness gate. `Update-Release.ps1`
runs it before building, and developers run it before committing. Git gives a
checkout neither of the two things the gate needs beyond the code:

1. an interpreter whose environment holds every pinned package, and
2. the league model sets, which are git-ignored.

A checkout that lacks either now fails in seconds, and the message names
exactly what is missing. This page names what the gate needs, where each piece
comes from, and how to provide it.

## What the gate runs

In this order:

| Stage | Command | Time |
|---|---|---|
| Release environment check | `tools/check_release_env.py` | under a second; runs before the pipeline imports |
| League model artifact validation | `tools/validate_model_sets.py` | seconds |
| Test suite | `python -m pytest -q` | minutes |
| Base image/icon freshness | `python -m poe2trade.utils.get_icon_utils --check` | seconds |

The gate stops at the first failure. `Update-Release.ps1` also runs the
environment check on its own before the version bump commit. After the gate it
runs `tools/validate_model_sets.py --require-set forbidden-rites --require-set
runes-of-aldur`.

## Interpreter

The release scripts resolve their interpreter with `Resolve-Python` in
`tools/ReleaseCommon.ps1`. This applies to `Update-Release.ps1`,
`tools/Sync-Downstream.ps1` and `build_android.ps1`. They try, in order:

1. `.venv\Scripts\python.exe` in the checkout,
2. `venv\Scripts\python.exe`,
3. whatever `python` is first on `PATH`.

They print the one they chose: `[*] Using interpreter: ...`, or
`[*] No venv found; using 'python' from PATH`. Run directly, the gate checks
whichever interpreter runs it, for example
`.\.venv\Scripts\python.exe -m poe2trade.db test`.

- The release machine's checkout uses its `.venv`, which is Python 3.12 (see
  [AGENTS.md](../AGENTS.md)). The supported range is 3.11 to 3.13.
- A separate clone has no `.venv`, so the release scripts fall back to `PATH`.
  That is usually a system-wide Python without this project's packages. Give
  such a clone its own venv:

  ```powershell
  py -3.12 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  ```

## Required packages

The environment check passes only when both of these hold:

- every pin in `requirements.txt` that applies to the platform is installed,
  and
- no distribution that shadows a stdlib module is installed. Currently that
  means `asyncio`: the 3.4.3 PyPI backport replaces the stdlib module and once
  broke training.

A version that differs from its pin is only a warning, because the builds
re-sync the pins.

Some pins are easy to miss because the desktop app never imports them. Only
the research and outreach code and their tests do:

- `boto3` (research dataset storage),
- `dnspython` (outreach domain checks),
- `psycopg[binary]` (research and outreach PostgreSQL).

An interpreter that runs the app can therefore still fail the gate.

When the check fails, it lists every problem and prints a fix command for each
kind of problem, with the full interpreter path:

```text
[!] Release environment is incomplete for C:\...\python.exe (3 problem(s)):
      - missing: boto3==1.43.108 is in requirements.txt but not installed
      - missing: dnspython==2.8.0 is in requirements.txt but not installed
      - stdlib shadow: the 'asyncio' distribution is installed (3.4.3); it shadows the stdlib module of the same name — uninstall it
      Fix: "C:\...\python.exe" -m pip install -r "...\requirements.txt"
      Fix: "C:\...\python.exe" -m pip uninstall -y asyncio
```

Run both commands with the interpreter the check names. Installing the missing
packages alone leaves a shadowing distribution in place, and the next run
stops at the same check.

## League model artifacts

### What the gate requires

A model set lives in `poe2trade/db/model_sets/<set>/` and holds:

- `model_set.json`,
- `super_models/`, with `*_xgb_model.pkl` and its `*_xgb_model.pricing.json`,
  `*_scoring.json`, `category_segment_stats.json`,
  `feature_importances_index.json` and `craft_oracle_affix_catalog.json`,
- `unsuper_models/`, with `*_knn_model.pkl`.

A release also ships a `*_price_dists.png` chart per model. The gate does not
check those.

Only the `.gitkeep` skeletons and `bundled_league.json` are tracked, so every
fresh clone has none of these files.

`python -m poe2trade.db test` requires the default set, the one
`poe2trade/db/model_sets/bundled_league.json` names (currently
`forbidden-rites`). `Update-Release.ps1` also requires `runes-of-aldur`.

### Where they are produced and stored

- **Produced:** by training. For example,
  `python -m poe2trade.db parse matrix train_super score_super train_unsuper
  <categories> --league forbidden-rites`, or a homeserver training sweep
  (`homeserver/train_sweep.py`), writes `poe2trade/db/model_sets/<league>/`
  in the checkout that trains.
- **Stored, newest:** in that checkout. A release ships the release machine's
  copy. A set newer than the last release exists only there until a release
  publishes it.
- **Stored, published:** every release uploads each file of every set as its
  own GitHub release asset on `rheinze08/StashSage`, named
  `<set>__<subdirectory>__<file>`. The tracked `docs/update-manifest.json` pins
  each file by path, size and SHA-256. Installed apps update their models from
  that list. For v0.5.31, `forbidden-rites` is 319 files (618.1 MB) and
  `runes-of-aldur` is 376 files (875.6 MB).

### Populating a checkout

Any checkout other than the release machine can provision the published sets
from that manifest:

```powershell
python tools\fetch_model_sets.py                                  # the default set
python tools\fetch_model_sets.py forbidden-rites runes-of-aldur   # both sets Update-Release requires
python tools\fetch_model_sets.py --dry-run forbidden-rites        # counts and sizes only
```

This applies to agent and build-thread clones, CI, and a second checkout. The
tool works as follows:

- It downloads each file the manifest lists for the set.
- It checks each file's size and SHA-256 before moving it into place.
- It keeps files that already match, so an interrupted run resumes.
- It refuses the whole set, before writing anything, if the set directory
  holds any file the manifest does not list or lists with different bytes.
  Those are local artifacts, trained here or taken from another release, and
  the tool never overwrites, mixes or deletes them.

A fetched set is the last release's set, byte for byte. It is the right input
for checking that code passes the gate against what shipped. It is not a
release input: a release ships what the release machine trained.

### Reading a model-validation failure

When a required set is unavailable, the gate prints a `[MISSING]` line for
every absent file and the fetch command for the sets involved:

```text
[ERROR] default model set 'forbidden-rites' is unavailable in ...\poe2trade\db\model_sets
[MISSING] forbidden-rites: 319 artifact(s) absent from this checkout (319 file(s), 618.1 MB, as the v0.5.31 release published them):
[MISSING]   poe2trade/db/model_sets/forbidden-rites/model_set.json
...
[HINT]   python tools/fetch_model_sets.py forbidden-rites
```

The list depends on the state of the set:

- **No files at all**, the fresh-clone state: the list is exactly the files the
  tracked manifest publishes for that set.
- **Some files present**: the list holds only the files every set must have. A
  newer training run can cover different categories than the last release, so
  the last release's file list would not be a requirement there.
