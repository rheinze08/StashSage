# File: poe2trade/utils/gui_utils.py
# · updated 2025-09-07 — skip flat/% defence patterns in modifiers; keep *_NORM only
# · updated 2025-09-16 — expand joint attribute/resistance lines; strip (descrated)/(desecrated)

from __future__ import annotations

import functools
import json
import os
import re
import pprint
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from poe2trade import poe2trade_root, jewel_list
from poe2trade.utils.parse_utils import (
    BOW_DPS_COLUMNS,
    DPS_WEAPON_OMITTED_MOD_PATTERNS,
    BOW_RAW_STAT_COLUMNS,
    DPS_WEAPON_CATEGORIES,
    UNSUPPORTED_WAYSTONE_MESSAGE,
    WAYSTONE_OMITTED_MODEL_FEATURES,
    _item_status_features_enabled,
    compute_bow_dps_features,
    compute_displayed_weapon_dps_features,
    extra_socket_count,
    normalize_item_category,
    parse_damage_range,
    parse_rolled_mod,
    strip_advanced_roll_annotations,
    supports_extra_socket_feature,
    waystone_segment,
)
from poe2trade.utils.ml_super_utils import call_ml as call_ml_super
from poe2trade.utils.ml_unsuper_utils import call_ml as call_ml_unsuper

_DEBUG = os.environ.get("STASHSAGE_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")


def _dbg(*args, **kwargs) -> None:
    if _DEBUG:
        print(*args, **kwargs)


def _copied_item_status_feature_values(text: str) -> dict[str, int]:
    if not _item_status_features_enabled():
        return {}
    return {
        "item_corrupted": int(bool(re.search(r"^\s*Corrupted\s*$", text, re.M | re.I))),
        "item_fractured": int(bool(re.search(r"^\s*Fractured Item\s*$", text, re.M | re.I))),
        "item_sanctified": int(bool(re.search(r"^\s*Sanctified\s*$", text, re.M | re.I))),
    }


@dataclass
class PreparedItem:
    text: str
    raw_parsed: dict
    features: pd.DataFrame
    category: str
    segment: str | None
    model_category: str
    model_supported: bool = True
    unsupported_reason: str | None = None
    display_features: pd.DataFrame | None = None

# ───────────────────────── 1.  QUALITY-LOOKUP TABLE ─────────────────────────
# The quality lookup is a static 12-row table. It is shipped as JSON and built
# lazily on first access so that importing this module does NOT pull in pandas'
# Excel reader (openpyxl), which adds ~400–900 ms to cold startup.
@functools.lru_cache(maxsize=1)
def _get_q_map() -> dict[str, list[str]]:
    """Return {quality_title: [mod_patterns]}, loaded once and cached.

    Prefers the prebuilt JSON sidecar; falls back to the legacy Excel file
    (rebuilding via parse_rolled_mod) if the JSON is missing.
    """
    files_dir = Path(poe2trade_root) / "db" / "files"
    json_path = files_dir / "ring_amulet_quality_lookup.json"
    if json_path.is_file():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Legacy fallback: build from the Excel file (imports openpyxl on demand).
    raw = pd.read_excel(files_dir / "ring_amulet_quality_lookup.xlsx")
    q_key = raw.columns[0]
    patt_cols = [c for c in raw.columns if c != q_key]
    header_map = {c: parse_rolled_mod(str(c))[0] for c in patt_cols}
    return {
        str(r[q_key]).strip().title(): [header_map[c] for c in patt_cols if r[c]]
        for _, r in raw.iterrows()
    }


def quality_type_modifier_patterns(quality_type: object) -> frozenset[str]:
    """Return canonical patterns affected by one jewellery quality type.

    Runtime feature preparation and Craft Oracle must share this exact lookup:
    the former removes typed-quality amplification from copied values, while
    the latter predicts which newly appended affix would receive it.
    """
    name = str(quality_type or "").strip().title()
    if not name:
        return frozenset()
    return frozenset(
        str(pattern).strip().lower()
        for pattern in _get_q_map().get(name, [])
        if str(pattern).strip()
    )

# ─────────────────── 2. CONSTANTS / PATTERN SETS ────────────────────────────
PCT_DEFENCE_PATTERNS = {
    "#% increased armour",
    "#% increased armour and energy shield",
    "#% increased armour and evasion",
    "#% increased energy shield",
    "#% increased evasion and energy shield",
    "#% increased evasion rating",
    "#% increased armour, evasion and energy shield",
}
FLAT_DEFENCE_PATTERNS = {
    "# to armour",
    "# to evasion rating",
    "# to maximum energy shield",
}

# include fractured/desecrated/descrated so lingering markers are dropped
_TOKEN_RE = re.compile(r'\((implicit|rune|enchant|augmented|fractured|desecrated|descrated)\)', re.I)

