import re
import pprint
import sys
import pandas as pd
from pathlib import Path
from poe2trade import poe2trade_root
# Import these from ml_utils directly, rather than re-importing from gui_utils
from poe2trade.utils.ml_utils import call_ml, call_ml_segmented

########################################################################
# parse_copied_item_text  – v5
# • stops the name reader on the first "--------" so no junk in Item Name
# • socket counter already fixed (handles S / s)
# • Price / Currency removed (never created)
########################################################################
def parse_copied_item_text(text: str) -> dict:
    import re, pprint
    print("\n[DEBUG] raw clipboard\n")
    print(text)

    # drop any ~price / ~b/o block
    text = re.sub(r'~(?:price|b\/o).*$', '', text,
                  flags=re.IGNORECASE | re.DOTALL).strip()

    is_corrupted = bool(re.search(r'^\s*Corrupted\s*$', text, re.M))
    row = {
        "Item Category": "",
        "Item Name": "",
        "Quality": 0,
        "Armour": 0,
        "Evasion Rating": 0,
        "Energy Shield": 0,
        "Corrupted": "Yes" if is_corrupted else "No",

        # pre‑mod bookkeeping
        "implicit_mod": None,
        "corruption_pattern": None,
        "socket_count": 0,
        "iron_rune_increase": 0.0,

        **{f"pre_mod{i}": None for i in range(1, 6)},
        **{f"mod{i}":      None for i in range(1,10)},
    }

    # ── split meta vs mods ──────────────────────────────────────────────
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    try:
        cut = next(i for i, ln in enumerate(lines)
                   if re.match(r'^Item Level:\s*\d+', ln, re.I))
    except StopIteration:
        cut = len(lines)

    meta_lines, mod_lines = lines[:cut+1], lines[cut+1:]

    # ── meta block ──────────────────────────────────────────────────────
    reading_name = False
    for ln in meta_lines:
        m = re.match(r'^Item Class:\s*(.*)$', ln, re.I)
        if m:
            row["Item Category"] = m.group(1).rstrip('s').lower().replace(' ', '_')
            continue

        if re.match(r'^Rarity:\s*Rare', ln, re.I):
            reading_name = True
            continue

        if reading_name:
            # stop on any marker or on the first separator line
            if (ln.startswith('--------') or
                re.match(r'^(Quality:|Armour|Evasion|Energy Shield|Requires|Sockets|Item Level)', ln, re.I)):
                reading_name = False
            else:
                row["Item Name"] += f"{ln} "
                continue

        m = re.match(r'^Quality:\s*\+?(\d+)%', ln, re.I)
        if m:
            row["Quality"] = int(m.group(1)); continue

        for key, patt in (("Armour", r'^Armour:\s*(\d+)'),
                          ("Evasion Rating", r'^Evasion Rating:\s*(\d+)'),
                          ("Energy Shield", r'^Energy Shield:\s*(\d+)')):
            m = re.match(patt, ln, re.I)
            if m:
                row[key] = int(m.group(1)); break

        if ln.lower().startswith('sockets:'):
            row["socket_count"] = ln.split(':',1)[1].lower().count('s')

    row["Item Name"] = row["Item Name"].strip()

    # ── mod block ───────────────────────────────────────────────────────
    premods, mods = [], []
    for ln in mod_lines:
        if (ln.startswith('--------') or ln.lower() == 'corrupted'
                or ln.lower().startswith('note:')):
            continue

        lw = ln.lower()
        if '(enchant)' in lw:
            if is_corrupted and row["corruption_pattern"] is None:
                row["corruption_pattern"] = ln
            premods.append(ln)

        elif '(implicit)' in lw:
            row["implicit_mod"] = ln
            premods.append(ln)

        elif '(rune)' in lw:
            premods.append(ln)
            inc = re.search(r'([\+\-]?\d+(?:\.\d+)?)\%?\s+increased', lw)
            if inc:
                row["iron_rune_increase"] += float(inc.group(1))

        else:
            mods.append(ln)

    for i, ln in enumerate(premods[:5], 1):
        row[f"pre_mod{i}"] = ln
    for i, ln in enumerate(mods[:9], 1):
        row[f"mod{i}"] = ln

    print("\n[DEBUG] parse_copied_item_text ➜ row\n")
    pprint.pprint(row, width=120, sort_dicts=False, indent=4)
    return row

