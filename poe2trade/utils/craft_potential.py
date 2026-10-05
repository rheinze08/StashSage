"""Counterfactual Craft Potential analysis.

This module intentionally owns the data discovery, eligibility checks, and
simulation work for the Craft Potential feature.  GUI callers only provide a
clipboard item and render the returned result.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

import pandas as pd

from poe2trade.utils.craft_affix_catalog import (
    AffixCatalogEntry,
    AffixCatalogError,
    AffixCatalogTierEntry,
    normalize_affix_name,
    runtime_affixes,
    runtime_maximum_rolls,
)
from poe2trade.utils.gui_utils import (
    FLAT_DEFENCE_PATTERNS,
    PCT_DEFENCE_PATTERNS,
    PreparedItem,
    call_super_prepared,
    parse_copied_item_text,
    prepare_item_features,
    process_all_mods,
    quality_type_modifier_patterns,
)
from poe2trade.utils.parse_utils import (
    BOW_DAMAGE_PREFIX,
    DPS_WEAPON_CATEGORIES,
    DPS_WEAPON_OMITTED_MOD_PATTERNS,
    compute_bow_dps_features,
    parse_rolled_mod,
)
from poe2trade.utils.ml_super_utils import model_feature_columns


class CraftPotentialError(ValueError):
    """A user-facing reason Craft Potential cannot analyze an item."""


@dataclass(frozen=True)
class CraftPotentialRow:
    pattern: str
    # This compatibility field holds the selected target-eligible intrinsic
    # roll. ``effective_roll`` is the value after target-local amplification.
    maximum_roll: float
    effective_roll: float
    affix_sides: tuple[str, ...]
    winning_tier: str
    required_level: int | None
    observations: int
    tier_observations: int
    affix_names: tuple[str, ...]
    prediction: float
    delta: float
    delta_percent: float | None


@dataclass(frozen=True)
class CraftPotentialResult:
    item_name: str
    category: str
    explicit_count: int
    baseline_prediction: float
    rows: tuple[CraftPotentialRow, ...]


@dataclass(frozen=True)
class _TargetAdjustedRoll:
    intrinsic_roll: float
    effective_roll: float
    feature_roll: float
    magnitude_percent: float
    quality_percent: float


@dataclass(frozen=True)
class _TargetAffixEligibility:
    item_level: int | None
    prefix_count: int
    suffix_count: int
    sides_known: bool
    affix_names: frozenset[str]


_EXPLICIT_MAGNITUDE_PATTERN = re.compile(
    r"^#% increased explicit (?P<scope>[a-z ]+?) modifier magnitudes$"
)
_MAX_AFFIXES_PER_SIDE = 3


def _explicit_patterns(raw: dict) -> set[str]:
    patterns: set[str] = set()
    for key, value in raw.items():
        if not re.fullmatch(r"explicit_mod_\d+", str(key)) or not value:
            continue
        pattern, *_ = parse_rolled_mod(str(value))
        if pattern:
            patterns.add(str(pattern).strip().lower())
    return patterns


def validate_item(text: str) -> tuple[dict, int]:
    """Validate the input scope and return its raw parsed form and affix count."""
    if not re.search(r"^Rarity:\s*Rare\s*$", text or "", flags=re.I | re.M):
        raise CraftPotentialError("Craft Potential only supports rare items.")
    raw = parse_copied_item_text(text)
    if str(raw.get("Corrupted") or "").strip().lower() == "yes":
        raise CraftPotentialError(
            "Craft Potential does not support corrupted items, which cannot gain new modifiers."
        )
    # Count affixes, not parsed feature slots.  A composite line expands into
    # several slots and a hybrid affix occupies several lines, so slot counting
    # rejects items that still have open affix space.
    count = _affix_count(raw)
    if count >= _MAX_AFFIXES_PER_SIDE * 2:
        raise CraftPotentialError(
            "Craft Potential only supports rare items with fewer than six explicit modifiers."
        )
    if not raw.get("Item Category"):
        raise CraftPotentialError("Could not determine the item's category from the clipboard text.")
    return raw, count


def _affix_count(raw: dict) -> int:
    """Return the parser's affix-level count, falling back to slot counting."""
    value = raw.get("explicit_affix_count")
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return sum(1 for key in raw if re.fullmatch(r"explicit_mod_\d+", str(key)))