# joint-line expansion sets/regexes
_ATTRS = ("strength", "dexterity", "intelligence")
_RES   = ("cold", "fire", "lightning", "chaos")
_RX_ATTRS = re.compile(
    r"\bto\s+(strength|dexterity|intelligence)\s+and\s+(strength|dexterity|intelligence)\b",
    re.I,
)
_RX_RESISTS = re.compile(
    r"\bto\s+(cold|fire|lightning|chaos)\s+and\s+(cold|fire|lightning|chaos)\s+resistances?\b",
    re.I,
)
# Any PoE advanced-description header, such as '{ Prefix Modifier ... }',
# '{ Enhancement }', or '{ Corruption Enhancement ... }'.
_RX_ADVANCED_AFFIX_LINE = re.compile(r"^\{\s*(.*?)\s*\}\s*$", re.I)
_RX_REMAINING_USES = re.compile(r"^\s*(\d+)\s+uses?\s+remaining\s*$", re.I)
# ─────────────────────────── 3. HELPERS ──────────────────────────────────────
def _clean_line(txt: str) -> str:
    txt = strip_advanced_roll_annotations(txt)
    txt = _TOKEN_RE.sub("", txt).replace("--------", "")
    txt = re.sub(r"[()]", "", txt)
    return re.sub(r"\s+", " ", txt).strip()

def _set_bow_damage_range(row: dict, damage_type: str, value: str) -> bool:
    parsed = parse_damage_range(value)
    if parsed is None:
        return False
    prefix = "phys" if damage_type == "physical" else damage_type
    row[f"{prefix}_damage_min"] = parsed[0]
    row[f"{prefix}_damage_max"] = parsed[1]
    return True

def _set_bow_elemental_damage_ranges(row: dict, value: str) -> bool:
    handled = False
    for part in str(value or "").split(","):
        type_match = re.search(r"\b(fire|cold|lightning)\b", part, re.I)
        if not type_match:
            continue
        handled = _set_bow_damage_range(row, type_match.group(1).lower(), part) or handled
    return handled

def _affix_header_type(line: str) -> str | None:
    """Map a PoE advanced-description header to a runtime copy-parser slot.

    Headers tag the mod line(s) that follow. The slot is read from the words
    *before* "Modifier":
      • '{ Implicit Modifier — ... }'          -> 'implicit'
      • '{ Corrupted Implicit Modifier }'      -> 'implicit'
      • '{ Enchant Modifier }'                 -> 'enchant'
      • '{ Rune Modifier }'                    -> 'rune'
      • '{ Prefix/Suffix Modifier "..." }'     -> 'explicit'
      • '{ Desecrated/Fractured/Crafted ... }' -> 'explicit'
    Unknown braced headers return "ignore" so metadata cannot leak into
    explicit modifier features.
    """
    m = _RX_ADVANCED_AFFIX_LINE.match(str(line or "").strip())
    if not m:
        return None
    kind = re.sub(r"\s+", " ", m.group(1).lower()).strip()
    if "corruption enhancement" in kind:
        return "explicit"
    if kind.startswith("enhancement"):
        return "ignore"
    if "implicit modifier" in kind:
        return "implicit"
    if "enchant modifier" in kind:
        return "enchant"
    if "rune modifier" in kind:
        return "rune"
    if any(token in kind for token in (
        "prefix modifier",
        "suffix modifier",
        "fractured modifier",
        "desecrated modifier",
        "descrated modifier",
        "crafted modifier",
    )):
        return "explicit"
    return "ignore"

def _is_advanced_affix_metadata(line: str) -> bool:
    """PoE advanced descriptions include affix headers; they are not item mods."""
    return _affix_header_type(line) is not None

# A header names its side ('{ Prefix Modifier "Rotund" ... }') and, for ordinary
# affixes, the contributor identity.  Crafted/fractured/desecrated headers keep
# the side word, so they are counted against affix capacity like any other.
AFFIX_METADATA_KEYS = (
    "explicit_affix_count",
    "explicit_prefix_count",
    "explicit_suffix_count",
    "explicit_affix_sides_known",
    "explicit_affix_names",
)
_RX_AFFIX_HEADER_SIDE = re.compile(r"\b(prefix|suffix)\s+modifier\b", re.I)
_RX_AFFIX_HEADER_NAME = re.compile(
    r'\b(?:prefix|suffix)\s+modifier\s+"(?P<name>[^"]+)"', re.I
)


def _affix_header_side(line: str) -> str | None:
    """Return 'prefix'/'suffix' when a header states which side it occupies."""
    m = _RX_ADVANCED_AFFIX_LINE.match(str(line or "").strip())
    if not m:
        return None
    side = _RX_AFFIX_HEADER_SIDE.search(m.group(1))
    return side.group(1).lower() if side else None


def _affix_header_name(line: str) -> str:
    """Return the quoted contributor identity from an affix header, if any."""
    m = _RX_ADVANCED_AFFIX_LINE.match(str(line or "").strip())
    if not m:
        return ""
    name = _RX_AFFIX_HEADER_NAME.search(m.group(1))
    return re.sub(r"\s+", " ", name.group("name")).strip() if name else ""

def _inline_slot_for(line: str) -> str | None:
    l = str(line or "").lower()
    if "(implicit)" in l:
        return "implicit"
    if "(enchant)" in l:
        return "enchant"
    if "(rune)" in l:
        return "rune"
    if any(tag in l for tag in ("(fractured)", "(desecrated)", "(descrated)", "(crafted)")):
        return "explicit"
    return None

