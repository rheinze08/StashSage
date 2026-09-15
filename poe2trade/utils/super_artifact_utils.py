from __future__ import annotations

import os
import datetime as _dt
import json
import shutil
import re
from pathlib import Path
from uuid import uuid4

from poe2trade import poe2trade_root


SUPER_SCORING_ARTIFACT_PATTERNS = (
    "*_scoring.json",
    "*_scoring.xlsx",
    "*_price_dists.png",
    "category_segment_stats.json",
    "score_super_report.pdf",
    "validation_report.pdf",
)
OPTIONAL_REPORT_ARTIFACT_PATTERNS = {
    "*_price_dists.png",
    "score_super_report.pdf",
    "validation_report.pdf",
}


def generated_super_models_dir() -> Path:
    return Path(poe2trade_root) / "generated" / "super_models"


def bundled_super_models_dir() -> Path:
    return Path(poe2trade_root) / "db" / "super_models"


def model_set_slug(league: str | None) -> str:
    """Directory-safe id for a league, e.g. "Forbidden Rites" -> forbidden-rites."""
    text = re.sub(r"[^a-z0-9]+", "-", str(league or "").strip().lower())
    return text.strip("-")


def training_league() -> str | None:
    """League the current conversion factors belong to, if it is known.

    Taken from the same manifest training stamps into each model's sidecar, so
    the set a run writes to and the economy its models record cannot disagree.
    """
    selected = os.environ.get("POE2TRADE_TRAINING_LEAGUE", "").strip()
    if selected:
        try:
            from poe2trade.db.league_paths import league_name
            return league_name(selected)
        except (ImportError, ValueError):
            return None
    try:
        from poe2trade.utils.pricing_conversions import current_conversion_manifest
        return current_conversion_manifest().get("league") or None
    except Exception:
        return None


def league_model_set_dir(
    league: str | None = None, bucket: str = "super_models", root: str | None = None
) -> Path:
    """Where a training run writes: db/model_sets/<slug>/<bucket>.

    ``root`` defaults to the package root but is taken explicitly by callers
    that resolve their own (train_utils patches its module-level
    ``poe2trade_root``, and the pipeline tests rely on that redirect).

    Falls back to the flat bundled directory when the league is unknown, so a
    run with no rates.json still produces artifacts somewhere the rest of the
    pipeline can find them rather than under a directory named "".
    """
    base = Path(root if root is not None else poe2trade_root)
    slug = model_set_slug(league if league is not None else training_league())
    if not slug:
        return base / "db" / bucket
    return base / "db" / "model_sets" / slug / bucket


def league_super_models_dir(league: str | None = None, root: str | None = None) -> Path:
    return league_model_set_dir(league, "super_models", root)


def league_unsuper_models_dir(league: str | None = None, root: str | None = None) -> Path:
    return league_model_set_dir(league, "unsuper_models", root)


MODEL_SET_METADATA_FILE = "model_set.json"


def write_model_set_metadata(league: str | None = None, root: str | None = None) -> Path | None:
    """Record the league a set was trained for, for display in the picker.

    Without this the UI can only show the directory id, and a slug is not a
    name a player recognises. Written at the set root because it describes the
    whole set, not just one bucket.
    """
    league = league if league is not None else training_league()
    slug = model_set_slug(league)
    if not slug:
        return None
    base = Path(root if root is not None else poe2trade_root)
    set_root = base / "db" / "model_sets" / slug
    set_root.mkdir(parents=True, exist_ok=True)
    path = set_root / MODEL_SET_METADATA_FILE
    existing: dict = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8-sig")) or {}
        except (OSError, ValueError):
            existing = {}
    existing.update({
        "schema_version": 1,
        "id": slug,
        "label": str(league),
        "league": str(league),
        "trained_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    })
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return path


def mirror_set_to_bundled(
    league: str | None = None, root: str | None = None,
    buckets: tuple[str, ...] = ("super_models", "unsuper_models"),
) -> int:
    """Explicit legacy export into db/<bucket>; not called by the pipeline.

    Kept for recovery/export to old consumers. Current builds, release gates,
    and downstream syncs use the named set directly.

    Every file is copied unconditionally: that is exactly what training did
    when it wrote here directly, so the mirror cannot leave a stale artifact
    behind from a different league. Files already in the flat directory that
    the set does not contain are left alone rather than deleted -- the same
    carry-over the in-place writes always had.

    Returns the number of files copied; 0 when the set already is the bundled
    directory (unknown league).
    """
    base = Path(root if root is not None else poe2trade_root)
    copied = 0
    for bucket in buckets:
        src = league_model_set_dir(league, bucket, root=str(base))
        dst = base / "db" / bucket
        if not src.is_dir() or src.resolve() == dst.resolve():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for artifact in sorted(src.iterdir()):
            if artifact.is_file() and artifact.name != ".gitkeep":
                shutil.copy2(artifact, dst / artifact.name)
                copied += 1
    return copied


def promote_super_scoring_artifacts(
    source_dir: str | Path | None = None,
    destination_dir: str | Path | None = None,
) -> list[Path]:
    """Promote generated scoring sidecars into the bundled super model dir.

    Trained model pickles and feature importances remain owned by db/super_models.
    Scoring sidecars are generated under generated/super_models, then promoted so
    release and Serve sync validate/export the same stats the runtime sees.
    """

    src = Path(source_dir) if source_dir is not None else generated_super_models_dir()
    dst = Path(destination_dir) if destination_dir is not None else bundled_super_models_dir()
    if not src.is_dir():
        return []

    # Collect the artifacts we will actually promote *first*. If the source has
    # none (e.g. a partial/aborted scoring run), do nothing: never delete the
    # bundled sidecars when there is no replacement to put in their place.
    sources: list[Path] = []
    incoming: set[str] = set()
    patterns_with_incoming: set[str] = set()
    for pattern in SUPER_SCORING_ARTIFACT_PATTERNS:
        for artifact in sorted(src.glob(pattern)):
            if artifact.is_file() and artifact.name not in incoming:
                sources.append(artifact)
                incoming.add(artifact.name)
                patterns_with_incoming.add(pattern)
    if not sources:
        return []

    dst.mkdir(parents=True, exist_ok=True)

    # Remove only stale sidecars that match our managed patterns but are not part
    # of the incoming set, so renamed/removed categories don't linger.
    for pattern in SUPER_SCORING_ARTIFACT_PATTERNS:
        if pattern not in patterns_with_incoming and pattern in OPTIONAL_REPORT_ARTIFACT_PATTERNS:
            continue
        for old in dst.glob(pattern):
            if old.is_file() and old.name not in incoming:
                old.unlink()

    # Copy each artifact atomically (temp + os.replace) so a mid-copy crash can
    # never leave a half-written sidecar that the runtime or validator reads.
    copied: list[Path] = []
    for artifact in sources:
        target = dst / artifact.name
        tmp = target.with_name(f"{target.name}.tmp-{os.getpid()}-{uuid4().hex}")
        try:
            shutil.copy2(artifact, tmp)
            os.replace(tmp, target)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
        copied.append(target)
    return copied
