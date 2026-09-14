# File: poe2trade/utils/parse_utils.py

"""
Flatten PoE trade-API JSON dumps into a tidy DataFrame.

Key features
------------
â€¢ Robust rolled-mod parsing (pattern + average value)
â€¢ Exhaustive tag cleanup for wiki-style â€œ[foo|bar]â€ strings
â€¢ Filters out passive-tree â€œallocates â€¦â€ mods
â€¢ Extracts quality / quality_type, ar, ev, es
â€¢ Gracefully skips local template JSON files; logs malformed entries

Notes
-----
â€¢ `fracturedMods` and `descratedMods` (max 3 each) are parsed into their own slots
  and are NOT merged into the `explicit` mod stream.
â€¢ Before parsing, mods are preprocessed to:
  - remove a literal "(descrated)" marker, and
  - split combined lines:
      "+# to X and Y"                  where X/Y âˆˆ {Strength, Dexterity, Intelligence}
      "+#% to X and Y Resistances"     where X/Y âˆˆ {Cold, Fire, Lightning, Chaos}
  These expansions produce two separate lines so patterns are matched and values summed downstream.
"""

from __future__ import annotations

import json
import os
import re
from typing import Callable, List, Tuple, Dict, Any, Mapping

import pandas as pd

import poe2trade as _poe2trade_cfg
from poe2trade import buyout_only

ITEM_STATUS_FEATURES = ("item_corrupted", "item_fractured", "item_sanctified")
EXTRA_SOCKET_BASE_MAX = {
    "body_armour": 2,
    "staff": 2,
    "bow": 2,
    "crossbow": 2,
    "mace_one_hand_mace": 1,
    "mace_two_hand_mace": 2,
    "quarterstaff": 2,
    "spear": 2,
    "talisman": 2,
    "boots": 1,
    "gloves": 1,
    "helmet": 1,
    "focus": 1,
    "shield": 1,
    "wand": 1,
    "sceptre": 1,
}

SUPPORTED_WAYSTONE_TIERS: tuple[int, ...] = (14, 15, 16)
SUPPORTED_WAYSTONE_SEGMENTS = frozenset(f"t{tier}" for tier in SUPPORTED_WAYSTONE_TIERS)
UNSUPPORTED_WAYSTONE_MESSAGE = "Waystone pricing is available for tiers 14-16 only."
WAYSTONE_OMITTED_MODEL_FEATURES = frozenset({"waystone_revives_available"})
WAYSTONE_MODEL_PROPERTY_LABELS = {
    "waystone_item_rarity": "Item Rarity",
    "waystone_pack_size": "Pack Size",
    "waystone_monster_rarity": "Monster Rarity",
    "waystone_drop_chance": "Waystone Drop Chance",
    "waystone_monster_effectiveness": "Monster Effectiveness",
}


