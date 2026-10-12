"""Read the portable model-set contract without desktop config or ML imports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re


DEFAULT_SET_MARKER = "bundled_league.json"


def resolve_default_model_set(root: Path, available: Iterable[str], requested: str | None = None) -> str:
    """Choose a named default without consulting historical flat artifacts."""
    candidates = set(available)
    selected = str(requested or "").strip()
    marker = root / DEFAULT_SET_MARKER
    if not selected and marker.is_file():
        data = json.loads(marker.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("id"), str):
            raise ValueError(f"invalid default model-set marker: {marker}")
        selected = data["id"].strip()
        if not selected:
            raise ValueError(f"empty default model-set marker: {marker}")
    if selected:
        if selected not in candidates:
            raise ValueError(f"default model set {selected!r} is unavailable in {root}")
        return selected
    if len(candidates) == 1:
        return next(iter(candidates))
    if not candidates:
        raise ValueError(f"no named model sets available in {root}")
    raise ValueError(f"multiple model sets in {root}; configure {DEFAULT_SET_MARKER} or an explicit league")


@dataclass(frozen=True)
class ModelSet:
    id: str
    label: str
    league: str
    super_dir: Path
    unsuper_dir: Path

    def public(self) -> dict:
        return {"id": self.id, "label": self.label}


def read_model_set(directory: Path) -> ModelSet:
    """Reject incomplete sets before they can be advertised or published.

    This checks the portable metadata, not pickle contents. Release validation
    additionally checks scoring consistency; deployment smoke loads the models.
    """
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", directory.name) or directory.name == "default":
        raise ValueError("invalid or reserved model-set ID")
    root = directory.parent.resolve()
    for path in [directory, *directory.rglob("*")]:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("model set contains a link or escaping path")
    meta = json.loads((directory / "model_set.json").read_text(encoding="utf-8-sig"))
    if not isinstance(meta, dict) or meta.get("id", directory.name) != directory.name:
        raise ValueError("model-set metadata ID does not match directory")
    league = meta.get("league")
    label = meta.get("label", league)
    if not isinstance(league, str) or not league.strip() or not isinstance(label, str) or not label.strip():
        raise ValueError("model-set league and label must be nonempty strings")
    super_dir = directory.resolve() / "super_models"
    unsuper_dir = directory.resolve() / "unsuper_models"
    supervised = list(super_dir.glob("*_xgb_model.pkl"))
    neighbors = list(unsuper_dir.glob("*_knn_model.pkl"))
    if not supervised or not neighbors:
        raise ValueError("both supervised and KNN models are required")
    supervised_bases = {path.name.removesuffix("_xgb_model.pkl") for path in supervised}
    neighbor_bases = {path.name.removesuffix("_knn_model.pkl") for path in neighbors}
    if not supervised_bases.intersection(neighbor_bases):
        raise ValueError("at least one matching supervised/KNN category pair is required")
    required = ("category_segment_stats.json", "feature_importances_index.json", "craft_oracle_affix_catalog.json")
    for filename in required:
        payload = json.loads((super_dir / filename).read_text(encoding="utf-8-sig"))
        # Training writes feature importances as a list of model entries;
        # legacy exports used an object. The other catalogs remain objects.
        allowed = (dict, list) if filename == "feature_importances_index.json" else (dict,)
        if not isinstance(payload, allowed):
            raise ValueError(f"{filename} has an invalid document type")
    for model in supervised:
        sidecar = json.loads(model.with_suffix(".pricing.json").read_text(encoding="utf-8-sig"))
        if not isinstance(sidecar, dict) or str(sidecar.get("league", "")).casefold() != league.strip().casefold():
            raise ValueError(f"{model.name}: pricing league mismatch")
        for key in ("divine_to_exalt", "chaos_to_exalt"):
            rate = float(sidecar.get(key, 0))
            if not math.isfinite(rate) or rate <= 0:
                raise ValueError(f"{model.name}: invalid {key}")
    return ModelSet(directory.name, label.strip(), league.strip(), super_dir, unsuper_dir)


def discover_model_sets(root: Path) -> tuple[dict[str, ModelSet], dict[str, str]]:
    sets: dict[str, ModelSet] = {}
    errors: dict[str, str] = {}
    if not root.exists():
        return sets, errors
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        # Tracked .gitkeep-only namespace skeletons are not attempted model
        # sets. Once any generated payload appears, normal validation applies
        # and catches incomplete training runs before release.
        payload = [
            path for path in directory.rglob("*")
            if path.is_file() and path.name != ".gitkeep"
        ]
        if not payload:
            continue
        try:
            sets[directory.name] = read_model_set(directory)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors[directory.name] = str(exc)
    # IDs and labels share one input namespace. Reject all ambiguous entries.
    aliases: dict[str, set[str]] = {}
    for entry in sets.values():
        for value in (entry.id, entry.label, entry.league):
            aliases.setdefault(value.casefold(), set()).add(entry.id)
    for ids in aliases.values():
        if len(ids) > 1:
            for set_id in ids:
                errors[set_id] = "ambiguous model-set ID or league label"
    return {key: value for key, value in sets.items() if key not in errors}, errors