def _maximum_explicit_rolls(category: str) -> dict[str, float]:
    """Read intrinsic ordinary-explicit maxima from the installed catalog."""
    try:
        return runtime_maximum_rolls(category)
    except AffixCatalogError as exc:
        raise CraftPotentialError(str(exc)) from exc


def _explicit_affixes(category: str) -> dict[str, AffixCatalogEntry]:
    """Read release-ready ordinary-explicit metadata from the catalog."""
    try:
        return runtime_affixes(category)
    except AffixCatalogError as exc:
        raise CraftPotentialError(str(exc)) from exc


def _target_affix_eligibility(text: str, raw: dict) -> _TargetAffixEligibility:
    """Read item level and trustworthy advanced prefix/suffix counts.

    The affix-level metadata comes from the clipboard parser, which groups
    expanded feature slots back to the header that produced them.  Side capacity
    is enforced only when every explicit affix declared a Prefix/Suffix side;
    basic copies and side-less special headers still fail open instead of hiding
    potentially valid candidates.
    """
    item_level_match = re.search(r"^Item Level:\s*(\d+)\s*$", text or "", re.I | re.M)
    item_level = int(item_level_match.group(1)) if item_level_match else None
    affix_names = frozenset(
        normalized
        for name in (raw.get("explicit_affix_names") or ())
        if (normalized := normalize_affix_name(name))
    )
    return _TargetAffixEligibility(
        item_level=item_level,
        prefix_count=int(raw.get("explicit_prefix_count") or 0),
        suffix_count=int(raw.get("explicit_suffix_count") or 0),
        sides_known=bool(raw.get("explicit_affix_sides_known")),
        affix_names=affix_names,
    )


def _entry_tiers(entry: AffixCatalogEntry) -> tuple[AffixCatalogTierEntry, ...]:
    """Return the structured ladder or a legacy one-tier compatibility view."""
    if entry.tiers:
        return entry.tiers
    return (AffixCatalogTierEntry(
        maximum_roll=entry.maximum_roll,
        affix_sides=entry.affix_sides,
        tier=entry.winning_tier,
        required_level=entry.required_level,
        observations=entry.observations,
        affix_names=entry.affix_names,
    ),)


def _select_affix_tier(
    entry: AffixCatalogEntry,
    target: _TargetAffixEligibility,
) -> AffixCatalogTierEntry | None:
    """Choose the strongest observed tier that can fit the selected target."""
    if target.affix_names.intersection(entry.affix_names):
        return None
    available_sides: set[str] | None = None
    if target.sides_known:
        available_sides = set()
        if target.prefix_count < _MAX_AFFIXES_PER_SIDE:
            available_sides.add("prefix")
        if target.suffix_count < _MAX_AFFIXES_PER_SIDE:
            available_sides.add("suffix")

    eligible = [
        tier
        for tier in _entry_tiers(entry)
        if (
            (
                target.item_level is None
                or tier.required_level is None
                or tier.required_level <= target.item_level
            )
            and (
                available_sides is None
                or bool(available_sides.intersection(tier.affix_sides))
            )
        )
    ]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda tier: (
            -tier.maximum_roll,
            tier.tier,
            tier.required_level if tier.required_level is not None else float("inf"),
        ),
    )


def _affix_is_eligible(
    entry: AffixCatalogEntry,
    target: _TargetAffixEligibility,
) -> bool:
    """Return whether at least one observed tier can fit this target."""
    return _select_affix_tier(entry, target) is not None


def _prediction(result: dict | None) -> float:
    if not result:
        raise CraftPotentialError("No supervised model is available for this item.")
    predictions = result.get("predictions") if isinstance(result, dict) else None
    value = (predictions or {}).get("xgb")
    if value is None:
        value = result.get("median") if isinstance(result, dict) else None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise CraftPotentialError("The supervised model did not return a usable prediction.")


def _processed_mod_values(raw: dict) -> dict[str, float]:
    """Return summed current mod values by canonical pattern."""
    parsed = process_all_mods(dict(raw))
    values: dict[str, float] = {}
    for key, pattern in parsed.items():
        if not re.fullmatch(r"(?:explicit|implicit|enchant)_mod_\d+_pattern", str(key)):
            continue
        value_key = str(key).replace("_pattern", "_value")
        try:
            values[str(pattern).lower()] = values.get(str(pattern).lower(), 0.0) + float(parsed.get(value_key, 0) or 0)
        except (TypeError, ValueError):
            continue
    return values