def normalize_waystone_tier(value: Any) -> int | None:
    """Return a supported integer tier, otherwise ``None``."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not numeric.is_integer():
        return None
    tier = int(numeric)
    return tier if tier in SUPPORTED_WAYSTONE_TIERS else None


def waystone_segment(value: Any) -> str | None:
    tier = normalize_waystone_tier(value)
    return f"t{tier}" if tier is not None else None


def waystone_segment_from_frame(frame: Any) -> str | None:
    """Resolve a segment only when a frame contains one unambiguous tier."""
    if frame is None or "waystone_tier" not in getattr(frame, "columns", ()):
        return None
    values = frame["waystone_tier"].dropna().unique().tolist()
    if len(values) != 1:
        return None
    return waystone_segment(values[0])


def normalize_item_category(category: Any) -> str:
    token = str(category or "").strip().lower().replace("-", "_")
    token = re.sub(r"\s+", "_", token)
    token = re.sub(r"[^a-z0-9_]+", "", token)
    return {
        "amulets": "amulet",
        "belts": "belt",
        "body_armours": "body_armour",
        "body_armour": "body_armour",
        "body_armors": "body_armour",
        "body_armor": "body_armour",
        "jewels": "jewel",
        "quivers": "quiver",
        "rings": "ring",
        "helmets": "helmet",
        "shields": "shield",
        "bucklers": "buckler",
        "wands": "wand",
        "bows": "bow",
        "crossbows": "crossbow",
        "one_hand_maces": "mace_one_hand_mace",
        "one_hand_mace": "mace_one_hand_mace",
        "one_handed_maces": "mace_one_hand_mace",
        "one_handed_mace": "mace_one_hand_mace",
        "two_hand_maces": "mace_two_hand_mace",
        "two_hand_mace": "mace_two_hand_mace",
        "two_handed_maces": "mace_two_hand_mace",
        "two_handed_mace": "mace_two_hand_mace",
        "quarterstaves": "quarterstaff",
        "quarterstave": "quarterstaff",
        "spears": "spear",
        "talismans": "talisman",
        "scepters": "sceptre",
        "scepter": "sceptre",
        "sceptres": "sceptre",
        "staves": "staff",
        "staffs": "staff",
        "foci": "focus",
        "tablets": "tablet",
        "waystones": "waystone",
    }.get(token, token)


def extra_socket_count(category: Any, socket_count: Any) -> int:
    category_n = normalize_item_category(category)
    base_max = EXTRA_SOCKET_BASE_MAX.get(category_n)
    if base_max is None:
        return 0
    try:
        count = int(float(socket_count or 0))
    except (TypeError, ValueError):
        count = 0
    return max(0, count - base_max)


def supports_extra_socket_feature(category: Any) -> bool:
    return normalize_item_category(category) in EXTRA_SOCKET_BASE_MAX


BOW_DAMAGE_TYPES = ("physical", "fire", "cold", "lightning", "chaos")
BOW_DAMAGE_PREFIX = {
    "physical": "phys",
    "fire": "fire",
    "cold": "cold",
    "lightning": "lightning",
    "chaos": "chaos",
}
BOW_RAW_STAT_COLUMNS = [
    *(f"{BOW_DAMAGE_PREFIX[typ]}_damage_{side}" for typ in BOW_DAMAGE_TYPES for side in ("min", "max")),
    "attack_speed",
]
BOW_DPS_COLUMNS = [
    "dps_total",
    "dps_physical",
    "dps_fire",
    "dps_cold",
    "dps_lightning",
    "dps_chaos",
    "crit_chance",
]
BOW_DPS_ENCODED_PATTERNS = {
    "#% increased physical damage",
    "#% increased attack speed",
    "adds # to # physical damage",
    "adds # to # fire damage",
    "adds # to # cold damage",
    "adds # to # lightning damage",
    "adds # to # chaos damage",
}
# The displayed critical-hit property already includes local critical chance
# modifiers, so retaining this modifier as a separate model feature duplicates
# the same signal for DPS weapons.
DPS_WEAPON_OMITTED_MOD_PATTERNS = BOW_DPS_ENCODED_PATTERNS | {
    "#% to critical hit chance",
}
# These categories share Bow's base-damage and DPS feature representation.
DPS_WEAPON_CATEGORIES = frozenset({
    "bow",
    "crossbow",
    "mace_one_hand_mace",
    "mace_two_hand_mace",
    "quarterstaff",
    "spear",
    "talisman",
})
_ELEMENT_VALUE_TYPES = {
    4: "fire",
    5: "cold",
    6: "lightning",
    7: "chaos",
    9: "physical",
}

_ADVANCED_ROLL_ANNOTATION = re.compile(
    r"(?<=\d)\s*\(\s*[+-]?\d+(?:\.\d+)?(?:\s*-\s*[+-]?\d+(?:\.\d+)?)?\s*\)"
)


def strip_advanced_roll_annotations(text: Any) -> str:
    """Remove PoE's parenthesized advanced-roll annotation after a value.

    Both ``+6(4)`` and ``88(85-109)%`` display the rolled value before the
    parentheses. Removing the annotation prevents the values being joined into
    ``+64`` by clipboard cleanup.
    """
    return _ADVANCED_ROLL_ANNOTATION.sub("", str(text or ""))


def parse_damage_range(text: Any) -> tuple[float, float] | None:
    """Parse a displayed A-B damage range. A single value is treated as A-A."""
    if text is None:
        return None
    txt = clean_mod_text(str(text))
    txt = strip_advanced_roll_annotations(txt)
    nums = [float(n) for n in re.findall(r"(?<!\d)[+-]?\d+(?:\.\d+)?", txt)]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return nums[0], nums[1]


def _add_bow_damage_range(rec: Dict[str, object], damage_type: str, low: float, high: float) -> None:
    prefix = BOW_DAMAGE_PREFIX.get(damage_type)
    if not prefix:
        return
    min_key = f"{prefix}_damage_min"
    max_key = f"{prefix}_damage_max"
    rec[min_key] = float(rec.get(min_key) or 0.0) + float(low)
    rec[max_key] = float(rec.get(max_key) or 0.0) + float(high)


def _numeric_from_mapping(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    lower_keys = {str(k).lower(): k for k in row.keys()}
    for key in keys:
        actual = key if key in row else lower_keys.get(key.lower())
        if actual is None:
            continue
        val = row.get(actual)
        if val is None or pd.isna(val):
            continue
        if isinstance(val, str):
            m = re.search(r"[+-]?\d+(?:\.\d+)?", val)
            if not m:
                continue
            val = m.group(0)
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return default


def _rune_flat_damage_type(pattern: str) -> str | None:
    m = re.fullmatch(
        r"adds # to # (physical|fire|cold|lightning|chaos) damage",
        str(pattern or "").strip().lower(),
    )
    return m.group(1) if m else None


def _rune_damage_average(row: Mapping[str, Any], idx: int) -> float:
    low = _numeric_from_mapping(row, f"rune_mod_{idx}_min", default=float("nan"))
    high = _numeric_from_mapping(row, f"rune_mod_{idx}_max", default=float("nan"))
    if not pd.isna(low) and not pd.isna(high):
        return (low + high) / 2.0
    raw = row.get(f"rune_mod_{idx}")
    parsed = parse_damage_range(raw)
    if parsed is not None:
        return (parsed[0] + parsed[1]) / 2.0
    return _numeric_from_mapping(row, f"rune_mod_{idx}_value")


def bow_rune_adjustments(row: Mapping[str, Any]) -> tuple[float, dict[str, float]]:
    """Return direct socket/rune physical-% and flat damage adjustments."""
    phys_pct = 0.0
    flat = {typ: 0.0 for typ in BOW_DAMAGE_TYPES}
    for idx in range(1, 7):
        pat = str(row.get(f"rune_mod_{idx}_pattern") or "").strip().lower()
        if pat == "#% increased physical damage":
            phys_pct += _numeric_from_mapping(row, f"rune_mod_{idx}_value")
            continue
        damage_type = _rune_flat_damage_type(pat)
        if damage_type:
            flat[damage_type] += _rune_damage_average(row, idx)
    return phys_pct, flat


def compute_bow_dps_features(row: Mapping[str, Any]) -> dict[str, float]:
    """Build model DPS features with quality and socket/rune effects removed."""
    attack_speed = _numeric_from_mapping(row, "attack_speed", "Attacks per Second")
    quality = _numeric_from_mapping(row, "quality", "Quality")
    rune_phys_pct, rune_flat = bow_rune_adjustments(row)
    dps: dict[str, float] = {}
    total = 0.0

    for damage_type in BOW_DAMAGE_TYPES:
        prefix = BOW_DAMAGE_PREFIX[damage_type]
        low = _numeric_from_mapping(row, f"{prefix}_damage_min")
        high = _numeric_from_mapping(row, f"{prefix}_damage_max")
        avg = (low + high) / 2.0
        if damage_type == "physical":
            denom = (1.0 + quality / 100.0) * (1.0 + rune_phys_pct / 100.0)
            if not denom:
                denom = 1.0
            avg = avg / denom - rune_flat[damage_type]
        else:
            avg -= rune_flat[damage_type]
        avg = max(0.0, avg)
        val = avg * attack_speed
        dps[f"dps_{damage_type}"] = val
        total += val

    dps["dps_total"] = total
    dps["crit_chance"] = _numeric_from_mapping(row, "crit_chance", "Critical Hit Chance")
    return dps


def compute_displayed_weapon_dps_features(row: Mapping[str, Any]) -> dict[str, float]:
    """Build actual weapon DPS from the augmented ranges shown on the item.

    Copied weapon properties already include local modifiers, quality, and
    socket/rune effects.  User-facing DPS therefore uses those ranges directly;
    unlike :func:`compute_bow_dps_features`, it must not deflate them.
    """
    attack_speed = _numeric_from_mapping(row, "attack_speed", "Attacks per Second")
    dps: dict[str, float] = {}
    total = 0.0

    for damage_type in BOW_DAMAGE_TYPES:
        prefix = BOW_DAMAGE_PREFIX[damage_type]
        low = _numeric_from_mapping(row, f"{prefix}_damage_min")
        high = _numeric_from_mapping(row, f"{prefix}_damage_max")
        val = max(0.0, (low + high) / 2.0) * attack_speed
        dps[f"dps_{damage_type}"] = val
        total += val

    dps["dps_total"] = total
    dps["crit_chance"] = _numeric_from_mapping(row, "crit_chance", "Critical Hit Chance")
    return dps


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _write_parse_excel() -> bool:
    return _env_flag("STASHSAGE_EXPORT_PARSE_XLSX", False)


def _item_status_features_enabled() -> bool:
    return bool(
        getattr(
            _poe2trade_cfg,
            "item_status_feature_flag",
            getattr(_poe2trade_cfg, "corrupted_feature_flag", False),
        )
    )


def _item_status_feature_values(item: Mapping[str, Any]) -> dict[str, int]:
    if not _item_status_features_enabled():
        return {}
    return {
        "item_corrupted": int(bool(item.get("corrupted"))),
        "item_fractured": int(bool(item.get("fractured"))),
        "item_sanctified": int(bool(item.get("sanctified"))),
    }


def _category_from_parse_context(
    category: str | None,
    item_json_file_path: str,
    output_excel_file: str | None,
) -> str:
    if category:
        return category
    if output_excel_file:
        parent = os.path.basename(os.path.dirname(output_excel_file))
        if parent:
            return parent
    return os.path.basename(os.path.dirname(item_json_file_path))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ rolled-mod helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def parse_rolled_mod(mod_str: str) -> Tuple[str, float, float, str | None, bool, bool, bool]:
    """
    Parse a single rolled-mod string into:
      â€¢ pattern (numbers â†’ '#')
      â€¢ average roll
      â€¢ max roll
      â€¢ bucket token ('#%' / '#' / None)
      â€¢ flags: references armour, evasion, energy shield
    """
    # Normalize leading + (e.g., "+# to dexterity" -> "# to dexterity")
    # Note: previous builds accidentally double-escaped the regex, failing to strip '+'.
    raw_txt = re.sub(r'^\+\s*', '', str(mod_str).lower().strip())
    # PoE advanced copied item text can include roll ranges after the actual
    # rolled value, e.g. "88(85-109)% increased physical damage". Those ranges
    # describe possible rolls and must not become feature values.
    raw_txt = strip_advanced_roll_annotations(raw_txt)
    _meter_re = re.compile(r"\b\d+(?:\.\d+)?\s*(?:-\s*\d+(?:\.\d+)?)?\s*m\b", re.I)
    # Extract numeric rolls ignoring metre tokens by masking them first
    raw_masked = _meter_re.sub("MET", raw_txt)
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", raw_masked)]
    if nums:
        mn, mx = nums[0], nums[-1]
        avg = (mn + mx) / 2.0
    else:
        mn = mx = None
        avg = None
    # Build pattern while preserving metre tokens like '6m' or '10-20m'
    protected = _meter_re.sub(lambda m: "<<"+m.group(0)+">>", raw_txt)
    pattern = re.sub(r"\d+(?:\.\d+)?", "#", protected)
    pattern = pattern.replace("<<","" ).replace(">>","")

    bad_kw = ('recharge', 'break', 'penetrate')
    ref_def = any(t in raw_txt for t in ('armour', 'evasion', 'energy shield')) \
              and not any(b in raw_txt for b in bad_kw)

    is_armour  = 'armour'        in raw_txt and ref_def
    is_evasion = 'evasion'       in raw_txt and ref_def
    is_es      = 'energy shield' in raw_txt and ref_def

    bucket = '#%' if (ref_def and '#%' in pattern) else (
             '#'  if (ref_def and  '#' in pattern) else None)

    return pattern, avg, mx, bucket, is_armour, is_evasion, is_es


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ tag-cleanup LUT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_TAG_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\[resistances\|([^\[\]]+?)\]", r"\1"),
    (r"\[maximumresistances\|maximum elemental resistances\]", "maximum elemental resistances"),

    # attributes / charges / ailments
    (r"\[attributes\|attribute\]", "attribute"),
    (r"\[charges\|endurance charges\]", "endurance charges"),
    (r"\[charges\|frenzy charges\]",    "frenzy charges"),
    (r"\[charges\|power charges\]",     "power charges"),

    # miscellaneous
    (r"\[recoup\|recouped\]", "recouped"),
    (r"\[buffmagnitude\|magnitude\]", "magnitude"),
    (r"\[buffmagnitude\|magnitudes\]", "magnitudes"),
    (r"\[buffeffect\|effect\]", "effect"),
    (r"\[cooldownrecovery\|cooldown recovery rate\]", "cooldown recovery rate"),
    (r"\[esrechargerate\|energy shield recharge rate\]", "energy shield recharge rate"),
    (r"\[minion\|minions\]", "minions"),
    (r"\[curse\|curses\]", "curses"),
    (r"\[critical\|critical hit\]", "critical hit"),
    (r"\[criticaldamagebonus\|critical damage bonus\]", "critical damage bonus"),
    (r"\[critical damage bonus\|critical damage bonus\]", "critical damage bonus"),

    # defence / speed
    (r"\[evasion\|evasion rating\]", "evasion rating"),
    (r"\[armourbreak\|break\]", "break"),

    # leech / convert / attacks / penetration / hit
    (r"\[lifeleech\|leech\]", "leech"),
    (r"\[manaleech\|leech\]", "leech"),
    (r"\[statconversion\|convert\]", "convert"),
    (r"\[attack\|attacks\]", "attacks"),
    (r"\[penetration\|penetrates\]", "penetrates"),
    (r"\[hitdamage\|hit\]", "hit"),

    # flask / elemental / rarity
    (r"\[flask\|flasks\]", "flasks"),
    (r"\[elementaldamage\|elemental\]", "elemental"),
    (r"\[itemrarity\|rarity of items\]", "rarity of items"),

    # gameplay-specific
    (r"\[fasteresrechargestart\|faster start of energy shield recharge\]", "faster start of energy shield recharge"),
    (r"\[ailmentthreshold\|elemental ailment threshold\]", "elemental ailment threshold"),
    (r"\[stunthreshold\|stun threshold\]", "stun threshold"),
    (r"\[charm\|charms\]", "charms"),
    (r"\[slow\|slowing\]", "slowing"),
    (r"\[debuff\|debuffs\]", "debuffs"),

    # fixed typos
    (r"\[maximumresistances\|maximum lightning resistance\]", "maximum lightning resistance"),
    (r"\[maximumresistances\|maximum fire resistance\]", "maximum fire resistance"),
    (r"\[maximumresistances\|maximum cold resistance\]", "maximum cold resistance"),

    # fixed typos 20250905
    (r"\[deflect\|deflection rating\]", "deflection rating"),
    (r"\[markofabyssallord\|mark of the abyssal lord\]", "mark of the abyssal lord"),
]


def clean_mod_text(text: str) -> str:
    """Expand wiki-style tags to plain text, preferring the DISPLAY side of [x|y] â†’ y."""
    if not isinstance(text, str):
        return text
    for patt, repl in _TAG_REPLACEMENTS:
        text = re.sub(patt, repl, text, flags=re.IGNORECASE)
    # Always prefer the display side for [a|b] â†’ b
    text = re.sub(r"\[([^\[\]\|]+)\|([^\[\]\|]+)\]", r"\2", text)
    # Strip single-bracket tags
    text = re.sub(r"\[([^\[\]\|]+)\]", r"\1", text)
    return text


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ composite-expansion helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_ATTRS = ("strength", "dexterity", "intelligence")
_RES   = ("cold", "fire", "lightning", "chaos")

# precompiled regexes (case-insensitive)
_RX_DESCRATED = re.compile(r"\s*\(descrated\)\s*", re.IGNORECASE)
_RX_ATTRS     = re.compile(
    r"\bto\s+(strength|dexterity|intelligence)\s+and\s+"
    r"(strength|dexterity|intelligence)\b",
    re.IGNORECASE,
)
_RX_RESISTS   = re.compile(
    r"\bto\s+(cold|fire|lightning|chaos)\s+and\s+"
    r"(cold|fire|lightning|chaos)\s+resistances?\b",
    re.IGNORECASE,
)

def _expand_composite_mods(line: str) -> list[str]:
    """
    Remove '(descrated)' and expand combined lines into two separate lines when applicable.
    Otherwise return the (possibly cleaned) line as a single-element list.
    """
    if not isinstance(line, str) or not line.strip():
        return []
    # 1) remove literal "(descrated)"
    s = _RX_DESCRATED.sub(" ", line).strip()
    if not s:
        return []

    # 2) split +# to X and Y  (attributes)
    m = _RX_ATTRS.search(s)
    if m:
        x, y = m.group(1).lower(), m.group(2).lower()
        if x in _ATTRS and y in _ATTRS and x != y:
            # Replace the whole "to X and Y" phrase with "to X" and "to Y"
            s1 = _RX_ATTRS.sub(f"to {x.title()}", s, count=1)
            s2 = _RX_ATTRS.sub(f"to {y.title()}", s, count=1)
            return [s1, s2]

    # 3) split +#% to X and Y Resistances (elements)
    m = _RX_RESISTS.search(s)
    if m:
        x, y = m.group(1).lower(), m.group(2).lower()
        if x in _RES and y in _RES and x != y:
            s1 = _RX_RESISTS.sub(f"to {x.title()} Resistance", s, count=1)
            s2 = _RX_RESISTS.sub(f"to {y.title()} Resistance", s, count=1)
            return [s1, s2]

    return [s]


def _mod_entry_text(mod: Any) -> str | None:
    """Return the display text from either legacy string mods or API mod objects."""
    if isinstance(mod, str):
        return mod
    if isinstance(mod, Mapping):
        for key in ("description", "text", "name"):
            val = mod.get(key)
            if isinstance(val, str) and val.strip():
                return val
    return None


def _expand_and_clean_mod_list(mods: list) -> list[str]:
    """
    1) Apply clean_mod_text to each entry,
    2) remove '(descrated)',
    3) expand composite lines, and
    4) normalize whitespace.
    """
    out: list[str] = []
    for m in mods or []:
        m = _mod_entry_text(m)
        if not m:
            continue
        # Uses are state, not part of the tablet/waystone mechanic feature.
        m = re.sub(r"(?im)^\s*\d+\s+uses?\s+remaining\s*$", "", m).strip()
        if not m:
            continue
        # clean wiki tags etc.
        cleaned = clean_mod_text(m)
        expanded = _expand_composite_mods(cleaned)
        for s in expanded:
            s = re.sub(r"\s{2,}", " ", s).strip()
            if s:
                out.append(s)
    return out


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ main flattener â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def parse_item_json(
    item_json_file_path: str,
    category: str | None = None,  # kept for backwards compat; ignored
    output_excel_file: str | None = None,
    affix_observer: Callable[[Mapping[str, Any]], None] | None = None,
) -> pd.DataFrame:
    """
    Read a PoE trade-API JSON dump and return a tidy DataFrame.

    Emits:
      - price, currency, base, name
      - enchant/implicit/explicit/fractured/descrated/rune mod slots (text + parsed pattern/value)
      - quality, quality_type
      - extra_sockets
      - ar, ev, es (defences)

    When provided, ``affix_observer`` sees each accepted structured item after
    its row is built. Observer errors are warnings and never affect the rows.
    """
    with open(item_json_file_path, encoding="utf-8") as fh:
        raw = json.load(fh)

    looks_api = (
        isinstance(raw, dict) and "result" in raw
    ) or (
        isinstance(raw, list)
        and any(isinstance(x, dict) and ("item" in x or "listing" in x) for x in raw)
    )
    if not looks_api:
        return pd.DataFrame()

    entries = raw.get("result", []) if isinstance(raw, dict) else raw
    category_context = _category_from_parse_context(category, item_json_file_path, output_excel_file)
    category_norm = normalize_item_category(category_context)
    dps_weapon_context = category_norm in DPS_WEAPON_CATEGORIES

    def _slot_mods(mods, pfx, slots, rec):
        expanded = _expand_and_clean_mod_list(mods)
        for i in range(slots):
            txt = expanded[i] if i < len(expanded) else None
            rec[f"{pfx}_mod_{i+1}"] = txt
            try:
                pat, avg, *_ = (
                    parse_rolled_mod(txt)
                    if isinstance(txt, str) and txt.strip()
                    else (None, None)
                )
            except Exception as err:
                print(f"[DEBUG] parse_rolled_mod failed on {txt!r}: {err}")
                raise
            # If no numeric roll was parsed, treat presence-only mods as 1 for
            # selected prefixes (implicit/explicit/fractured/desecrated).
            if avg is None and pat is not None and pfx in {"implicit", "explicit", "fractured", "desecrated"}:
                avg = 1.0
            rec[f"{pfx}_mod_{i+1}_pattern"] = pat
            rec[f"{pfx}_mod_{i+1}_value"]   = avg

    DEFENCE_KEYS = {
        "armour": "ar",
        "armor": "ar",
        "evasion": "ev",
        "evasion rating": "ev",
        "energy shield": "es",
        # shields/bucklers: expose block chance alongside defences
        "block": "block",
        "block chance": "block",
    }

    rows: List[Dict] = []
    for e in entries:
        try:
            itm = e.get("item", e)
            listing = (e.get("listing") or {}) if isinstance(e, Mapping) else {}
            rec: Dict[str, object] = {
                "price":    listing.get("price", {}).get("amount"),
                "currency": listing.get("price", {}).get("currency"),
                "name":     itm.get("name"),
                "base":     itm.get("baseType") or itm.get("base"),
            }
            if category_norm == "waystone":
                for candidate in (rec.get("base"), rec.get("name"), itm.get("baseType")):
                    tier_match = re.search(r"(?i)\bWaystone\s*\(\s*Tier\s*(\d+)\s*\)", str(candidate or ""))
                    if tier_match:
                        rec["waystone_tier"] = int(tier_match.group(1))
                        break
            if supports_extra_socket_feature(category_context):
                rec["extra_sockets"] = extra_socket_count(category_context, len(itm.get("sockets") or []))
            rec.update(_item_status_feature_values(itm))

            stash_info = listing.get("stash") or {}
            if isinstance(stash_info, Mapping):
                rec["stash_name"] = stash_info.get("name", "")
                rec["stash_x"] = stash_info.get("x")
                rec["stash_y"] = stash_info.get("y")
            else:
                rec["stash_name"] = ""
                rec["stash_x"] = None
                rec["stash_y"] = None

            if buyout_only:
                ltype = listing.get("price", {}).get("type")
                if not (isinstance(ltype, str) and ltype.startswith("~b/o")):
                    continue

            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ write per-slot groups (no merging) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            all_mod_lists = (
                itm.get("enchantMods", []), itm.get("implicitMods", []),
                itm.get("explicitMods", []), itm.get("fracturedMods", []),
                itm.get("desecratedMods", []), itm.get("runeMods", []),
            )
            for mod_list in all_mod_lists:
                for mod in mod_list or []:
                    use_match = re.search(r"(?im)^\s*(\d+)\s+uses?\s+remaining\s*$", _mod_entry_text(mod))
                    if use_match:
                        rec["remaining_uses"] = int(use_match.group(1))
                        break
                if "remaining_uses" in rec:
                    break

            _slot_mods(itm.get("enchantMods",   []), "enchant",   3, rec)
            _slot_mods(itm.get("implicitMods",  []), "implicit",  3, rec)
            _slot_mods(itm.get("explicitMods",  []), "explicit", 10, rec)
            _slot_mods((itm.get("fracturedMods", []) or [])[:3], "fractured", 3, rec)
            _slot_mods((itm.get("desecratedMods", []) or [])[:3], "desecrated", 3, rec)
            _slot_mods(itm.get("runeMods",      []), "rune",      6, rec)

            # properties
            for prop in itm.get("properties", []):
                nm   = clean_mod_text(prop.get("name", "") or "").strip()
                vals = prop.get("values", [[]])
                rv   = vals[0][0] if vals and isinstance(vals[0], list) and vals[0] else None

                # plain quality
                if re.fullmatch(r"quality", nm, flags=re.I) and rv is not None:
                    m = re.search(r"([+-]?\d+(?:\.\d+)?)", str(rv))
                    if m:
                        rec["quality"] = float(m.group(1))
                    continue

                # typed quality
                mqual = re.match(r"^quality\s*\(([^)]+)\s+modifiers\)$", nm, flags=re.I)
                if mqual and rv is not None:
                    rec["quality_type"] = mqual.group(1).lower()
                    m = re.search(r"([+-]?\d+(?:\.\d+)?)", str(rv))
                    if m:
                        rec["quality"] = float(m.group(1))
                    continue

                if category_norm == "waystone":
                    waystone_properties = {
                        "item rarity": "waystone_item_rarity",
                        "pack size": "waystone_pack_size",
                        "monster rarity": "waystone_monster_rarity",
                        "monster effectiveness": "waystone_monster_effectiveness",
                        "waystone drop chance": "waystone_drop_chance",
                    }
                    feature_name = waystone_properties.get(nm.lower())
                    if feature_name and rv is not None:
                        m = re.search(r"([+-]?\d+(?:\.\d+)?)", str(rv))
                        if m:
                            rec[feature_name] = float(m.group(1))
                        continue

                # defences
                key = DEFENCE_KEYS.get(nm.lower())
                if key and rv is not None:
                    # Normalize numeric extraction for block chance; keep others as-is
                    if key == "block":
                        m = re.search(r"([+-]?\d+(?:\.\d+)?)", str(rv))
                        if m:
                            rec[key] = float(m.group(1))
                        else:
                            rec[key] = rv
                    else:
                        rec[key] = rv

                if dps_weapon_context and rv is not None:
                    nm_l = nm.lower()
                    if nm_l in {"critical hit chance", "critical chance"}:
                        rec["crit_chance"] = _numeric_from_mapping({"v": rv}, "v")
                        continue
                    if nm_l == "attacks per second":
                        rec["attack_speed"] = _numeric_from_mapping({"v": rv}, "v")
                        continue

                    direct_type = None
                    for damage_type in BOW_DAMAGE_TYPES:
                        label = "physical" if damage_type == "physical" else damage_type
                        if f"{label} damage" in nm_l:
                            direct_type = damage_type
                            break

                    if direct_type and "elemental damage" not in nm_l:
                        parsed = parse_damage_range(rv)
                        if parsed is not None:
                            _add_bow_damage_range(rec, direct_type, parsed[0], parsed[1])
                        continue

                    if "elemental damage" in nm_l:
                        for val_pair in vals or []:
                            if not (isinstance(val_pair, list) and val_pair):
                                continue
                            parsed = parse_damage_range(val_pair[0])
                            if parsed is None:
                                continue
                            try:
                                damage_type = _ELEMENT_VALUE_TYPES.get(int(val_pair[1]))
                            except Exception:
                                damage_type = None
                            if damage_type in {"fire", "cold", "lightning"}:
                                _add_bow_damage_range(rec, damage_type, parsed[0], parsed[1])

            # grantedSkills â†’ (skill_pattern, skill_value) [first only]
            try:
                gskills: list[Dict[str, Any]] = itm.get("grantedSkills", []) or []
                if gskills:
                    vs = gskills[0].get("values", [])
                    label = vs[0][0] if vs and isinstance(vs[0], list) and vs[0] else None
                    if isinstance(label, str) and label:
                        lab_norm = clean_mod_text(label).lower()
                        # normalize: drop leading 'grants skill:' or 'grants skills:' prefix
                        lab_norm = re.sub(r"^\s*grants\s+skills?\s*:\s*", "", lab_norm, flags=re.I)
                        skill_pat = re.sub(r"\d+(?:\.\d+)?", "#", lab_norm)
                        m = re.search(r"(\d+(?:\.\d+)?)", lab_norm)
                        lvl = float(m.group(1)) if m else None
                        rec["skill_pattern"] = skill_pat
                        if lvl is not None:
                            rec["skill_value"] = lvl
            except Exception:
                pass

            rows.append(rec)
            if affix_observer is not None:
                # Catalog extraction is an observational side channel. It must
                # never remove or mutate a training row if malformed structured
                # modifier metadata is encountered.
                try:
                    affix_observer(itm)
                except Exception as observer_err:
                    print(
                        f"[WARN] Affix catalog observer failed for "
                        f"{itm.get('name') or itm.get('baseType') or '(unknown item)'}: "
                        f"{observer_err!r}"
                    )

        except Exception as err:
            print(f"âš ï¸  Skipping entry in {os.path.basename(item_json_file_path)}: {err!r}")

    df = pd.DataFrame(rows)

    # ensure canonical lowercase columns exist
    canonical_cols = ["quality", "quality_type"]
    if supports_extra_socket_feature(category_context):
        canonical_cols.append("extra_sockets")
    if _item_status_features_enabled():
        canonical_cols.extend(ITEM_STATUS_FEATURES)
    canonical_cols.extend(["ar", "ev", "es", "skill_pattern", "skill_value"])
    if dps_weapon_context:
        canonical_cols.extend([*BOW_RAW_STAT_COLUMNS, "crit_chance"])
    for col in canonical_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # remove unwanted rows (allocates / bears / on corruption)
    # these are mod statuses, not item statuses -- desecrated/corrupted/fractured statuses don't impact scraped data
    for pfx, cnt in (("explicit", 10), ("enchant", 3)):
        cols = [f"{pfx}_mod_{i+1}" for i in range(cnt)]
        if set(cols).issubset(df.columns) and not df.empty:
            s = df[cols].astype(str)
            bad = (
                s.apply(lambda c: c.str.contains(r"allocates", case=False, regex=True))
                | s.apply(lambda c: c.str.contains(r"bears", case=False, regex=True))  # abyssal lord
                | s.apply(lambda c: c.str.contains(r"on corruption", case=False, regex=True))
            ).any(axis=1)
            df = df[~bad]

    # drop helper-only columns that should never be emitted
    if "listing_type" in df.columns:
        df.drop(columns=["listing_type"], inplace=True, errors="ignore")

    # final ordering
    front = [
        "price", "currency", "base", "name",
        "quality", "quality_type", "extra_sockets",
        *ITEM_STATUS_FEATURES,
        "ar", "ev", "es",
        *BOW_RAW_STAT_COLUMNS, "crit_chance",
        "skill_pattern", "skill_value",
    ]
    existing_front = [c for c in front if c in df.columns]
    others = [c for c in df.columns if c not in existing_front]
    df = df[existing_front + others]

    if df.empty:
        print("âš ï¸  parse_item_json produced an EMPTY DataFrame.")

    if output_excel_file:
        os.makedirs(os.path.dirname(output_excel_file) or ".", exist_ok=True)
        df.to_parquet(os.path.splitext(output_excel_file)[0] + ".parquet", index=False)
        if _write_parse_excel():
            df.to_excel(output_excel_file, index=False)
    # Always report how many items were parsed from this JSON file
    try:
        fname = os.path.basename(item_json_file_path)
    except Exception:
        fname = str(item_json_file_path)
    print(f"Parsed {len(df)} items from {fname}")

    return df