def _expand_composite_line(s: str) -> list[str]:
    """
    Expand a single mod line into 1..2 lines:
      • remove (descrated)/(desecrated) marker if present (case-insensitive)
      • split '+# to X and Y' (attributes)
      • split '+#% to X and Y Resistances' (elements)
    Return a list of expanded lines (tokens like '(implicit)' are preserved as-is).
    """
    if not isinstance(s, str) or not s.strip():
        return []
    # remove literal '(descrated)' and '(desecrated)' only (keep other tags for slot routing)
    s = re.sub(r"\((?:descrated|desecrated)\)", "", s, flags=re.I)

    # attributes
    m = _RX_ATTRS.search(s)
    if m:
        x, y = m.group(1).lower(), m.group(2).lower()
        if x in _ATTRS and y in _ATTRS and x != y:
            s1 = _RX_ATTRS.sub(f"to {x.title()}", s, count=1)
            s2 = _RX_ATTRS.sub(f"to {y.title()}", s, count=1)
            return [s1, s2]

    # resistances
    m = _RX_RESISTS.search(s)
    if m:
        x, y = m.group(1).lower(), m.group(2).lower()
        if x in _RES and y in _RES and x != y:
            s1 = _RX_RESISTS.sub(f"to {x.title()} Resistance", s, count=1)
            s2 = _RX_RESISTS.sub(f"to {y.title()} Resistance", s, count=1)
            return [s1, s2]

    return [s]