def _magnitude_scope_applies(scope: str, pattern: str) -> bool:
    """Conservatively map a local explicit-magnitude scope to a feature.

    Copied items do not expose a reusable affix-tag database. Exact jewellery
    quality mappings are authoritative where available; canonical feature
    words cover the remaining currently observed magnitude scopes.
    """
    scope = re.sub(r"\s+", " ", str(scope or "").strip().lower())
    pattern = re.sub(r"\s+", " ", str(pattern or "").strip().lower())
    if not scope or not pattern:
        return False
    if pattern in quality_type_modifier_patterns(scope):
        return True
    if scope == "elemental damage":
        return "damage" in pattern and any(
            word in pattern for word in ("elemental", "fire", "cold", "lightning")
        )
    if scope == "resistance":
        return "resistance" in pattern
    if scope == "critical":
        return "critical" in pattern
    if scope == "speed":
        return "speed" in pattern
    if scope in {"physical", "fire", "cold", "lightning", "chaos", "mana"}:
        return scope in pattern
    return False


def _target_adjusted_roll(
    raw: dict,
    pattern: str,
    intrinsic_roll: float,
) -> _TargetAdjustedRoll:
    """Map an intrinsic ceiling into target display and model feature space.

    Local explicit-magnitude effects and typed quality add to the displayed
    magnitude. Jewellery preprocessing divides matching typed quality back out,
    so only the quality-normalized value may be appended to the prepared model
    row. This mirrors the normal copied-item path without mutating it.
    """
    pattern = str(pattern or "").strip().lower()
    magnitude_percent = 0.0
    for current_pattern, value in _processed_mod_values(raw).items():
        match = _EXPLICIT_MAGNITUDE_PATTERN.fullmatch(current_pattern)
        if match and _magnitude_scope_applies(match.group("scope"), pattern):
            magnitude_percent += float(value)

    category = str(raw.get("Item Category") or "").strip().lower().replace(" ", "_")
    if category in {"rings", "amulets", "belts"}:
        category = category[:-1]
    quality_percent = 0.0
    if category in {"ring", "amulet", "belt"}:
        if pattern in quality_type_modifier_patterns(raw.get("Quality_Type")):
            try:
                quality_percent = max(0.0, float(raw.get("Quality_Type_Pct") or 0.0))
            except (TypeError, ValueError):
                quality_percent = 0.0

    intrinsic_roll = float(intrinsic_roll)
    effective_roll = intrinsic_roll * (
        1.0 + (magnitude_percent + quality_percent) / 100.0
    )
    feature_roll = effective_roll / (1.0 + quality_percent / 100.0)
    return _TargetAdjustedRoll(
        intrinsic_roll=round(intrinsic_roll, 4),
        effective_roll=round(effective_roll, 4),
        feature_roll=round(feature_roll, 4),
        magnitude_percent=round(magnitude_percent, 4),
        quality_percent=round(quality_percent, 4),
    )


_PHYS_PCT_PATTERN = "#% increased physical damage"
_ATTACK_SPEED_PATTERN = "#% increased attack speed"
_CRIT_CHANCE_PATTERN = "#% to critical hit chance"
_FLAT_DAMAGE_PATTERN = re.compile(
    r"adds # to # (?P<type>physical|fire|cold|lightning|chaos) damage"
)


def _local_percent(processed: dict, pattern: str) -> float:
    """Sum every local source of one percent modifier already shown on the item.

    Runes are included because their effect is present in the displayed weapon
    property, which is what the candidate modifier stacks with in game.
    """
    total = 0.0
    for prefix in ("explicit", "implicit", "enchant", "rune"):
        for index in range(1, 11):
            if str(processed.get(f"{prefix}_mod_{index}_pattern") or "").strip().lower() != pattern:
                continue
            try:
                total += float(processed.get(f"{prefix}_mod_{index}_value") or 0.0)
            except (TypeError, ValueError):
                continue
    return total


