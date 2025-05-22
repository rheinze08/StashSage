# gui_utils.py · v14 — helmet double‑corruption; no corruption_pattern anywhere
# ─────────────────────────────────────────────────────────────────────────────
import re
import pprint

import numpy as np
import pandas as pd

from poe2trade.utils.train_utils import normalise_pattern
from poe2trade.utils.ml_utils   import call_ml, call_ml_segmented

# ─────────────────────────────────────────────────────────────────────────────
#  parse_copied_item_text
# ─────────────────────────────────────────────────────────────────────────────
def parse_copied_item_text(text: str) -> dict:
    """Convert a full PoE ‹Ctrl‑C› clipboard dump into a row‑dict."""
    print("\n[DEBUG] raw clipboard\n")
    print(text)

    text = re.sub(r'~(?:price|b/​o).*$', '', text,
                  flags=re.IGNORECASE | re.DOTALL).strip()

    is_corrupted = bool(re.search(r'^\s*Corrupted\s*$', text, re.M))

    row = {
        # meta
        "Item Category": "", "Item Name": "", "Quality": 0,
        "Armour": 0, "Evasion Rating": 0, "Energy Shield": 0,
        "Corrupted": "Yes" if is_corrupted else "No",
        "socket_count": 0, "iron_rune_increase": 0.0,
        # raw mod slots
        "implicit_mod": None,
        **{f"pre_mod{i}": None for i in range(1, 6)},
        **{f"mod{i}": None  for i in range(1, 10)},
    }

    # ── split clipboard into meta / mod sections -------------------------
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    try:
        cut = next(i for i, ln in enumerate(lines)
                   if re.match(r'^Item Level:\s*\d+', ln, re.I))
    except StopIteration:
        cut = len(lines)

    meta_lines, mod_lines = lines[:cut + 1], lines[cut + 1:]

    # ── meta block -------------------------------------------------------
    reading_name = False
    for ln in meta_lines:
        m = re.match(r'^Item Class:\s*(.*)$', ln, re.I)
        if m:
            cls = m.group(1).strip().lower().replace(' ', '_')
            if cls not in ("boots", "gloves"):
                cls = cls.rstrip('s')
            row["Item Category"] = cls
            continue

        if re.match(r'^Rarity:\s*Rare', ln, re.I):
            reading_name = True
            continue

        if reading_name:
            if (ln.startswith('--------') or
                    re.match(r'^(Quality:|Armour|Evasion|Energy Shield|Requires|Sockets|Item Level)',
                             ln, re.I)):
                reading_name = False
            else:
                row["Item Name"] += f"{ln} "
                continue

        m = re.match(r'^Quality:\s*\+?(\d+)%', ln, re.I)
        if m:
            row["Quality"] = int(m.group(1))
            continue

        for key, patt in (("Armour", r'^Armour:\s*(\d+)'),
                          ("Evasion Rating", r'^Evasion Rating:\s*(\d+)'),
                          ("Energy Shield", r'^Energy Shield:\s*(\d+)')):
            m = re.match(patt, ln, re.I)
            if m:
                row[key] = int(m.group(1))
                break

        if ln.lower().startswith('sockets:'):
            row["socket_count"] = ln.split(':', 1)[1].lower().count('s')

    row["Item Name"] = row["Item Name"].strip()

    # ── mod blocks -------------------------------------------------------
    premods, mods = [], []
    for ln in mod_lines:
        if (ln.startswith('--------') or ln.lower() == 'corrupted'
                or ln.lower().startswith('note:')):
            continue
        lw = ln.lower()
        if '(enchant)' in lw:                       # corruption implicit(s)
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


# ─────────────────────────────────────────────────────────────────────────────
#  process_all_mods – canonicalises patterns
# ─────────────────────────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r'\(implicit|\(rune|\(enchant|\(augmented', re.I)

def _clean_line(txt: str) -> str:
    tmp = _TOKEN_RE.sub('', txt)
    tmp = tmp.replace('--------', '')
    tmp = re.sub(r'[()]', '', tmp)
    tmp = re.sub(r'\s+', ' ', tmp)
    return tmp.strip()