# ────────────────────── 4. CLIPBOARD → RAW ROW ───────────────────────────────
def parse_copied_item_text(text: str) -> dict:
    """
    Parses clipboard dump into a dict of:
      - metadata: category, name, base stats, corruption, extra_sockets
      - raw mod lines in fixed slots
    """
    _dbg("\n[DEBUG] raw clipboard\n", text)
    text = re.sub(r'~(?:price|b/​o).*$','', text, flags=re.I|re.S).strip()

    row = {
        "Item Category": "",
        "Item Name": "",
        "Quality": 0,
        "Armour": 0,
        "Evasion Rating": 0,
        "Energy Shield": 0,
        "Corrupted": "Yes" if re.search(r"^\s*Corrupted\s*$", text, re.M) else "No",
    }
    use_match = re.search(r"(?im)^\s*(\d+)\s+uses?\s+remaining\s*$", text)
    if use_match:
        row["remaining_uses"] = int(use_match.group(1))
    row.update(_copied_item_status_feature_values(text))
    tier_match = re.search(r"(?im)\bWaystone\s*\(\s*Tier\s*(\d+)\s*\)", text)
    if tier_match:
        row["waystone_tier"] = int(tier_match.group(1))

    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not _RX_REMAINING_USES.match(ln)]
    raw_socket_count = 0
    try:
        cut = next(i for i, ln in enumerate(lines)
                   if re.match(r"^Item Level:\s*\d+", ln, re.I))
    except StopIteration:
        cut = len(lines)
    meta_lines, mod_lines = lines[:cut+1], lines[cut+1:]

    # ── META SECTION ────────────────────────────────────────────────────
    reading_name = False
    for ln in meta_lines:
        # 1) Item Class → singular folder name
        if m := re.match(r"^Item Class:\s*(.*)$", ln, re.I):
            cls = m.group(1).strip().lower().replace(" ", "_")
            cls = {
                "staves": "staff",
                "staffs": "staff",
                "scepters": "sceptre",
                "sceptres": "sceptre",
                "bows": "bow",
            }.get(cls, cls)
            if cls not in ("boots","gloves","helmet","body_armour"):
                cls = cls.rstrip("s")
            cls = normalize_item_category(cls)
            row["Item Category"] = cls
            continue

        # 2) Rarity Rare → next lines name
        if re.match(r"^Rarity:\s*Rare", ln, re.I):
            reading_name = True
            continue
        if reading_name:
            if ln.startswith("--------") or re.match(
                r"^(Quality|Armour|Evasion|Energy Shield|Physical Damage|Elemental Damage|Fire Damage|Cold Damage|Lightning Damage|Chaos Damage|Critical Hit Chance|Attacks per Second|Requires|Sockets|Item Level)",
                ln, re.I
            ):
                reading_name = False
            else:
                row["Item Name"] += ln + " "
            continue

        # 3) Plain Quality
        if m := re.match(r"^Quality:\s*\+?(\d+)%", ln, re.I):
            row["Quality"] = int(m.group(1))
            continue

        # 4) Jewellery‐type Quality
        ln_clean = re.sub(r"\(augmented\)", "", ln, flags=re.I).strip()
        if m := re.match(
            r"^Quality\s*\(([^)]+)\s+Modifiers\):\s*\+?(\d+)%", ln_clean, re.I
        ):
            row["Quality_Type"]     = m.group(1).title()
            row["Quality_Type_Pct"] = int(m.group(2))
            continue

        # 5) Base stats. Block chance is a shield/buckler base stat only.
        cat_now = str(row.get("Item Category", "")).strip().lower()
        if cat_now == "waystone":
            waystone_properties = {
                "item rarity": "waystone_item_rarity",
                "pack size": "waystone_pack_size",
                "monster rarity": "waystone_monster_rarity",
                "monster effectiveness": "waystone_monster_effectiveness",
                "waystone drop chance": "waystone_drop_chance",
            }
            prop_match = re.match(r"^([^:]+):\s*([+-]?\d+(?:\.\d+)?)", ln)
            if prop_match:
                property_name = prop_match.group(1).strip().lower()
                if property_name == "revives available":
                    continue
                feature_name = waystone_properties.get(property_name)
                if feature_name:
                    row[feature_name] = float(prop_match.group(2))
                    continue
        m_block = re.match(r"^Block\s*chance:\s*(\d+)\s*%", ln, re.I)
        if m_block and cat_now in ("shield", "buckler"):
            try:
                row["block"] = int(m_block.group(1))
            except Exception:
                pass
        elif m_block:
            continue
        else:
            handled_bow_stat = False
            if cat_now in DPS_WEAPON_CATEGORIES:
                damage_match = re.match(
                    r"^(Physical|Fire|Cold|Lightning|Chaos)\s+Damage:\s*(.+)$",
                    ln,
                    re.I,
                )
                if damage_match:
                    damage_type = damage_match.group(1).lower()
                    if _set_bow_damage_range(row, damage_type, damage_match.group(2)):
                        handled_bow_stat = True
                elif elemental_match := re.match(r"^Elemental\s+Damage:\s*(.+)$", ln, re.I):
                    if _set_bow_elemental_damage_ranges(row, elemental_match.group(1)):
                        handled_bow_stat = True
                elif m := re.match(r"^Critical Hit Chance:\s*([+-]?\d+(?:\.\d+)?)\s*%", ln, re.I):
                    row["crit_chance"] = float(m.group(1))
                    handled_bow_stat = True
                elif m := re.match(r"^Attacks per Second:\s*([+-]?\d+(?:\.\d+)?)", ln, re.I):
                    row["attack_speed"] = float(m.group(1))
                    handled_bow_stat = True
            if handled_bow_stat:
                continue
            for key,patt in (
                ("Armour",r"^Armour:\s*(\d+)"),
                ("Evasion Rating",r"^Evasion Rating:\s*(\d+)"),
                ("Energy Shield",r"^Energy Shield:\s*(\d+)")
            ):
                if m := re.match(patt, ln, re.I):
                    row[key] = int(m.group(1))
                    break

        # 6) Sockets line (for rare boots/gloves/helmets)
        if ln.lower().startswith("sockets:"):
            raw_socket_count = ln.split(":",1)[1].upper().count("S")

    row["Item Name"] = row["Item Name"].strip()
    if supports_extra_socket_feature(row.get("Item Category")):
        row["extra_sockets"] = extra_socket_count(row.get("Item Category"), raw_socket_count)

    # ── MOD LINES ────────────────────────────────────────────────────────
    implicit, enchant, rune, explicit = [], [], [], []
    current_affix = None  # affix type from the most recent '{ ... Modifier }' header
    # One *affix* is not one parsed slot.  Composite lines ('+# to Str and Int')
    # expand into several slots, and a hybrid affix prints several lines under a
    # single header.  Group explicit source lines by their originating header so
    # affix-level consumers can count affixes instead of feature slots.
    current_affix_group: int | None = None
    header_index = 0
    affix_groups: dict[int, dict[str, str]] = {}
    ungrouped_explicit_lines = 0
    for ln in mod_lines:
        # strip fractured/desecrated/descrated markers but keep other tags for slot routing
        clean0 = re.sub(r"\((fractured|desecrated|descrated)\)", "", ln, flags=re.I).strip()
        lw = clean0.lower()

        # advanced-description affix header: record the type, then skip the header line
        header_type = _affix_header_type(clean0)
        if header_type is not None:
            current_affix = header_type
            header_index += 1
            current_affix_group = header_index
            if header_type == "explicit":
                affix_groups[header_index] = {
                    "side": _affix_header_side(clean0) or "",
                    "name": _affix_header_name(clean0),
                    "seen": "",
                }
            continue

        # dividers reset the active header so a stale type can't leak onto later mods
        if clean0.startswith("--------"):
            current_affix = None
            current_affix_group = None
            continue

        # skip flags/noise and non-mod text
        _bad_substrings = (
            "allocates ",
            "can only be equipped if you are wielding a bow",
            "place into an allocated jewel socket",
        )
        if (
            lw in ("corrupted", "fractured item")
            or lw.startswith("note:")
            or any(sub in lw for sub in _bad_substrings)
        ):
            continue
        if not re.search(r"\d", clean0) and str(row.get("Item Category", "")).lower() not in {"tablet", "waystone"}:
            continue

        # expand composites before slotting
        inline_slot = _inline_slot_for(clean0)
        slot_name = inline_slot or current_affix
        if slot_name in (None, "ignore"):
            continue

        expanded = _expand_composite_line(clean0)

        # classify by inline tag first; otherwise fall back to the active header
        # type ('{ Implicit Modifier }' etc.). prefix/suffix headers → explicit.
        slots = {
            "implicit": implicit,
            "enchant": enchant,
            "rune": rune,
            "explicit": explicit,
        }
        slot = slots.get(slot_name)
        if slot is None:
            continue

        if slot_name == "explicit":
            # An inline-tagged line in a basic copy has no header to group it,
            # so it counts as its own affix.
            group = current_affix_group if inline_slot is None else None
            if group is not None and group in affix_groups:
                affix_groups[group]["seen"] = "1"
            else:
                ungrouped_explicit_lines += 1

        for candidate in expanded:
            slot.append(candidate)

    observed_groups = [meta for meta in affix_groups.values() if meta["seen"]]
    row["explicit_affix_count"] = len(observed_groups) + ungrouped_explicit_lines
    row["explicit_prefix_count"] = sum(1 for m in observed_groups if m["side"] == "prefix")
    row["explicit_suffix_count"] = sum(1 for m in observed_groups if m["side"] == "suffix")
    # Sides are trustworthy only when every explicit affix on the item declared
    # one.  Basic copies and side-less headers leave capacity unknown.
    row["explicit_affix_sides_known"] = bool(observed_groups) and not ungrouped_explicit_lines and all(
        m["side"] for m in observed_groups
    )
    row["explicit_affix_names"] = tuple(
        name for m in observed_groups if (name := m["name"])
    )

    # fixed-slot assignment
    for i, ln in enumerate(implicit[:3],  1): row[f"implicit_mod_{i}"] = ln
    for i, ln in enumerate(enchant[:3],   1): row[f"enchant_mod_{i}"]  = ln
    for i, ln in enumerate(rune[:6],      1): row[f"rune_mod_{i}"]     = ln
    for i, ln in enumerate(explicit[:10], 1): row[f"explicit_mod_{i}"] = ln

    if _DEBUG:
        _dbg("\n[DEBUG] parse_copied_item_text -> row\n")
        pprint.pprint(row, width=110, sort_dicts=False)
    return row

