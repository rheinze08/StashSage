# File: parse_utils.py
# ─────────────────────────────────────────────────────────────────────────────
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd

from poe2trade.utils import submodule_path
from poe2trade import ignore_allocates_flag

# ─────────────────────────────────────────────────────────────────────────────
#  parse_item_string
# ─────────────────────────────────────────────────────────────────────────────
def parse_item_string(item_string: str, right_string: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses a single PoE item string and extracts:
      - Basic item info (name, category, quality, etc.)
      - 'pre_mod' lines (lines before the first tier line).
      - Tiers + mod text (up to 9 possible mods).
      - Corrupted flag ('Yes' or 'No').
      - Price and seller info from `right_string` (optional).

    Steps in detail:
      1) Remove everything from '~price' or '~b/o' onward (including that text).
      2) Cut at first "Corrupted" line => sets 'Corrupted'='Yes' if found.
      3) Lines 0..2 become mod_value, item_name, item_category (heuristic).
      4) Then scan subsequent lines for:
         - 'Quality: N%',
         - 'Armour: N',
         - 'Evasion Rating: N',
         - 'Energy Shield: N',
         - 'Requires Level N <stats>',
         - 'Item Level: N',
         ...and store them in columns.
      5) The rest of lines go to `post_req_lines`.
         * Find first Tier line => everything before => pre_mod1..5
         * everything after => mod1..9
      6) Attempt to parse price from `right_string` if present.
      7) We no longer handle Iron Runes logic here.
    """

    # 1) Remove ~price or ~b/o tails
    item_string = re.sub(
        r'~(?:price|b\/o).*$', '', item_string,
        flags=re.IGNORECASE | re.DOTALL
    ).strip()

    # 2) Trim at "Corrupted"
    lines_all = item_string.split("\n")
    new_lines: List[str] = []
    corrupted_flag = "No"
    for line in lines_all:
        if re.match(r"^Corrupted", line.strip(), re.IGNORECASE):
            corrupted_flag = "Yes"
            break
        new_lines.append(line)
    item_string = "\n".join(new_lines)

    # ── initialise scalar fields ──────────────────────────────────────────
    lines = item_string.split("\n")
    mod_value = item_name_value = item_category = None
    quality_value = quality_mod_value = None
    energy_shield_value = evasion_value = armor_value = None
    item_level_value = requires_level_value = None
    requires_str_value = requires_dex_value = requires_int_value = None

    # (3) Heuristic for lines 0..2
    if len(lines) > 0:
        mod_value = lines[0].strip()
    if len(lines) > 1:
        item_name_value = lines[1].strip()
    if len(lines) > 2:
        item_category = lines[2].strip()

    # (4) Parse subsequent lines
    post_req_lines: List[str] = []
    start_idx = 3
    for line in lines[start_idx:]:
        ln = line.strip()

        # Quality
        m_qual = re.match(
            r"^Quality\s*(?:\(([^)]+?)\s*Modifiers\))?:\s*\+?(\d+)%", ln, re.IGNORECASE
        )
        if m_qual:
            quality_value = m_qual.group(2)
            if m_qual.group(1):
                quality_mod_value = m_qual.group(1).strip()
            continue

        # Armour
        m_arm = re.match(r"^Armour:\s*(\d+)", ln, re.IGNORECASE)
        if m_arm:
            armor_value = m_arm.group(1)
            continue

        # Evasion
        m_eva = re.match(r"^Evasion Rating:\s*(\d+)", ln, re.IGNORECASE)
        if m_eva:
            evasion_value = m_eva.group(1)
            continue

        # Energy Shield
        m_es = re.match(r"^Energy Shield:\s*(\d+)", ln, re.IGNORECASE)
        if m_es:
            energy_shield_value = m_es.group(1)
            continue

        # Item Level
        m_il = re.match(r"^Item Level:\s*(\d+)", ln, re.IGNORECASE)
        if m_il:
            item_level_value = m_il.group(1)
            continue

        # Requires Level N ...
        m_rl = re.match(r"^Requires Level\s*(\d+)(.*)", ln, re.IGNORECASE)
        if m_rl:
            requires_level_value = m_rl.group(1)
            sub_part = m_rl.group(2)
            sub_stats = re.findall(r"(\d+)\s*(Str|Dex|Int)", sub_part, re.IGNORECASE)
            for val, stat in sub_stats:
                st_ = stat.lower()
                if st_ == "str":
                    requires_str_value = val
                elif st_ == "dex":
                    requires_dex_value = val
                elif st_ == "int":
                    requires_int_value = val
            continue

        # Not matched => accumulate
        post_req_lines.append(ln)

    # (5) Tier lines
    tier_pattern = re.compile(
        r"^(([PS]\d+)(?:\s*\+\s*[PS]\d+)*)(?:\s*\[.*\])?$", re.IGNORECASE
    )
    first_tier_index = next(
        (i for i, txt in enumerate(post_req_lines) if tier_pattern.match(txt.strip())),
        -1
    )

    if first_tier_index >= 0:
        pre_mod_substring_lines = post_req_lines[:first_tier_index]
        remainder_lines = post_req_lines[first_tier_index:]
    else:
        pre_mod_substring_lines = post_req_lines
        remainder_lines = []

    bracket_pattern = re.compile(r'^\[[^\]]+\]$')
    pre_mod_substring_lines = [
        l for l in pre_mod_substring_lines if not bracket_pattern.match(l.strip())
    ]

    pre_mods_output: Dict[str, Optional[str]] = {}
    for i in range(5):
        key = f"pre_mod{i + 1}"
        pre_mods_output[key] = pre_mod_substring_lines[i] if i < len(pre_mod_substring_lines) else None

    # Mods (tiers + texts)
    mods_output: Dict[str, Optional[str]] = {f"mod{i}": None for i in range(1, 10)}
    mods_output.update({f"mod{i}_tier": None for i in range(1, 10)})

    collected_tiers: List[tuple[str, str]] = []
    i = 0
    while i < len(remainder_lines):
        li = remainder_lines[i].strip()
        mm = tier_pattern.match(li)
        if mm:
            tval = mm.group(1).strip()
            mod_txt = remainder_lines[i + 1].strip() if i + 1 < len(remainder_lines) else ""
            collected_tiers.append((tval, mod_txt))
            i += 2
            while i < len(remainder_lines) and not tier_pattern.match(remainder_lines[i].strip()):
                i += 1
        else:
            i += 1

    for idx, (tier_val, mod_txt) in enumerate(collected_tiers[:9], start=1):
        mods_output[f"mod{idx}_tier"] = tier_val
        mods_output[f"mod{idx}"] = mod_txt

    leftover_lines: List[str] = []
    for tv, mz in collected_tiers[9:]:
        leftover_lines.append(tv)
        if mz:
            leftover_lines.append(mz)
    final_remainder = "\n".join(leftover_lines)

    # (8) Check "Corrupted" inside last mod if not already found
    if corrupted_flag == "No":
        last_mod_idx = next(
            (j for j in reversed(range(1, 10)) if mods_output[f"mod{j}_tier"] is not None),
            None
        )
        if last_mod_idx is not None and mods_output[f"mod{last_mod_idx}"]:
            filtered = []
            for line_str in mods_output[f"mod{last_mod_idx}"].split("\n"):
                if re.match(r"^Corrupted$", line_str.strip(), re.IGNORECASE):
                    corrupted_flag = "Yes"
                else:
                    filtered.append(line_str)
            mods_output[f"mod{last_mod_idx}"] = "\n".join(filtered)

    # (9) Parse trade‑helper panel (right_string)
    price_value = price_currency = player_value = days_listed_value = None
    if right_string:
        rls = [ln.strip() for ln in right_string.split("\n") if ln.strip()]
        price_key = next((k for k in ["exact price:", "asking price:"] if k in [l.lower() for l in rls]), None)
        if price_key:
            key_idx = next((idx for idx, val_ in enumerate(rls) if val_.lower() == price_key), None)
            if key_idx is not None:
                if key_idx + 1 < len(rls):
                    mp = re.match(
                        r"^(\d+)[×x]\s*(exalted|divine|chaos)\s+orb", rls[key_idx + 1], re.IGNORECASE
                    )
                    if mp:
                        price_value = mp.group(1)
                        price_currency = mp.group(2).capitalize()
                if key_idx + 2 < len(rls):
                    pl = re.match(
                        r"^(.+?)\s+listed\s+(\d+|a)\s+days?\s+ago", rls[key_idx + 2], re.IGNORECASE
                    )
                    if pl:
                        player_value = pl.group(1).strip()
                        dd_ = pl.group(2).lower()
                        days_listed_value = "1" if dd_ == "a" else dd_

    # Default quality to "0"
    if not quality_value:
        quality_value = "0"

    # Assemble final dict
    return {
        "Mod":           mod_value,
        "Item Name":     item_name_value,
        "Item Category": item_category,
        "Quality":       quality_value,
        "Quality Mod":   quality_mod_value,
        "Energy Shield": energy_shield_value,
        "Evasion Rating":evasion_value,
        "Armour":        armor_value,
        "Item Level":    item_level_value,
        "Requires Level":requires_level_value,
        "Requires Str":  requires_str_value,
        "Requires Dex":  requires_dex_value,
        "Requires Int":  requires_int_value,
        **pre_mods_output,
        "Corrupted":     corrupted_flag,
        "Price":         price_value,
        "Currency":      price_currency,
        "Days Listed":   days_listed_value,
        "Player":        player_value,
        "remainder_to_parse": final_remainder,
        **mods_output
    }

# ─────────────────────────────────────────────────────────────────────────────
#  parse_excel_file
# ─────────────────────────────────────────────────────────────────────────────
def parse_excel_file(input_excel_file: str, output_excel_file: Optional[str] = None) -> pd.DataFrame:
    """
    Read the input Excel file containing item data, apply parse_item_string
    to each row, and write/return the resulting DataFrame.

    If `ignore_allocates_flag` is True, any item whose raw text contains the
    word "allocates" (case‑insensitive) is *completely discarded*.
    """
    input_df = pd.read_excel(input_excel_file)

    parsed_rows: List[Dict[str, Any]] = []
    for _, row in input_df.iterrows():
        item_str  = row.get("Name", "") or ""
        right_str = row.get("Right", "") or ""

        # ── skip "allocates" items when flag is on ───────────────────────
        if ignore_allocates_flag and re.search(r"\ballocates\b", item_str, re.IGNORECASE):
            continue

        parsed_data = parse_item_string(item_str, right_str)
        combined = row.to_dict()
        combined.update(parsed_data)
        parsed_rows.append(combined)

    final_df = pd.DataFrame(parsed_rows)

    # Ensure mandatory columns exist
    if "Mod" not in final_df.columns:
        final_df["Mod"] = ""
    if "Item Name" not in final_df.columns:
        final_df["Item Name"] = ""

    final_df["Item Title"] = (
        final_df["Mod"].fillna("") + " " + final_df["Item Name"].fillna("")
    ).str.strip()

    # Typical column ordering
    report_cols = [
        "Item Title",
        "Mod", "Item Name", "Item Category", "Quality", "Quality Mod",
        "Energy Shield", "Evasion Rating", "Armour", "Item Level",
        "Requires Level", "Requires Str", "Requires Dex", "Requires Int",
        "pre_mod1", "pre_mod2", "pre_mod3", "pre_mod4", "pre_mod5",
        "mod1", "mod1_tier", "mod2", "mod2_tier", "mod3", "mod3_tier",
        "mod4", "mod4_tier", "mod5", "mod5_tier", "mod6", "mod6_tier",
        "mod7", "mod7_tier", "mod8", "mod8_tier", "mod9", "mod9_tier",
        "Corrupted", "Price", "Currency", "Days Listed", "Player",
        "remainder_to_parse",
    ]
    final_df = final_df[[c for c in report_cols if c in final_df.columns]]

    if output_excel_file:
        final_df.to_excel(output_excel_file, sheet_name="Report", index=False)

    return final_df

# ─────────────────────────────────────────────────────────────────────────────
#  CLI entry
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python parse_utils.py <input_excel_file> <output_excel_file>")
        sys.exit(1)
    inf = sys.argv[1]
    outf = sys.argv[2]
    parse_excel_file(inf, outf)
