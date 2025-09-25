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
from typing import List, Tuple, Dict, Any

import pandas as pd

from poe2trade import buyout_only


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
    raw_txt = re.sub(r'^\\+\\s*', '', str(mod_str).lower().strip())
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


def _expand_and_clean_mod_list(mods: list) -> list[str]:
    """
    1) Apply clean_mod_text to each entry,
    2) remove '(descrated)',
    3) expand composite lines, and
    4) normalize whitespace.
    """
    out: list[str] = []
    for m in mods or []:
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
    output_excel_file: str | None = None
) -> pd.DataFrame:
    """
    Read a PoE trade-API JSON dump and return a tidy DataFrame.

    Emits:
      - price, currency, base, name
      - enchant/implicit/explicit/fractured/descrated/rune mod slots (text + parsed pattern/value)
      - quality, quality_type
      - ar, ev, es (defences)
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
    }

    rows: List[Dict] = []
    for e in entries:
        try:
            itm = e.get("item", e)
            rec: Dict[str, object] = {
                "price":    e.get("listing", {}).get("price", {}).get("amount"),
                "currency": e.get("listing", {}).get("price", {}).get("currency"),
                "name":     itm.get("name"),
                "base":     itm.get("baseType") or itm.get("base"),
            }

            if buyout_only:
                ltype = e.get("listing", {}).get("price", {}).get("type")
                if not (isinstance(ltype, str) and ltype.startswith("~b/o")):
                    continue

            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ write per-slot groups (no merging) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

                # defences
                key = DEFENCE_KEYS.get(nm.lower())
                if key and rv is not None:
                    rec[key] = rv

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

        except Exception as err:
            print(f"âš ï¸  Skipping entry in {os.path.basename(item_json_file_path)}: {err!r}")

    df = pd.DataFrame(rows)

    # ensure canonical lowercase columns exist
    for col in ["quality", "quality_type", "ar", "ev", "es", "skill_pattern", "skill_value"]:
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
        "quality", "quality_type", "ar", "ev", "es",
        "skill_pattern", "skill_value",
    ]
    existing_front = [c for c in front if c in df.columns]
    others = [c for c in df.columns if c not in existing_front]
    df = df[existing_front + others]

    if df.empty:
        print("âš ï¸  parse_item_json produced an EMPTY DataFrame.")

    if output_excel_file:
        os.makedirs(os.path.dirname(output_excel_file) or ".", exist_ok=True)
        df.to_excel(output_excel_file, index=False)
        df.to_parquet(os.path.splitext(output_excel_file)[0] + ".parquet", index=False)

    return df