def _weapon_stat_mutation(
    processed: dict,
    pattern: str,
    value: float,
) -> Callable[[dict], dict] | None:
    """Return a displayed-space mutation for one candidate weapon modifier.

    PoE stacks local weapon increases *additively*: quality, rune, and explicit
    increased-physical all add before scaling the base range, and local flat
    damage is added before those increases apply. Encoding that here — rather
    than adding a hand-derived increment straight into a normalized DPS feature
    — keeps the counterfactual aligned with whatever deflation
    :func:`compute_bow_dps_features` performs, so the two cannot drift apart.
    """
    quality = float(processed.get("Quality") or processed.get("quality") or 0.0)

    if pattern == _PHYS_PCT_PATTERN:
        local = quality + _local_percent(processed, _PHYS_PCT_PATTERN)
        factor = (1.0 + (local + value) / 100.0) / (1.0 + local / 100.0)

        def mutate(row: dict) -> dict:
            for side in ("min", "max"):
                key = f"phys_damage_{side}"
                row[key] = float(row.get(key) or 0.0) * factor
            return row

        return mutate

    if pattern == _ATTACK_SPEED_PATTERN:
        local = _local_percent(processed, _ATTACK_SPEED_PATTERN)
        factor = (1.0 + (local + value) / 100.0) / (1.0 + local / 100.0)

        def mutate(row: dict) -> dict:
            row["attack_speed"] = float(row.get("attack_speed") or 0.0) * factor
            return row

        return mutate

    if pattern == _CRIT_CHANCE_PATTERN:
        # The canonical pattern reads "+#% *to* critical hit chance", so the
        # roll adds to the displayed critical property rather than scaling it.
        def mutate(row: dict) -> dict:
            row["crit_chance"] = float(row.get("crit_chance") or 0.0) + value
            return row

        return mutate

    match = _FLAT_DAMAGE_PATTERN.fullmatch(pattern)
    if match:
        damage_type = match.group("type")
        prefix = BOW_DAMAGE_PREFIX[damage_type]
        # Only physical carries a local increased-physical multiplier; flat
        # elemental and chaos rolls are shown at their face value.
        scale = 1.0
        if damage_type == "physical":
            scale = 1.0 + (quality + _local_percent(processed, _PHYS_PCT_PATTERN)) / 100.0
        # The stored value is the roll's range average, matching the DPS
        # feature's average-damage basis, so both ends move by the same amount.
        added = value * scale

        def mutate(row: dict) -> dict:
            for side in ("min", "max"):
                key = f"{prefix}_damage_{side}"
                row[key] = float(row.get(key) or 0.0) + added
            return row

        return mutate

    return None


def _weapon_dps_delta(
    processed: dict,
    mutate: Callable[[dict], dict],
) -> dict[str, float]:
    """Return the model-space DPS change produced by a displayed-space edit."""
    before = compute_bow_dps_features(processed)
    after = compute_bow_dps_features(mutate(dict(processed)))
    return {
        key: float(after.get(key, 0.0)) - float(before.get(key, 0.0))
        for key in after
    }


def _simulate_derived_feature(
    base: pd.DataFrame, raw: dict, category: str, pattern: str, value: float, supported: set[str]
) -> pd.DataFrame | None:
    """Apply the pipeline's derived armour/DPS semantics to one candidate mod."""
    category = category.lower()
    simulated = base.copy()
    current = _processed_mod_values(raw)
    row = simulated.iloc[0]
    if category in {"boots", "gloves", "helmet", "body_armour", "shield", "buckler", "focus"}:
        if pattern in FLAT_DEFENCE_PATTERNS:
            target = {
                "# to armour": "ar_norm",
                "# to evasion rating": "ev_norm",
                "# to maximum energy shield": "es_norm",
            }[pattern]
            if target not in supported:
                return None
            current_pct = max((current.get(pat, 0.0) for pat in PCT_DEFENCE_PATTERNS), default=0.0)
            simulated.loc[simulated.index[0], target] = float(row.get(target, 0.0)) + value * (1.0 + current_pct / 100.0)
            return simulated
        if pattern in PCT_DEFENCE_PATTERNS:
            targets = [target for target in ("ar_norm", "ev_norm", "es_norm") if target in supported]
            if not targets:
                return None
            old_pct = max((current.get(pat, 0.0) for pat in PCT_DEFENCE_PATTERNS), default=0.0)
            new_pct = max(old_pct, value)
            multiplier = (1.0 + new_pct / 100.0) / (1.0 + old_pct / 100.0)
            for target in targets:
                simulated.loc[simulated.index[0], target] = float(row.get(target, 0.0)) * multiplier
            return simulated
    if category in DPS_WEAPON_CATEGORIES and pattern in DPS_WEAPON_OMITTED_MOD_PATTERNS:
        processed = process_all_mods(dict(raw))
        mutate = _weapon_stat_mutation(processed, pattern, value)
        if mutate is None:
            return None
        deltas = _weapon_dps_delta(processed, mutate)
        targets = [key for key, delta in deltas.items() if key in supported and delta]
        if not targets:
            return None
        for target in targets:
            simulated.loc[simulated.index[0], target] = float(row.get(target, 0.0)) + deltas[target]
        return simulated
    return None