# ─────────────────── 5. RAW-MOD → (PATTERN, VALUE) ──────────────────────────
def process_all_mods(row: dict) -> dict:
    """
    Turn each raw slot into:
      - <prefix>_mod_i_pattern
      - <prefix>_mod_i_value
    """
    # Normalized category for shield/buckler filtering
    cat_norm = str(row.get("Item Category", "")).strip().lower().replace(" ", "_")
    if cat_norm in ("shields", "bucklers"):  # plural to singular
        cat_norm = cat_norm[:-1]

    for prefix, max_i in (("implicit",3),("enchant",3),("rune",6),("explicit",10)):
        for i in range(1, max_i+1):
            raw = row.pop(f"{prefix}_mod_{i}", None)
            if not raw:
                continue
            # For Shield/Buckler: ignore skill grants like "Grants Skill: Raise Shield/Parry"
            if cat_norm in ("shield", "buckler"):
                rl = str(raw).lower()
                if rl.startswith("grants skill:") and ("raise shield" in rl or "parry" in rl):
                    continue
            # Tablet/waystone descriptions may carry this state line alongside
            # the mechanic text. It is a dedicated numeric feature, never a
            # modifier-pattern suffix.
            raw_without_uses = re.sub(r"(?im)^\s*\d+\s+uses?\s+remaining\s*$", "", str(raw)).strip()
            if not raw_without_uses:
                continue
            pat, avg, *_ = parse_rolled_mod(_clean_line(raw_without_uses))
            if avg is None and str(row.get("Item Category", "")).lower() in {"tablet", "waystone"}:
                avg = 1.0
            # Normalize skill grant prefix so it matches model features
            if isinstance(pat, str):
                import re as _re
                pat = _re.sub(r"^\s*grants\s+skills?\s*:\s*", "", pat, flags=_re.I)
            if "(augmented)" in raw.lower():
                avg /= 20.0
            row[f"{prefix}_mod_{i}_pattern"] = re.sub(r"\s+"," ", pat).strip()
            row[f"{prefix}_mod_{i}_value"]   = round(float(avg),4)
            if prefix == "rune":
                parsed_range = parse_damage_range(_clean_line(raw))
                if parsed_range is not None:
                    row[f"{prefix}_mod_{i}_min"] = parsed_range[0]
                    row[f"{prefix}_mod_{i}_max"] = parsed_range[1]
    return row

# ───── 6. JEWELLERY QUALITY‐TYPE DEFLATOR ──────────────────────────────────
def _deflate_quality_type_modifiers(row: dict) -> dict:
    cat = str(row.get("Item Category","")).lower().replace(" ", "_")
    if cat in ("rings", "amulets", "belts"):
        cat = cat[:-1]
    if cat not in ("ring", "amulet", "belt"):
        return row

    qtype = row.get("Quality_Type")
    qpct  = row.get("Quality_Type_Pct")
    if not qtype or qpct is None:
        return row

    pats   = quality_type_modifier_patterns(qtype)
    factor = 1.0 + qpct/100.0
    for i in range(1,11):
        pkey, vkey = f"explicit_mod_{i}_pattern", f"explicit_mod_{i}_value"
        if row.get(pkey) in pats and vkey in row:
            row[vkey] = round(float(row[vkey]) / factor, 4)
    return row