########################################################################
# process_all_mods
########################################################################
def process_all_mods(row: dict) -> dict:
    """
    Consolidate **unique** explicit modifiers.

    * skip anything flagged (rune)
    * skip the corruption_pattern artefact
    * keep implicit_mod (it is never (rune))
    * pre‑mods are *never* auto‑promoted to explicit mods
    Result pairs land in unique_mod{i}_{pattern,value}.
    """
    def sf(x):                          # safe float
        try:   return float(x)
        except: return 0.0

    explicit_lines = []

    # pull clean candidates ---------------------------------------------------
    for i in range(1, 10):
        mm = row.get(f"mod{i}")
        if mm and '(rune)' not in mm.lower():
            explicit_lines.append(mm)

    if row.get("implicit_mod"):
        explicit_lines.append(row["implicit_mod"])

    # prune corruption pattern
    if row.get("corruption_pattern"):
        explicit_lines = [ln for ln in explicit_lines
                          if ln != row["corruption_pattern"]]

    # collapse to unique mod buckets ------------------------------------------
    for idx, ln in enumerate(explicit_lines[:40], 1):   # generous upper bound
        cleaned = re.sub(r'\((?:implicit|enchant)\)', '', ln, flags=re.I)
        patt   = re.sub(r'\s+', ' ', cleaned).strip()

        # extract first numeric token (if any)
        m = re.search(r'([\+\-]?\d+(?:\.\d+)?)', patt)
        val = float(m.group(1)) if m else 0.0
        row[f"unique_mod{idx}_pattern"] = patt
        row[f"unique_mod{idx}_value"]   = val

    # corruption value (if any)
    if row.get("corruption_pattern"):
        cp = re.sub(r'\((?:enchant)\)', '', row["corruption_pattern"], flags=re.I).strip()
        m  = re.search(r'([\+\-]?\d+(?:\.\d+)?)', cp)
        row["corruption_pattern"] = cp
        row["corruption_value"]   = float(m.group(1)) if m else 0.0
    else:
        row["corruption_value"] = 0.0

    return row

########################################################################
# process_all_mods
########################################################################
def process_all_mods(row: dict) -> dict:
    """
    1) Exclude lines containing '(rune)'
    2) Skip line if it matches row['corruption_pattern']
    3) Include row['implicit_mod'] if it doesn't have (rune)
    4) For each final line => remove tags => store in unique_mod{idx}
    5) If corruption_pattern => parse corruption_value
    """
    lines = []

    for i in range(1,6):
        pm_ = row.get(f"pre_mod{i}")
        if pm_ and "(rune)" not in pm_.lower():
            lines.append(pm_)
    for j in range(1,10):
        mm_ = row.get(f"mod{j}")
        if mm_ and "(rune)" not in mm_.lower():
            lines.append(mm_)

    if row.get("implicit_mod"):
        if "(rune)" not in row["implicit_mod"].lower():
            lines.append(row["implicit_mod"])

    final_mods=[]
    for ln in lines:
        if row.get("corruption_pattern") and ln==row["corruption_pattern"]:
            continue
        final_mods.append(ln)

    idx=1
    for line_ in final_mods:
        cleaned = re.sub(r'\(implicit\)|\(rune\)|\(enchant\)', '', line_, flags=re.IGNORECASE)
        cleaned = cleaned.replace("--------","").strip()
        pat, val = extract_first_number(cleaned)
        if "(augmented)" in line_.lower():
            val/=20.0

        row[f"unique_mod{idx}_pattern"] = pat
        row[f"unique_mod{idx}_value"]   = val
        idx+=1

    if row.get("corruption_pattern"):
        cln = re.sub(r'\(implicit\)|\(rune\)|\(enchant\)', '', row["corruption_pattern"], flags=re.IGNORECASE)
        cln = cln.replace("--------","").strip()
        cp, cv = extract_first_number(cln)
        row["corruption_pattern"]= cp
        row["corruption_value"]  = cv
    else:
        row["corruption_value"]= 0.0

    return row

