"""Single source of truth for pipeline-generated (derived) artifacts.

These are the file classes produced by the ``poe2trade.db`` pipeline stages.
The ``clean`` action (see ``poe2trade/db/__main__.py``) deletes them to force a
fresh rebuild.

The glob patterns here mirror the corresponding ``.gitignore`` rules, but the
default (safe) set is intentionally MORE conservative than ``.gitignore``: raw
scraped item JSON under ``db/files/<Category>/*.json`` is gitignored yet
expensive to reacquire (a full Selenium scrape), so it is NOT part of the
derived set. It is only removed when the caller explicitly opts in via
``--clean-raw`` (``RAW_INPUT_GLOBS``).

Patterns are relative to ``poe2trade_root`` (the ``poe2trade/`` package dir).
Keep them in sync with ``.gitignore``; ``tests/test_db_artifacts.py`` asserts
they do not drift.
"""

from pathlib import Path

from poe2trade import poe2trade_root

_ROOT = Path(poe2trade_root)

# Derived artifacts safe to delete on a default ``clean``.
DERIVED_ARTIFACT_GLOBS = (
    "db/files/**/*_agg_parsed*",   # parse/matrix output (parquet + xlsx)
    "generated/super_models/*",    # scoring json/xlsx, price-dist png, report pdf
    "db/super_models/*",           # trained supervised model pickles/summaries
    "db/unsuper_models/*",         # trained KNN bundles
    "logs/db_pipeline_runs/*",     # per-run stage transcripts
)

# Raw pipeline INPUT removed only when ``clean --clean-raw`` is requested.
# Expensive to reacquire; gitignored but never deleted by the safe tier.
RAW_INPUT_GLOBS = (
    "db/files/**/*.json",          # raw scraped per-item JSON, including league roots
    "db/file_sets_to_combine/*",   # scrape-batch staging dirs
)

# Never delete these even when a glob would otherwise match them. ``.gitkeep``
# placeholders keep the (gitignored) model/staging dirs present locally.
_PROTECTED_NAMES = frozenset({".gitkeep"})


def iter_artifact_paths(
    include_raw: bool = False,
    root: Path | None = None,
    league_id: str | None = None,
) -> list[Path]:
    """Return existing artifact paths to delete, deduplicated and sorted.

    ``include_raw`` adds :data:`RAW_INPUT_GLOBS` to the default derived set.
    ``root`` overrides the base directory (used in tests).
    """
    base = root or _ROOT
    if league_id:
        globs = [
            f"db/files/{league_id}/**/*_agg_parsed*",
            f"db/model_sets/{league_id}/super_models/*",
            f"db/model_sets/{league_id}/unsuper_models/*",
            f"logs/db_pipeline_runs/{league_id}/*",
        ]
        if include_raw:
            globs += [
                f"db/files/{league_id}/**/*.json",
                f"db/file_sets_to_combine/{league_id}/*",
            ]
    else:
        globs = list(DERIVED_ARTIFACT_GLOBS)
        if include_raw:
            globs += list(RAW_INPUT_GLOBS)

    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in globs:
        for path in base.glob(pattern):
            if path.name in _PROTECTED_NAMES:
                continue
            if path in seen:
                continue
            seen.add(path)
            out.append(path)
    return sorted(out)
