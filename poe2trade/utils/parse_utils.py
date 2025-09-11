# File: poe2trade/utils/parse_utils.py

"""
Flatten PoE trade-API JSON dumps into a tidy DataFrame.

Key features
------------
• Robust rolled-mod parsing (pattern + average value)
• Exhaustive tag cleanup for wiki-style “[foo|bar]” strings
• Filters out passive-tree “allocates …” mods
• Extracts quality / quality_type, ar, ev, es
• Gracefully skips local template JSON files; logs malformed entries
"""

from __future__ import annotations

import json
import os
import re
from typing import List, Tuple, Dict

import pandas as pd

from poe2trade import buyout_only


# ───────────────────────────── rolled-mod helper ─────────────────────────────
def parse_rolled_mod(mod_str: str) -> Tuple[str, float, float, str | None, bool, bool, bool]:
    """
    Parse a single rolled-mod string into:
      • pattern (numbers → '#')
      • average roll
      • max roll
      • bucket token ('#%' / '#' / None)
      • flags: references armour, evasion, energy shield
    """
    raw = re.sub(r'^\+\s*', '', str(mod_str).lower().strip())

    nums = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', raw)]
    mn, mx = (nums[0], nums[-1]) if nums else (1.0, 1.0)
    avg = (mn + mx) / 2.0
    pattern = re.sub(r'\d+(?:\.\d+)?', '#', raw)

    bad_kw = ('recharge', 'break', 'penetrate')
    ref_def = any(t in raw for t in ('armour', 'evasion', 'energy shield')) \
              and not any(b in raw for b in bad_kw)

    is_armour  = 'armour'        in raw and ref_def
    is_evasion = 'evasion'       in raw and ref_def
    is_es      = 'energy shield' in raw and ref_def

    bucket = '#%' if (ref_def and '#%' in pattern) else (
             '#'  if (ref_def and  '#' in pattern) else None)

    return pattern, avg, mx, bucket, is_armour, is_evasion, is_es


# ───────────────────────────── tag-cleanup LUT ───────────────────────────────
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
    """Expand wiki-style tags to plain text, preferring the DISPLAY side of [x|y] → y."""
    if not isinstance(text, str):
        return text
    for patt, repl in _TAG_REPLACEMENTS:
        text = re.sub(patt, repl, text, flags=re.IGNORECASE)
    # Always prefer the display side for [a|b] → b
    text = re.sub(r"\[([^\[\]\|]+)\|([^\[\]\|]+)\]", r"\2", text)
    # Strip single-bracket tags
    text = re.sub(r"\[([^\[\]\|]+)\]", r"\1", text)
    return text


# ───────────────────────────── main flattener ────────────────────────────────
def parse_item_json(
    item_json_file_path: str,
    category: str | None = None,  # kept for backwards compat; ignored
    output_excel_file: str | None = None
) -> pd.DataFrame:
    """
    Read a PoE trade-API JSON dump and return a tidy DataFrame.

    Emits:
      - price, currency, base, name
      - enchant/implicit/explicit/rune mod slots (text + parsed pattern/value)
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
        cleaned = [clean_mod_text(m) for m in mods]
        for i in range(slots):
            txt = cleaned[i] if i < len(cleaned) else None
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

            # mods
            _slot_mods(itm.get("enchantMods", []),  "enchant",  3,  rec)
            _slot_mods(itm.get("implicitMods", []), "implicit", 3,  rec)
            _slot_mods(itm.get("explicitMods", []), "explicit", 10, rec)
            _slot_mods(itm.get("runeMods", []),     "rune",     6,  rec)

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

            rows.append(rec)

        except Exception as err:
            print(f"⚠️  Skipping entry in {os.path.basename(item_json_file_path)}: {err!r}")

    df = pd.DataFrame(rows)

    # ensure canonical lowercase columns exist
    for col in ["quality", "quality_type", "ar", "ev", "es"]:
        if col not in df.columns:
            df[col] = pd.NA

    # remove unwanted rows (allocates / bears / on corruption)
    for pfx, cnt in (("explicit", 10), ("enchant", 3)):
        cols = [f"{pfx}_mod_{i+1}" for i in range(cnt)]
        if set(cols).issubset(df.columns) and not df.empty:
            s = df[cols].astype(str)
            bad = (
                s.apply(lambda c: c.str.contains(r"allocates", case=False, regex=True))
                | s.apply(lambda c: c.str.contains(r"bears", case=False, regex=True))
                | s.apply(lambda c: c.str.contains(r"on corruption", case=False, regex=True))
            ).any(axis=1)
            df = df[~bad]

    # drop helper-only columns that should never be emitted
    if "listing_type" in df.columns:
        df.drop(columns=["listing_type"], inplace=True, errors="ignore")

    # final ordering
    front = ["price", "currency", "base", "name",
             "quality", "quality_type", "ar", "ev", "es"]
    existing_front = [c for c in front if c in df.columns]
    others = [c for c in df.columns if c not in existing_front]
    df = df[existing_front + others]

    if df.empty:
        print("⚠️  parse_item_json produced an EMPTY DataFrame.")

    if output_excel_file:
        os.makedirs(os.path.dirname(output_excel_file) or ".", exist_ok=True)
        df.to_excel(output_excel_file, index=False)
        df.to_parquet(os.path.splitext(output_excel_file)[0] + ".parquet", index=False)

    return df