def extract_first_number(txt:str):
    m = re.search(r'([\+\-]?\d+(\.\d+)?)', txt)
    if not m:
        return (txt, 0.0)
    return (txt, float(m.group(1)))

########################################################################
# deflator  – v3
# • % lines that mention multiple defences now buff every defence named
# • confirmed maths: 311 ES, +42 flat, 86 % mod, 20 % rune, 20 % quality
#   → 311 / 2.472 − 42 = 83.97  (matches manual)
########################################################################
def deflator(row: dict) -> dict:
    def f(x):            # safe float
        try:   return float(x or 0)
        except: return 0

    A, Ev, Es = f(row["Armour"]), f(row["Evasion Rating"]), f(row["Energy Shield"])
    Q   = f(row["Quality"])
    run = f(row.get("iron_rune_increase", 0))

    arm_f = arm_p = eva_f = eva_p = es_f = es_p = 0

    for i in range(1, 50):
        pat = (row.get(f"unique_mod{i}_pattern") or "").lower()
        val = f(row.get(f"unique_mod{i}_value"))

        # flat rolls
        if " to armour" in pat:
            arm_f += val
        if " to evasion" in pat:
            eva_f += val
        if " to maximum energy shield" in pat:
            es_f += val

        # % rolls → apply to *every* defence named in the line
        if "% increased" in pat:
            if "armour" in pat:
                arm_p += val
            if "evasion" in pat:
                eva_p += val
            if "energy shield" in pat:
                es_p  += val

    def base(display, flat, pct):
        denom = (1 + (pct + run) / 100) * (1 + Q / 100)
        return (display / denom) - flat if denom else 0

    row["Deflated_Armour"]        = base(A,  arm_f, arm_p)
    row["Deflated_Evasion"]       = base(Ev, eva_f, eva_p)
    row["Deflated_EnergyShield"]  = base(Es, es_f,  es_p)
    return row

########################################################################
# call_ml_segmented_with_debug
########################################################################
def call_ml_segmented_with_debug(row: dict) -> dict or None:
    print("[DEBUG] => call_ml_segmented_with_debug => row =>")
    pprint.pprint(row, width=120, sort_dicts=False, indent=4)
    return call_ml_segmented(row)

########################################################################
# call_ml_with_debug
########################################################################
def call_ml_with_debug(row: dict) -> dict or None:
    print("\n[DEBUG] => call_ml_with_debug => single-model.\n")
    return call_ml(row)

########################################################################
# predict_item_text
########################################################################
def predict_item_text(text: str):
    """
    Full pipeline:
      1) parse_copied_item_text
      2) process_all_mods
      3) deflator
      4) call segmented or single-model
    """
    parsed = parse_copied_item_text(text)
    if not parsed.get("Item Category"):
        parsed["Item Category"] = "default_model"

    parsed = process_all_mods(parsed)
    print("\n[DEBUG] => after process_all_mods =>\n")
    pprint.pprint(parsed, width=120, sort_dicts=False, indent=4)

    parsed = deflator(parsed)
    print("\n[DEBUG] => after deflator =>\n")
    pprint.pprint(parsed, width=120, sort_dicts=False, indent=4)

    cat_ = (parsed["Item Category"] or "").lower()
    if cat_ in ["body_armour","helmet","gloves","boots"]:
        print("[DEBUG] => segmented => calling call_ml_segmented_with_debug")
        result = call_ml_segmented_with_debug(parsed)
    else:
        print("[DEBUG] => single => calling call_ml_with_debug")
        result = call_ml_with_debug(parsed)

    if not result:
        print("\n[DEBUG] => no predictions => no model found.\n")
        return None

    print("\n[DEBUG] => final predictions =>\n")
    pprint.pprint(result, width=120, sort_dicts=False, indent=4)
    return result