def process_all_mods(row: dict) -> dict:
    """Convert raw pre/implicit/explicit lines → unique_modN_* columns."""
    lines: list[str] = []

    # collect non‑rune pre‑mods
    for i in range(1, 6):
        pm = row.get(f"pre_mod{i}")
        if pm and "(rune)" not in pm.lower():
            lines.append(pm)

    # explicit mods
    for j in range(1, 10):
        mm = row.get(f"mod{j}")
        if mm and "(rune)" not in mm.lower():
            lines.append(mm)

    # implicit (if exists, already excluded from runes)
    if row.get("implicit_mod") and "(rune)" not in row["implicit_mod"].lower():
        lines.append(row["implicit_mod"])

    idx = 1
    seen_patterns: set[str] = set()
    for ln in lines:
        clean = _clean_line(ln)
        canon = normalise_pattern(clean)
        if canon in seen_patterns:
            continue
        seen_patterns.add(canon)

        m = re.search(r'([\+\-]?\d+(?:\.\d+)?)', clean)
        val = float(m.group(1)) if m else 0.0
        if "(augmented)" in ln.lower():
            val /= 20.0

        row[f"unique_mod{idx}_pattern"] = canon
        row[f"unique_mod{idx}_value"]   = val
        idx += 1

    row["extra_socket_mod"] = max(0, row.get("socket_count", 0) - 4)
    return row


# ─────────────────────────────────────────────────────────────────────────────
#  deflator – multi‑stat aware
# ─────────────────────────────────────────────────────────────────────────────
def _sf(x):
    try:
        return float(x or 0)
    except Exception:
        return 0.0

def deflator(row: dict) -> dict:
    A  = _sf(row.get("Armour"))
    Ev = _sf(row.get("Evasion Rating"))
    Es = _sf(row.get("Energy Shield"))
    Q  = _sf(row.get("Quality"))
    run_pct = _sf(row.get("iron_rune_increase", 0))

    arm_f = arm_p = eva_f = eva_p = es_f = es_p = 0.0

    for i in range(1, 50):
        pat = str(row.get(f"unique_mod{i}_pattern") or "").lower()
        if not pat:
            continue
        val = _sf(row.get(f"unique_mod{i}_value"))

        if " to " in pat:
            if "armour" in pat:          arm_f += val
            if "evasion" in pat:         eva_f += val
            if "energy shield" in pat:   es_f  += val

        if "% increased" in pat:
            if "armour" in pat:          arm_p += val
            if "evasion" in pat:         eva_p += val
            if "energy shield" in pat:   es_p  += val

    def base(display, flat, pct):
        denom = (1 + (pct + run_pct) / 100) * (1 + Q / 100)
        return (display / denom) - flat if denom else 0.0

    row["Deflated_Armour"]       = base(A,  arm_f, arm_p)
    row["Deflated_Evasion"]      = base(Ev, eva_f, eva_p)
    row["Deflated_EnergyShield"] = base(Es, es_f,  es_p)
    return row


