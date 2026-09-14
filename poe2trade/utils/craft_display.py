"""Shared, dependency-free display helpers for Craft Oracle results."""
from __future__ import annotations

from collections.abc import Mapping
import math
import re


_TIER_RE = re.compile(r"^[PS][1-9]\d*$", re.IGNORECASE)


def _value(row: object, key: str, default: object = None) -> object:
    if isinstance(row, Mapping):
        return row.get(key, default)
    return getattr(row, key, default)


def _number(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "-"
    if not math.isfinite(number):
        return "-"
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _integer(value: object, *, minimum: int) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or not number.is_integer() or number < minimum:
        return None
    return int(number)


def _provenance_text(row: object) -> str:
    """Return compact selected-tier provenance when the payload provides it."""
    parts: list[str] = []

    tier = str(_value(row, "winning_tier") or "").strip().upper()
    if _TIER_RE.fullmatch(tier):
        side = "prefix" if tier.startswith("P") else "suffix"
        parts.append(f"{tier} {side}")

    required_level = _integer(_value(row, "required_level"), minimum=0)
    if required_level is not None:
        parts.append(f"ilvl {required_level}")

    tier_observations = _integer(_value(row, "tier_observations"), minimum=1)
    if tier_observations is not None:
        parts.append(f"{tier_observations} obs")
    else:
        pattern_observations = _integer(_value(row, "observations"), minimum=1)
        if pattern_observations is not None:
            parts.append(f"{pattern_observations} pattern obs")

    return f" [{' · '.join(parts)}]" if parts else ""


def craft_delta_text(value: object, percent: object = None) -> str:
    """Format one predicted change with precision matched to its magnitude.

    A fixed whole-exalt format collapses every sub-1e change to ``+0e``, which
    on a cheap item renders an entire ranked list as zeros while still ordering
    it. Precision therefore scales with the value, and all three Craft Oracle
    result routes share this one formatter so they cannot disagree.
    """
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "-"
    if not math.isfinite(number):
        return "-"
    magnitude = abs(number)
    digits = 2 if magnitude < 10 else (1 if magnitude < 100 else 0)
    text = f"{number:+.{digits}f}e"
    try:
        share = float(percent)
    except (TypeError, ValueError, OverflowError):
        return text
    return f"{text} ({share:+.1f}%)" if math.isfinite(share) else text


def craft_roll_text(row: object) -> str:
    """Describe one selected intrinsic/effective roll and its provenance."""
    pattern = str(_value(row, "pattern") or "")
    intrinsic = _value(row, "maximum_roll")
    effective = _value(row, "effective_roll", intrinsic)
    try:
        differs = not math.isclose(
            float(intrinsic), float(effective), rel_tol=1e-9, abs_tol=1e-9
        )
    except (TypeError, ValueError, OverflowError):
        differs = False

    if differs:
        roll = (
            f"{pattern}: intrinsic {_number(intrinsic)}; "
            f"effective {_number(effective)}"
        )
    else:
        roll = f"{pattern}: {_number(intrinsic)}"
    return roll + _provenance_text(row)