def analyze(text: str, progress: Callable[[int, int], None] | None = None) -> CraftPotentialResult:
    """Evaluate every missing explicit modifier at its intrinsic catalog maximum."""
    raw, explicit_count = validate_item(text)
    prepared: PreparedItem = prepare_item_features(text)
    baseline = _prediction(call_super_prepared(prepared))
    existing = _explicit_patterns(raw)
    affixes = _explicit_affixes(prepared.model_category)
    target_eligibility = _target_affix_eligibility(text, raw)
    base = prepared.features.copy()
    supported = model_feature_columns(
        prepared.model_category,
        None if prepared.model_category == "jewel" else prepared.segment,
    )
    if not supported:
        raise CraftPotentialError("No supervised model is available for this item.")
    derived_patterns = (PCT_DEFENCE_PATTERNS | FLAT_DEFENCE_PATTERNS) if prepared.category in {
        "boots", "gloves", "helmet", "body_armour", "shield", "buckler", "focus"
    } else (
        # Every pattern the weapon branch folds into a displayed property is a
        # derived candidate, including critical hit chance.
        DPS_WEAPON_OMITTED_MOD_PATTERNS
        if prepared.category in DPS_WEAPON_CATEGORIES
        else set()
    )
    candidates: list[
        tuple[str, AffixCatalogEntry, AffixCatalogTierEntry]
    ] = []
    for pattern, entry in affixes.items():
        if pattern in existing or (
            pattern not in supported and pattern not in derived_patterns
        ):
            continue
        selected_tier = _select_affix_tier(entry, target_eligibility)
        if selected_tier is not None:
            candidates.append((pattern, entry, selected_tier))
    if not candidates:
        raise CraftPotentialError(
            "No item-level and affix-slot eligible model-supported explicit modifiers were found."
        )

    rows: list[CraftPotentialRow] = []
    total = len(candidates)
    for position, (pattern, entry, selected_tier) in enumerate(candidates, start=1):
        adjusted = _target_adjusted_roll(raw, pattern, selected_tier.maximum_roll)
        if pattern in supported:
            simulated = base.copy()
            simulated.loc[simulated.index[0], pattern] = (
                float(simulated.iloc[0].get(pattern, 0.0)) + adjusted.feature_roll
            )
        else:
            simulated = _simulate_derived_feature(
                base,
                raw,
                prepared.category,
                pattern,
                adjusted.feature_roll,
                supported,
            )
            if simulated is None:
                continue
        candidate = PreparedItem(
            text=prepared.text, raw_parsed=prepared.raw_parsed, features=simulated,
            category=prepared.category, segment=prepared.segment,
            model_category=prepared.model_category,
        )
        predicted = _prediction(call_super_prepared(candidate))
        delta = predicted - baseline
        rows.append(CraftPotentialRow(
            pattern=pattern,
            maximum_roll=adjusted.intrinsic_roll,
            effective_roll=adjusted.effective_roll,
            affix_sides=selected_tier.affix_sides,
            winning_tier=selected_tier.tier,
            required_level=selected_tier.required_level,
            observations=entry.observations,
            tier_observations=selected_tier.observations,
            affix_names=selected_tier.affix_names,
            prediction=predicted,
            delta=delta,
            delta_percent=(delta / baseline * 100.0) if baseline else None,
        ))
        if progress:
            progress(position, total)
    rows.sort(key=lambda row: (-row.delta, row.pattern))
    return CraftPotentialResult(
        item_name=str(raw.get("Item Name") or raw.get("Base Type") or "(Unknown item)"),
        category=prepared.category, explicit_count=explicit_count,
        baseline_prediction=baseline, rows=tuple(rows),
    )