# ───── 7. ARMOUR DEFENCE NORMALISER ────────────────────────────────────────
def deflator_and_normaliser(row: dict) -> dict:
    cat = str(row.get("Item Category","")).lower().replace(" ", "_")
    # Normalize common plurals/aliases
    if cat == "foci":
        cat = "focus"
    if cat == "shields":
        cat = "shield"
    if cat == "bucklers":
        cat = "buckler"
    if cat == "helmets":
        cat = "helmet"
    if cat == "body_armours":
        cat = "body_armour"
    cat = normalize_item_category(cat)
    if cat in DPS_WEAPON_CATEGORIES:
        model_dps = compute_bow_dps_features(row)
        row.update(compute_displayed_weapon_dps_features(row))
        for key, value in model_dps.items():
            row[f"_model_{key}"] = value
        return row
    # Treat Focus, Shield, and Buckler as armour-like for UI normalisation
    if cat not in ("boots","gloves","helmet","body_armour","shield","buckler","focus"):
        return row

    Q = float(row.get("Quality",0) or 0)

    EM = max(
        (
            float(row.get(f"{pfx}_mod_{i}_value",0) or 0)
            for pfx in ("explicit","implicit","enchant")
            for i in range(1,11)
            if row.get(f"{pfx}_mod_{i}_pattern","") in PCT_DEFENCE_PATTERNS
        ),
        default=0.0
    )
    row["explicit_mod_%"] = EM

    RM = 0.0
    tgt = "#% increased armour, evasion and energy shield"
    for i in range(1,7):
        if row.get(f"rune_mod_{i}_pattern") == tgt:
            RM = float(row.get(f"rune_mod_{i}_value",0) or 0)
            break
    row["rune_mod_%"] = RM

    flatA = flatE = flatS = 0.0
    for pfx in ("explicit","implicit","enchant"):
        for i in range(1,11):
            pat = row.get(f"{pfx}_mod_{i}_pattern","")
            val = float(row.get(f"{pfx}_mod_{i}_value",0) or 0)
            if   pat=="# to armour":                flatA += val
            elif pat=="# to evasion rating":        flatE += val
            elif pat=="# to maximum energy shield": flatS += val

    A  = float(row.get("Armour",0) or 0)
    Ev = float(row.get("Evasion Rating",0) or 0)
    Es = float(row.get("Energy Shield",0) or 0)
    denom = (1 + Q/100)*(1 + (EM + RM)/100)

    if denom:
        # use lowercased normalized defence keys
        row["ar_norm"] = (A/denom - flatA + flatA)*(1 + EM/100)
        row["ev_norm"] = (Ev/denom - flatE + flatE)*(1 + EM/100)
        row["es_norm"] = (Es/denom - flatS + flatS)*(1 + EM/100)

    # For shields/bucklers, the copied "Block chance" line is already the
    # augmented displayed value, so block_norm carries the encoded block affix.
    if cat in ("shield","buckler"):
        try:
            blk = float(row.get("block", 0) or 0)
        except (TypeError, ValueError):
            blk = 0.0
        row["block_norm"] = blk

    return row

# ───── 8. FLATTEN & COMBINE PATTERNS ───────────────────────────────────────
def flatten_all_mod_patterns(row: dict) -> None:
    """
    For each pattern slot, add its value into row[pattern], summing if it
    already exists—except skip any 'charm slot' patterns *and* any defence
    flat/% patterns (encoded by *_NORM already).
    """
    # For jewellery (ring/amulet/belt), KEEP flat/% defence patterns.
    # For armour pieces, SKIP them (already encoded by *_norm).
    cat = str(row.get("Item Category", "")).strip().lower().replace(" ", "_")
    is_jewellery = cat in ("ring", "amulet", "belt")
    SKIP_PATTERNS = set() if is_jewellery else (PCT_DEFENCE_PATTERNS | FLAT_DEFENCE_PATTERNS)
    # For Shield/Buckler, also exclude explicit block % pattern — already encoded in block_norm
    if cat in ("shield", "buckler"):
        SKIP_PATTERNS = set(SKIP_PATTERNS)
        SKIP_PATTERNS.add("#% increased block chance")
    if normalize_item_category(cat) in DPS_WEAPON_CATEGORIES:
        SKIP_PATTERNS = set(SKIP_PATTERNS)
        SKIP_PATTERNS.update(DPS_WEAPON_OMITTED_MOD_PATTERNS)
    for prefix, max_i in (("implicit",3),("enchant",3),("explicit",10)):
        for i in range(1, max_i+1):
            pkey = f"{prefix}_mod_{i}_pattern"
            vkey = f"{prefix}_mod_{i}_value"
            pat = row.get(pkey)
            val = row.get(vkey)
            if not pat or val is None:
                continue

            _lc = pat.lower()
            if "charm slot" in _lc:
                continue
            if pat in SKIP_PATTERNS:
                continue

            # sum up identical patterns across prefixes
            row[pat] = float(row.get(pat, 0)) + float(val)

def drop_raw_mod_slots(row: dict) -> None:
    for k in list(row):
        if re.match(r"^(implicit|enchant|rune|explicit)_mod_\d+_(pattern|value|min|max)$", k):
            row.pop(k)