# ─────────────────────────────────────────────────────────────────────────────
#  defence / resistance flag builder (resist_count only)
# ─────────────────────────────────────────────────────────────────────────────
def _defence_and_resist_flags(row: dict) -> dict:
    """
    Mirrors features_utils.set_defense_and_resistance_flags()
    but retains only resist_count and has_flat_and_pct.
    A “flat” or “pct” line must affect Armour / Evasion / Energy Shield.
    """
    A = _sf(row.get("Armour"))
    E = _sf(row.get("Evasion Rating"))
    S = _sf(row.get("Energy Shield"))

    flags = {
        "ar_only": 0, "ev_only": 0, "es_only": 0,
        "ar_ev_only": 0, "ar_es_only": 0, "ev_es_only": 0, "all_three": 0,
        "resist_count": 0, "has_flat_and_pct": 0,
    }

    ca, ce, cs = int(A > 0), int(E > 0), int(S > 0)
    su = ca + ce + cs
    if su == 3:
        flags["all_three"] = 1
    elif su == 2:
        if ca and ce: flags["ar_ev_only"] = 1
        elif ca and cs: flags["ar_es_only"] = 1
        elif ce and cs: flags["ev_es_only"] = 1
    elif su == 1:
        if ca: flags["ar_only"] = 1
        if ce: flags["ev_only"] = 1
        if cs: flags["es_only"] = 1

    flat_seen = pct_seen = False
    rc = 0
    for i in range(1, 50):
        pat = (row.get(f"unique_mod{i}_pattern") or "").lower()
        if not pat:
            continue
        val = _sf(row.get(f"unique_mod{i}_value"))
        if val <= 0:
            continue

        # —— resistance counting (unchanged) ——————————
        if ("to cold resistance"      in pat or
            "to fire resistance"      in pat or
            "to lightning resistance" in pat or
            "to chaos resistance"     in pat):
            rc += 1

        # —— defence‑specific flat / pct detection ————
        if (" to armour" in pat or
            " to evasion" in pat or
            " to maximum energy shield" in pat):
            flat_seen = True

        if ("% increased armour" in pat or
            "% increased evasion" in pat or
            "% increased energy shield" in pat or
            "% increased armour and evasion" in pat or
            "% increased armour and energy shield" in pat or
            "% increased evasion and energy shield" in pat):
            pct_seen = True

    flags["resist_count"]     = rc
    flags["has_flat_and_pct"] = 1 if (flat_seen and pct_seen) else 0

    row.update(flags)
    return row

# ─────────────────────────────────────────────────────────────────────────────
#  safe ML wrappers
# ─────────────────────────────────────────────────────────────────────────────
def _safe_call_ml_segmented(row: dict):
    print("[DEBUG] ⇒ call_ml_segmented")
    try:
        pred = call_ml_segmented(row)
    except Exception as e:
        print(f"[DEBUG] segmented‑path error: {e}")
        pred = None
    if not pred:
        print("[DEBUG] fall back to single‑model")
        pred = call_ml(row)
    return pred

def _safe_call_ml(row: dict):
    print("[DEBUG] ⇒ call_ml")
    return call_ml(row)


# ─────────────────────────────────────────────────────────────────────────────
#  predict_item_text
# ─────────────────────────────────────────────────────────────────────────────
def predict_item_text(text: str):
    """Clipboard text → parsed → deflated → defence flags → ML prediction.

    Now also prints the “Value Indicator” (Low / Medium / High) with the
    bucket’s training-set median, e.g. “High -- 62”.
    """
    parsed = parse_copied_item_text(text)
    if not parsed.get("Item Category"):
        parsed["Item Category"] = "default_model"

    parsed = process_all_mods(parsed)
    print("\n[DEBUG] after process_all_mods\n")
    pprint.pprint(parsed, width=120, sort_dicts=False, indent=4)

    parsed = deflator(parsed)
    print("\n[DEBUG] after deflator\n")
    pprint.pprint(parsed, width=120, sort_dicts=False, indent=4)

    parsed = _defence_and_resist_flags(parsed)
    print("\n[DEBUG] after defence/resist flags\n")
    pprint.pprint(parsed, width=120, sort_dicts=False, indent=4)

    cat = parsed["Item Category"].lower()
    result = (_safe_call_ml_segmented(parsed)
              if cat in ("body_armour", "helmet", "gloves", "boots")
              else _safe_call_ml(parsed))

    if not result:
        print("[DEBUG] no predictions found")
        return None

    # ─── new: pretty print “Value Indicator” if available ────────────────
    if "value_indicator" in result:
        print(f"\nValue Indicator : {result['value_indicator']}")
    else:
        print("\nValue Indicator : n/a")

    print("\n[DEBUG] final predictions\n")
    pprint.pprint(result, width=120, sort_dicts=False, indent=4)
    return result