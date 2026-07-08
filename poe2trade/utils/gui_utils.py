# File: poe2trade/utils/gui_utils.py
# · updated 2025-09-07 — skip flat/% defence patterns in modifiers; keep *_NORM only
# · updated 2025-09-16 — expand joint attribute/resistance lines; strip (descrated)/(desecrated)

from __future__ import annotations

import re
import pprint
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from poe2trade import poe2trade_root, jewel_list
from poe2trade.utils.parse_utils import parse_rolled_mod
from poe2trade.utils.ml_super_utils import call_ml as call_ml_super
from poe2trade.utils.ml_unsuper_utils import call_ml as call_ml_unsuper

# ───────────────────────── 1.  QUALITY-LOOKUP TABLE ─────────────────────────
_RAW_QUALITY_LUT = pd.read_excel(
    Path(poe2trade_root) / "db" / "files" / "ring_amulet_quality_lookup.xlsx"
)
_Q_KEY     = _RAW_QUALITY_LUT.columns[0]
_patt_cols = [c for c in _RAW_QUALITY_LUT.columns if c != _Q_KEY]
_HEADER_MAP = {c: parse_rolled_mod(str(c))[0] for c in _patt_cols}
_Q_MAP: dict[str, list[str]] = {
    str(r[_Q_KEY]).strip().title(): [
        _HEADER_MAP[c] for c in _patt_cols if r[c]
    ]
    for _, r in _RAW_QUALITY_LUT.iterrows()
}

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