def cleanup_unused_features(row: dict) -> dict:
    # The API builds its target-item payload before cleanup, when dps_* contains
    # actual displayed DPS. Inference happens after cleanup and must retain the
    # historical quality/rune-deflated model features.
    for key in BOW_DPS_COLUMNS:
        model_key = f"_model_{key}"
        if model_key in row:
            row[key] = row.pop(model_key)
    for k in (
        "Armour", "Evasion Rating", "Energy Shield", "block", "Quality",
        "Quality_Type", "Quality_Type_Pct", "Item Name",
        "explicit_mod_%", "rune_mod_%",
        # Affix-level metadata is for eligibility checks, never a model feature.
        *AFFIX_METADATA_KEYS,
        *BOW_RAW_STAT_COLUMNS
    ):
        row.pop(k, None)
    for key in WAYSTONE_OMITTED_MODEL_FEATURES:
        row.pop(key, None)
    return row

# ───── 9. SEGMENT DETECTION & DF BUILDER ───────────────────────────────────
def detect_category_segment(row: dict) -> tuple[str, str|None]:
    cat = normalize_item_category(row.get("Item Category", "default_model"))
    # Normalize plural/synonym forms to singular internal tokens used by folders/models
    cat = {
        # common singularizations and synonyms
        "body_armours": "body_armour",
        "helmets": "helmet",
        "shields": "shield",
        "bucklers": "buckler",
        "rings": "ring",
        "amulets": "amulet",
        "belts": "belt",
        "wands": "wand",
        "quivers": "quiver",
        "tablets": "tablet",
        "waystones": "waystone",
        "jewels": "jewel",
        "foci": "focus",
        "scepters": "sceptre",
        "sceptres": "sceptre",
        "bows": "bow",
        "stave": "staff",
        "staves": "staff",
        "staffs": "staff",
        # keep canonical tokens as-is
        "boots": "boots",
        "gloves": "gloves",
        # singular typos → canonical
        "boot": "boots",
        "glove": "gloves",
        "scepter": "sceptre",
        "bow": "bow",
        "staff": "staff",
    }.get(cat, cat)
    if cat == "waystone":
        return cat, waystone_segment(row.get("waystone_tier"))
    # For simple categories and DPS weapons, force a single global model.
    if cat in ("ring","amulet","belt","jewel","sceptre","scepter","staff","wand","quiver","tablet", *DPS_WEAPON_CATEGORIES) or cat.startswith("tablet_"):
        return cat, None
    ar,ev,es = (float(row.get(k,0)) for k in ("ar_norm","ev_norm","es_norm"))
    if   ar and not(ev or es):    seg="ar_only"
    elif ev and not(ar or es):    seg="ev_only"
    elif es and not(ar or ev):    seg="es_only"
    elif ar and ev and not es:    seg="ar_ev_only"
    elif ar and es and not ev:    seg="ar_es_only"
    elif ev and es and not ar:    seg="ev_es_only"
    elif ar and ev and es:        seg="all_three"
    else:                         seg=None
    return cat, seg

def build_feature_dataframe(row: dict) -> pd.DataFrame:
    numeric = {k: float(v) for k,v in row.items() if isinstance(v,(int,float,np.number))}
    df = pd.DataFrame([numeric]).round(4)
    # standardize to lowercase column names to align with model features
    df.columns = [str(c).lower() for c in df.columns]
    return df

# Jewel helper: infer subtype from raw clipboard text
def _jewel_match_tokens(value: str) -> list[str]:
    base = str(value or "").strip()
    if not base:
        return []
    spaced = re.sub(r"[_-]+", " ", base)
    compact = re.sub(r"[^a-z0-9]+", "", base.lower())
    return [base.lower(), spaced.lower(), compact]


def _infer_jewel_subtype(text: str) -> str | None:
    try:
        t = (text or "").lower()
        compact_text = re.sub(r"[^a-z0-9]+", "", t)
        subtype_names = sorted(
            [str(j).strip() for j in (jewel_list or []) if str(j).strip()],
            key=lambda name: len(re.sub(r"[^a-z0-9]+", "", name.lower())),
            reverse=True,
        )
        for jt in subtype_names:
            tokens = _jewel_match_tokens(jt)
            if not tokens:
                continue
            if any(re.search(rf"\b{re.escape(tok)}\b", t, flags=re.I) for tok in tokens[:2]):
                return jt
            if tokens[2] and tokens[2] in compact_text:
                return jt
    except Exception:
        pass
    return None


def _infer_tablet_subtype(text: str) -> str | None:
    """Return a stable per-family model token, e.g. ``tablet_delirium``."""
    known = ("abyss", "breach", "delirium", "expedition", "irradiated", "overseer", "ritual", "temple", "ultimatum")
    family_pattern = "|".join(re.escape(name) for name in known)
    match = re.search(
        rf"(?im)^\s*({family_pattern})\s+tablet\s*$",
        str(text or ""),
    )
    if match:
        return f"tablet_{match.group(1).lower()}"
    return None

