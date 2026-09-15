"""League-scoped paths used by the offline database pipeline."""

from __future__ import annotations

import os
import re
from pathlib import Path

from poe2trade import poe2trade_root


TRAINING_LEAGUE_ENV = "POE2TRADE_TRAINING_LEAGUE"
TRAINING_FILES_ENV = "POE2TRADE_DB_FILES_DIR"
TRAINING_CONVERSIONS_ENV = "POE2TRADE_TRAINING_CONVERSIONS"
SUPPORTED_LEAGUES = {
    "forbidden-rites": "Forbidden Rites",
    "runes-of-aldur": "Runes of Aldur",
}
_SAFE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?$")


def validate_league_id(value: str) -> str:
    league_id = str(value or "").strip().lower().replace("_", "-")
    if not _SAFE_ID.fullmatch(league_id):
        raise ValueError(f"invalid league id: {value!r}")
    return league_id


def league_name(league_id: str) -> str:
    league_id = validate_league_id(league_id)
    return SUPPORTED_LEAGUES.get(
        league_id,
        " ".join(part.capitalize() for part in league_id.split("-")),
    )


def active_league_id() -> str | None:
    value = os.environ.get(TRAINING_LEAGUE_ENV, "").strip()
    return validate_league_id(value) if value else None


def files_root(
    league_id: str | None = None,
    *,
    package_root: str | Path | None = None,
    db_root: str | Path | None = None,
) -> Path:
    override = os.environ.get(TRAINING_FILES_ENV, "").strip()
    if override and league_id is None:
        return Path(override)
    selected = validate_league_id(league_id) if league_id else active_league_id()
    if package_root is not None and db_root is not None:
        raise ValueError("pass package_root or db_root, not both")
    root = (
        Path(db_root) / "files"
        if db_root is not None
        else Path(package_root if package_root is not None else poe2trade_root) / "db" / "files"
    )
    return root / selected if selected else root


def model_set_root(league_id: str | None = None) -> Path:
    selected = validate_league_id(league_id) if league_id else active_league_id()
    if not selected:
        raise ValueError("a league is required for a model-set path")
    return Path(poe2trade_root) / "db" / "model_sets" / selected


def file_sets_root(league_id: str | None = None) -> Path:
    selected = validate_league_id(league_id) if league_id else active_league_id()
    root = Path(poe2trade_root) / "db" / "file_sets_to_combine"
    return root / selected if selected else root


def training_conversions_path(league_id: str | None = None) -> Path:
    """Return the immutable rate manifest consumed by one league run."""
    return files_root(league_id) / "currency_conversions.json"


def available_leagues() -> list[str]:
    root = Path(poe2trade_root) / "db" / "files"
    if not root.is_dir():
        return []
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and entry.name in SUPPORTED_LEAGUES
    )


def configure_training_league(league_id: str) -> str:
    """Select one league and direct every pipeline artifact to its namespace."""
    selected = validate_league_id(league_id)
    source = files_root(selected)
    if not source.is_dir():
        raise ValueError(f"league input directory does not exist: {source}")
    output = model_set_root(selected)
    os.environ[TRAINING_LEAGUE_ENV] = selected
    os.environ[TRAINING_FILES_ENV] = str(source)
    os.environ[TRAINING_CONVERSIONS_ENV] = str(training_conversions_path(selected))
    os.environ["POE_LEAGUE"] = league_name(selected)
    os.environ["STASHSAGE_SUPER_MODELS_DIR"] = str(output / "super_models")
    os.environ["STASHSAGE_UNSUPER_MODELS_DIR"] = str(output / "unsuper_models")
    os.environ["STASHSAGE_SCORING_OUTPUT_DIR"] = str(output / "super_models")
    return selected
