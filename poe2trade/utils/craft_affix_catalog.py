"""Build the intrinsic ordinary-explicit affix catalog used by Craft Oracle.

The pricing pipeline intentionally models effective item totals.  Craft Oracle
instead needs the ceiling of one underlying ordinary affix.  Structured item
payloads retain that contributor data in ``explicitMods[*].mods`` even when
the parent description has already combined transformed modifiers and local
magnitude effects.

Catalog collection never mutates parsed item rows or model feature matrices.
The runtime reader exposes only the resulting validated intrinsic maxima.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping

from poe2trade import poe2trade_root
from poe2trade.db.categories import model_category_name
from poe2trade.utils.parse_utils import (
    _expand_and_clean_mod_list,
    normalize_item_category,
    parse_rolled_mod,
)


CATALOG_SCHEMA_VERSION = 1
CATALOG_FILENAME = "craft_oracle_affix_catalog.json"
MIN_CATEGORY_ITEMS_SEEN = 10
MIN_CATEGORY_ACCEPTED_CONTRIBUTORS = 10
MIN_PATTERN_OBSERVATIONS = 2
MIN_USABLE_EVIDENCE_RATE = 0.50
CATALOG_AUDIT_STATISTICS = (
    "items_seen",
    "parent_entries_seen",
    "accepted_contributors",
    "skipped_legacy_entries",
    "skipped_special_domains",
    "skipped_missing_contributors",
    "skipped_nonordinary_tiers",
    "skipped_missing_magnitudes",
)
DEFAULT_CATALOG_PATH = (
    Path(poe2trade_root) / "db" / "super_models" / CATALOG_FILENAME
)

_ORDINARY_TIER_RE = re.compile(r"^(?P<side>[PS])(?P<number>[1-9]\d*)$", re.I)
_SPECIAL_FLAGS = frozenset({"crafted", "desecrated", "descrated", "fractured"})


class AffixCatalogError(ValueError):
    """Raised when a catalog cannot be read or safely updated."""


@dataclass(frozen=True)
class AffixCatalogTierEntry:
    """Validated intrinsic roll metadata for one observed ordinary affix tier."""

    maximum_roll: float
    affix_sides: tuple[str, ...]
    tier: str
    required_level: int | None
    observations: int
    affix_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class AffixCatalogEntry:
    """Validated runtime metadata for one ordinary explicit-affix pattern."""

    pattern: str
    maximum_roll: float
    affix_sides: tuple[str, ...]
    winning_tier: str
    required_level: int | None
    observations: int
    tiers: tuple[AffixCatalogTierEntry, ...] = ()
    affix_names: tuple[str, ...] = ()


def catalog_category_key(category: str) -> str:
    """Return the canonical key shared by training folders and runtime models."""
    return normalize_item_category(model_category_name(str(category or "")))


def normalize_affix_name(value: Any) -> str:
    """Return the stable identity shared by structured data and copy headers."""
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _ordinary_explicit_parent(entry: Mapping[str, Any]) -> bool:
    flags = entry.get("flags")
    if isinstance(flags, Mapping) and any(bool(flags.get(name)) for name in _SPECIAL_FLAGS):
        return False
    domain = str(entry.get("domain") or "").strip().lower()
    if domain:
        return domain == "explicit"
    stat_hash = str(entry.get("hash") or "").strip().lower()
    return stat_hash.startswith("stat.explicit.") or ".explicit." in stat_hash


def _intrinsic_value(magnitudes: Any, *, pattern_count: int = 1) -> float | None:
    """Return the pipeline scalar for one contributor's intrinsic maxima.

    Averaging the first and last maximum matches ``parse_rolled_mod``'s scalar
    convention for a two-ended range such as ``Adds # to # Fire Damage``. It is
    only meaningful when the magnitudes describe *one* stat. A contributor that
    supplies several distinct stats to several canonical patterns cannot be
    reduced to one scalar, so it is rejected rather than averaged into a value
    that belongs to neither pattern.
    """
    if not isinstance(magnitudes, list):
        return None
    maxima: list[float] = []
    for magnitude in magnitudes:
        if not isinstance(magnitude, Mapping):
            continue
        value = _finite_float(magnitude.get("max"))
        if value is not None:
            maxima.append(value)
    if not maxima:
        return None
    if pattern_count > 1 and len(maxima) > 1:
        return None
    value = (maxima[0] + maxima[-1]) / 2.0
    return value if value > 0 else None


@dataclass
class _TierAccumulator:
    maximum_roll: float = 0.0
    required_level: int | None = None
    observations: int = 0
    affix_names: set[str] = field(default_factory=set)

    def observe(
        self,
        value: float,
        required_level: int | None,
        affix_name: str,
    ) -> None:
        self.observations += 1
        if affix_name:
            self.affix_names.add(affix_name)
        candidate_level = required_level if required_level is not None else math.inf
        winner_level = (
            self.required_level if self.required_level is not None else math.inf
        )
        if value > self.maximum_roll or (
            value == self.maximum_roll and candidate_level < winner_level
        ):
            self.maximum_roll = value
            self.required_level = required_level

    def as_dict(self, tier: str, allowed_names: set[str]) -> dict[str, Any]:
        out: dict[str, Any] = {
            "maximum_roll": round(float(self.maximum_roll), 4),
            "tier": tier,
            "observations": int(self.observations),
            "affix_names": sorted(self.affix_names.intersection(allowed_names)),
        }
        if self.required_level is not None:
            out["required_level"] = self.required_level
        return out


@dataclass
class _PatternAccumulator:
    maximum_roll: float = 0.0
    winning_tier: str = ""
    required_level: int | None = None
    observations: int = 0
    affix_sides: set[str] = field(default_factory=set)
    tiers: dict[str, _TierAccumulator] = field(default_factory=dict)
    affix_names: set[str] = field(default_factory=set)

    def observe(self, value: float, tier: str, level: Any, affix_name: str) -> None:
        match = _ORDINARY_TIER_RE.fullmatch(tier)
        if match is None:
            return
        tier = tier.upper()
        self.observations += 1
        self.affix_sides.add("prefix" if match.group("side").upper() == "P" else "suffix")
        if affix_name:
            self.affix_names.add(affix_name)
        level_value = _finite_float(level)
        required_level = int(level_value) if level_value is not None else None
        self.tiers.setdefault(tier, _TierAccumulator()).observe(
            value,
            required_level,
            affix_name,
        )
        candidate_key = (tier, required_level if required_level is not None else math.inf)
        winner_key = (
            self.winning_tier or "~",
            self.required_level if self.required_level is not None else math.inf,
        )
        if value > self.maximum_roll or (
            value == self.maximum_roll and candidate_key < winner_key
        ):
            self.maximum_roll = value
            self.winning_tier = tier
            self.required_level = required_level

    def as_dict(self, allowed_names: set[str]) -> dict[str, Any]:
        out: dict[str, Any] = {
            "maximum_roll": round(float(self.maximum_roll), 4),
            "affix_sides": sorted(self.affix_sides),
            "winning_tier": self.winning_tier,
            "observations": int(self.observations),
            "affix_names": sorted(self.affix_names.intersection(allowed_names)),
            "tiers": [
                self.tiers[tier].as_dict(tier, allowed_names)
                for tier in sorted(self.tiers)
            ],
        }
        if self.required_level is not None:
            out["required_level"] = self.required_level
        return out


@dataclass
class AffixCatalogCollector:
    """Collect intrinsic ordinary-explicit maxima for one canonical category."""

    category: str
    _patterns: dict[str, _PatternAccumulator] = field(default_factory=dict)
    _identity_signatures: dict[str, set[tuple[str, ...]]] = field(
        default_factory=dict
    )
    _statistics: dict[str, int] = field(default_factory=lambda: {
        "items_seen": 0,
        "parent_entries_seen": 0,
        "accepted_contributors": 0,
        "skipped_legacy_entries": 0,
        "skipped_special_domains": 0,
        "skipped_missing_contributors": 0,
        "skipped_nonordinary_tiers": 0,
        "skipped_missing_magnitudes": 0,
    })

    def __post_init__(self) -> None:
        self.category = catalog_category_key(self.category)

    def observe_item(self, item: Mapping[str, Any]) -> None:
        """Observe one structured item without mutating it."""
        if not isinstance(item, Mapping):
            return
        self._statistics["items_seen"] += 1
        entries = item.get("explicitMods") or []
        if not isinstance(entries, list):
            return
        for entry in entries:
            self._statistics["parent_entries_seen"] += 1
            if not isinstance(entry, Mapping):
                self._statistics["skipped_legacy_entries"] += 1
                continue
            if not _ordinary_explicit_parent(entry):
                self._statistics["skipped_special_domains"] += 1
                continue
            description = entry.get("description") or entry.get("text") or entry.get("name")
            contributors = entry.get("mods")
            if not isinstance(description, str) or not isinstance(contributors, list) or not contributors:
                self._statistics["skipped_missing_contributors"] += 1
                continue
            descriptions = _expand_and_clean_mod_list([description])
            patterns = {
                str(parse_rolled_mod(text)[0]).strip().lower()
                for text in descriptions
                if isinstance(text, str) and text.strip()
            }
            patterns.discard("")
            if not patterns:
                self._statistics["skipped_missing_contributors"] += len(contributors)
                continue
            for contributor in contributors:
                if not isinstance(contributor, Mapping):
                    self._statistics["skipped_missing_contributors"] += 1
                    continue
                tier = str(contributor.get("tier") or "").strip().upper()
                if _ORDINARY_TIER_RE.fullmatch(tier) is None:
                    self._statistics["skipped_nonordinary_tiers"] += 1
                    continue
                value = _intrinsic_value(
                    contributor.get("magnitudes"),
                    pattern_count=len(patterns),
                )
                if value is None:
                    self._statistics["skipped_missing_magnitudes"] += 1
                    continue
                affix_name = normalize_affix_name(contributor.get("name"))
                if affix_name and len(contributors) == 1:
                    self._identity_signatures.setdefault(affix_name, set()).add(
                        tuple(sorted(patterns))
                    )
                else:
                    # A flattened parent with multiple contributors cannot
                    # prove which native affix name produced which final stat.
                    affix_name = ""
                for pattern in patterns:
                    self._patterns.setdefault(pattern, _PatternAccumulator()).observe(
                        value,
                        tier,
                        contributor.get("level"),
                        affix_name,
                    )
                self._statistics["accepted_contributors"] += 1

    def category_payload(
        self,
        *,
        min_pattern_observations: int = 1,
    ) -> dict[str, Any]:
        """Return category data, optionally excluding weak pattern evidence.

        Collection keeps every observation so parse-time diagnostics and tests
        can inspect the raw result.  Production callers pass the shared release
        threshold so singleton patterns never become Craft Oracle candidates.
        """
        stable_names = {
            name
            for name, signatures in self._identity_signatures.items()
            if len(signatures) == 1
        }
        return {
            "patterns": {
                pattern: self._patterns[pattern].as_dict(stable_names)
                for pattern in sorted(self._patterns)
                if self._patterns[pattern].observations >= min_pattern_observations
            },
            "statistics": {
                key: int(self._statistics[key])
                for key in sorted(self._statistics)
            },
        }


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    """Load an existing catalog or return a new empty payload."""
    path = Path(path)
    if not path.is_file():
        return {"schema_version": CATALOG_SCHEMA_VERSION, "categories": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AffixCatalogError(f"Could not read affix catalog {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AffixCatalogError(f"Affix catalog {path} must contain an object.")
    if payload.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise AffixCatalogError(
            f"Affix catalog {path} has unsupported schema {payload.get('schema_version')!r}."
        )
    if not isinstance(payload.get("categories"), dict):
        raise AffixCatalogError(f"Affix catalog {path} has no categories object.")
    return payload


def category_readiness_issues(category_payload: Mapping[str, Any]) -> list[str]:
    """Return evidence/readiness failures for one catalog category payload."""
    issues: list[str] = []
    statistics = category_payload.get("statistics")
    if not isinstance(statistics, Mapping):
        return ["has no audit statistics object"]

    values: dict[str, int] = {}
    for name in CATALOG_AUDIT_STATISTICS:
        value = statistics.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            issues.append(f"has invalid audit statistic {name}={value!r}")
        else:
            values[name] = value
    if issues:
        return issues

    if values["items_seen"] < MIN_CATEGORY_ITEMS_SEEN:
        issues.append(
            f"has only {values['items_seen']} items; minimum is {MIN_CATEGORY_ITEMS_SEEN}"
        )
    if values["accepted_contributors"] < MIN_CATEGORY_ACCEPTED_CONTRIBUTORS:
        issues.append(
            "has only "
            f"{values['accepted_contributors']} accepted contributors; minimum is "
            f"{MIN_CATEGORY_ACCEPTED_CONTRIBUTORS}"
        )

    evidence_total = (
        values["accepted_contributors"]
        + values["skipped_legacy_entries"]
        + values["skipped_missing_contributors"]
        + values["skipped_missing_magnitudes"]
    )
    usable_rate = (
        values["accepted_contributors"] / evidence_total
        if evidence_total
        else 0.0
    )
    if usable_rate < MIN_USABLE_EVIDENCE_RATE:
        issues.append(
            f"has {usable_rate:.1%} usable structured evidence; minimum is "
            f"{MIN_USABLE_EVIDENCE_RATE:.0%}"
        )

    patterns = category_payload.get("patterns")
    if not isinstance(patterns, Mapping) or not patterns:
        issues.append("has no patterns")
        return issues
    for pattern, entry in patterns.items():
        observations = entry.get("observations") if isinstance(entry, Mapping) else None
        if (
            isinstance(observations, bool)
            or not isinstance(observations, int)
            or observations < MIN_PATTERN_OBSERVATIONS
        ):
            issues.append(
                f"pattern {pattern!r} has {observations!r} observations; minimum is "
                f"{MIN_PATTERN_OBSERVATIONS}"
            )
    return issues


def category_audit_summary(category: str, category_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic report row for parse-stage training logs."""
    statistics = category_payload.get("statistics")
    stats = statistics if isinstance(statistics, Mapping) else {}
    stat_values: dict[str, int] = {}
    for name in CATALOG_AUDIT_STATISTICS:
        value = stats.get(name)
        stat_values[name] = (
            value
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0
            else 0
        )
    patterns = category_payload.get("patterns")
    pattern_entries = patterns if isinstance(patterns, Mapping) else {}
    tier_count = 0
    affix_names: set[str] = set()
    for entry in pattern_entries.values():
        if not isinstance(entry, Mapping):
            continue
        tiers = entry.get("tiers")
        tier_count += len(tiers) if isinstance(tiers, list) else 1
        raw_names = entry.get("affix_names")
        if isinstance(raw_names, list):
            affix_names.update(
                normalized
                for name in raw_names
                if (normalized := normalize_affix_name(name))
            )
    accepted = stat_values["accepted_contributors"]
    evidence_total = sum(
        stat_values[name]
        for name in (
            "accepted_contributors",
            "skipped_legacy_entries",
            "skipped_missing_contributors",
            "skipped_missing_magnitudes",
        )
    )
    usable_rate = float(accepted or 0) / evidence_total if evidence_total else 0.0
    issues = category_readiness_issues(category_payload)
    return {
        "category": catalog_category_key(category),
        "ready": not issues,
        "patterns": len(pattern_entries),
        "tiers": tier_count,
        "affix_identities": len(affix_names),
        "usable_evidence_rate": round(usable_rate, 4),
        "statistics": stat_values,
        "issues": tuple(issues),
    }