# ───── 10. PUBLIC ENTRY POINT ───────────────────────────────────────────────
def prepare_item_features(text: str) -> PreparedItem:
    raw_parsed = parse_copied_item_text(text)
    parsed = dict(raw_parsed)
    if not parsed.get("Item Category"):
        parsed["Item Category"] = "default_model"

    parsed = process_all_mods(parsed)

    # ── BELT CHARM-SLOT FIX ──────────────────────────────────────────
    if parsed.get("Item Category","").lower() == "belt":
        # default to 1 slot
        total = 1
        # scan every pattern slot for "charm slot"
        for prefix, max_i in (("implicit",3),("enchant",3),("rune",6),("explicit",10)):
            for i in range(1, max_i+1):
                pat = parsed.get(f"{prefix}_mod_{i}_pattern","").lower()
                val = parsed.get(f"{prefix}_mod_{i}_value", 0) or 0
                if "charm slot" in pat:
                    try:
                        total = max(total, int(val))
                    except ValueError:
                        pass
        # expose for ML if needed
        parsed["has # charm slots"] = total

    # 4) jewellery quality deflator
    parsed = _deflate_quality_type_modifiers(parsed)
    # 5) armour defence normaliser
    parsed = deflator_and_normaliser(parsed)
    # 6) cleanup, flatten & combine patterns, drop raw slots
    parsed = cleanup_unused_features(parsed)
    flatten_all_mod_patterns(parsed)
    drop_raw_mod_slots(parsed)

    # 7) determine segment (jewellery always seg=None)
    cat, seg = detect_category_segment(parsed)
    if cat in ("ring","amulet","belt"):
        seg = None

    # Special-case Jewels: switch category to the specific subtype so model lookup
    # uses per-type files. Also append the subtype to the
    # display name so the KNN overlay mirrors neighbour names.
    cat_for_models = cat
    if cat == "jewel":
        jt = _infer_jewel_subtype(text)
        if jt:
            cat_for_models = jt
            # Ensure GUI shows the subtype at the end for Your Item
            name0 = (parsed.get("Item Name") or "").strip()
            jt_title = jt.title()
            if jt_title and jt_title not in name0:
                parsed["Item Name"] = (name0 + (" " if name0 else "") + jt_title).strip()
    elif cat == "tablet":
        tablet_type = _infer_tablet_subtype(text)
        if tablet_type:
            cat_for_models = tablet_type

    model_supported = not (cat == "waystone" and seg is None)
    unsupported_reason = UNSUPPORTED_WAYSTONE_MESSAGE if not model_supported else None

    # 8) build DataFrame. Tier chooses the model and must not also influence it.
    X = build_feature_dataframe(parsed)
    if cat == "waystone":
        X.drop(columns=["waystone_tier"], inplace=True, errors="ignore")
    display_X = X.copy()
    if cat in DPS_WEAPON_CATEGORIES:
        displayed_dps = compute_displayed_weapon_dps_features(raw_parsed)
        for key, value in displayed_dps.items():
            display_X.loc[display_X.index[0], key] = float(value)
    if _DEBUG:
        _dbg("\n[DEBUG] Feature DataFrame X:")
        _dbg(X.T)

    return PreparedItem(
        text=text,
        raw_parsed=raw_parsed,
        features=X,
        category=cat,
        segment=seg,
        model_category=cat_for_models,
        model_supported=model_supported,
        unsupported_reason=unsupported_reason,
        display_features=display_X,
    )


def call_super_prepared(prepared: PreparedItem):
    if not prepared.model_supported:
        return None
    return call_ml_super(
        prepared.model_category,
        None if prepared.model_category in (jewel_list or []) or prepared.model_category.startswith("tablet_") else prepared.segment,
        prepared.features,
    )


def call_unsuper_prepared(prepared: PreparedItem):
    if not prepared.model_supported:
        raise FileNotFoundError(prepared.unsupported_reason or UNSUPPORTED_WAYSTONE_MESSAGE)
    # Primary attempt: use detected segment (or None for jewels)
    seg_in = None if prepared.model_category in (jewel_list or []) or prepared.model_category.startswith("tablet_") else prepared.segment
    last_cat = prepared.model_category
    last_seg = seg_in

    def _safe_call(cat_name: str, seg_name: Optional[str]) -> Optional[pd.DataFrame]:
        nonlocal last_cat, last_seg
        last_cat = cat_name
        last_seg = seg_name
        try:
            return call_ml_unsuper(cat_name, seg_name, prepared.features)
        except Exception:
            return None

    nbrs = _safe_call(prepared.model_category, seg_in)
    # Fallback 1: if no neighbours, retry without segment to allow loader fallbacks
    if nbrs is None and seg_in is not None:
        nbrs = _safe_call(prepared.model_category, None)
    # Fallback 2: as a last resort, try the original detected category (pre jewel-subtype switch)
    if nbrs is None and prepared.model_category != prepared.category:
        fallback_seg = None if prepared.category in (jewel_list or []) else prepared.segment
        nbrs = _safe_call(prepared.category, fallback_seg)

    if nbrs is None:
        seg_label = "global" if last_seg in (None, "", "none") else str(last_seg)
        raise FileNotFoundError(
            f"No unsupervised model available for category '{last_cat}' (segment '{seg_label}')."
        )

    if _DEBUG:
        pprint.pprint(nbrs)
    return prepared.features, nbrs


def main(text: str, key: str):
    prepared = prepare_item_features(text)

    if key == "super":
        return call_super_prepared(prepared)
    if key == "unsuper":
        return call_unsuper_prepared(prepared)

    raise ValueError("key must be 'super' or 'unsuper'")