# ─────────────────────────── 3. HELPERS ──────────────────────────────────────
def _clean_line(txt: str) -> str:
    txt = _TOKEN_RE.sub("", txt).replace("--------", "")
    txt = re.sub(r"[()]", "", txt)
    return re.sub(r"\s+", " ", txt).strip()

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
      - metadata: category, name, base stats, corruption, socket_count
      - raw mod lines in fixed slots
    """
    print("\n[DEBUG] raw clipboard\n", text)
    text = re.sub(r'~(?:price|b/​o).*$','', text, flags=re.I|re.S).strip()

    row = {
        "Item Category": "",
        "Item Name": "",
        "Quality": 0,
        "Armour": 0,
        "Evasion Rating": 0,
        "Energy Shield": 0,
        "Corrupted": "Yes" if re.search(r"^\s*Corrupted\s*$", text, re.M) else "No",
        "socket_count": 0,
    }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
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
            if cls not in ("boots","gloves","helmet","body_armour"):
                cls = cls.rstrip("s")
            row["Item Category"] = cls
            continue

        # 2) Rarity Rare → next lines name
        if re.match(r"^Rarity:\s*Rare", ln, re.I):
            reading_name = True
            continue
        if reading_name:
            if ln.startswith("--------") or re.match(
                r"^(Quality|Armour|Evasion|Energy Shield|Requires|Sockets|Item Level)",
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

        cat_now = str(row.get("Item Category", "")).strip().lower()

        # 5) Base stats. Block chance is a shield/buckler base stat only.
        m_block = re.match(r"^Block\s*chance:\s*(\d+)\s*%", ln, re.I)
        if m_block and cat_now in ("shield", "buckler"):
            try:
                row["block"] = int(m_block.group(1))
            except Exception:
                pass
        elif m_block:
            continue
        else:
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
            row["socket_count"] = ln.split(":",1)[1].upper().count("S")

    row["Item Name"] = row["Item Name"].strip()

    # ── MOD LINES ────────────────────────────────────────────────────────
    implicit, enchant, rune, explicit = [], [], [], []
    for ln in mod_lines:
        # strip fractured/desecrated/descrated markers but keep other tags for slot routing
        clean0 = re.sub(r"\((fractured|desecrated|descrated)\)", "", ln, flags=re.I).strip()
        lw = clean0.lower()

        # skip dividers/flags/noise and non-mod text
        _bad_substrings = (
            "allocates ",
            "can only be equipped if you are wielding a bow",
            "place into an allocated jewel socket",
        )
        if (
            clean0.startswith("--------")
            or lw in ("corrupted", "fractured item")
            or lw.startswith("note:")
            or any(sub in lw for sub in _bad_substrings)
        ):
            continue

        # expand composites before slotting
        expanded = _expand_composite_line(clean0)

        # classify by tag in original (un-expanded) line; if missing, classify per each expanded line
        def _slot_for(s: str) -> list:
            l = s.lower()
            if "(implicit)" in l: return implicit
            if "(enchant)"  in l: return enchant
            if "(rune)"     in l: return rune
            return explicit

        for candidate in expanded:
            _slot_for(candidate).append(candidate)

    # fixed-slot assignment
    for i, ln in enumerate(implicit[:3],  1): row[f"implicit_mod_{i}"] = ln
    for i, ln in enumerate(enchant[:3],   1): row[f"enchant_mod_{i}"]  = ln
    for i, ln in enumerate(rune[:6],      1): row[f"rune_mod_{i}"]     = ln
    for i, ln in enumerate(explicit[:10], 1): row[f"explicit_mod_{i}"] = ln

    print("\n[DEBUG] parse_copied_item_text ➜ row\n")
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
            pat, avg, *_ = parse_rolled_mod(_clean_line(raw))
            # Normalize skill grant prefix so it matches model features
            if isinstance(pat, str):
                import re as _re
                pat = _re.sub(r"^\s*grants\s+skills?\s*:\s*", "", pat, flags=_re.I)
            if "(augmented)" in raw.lower():
                avg /= 20.0
            row[f"{prefix}_mod_{i}_pattern"] = re.sub(r"\s+"," ", pat).strip()
            row[f"{prefix}_mod_{i}_value"]   = round(float(avg),4)
    return row

# ───── 6. JEWELLERY QUALITY‐TYPE DEFLATOR ──────────────────────────────────
def _deflate_quality_type_modifiers(row: dict) -> dict:
    cat = str(row.get("Item Category","")).lower()
    if cat not in ("ring","amulet","belt"):
        return row

    qtype = row.get("Quality_Type")
    qpct  = row.get("Quality_Type_Pct")
    if not qtype or qpct is None:
        return row

    pats   = _Q_MAP.get(qtype.strip().title(), [])
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

    # For shields/bucklers, surface a simple block_norm for display
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
        if re.match(r"^(implicit|enchant|rune|explicit)_mod_\d+_(pattern|value)$", k):
            row.pop(k)

def cleanup_unused_features(row: dict) -> dict:
    for k in (
        "Armour", "Evasion Rating", "Energy Shield", "Quality",
        "Quality_Type", "Quality_Type_Pct", "socket_count", "Item Name",
        "explicit_mod_%", "rune_mod_%"
    ):
        row.pop(k, None)
    return row

# ───── 9. SEGMENT DETECTION & DF BUILDER ───────────────────────────────────
def detect_category_segment(row: dict) -> tuple[str, str|None]:
    cat = str(row.get("Item Category","default_model")).lower().replace(" ","_")
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
        "jewels": "jewel",
        "foci": "focus",
        "scepters": "sceptre",
        "sceptres": "sceptre",
        # keep canonical tokens as-is
        "boots": "boots",
        "gloves": "gloves",
        # singular typos → canonical
        "boot": "boots",
        "glove": "gloves",
        "scepter": "sceptre",
    }.get(cat, cat)
    # For simple categories (jewel/sceptre/wand/quiver) and jewellery, force seg=None
    if cat in ("ring","amulet","belt","jewel","sceptre","scepter","wand","quiver"):
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

# Jewel helper: infer subtype (sapphire/emerald/ruby) from raw clipboard text
def _infer_jewel_subtype(text: str) -> str | None:
    try:
        t = (text or "").lower()
        for jt in (jewel_list or []):
            pat = str(jt).strip().lower()
            if not pat:
                continue
            # strict word-boundary search to avoid partials
            if re.search(rf"\b{re.escape(pat)}\b", t, flags=re.I):
                return pat
    except Exception:
        pass
    return None

# ───── 10. PUBLIC ENTRY POINT ───────────────────────────────────────────────
def main(text: str, key: str):
    parsed = parse_copied_item_text(text)
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
        parsed["socket_count"] = total
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
    # uses per-type files (emerald/sapphire/ruby). Also append the subtype to the
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

    # 8) build DataFrame & dispatch ML
    X = build_feature_dataframe(parsed)
    print("\n[DEBUG] Feature DataFrame X:")
    print(X.T)

    if key == "super":
        return call_ml_super(cat_for_models, None if cat_for_models in ("sapphire","emerald","ruby") else seg, X)
    if key == "unsuper":
        # Primary attempt: use detected segment (or None for jewels)
        seg_in = None if cat_for_models in ("sapphire","emerald","ruby") else seg
        last_cat = cat_for_models
        last_seg = seg_in

        def _safe_call(cat_name: str, seg_name: Optional[str]) -> Optional[pd.DataFrame]:
            nonlocal last_cat, last_seg
            last_cat = cat_name
            last_seg = seg_name
            try:
                return call_ml_unsuper(cat_name, seg_name, X)
            except Exception:
                return None

        nbrs = _safe_call(cat_for_models, seg_in)
        # Fallback 1: if no neighbours, retry without segment to allow loader fallbacks
        if nbrs is None and seg_in is not None:
            nbrs = _safe_call(cat_for_models, None)
        # Fallback 2: as a last resort, try the original detected category (pre jewel-subtype switch)
        if nbrs is None and cat_for_models != cat:
            fallback_seg = None if cat in ("sapphire","emerald","ruby") else seg
            nbrs = _safe_call(cat, fallback_seg)

        if nbrs is None:
            seg_label = "global" if last_seg in (None, "", "none") else str(last_seg)
            raise FileNotFoundError(
                f"No unsupervised model available for category '{last_cat}' (segment '{seg_label}')."
            )

        pprint.pprint(nbrs)
        return X, nbrs

    raise ValueError("key must be 'super' or 'unsuper'")