def _validated_affix_names(value: Any, context: str) -> tuple[str, ...]:
    """Validate optional additive identity metadata and return canonical names."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AffixCatalogError(f"{context} has invalid affix_names.")
    normalized: list[str] = []
    for name in value:
        if not isinstance(name, str) or not (token := normalize_affix_name(name)):
            raise AffixCatalogError(f"{context} has invalid affix_names.")
        normalized.append(token)
    if len(set(normalized)) != len(normalized):
        raise AffixCatalogError(f"{context} has duplicate affix_names.")
    return tuple(sorted(normalized))


def category_affixes(
    payload: Mapping[str, Any],
    category: str,
) -> dict[str, AffixCatalogEntry]:
    """Return validated, release-ready affix metadata for one model category."""
    key = catalog_category_key(category)
    categories = payload.get("categories")
    if not isinstance(categories, Mapping):
        raise AffixCatalogError("Affix catalog has no categories object.")
    category_payload = categories.get(key)
    if not isinstance(category_payload, Mapping):
        raise AffixCatalogError(f"Affix catalog has no category '{key}'.")
    patterns = category_payload.get("patterns")
    if not isinstance(patterns, Mapping) or not patterns:
        raise AffixCatalogError(f"Affix catalog category '{key}' has no patterns.")

    affixes: dict[str, AffixCatalogEntry] = {}
    for raw_pattern, entry in patterns.items():
        pattern = str(raw_pattern or "").strip().lower()
        if not pattern or not isinstance(entry, Mapping):
            raise AffixCatalogError(
                f"Affix catalog category '{key}' contains an invalid pattern entry."
            )
        value = _finite_float(entry.get("maximum_roll"))
        if value is None or value <= 0:
            raise AffixCatalogError(
                f"Affix catalog category '{key}' pattern '{pattern}' has an invalid maximum_roll."
            )
        sides = entry.get("affix_sides")
        if (
            not isinstance(sides, list)
            or not sides
            or any(side not in {"prefix", "suffix"} for side in sides)
        ):
            raise AffixCatalogError(
                f"Affix catalog category '{key}' pattern '{pattern}' has invalid affix_sides."
            )
        tier = str(entry.get("winning_tier") or "").strip().upper()
        if _ORDINARY_TIER_RE.fullmatch(tier) is None:
            raise AffixCatalogError(
                f"Affix catalog category '{key}' pattern '{pattern}' has an invalid winning_tier."
            )
        observations = entry.get("observations")
        required_level = entry.get("required_level")
        if (
            isinstance(observations, bool)
            or not isinstance(observations, int)
            or observations <= 0
        ):
            raise AffixCatalogError(
                f"Affix catalog category '{key}' pattern '{pattern}' has invalid observations."
            )
        if required_level is not None and (
            isinstance(required_level, bool)
            or not isinstance(required_level, int)
            or required_level < 0
        ):
            raise AffixCatalogError(
                f"Affix catalog category '{key}' pattern '{pattern}' has an invalid required_level."
            )
        summary_names = _validated_affix_names(
            entry.get("affix_names"),
            f"Affix catalog category '{key}' pattern '{pattern}'",
        )
        raw_tiers = entry.get("tiers")
        tier_entries: list[AffixCatalogTierEntry] = []
        if raw_tiers is None:
            # Schema v1 originally shipped only the winning-tier summary.
            # Treat it as a one-tier ladder so installed catalogs remain usable
            # until the next parse refresh writes the additive ``tiers`` field.
            tier_entries.append(AffixCatalogTierEntry(
                maximum_roll=value,
                affix_sides=tuple(sorted(set(sides))),
                tier=tier,
                required_level=required_level,
                observations=int(observations),
                affix_names=summary_names,
            ))
        elif not isinstance(raw_tiers, list) or not raw_tiers:
            raise AffixCatalogError(
                f"Affix catalog category '{key}' pattern '{pattern}' has invalid tiers."
            )
        else:
            seen_tiers: set[str] = set()
            for index, raw_tier in enumerate(raw_tiers):
                context = (
                    f"Affix catalog category '{key}' pattern '{pattern}' "
                    f"tier entry {index}"
                )
                if not isinstance(raw_tier, Mapping):
                    raise AffixCatalogError(f"{context} must be an object.")
                candidate_tier = str(raw_tier.get("tier") or "").strip().upper()
                tier_match = _ORDINARY_TIER_RE.fullmatch(candidate_tier)
                if tier_match is None or candidate_tier in seen_tiers:
                    raise AffixCatalogError(
                        f"{context} has invalid or duplicate tier {candidate_tier!r}."
                    )
                candidate_value = _finite_float(raw_tier.get("maximum_roll"))
                if candidate_value is None or candidate_value <= 0:
                    raise AffixCatalogError(
                        f"{context} has an invalid maximum_roll."
                    )
                candidate_observations = raw_tier.get("observations")
                if (
                    isinstance(candidate_observations, bool)
                    or not isinstance(candidate_observations, int)
                    or candidate_observations <= 0
                ):
                    raise AffixCatalogError(f"{context} has invalid observations.")
                candidate_level = raw_tier.get("required_level")
                if candidate_level is not None and (
                    isinstance(candidate_level, bool)
                    or not isinstance(candidate_level, int)
                    or candidate_level < 0
                ):
                    raise AffixCatalogError(f"{context} has an invalid required_level.")
                candidate_names = _validated_affix_names(
                    raw_tier.get("affix_names"),
                    context,
                )
                candidate_side = (
                    "prefix"
                    if tier_match.group("side").upper() == "P"
                    else "suffix"
                )
                tier_entries.append(AffixCatalogTierEntry(
                    maximum_roll=candidate_value,
                    affix_sides=(candidate_side,),
                    tier=candidate_tier,
                    required_level=candidate_level,
                    observations=candidate_observations,
                    affix_names=candidate_names,
                ))
                seen_tiers.add(candidate_tier)

            tier_observations = sum(candidate.observations for candidate in tier_entries)
            tier_sides = {
                side
                for candidate in tier_entries
                for side in candidate.affix_sides
            }
            tier_names = {
                name
                for candidate in tier_entries
                for name in candidate.affix_names
            }
            tier_winner = min(
                tier_entries,
                key=lambda candidate: (
                    -candidate.maximum_roll,
                    candidate.tier,
                    candidate.required_level
                    if candidate.required_level is not None
                    else math.inf,
                ),
            )
            if tier_observations != observations:
                raise AffixCatalogError(
                    f"Affix catalog category '{key}' pattern '{pattern}' tier "
                    "observations do not match the pattern summary."
                )
            if tier_sides != set(sides):
                raise AffixCatalogError(
                    f"Affix catalog category '{key}' pattern '{pattern}' tier "
                    "sides do not match affix_sides."
                )
            if tier_names != set(summary_names):
                raise AffixCatalogError(
                    f"Affix catalog category '{key}' pattern '{pattern}' tier "
                    "affix names do not match the pattern summary."
                )
            if (
                not math.isclose(
                    tier_winner.maximum_roll,
                    value,
                    rel_tol=0.0,
                    abs_tol=0.0001,
                )
                or tier_winner.tier != tier
                or tier_winner.required_level != required_level
            ):
                raise AffixCatalogError(
                    f"Affix catalog category '{key}' pattern '{pattern}' tier "
                    "winner does not match the pattern summary."
                )

        affixes[pattern] = AffixCatalogEntry(
            pattern=pattern,
            maximum_roll=value,
            affix_sides=tuple(sorted(set(sides))),
            winning_tier=tier,
            required_level=required_level,
            observations=int(observations),
            tiers=tuple(tier_entries),
            affix_names=summary_names,
        )
    readiness_issues = category_readiness_issues(category_payload)
    if readiness_issues:
        raise AffixCatalogError(
            f"Affix catalog category '{key}' is not release-ready: "
            + "; ".join(readiness_issues)
        )
    return {pattern: affixes[pattern] for pattern in sorted(affixes)}


def category_maximum_rolls(payload: Mapping[str, Any], category: str) -> dict[str, float]:
    """Return validated intrinsic maxima for one canonical model category."""
    return {
        pattern: entry.maximum_roll
        for pattern, entry in category_affixes(payload, category).items()
    }


@lru_cache(maxsize=16)
def _load_runtime_catalog_snapshot(
    path_text: str,
    modified_ns: int,
    size: int,
) -> dict[str, Any]:
    """Load one immutable-on-disk catalog revision for the runtime cache."""
    del modified_ns, size  # Cache-key metadata; the path is the actual input.
    return load_catalog(Path(path_text))


def clear_runtime_catalog_cache() -> None:
    """Clear cached runtime catalog revisions (primarily for tests/tools)."""
    _load_runtime_catalog_snapshot.cache_clear()


def runtime_affixes(
    category: str,
    *,
    path: Path | None = None,
) -> dict[str, AffixCatalogEntry]:
    """Resolve the updater/bundled catalog and return one category's entries.

    The resolved path and its file metadata form the cache key, so an updater
    replacement or a switch between override and bundled assets is visible to
    a long-running process without reparsing unchanged JSON on every craft.
    """
    if path is None:
        from poe2trade.app import asset_paths

        path = asset_paths.resolve_asset_file("super_models", CATALOG_FILENAME)
    path = Path(path)
    try:
        stat = path.stat()
    except OSError as exc:
        raise AffixCatalogError(
            "Craft Oracle intrinsic-affix catalog is not installed. "
            "Rebuild or update the supervised model assets."
        ) from exc
    resolved = str(path.resolve())
    payload = _load_runtime_catalog_snapshot(resolved, stat.st_mtime_ns, stat.st_size)
    return category_affixes(payload, category)


def runtime_maximum_rolls(
    category: str,
    *,
    path: Path | None = None,
) -> dict[str, float]:
    """Resolve the runtime catalog and return one category's intrinsic maxima."""
    return {
        pattern: entry.maximum_roll
        for pattern, entry in runtime_affixes(category, path=path).items()
    }


def update_catalog_categories(
    replacements: Mapping[str, AffixCatalogCollector | None],
    path: Path = DEFAULT_CATALOG_PATH,
) -> Path:
    """Atomically replace selected category entries and preserve all others."""
    payload = load_catalog(path)
    categories = dict(payload["categories"])
    for raw_category, collector in replacements.items():
        key = catalog_category_key(raw_category)
        if collector is None:
            categories.pop(key, None)
        else:
            categories[key] = collector.category_payload(
                min_pattern_observations=MIN_PATTERN_OBSERVATIONS,
            )
    output = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "categories": {key: categories[key] for key in sorted(categories)},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return path
