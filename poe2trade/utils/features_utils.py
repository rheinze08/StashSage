# features_utils.py  –  v2.3 (final helmet‑double‑corruption patch + implicit‑flag fix)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import re, os
from pathlib import Path
from typing import List, Tuple, Dict

import pandas as pd
from poe2trade import poe2trade_root           # used by features_excel_file()


# ════════════════════════════════════════════════════════════════════════════
#  Generic helpers
# ════════════════════════════════════════════════════════════════════════════
def parse_rolled_mod(mod_str: str) -> Tuple[str, float, float,
                                            str | None, bool, bool, bool]:
    raw = re.sub(r'^\+\s*', '', str(mod_str).lower().strip())
    nums = [float(g0) for g0, _ in re.findall(r'(\d+(\.\d+)?)', raw)]
    mn, mx = (nums[0], nums[-1]) if nums else (1.0, 1.0)
    pattern = re.sub(r'\d+(?:\.\d+)?', '#', raw)

    bad_kw = ('recharge', 'break', 'penetrate')
    ref_def = any(t in raw for t in ('armour', 'evasion', 'energy shield')) \
              and not any(b in raw for b in bad_kw)

    aA = 'armour'        in raw and ref_def
    aE = 'evasion'       in raw and ref_def
    aS = 'energy shield' in raw and ref_def
    bt = '#%' if (ref_def and '#%' in pattern) else '#'\
         if (ref_def and '#'  in pattern) else None
    return pattern, mn, mx, bt, aA, aE, aS


def parse_unrolled_mod(mod_str: str) -> Tuple[str, float, float, bool,
                                              str | None, bool, bool, bool]:
    raw = re.sub(r'^\+\s*', '', str(mod_str).lower().strip())
    mid = re.sub(r'[()]', '', raw)
    mid = re.sub(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', r'\1', mid)
    pattern = re.sub(r'\d+(?:\.\d+)?', '#', mid)

    mult_ok = not bool(re.search(r'\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?', raw))
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', raw)]
    mn, mx = (nums[0], nums[-1]) if nums else (1.0, 1.0)

    bad_kw = ('recharge', 'break', 'penetrate')
    ref_def = any(t in raw for t in ('armour', 'evasion', 'energy shield')) \
              and not any(b in raw for b in bad_kw)

    aA = 'armour'        in raw and ref_def
    aE = 'evasion'       in raw and ref_def
    aS = 'energy shield' in raw and ref_def
    bt = '#%' if (ref_def and '#%' in pattern) else '#'\
         if (ref_def and '#'  in pattern) else None
    return pattern, mn, mx, mult_ok, bt, aA, aE, aS


def compare_mods(rolled: str, unrolled: str) -> Tuple[bool, int | None]:
    rp, rmin, *_ = parse_rolled_mod(rolled)
    up, umin, *_ = parse_unrolled_mod(unrolled)
    if rp != up:
        return False, None
    mult_ok = parse_unrolled_mod(unrolled)[3]
    if not mult_ok:
        return rmin == umin, None
    if abs(umin) < 1e-9:
        return False, None
    k = round(rmin / umin)
    return abs(rmin - k * umin) <= 1e-9, k


def minimal_additive_combo(total: float, variants: List[float],
                           max_runes: int = 3) -> List[float]:
    EPS = 1e-9
    variants = sorted(variants, reverse=True)

    def dfs(rem, idx, path):
        if abs(rem) <= EPS:
            return path[:]
        if len(path) == max_runes:
            return None
        for i in range(idx, len(variants)):
            v = variants[i]
            if v > rem + EPS:
                continue
            res = dfs(rem - v, i, path + [v])
            if res:
                return res
        return None
    return dfs(total, 0, []) or []


# ════════════════════════════════════════════════════════════════════════════
#  Pre‑mods  (helmet double‑corruption + implicit‑flag fix)
# ════════════════════════════════════════════════════════════════════════════
def _clean_cell(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ''
    s = str(val).strip()
    return '' if s.lower() == 'nan' else s


def parse_pre_mods(row: dict,
                   df_category_items: pd.DataFrame,
                   df_corruption:   pd.DataFrame,
                   df_rune:         pd.DataFrame) -> dict:
    num_re = re.compile(r'(\d+(?:\.\d+)?)')
    cat = str(row.get('Item Category', '') or
              row.get('Category', '')).lower().replace(' ', '_')
    corrupted = str(row.get('Corrupted', '')).lower() == 'yes'

    slots: list[tuple[int, str]] = [
        (i, txt) for i in range(1, 6)
        if (txt := _clean_cell(row.get(f'pre_mod{i}')))
    ]

    flags = df_category_items[
        (df_category_items['category']  == cat) &
        (df_category_items['item name'] ==
         str(row.get('Item Name', '')).lower())
    ]['implicit mod flag']
    impl_flag = (not flags.empty) and int(flags.iloc[0]) == 1

    implicit_line = None
    if impl_flag and slots:
        _, implicit_line = slots.pop()

    row.update({
        'implicit_mod_pattern': None, 'implicit_mod_value': None,
        'implicit_mod_base_type': None,
        'implicit_mod_affects_armour': False,
        'implicit_mod_affects_evasion': False,
        'implicit_mod_affects_energy_shield': False,
    })
    if implicit_line:
        pat, mn, *_ = parse_rolled_mod(implicit_line)
        bt, aA, aE, aS = parse_rolled_mod(implicit_line)[3:]
        row.update({
            'implicit_mod_pattern': pat, 'implicit_mod_value': mn,
            'implicit_mod_base_type': bt,
            'implicit_mod_affects_armour': aA,
            'implicit_mod_affects_evasion': aE,
            'implicit_mod_affects_energy_shield': aS,
        })

    corr_ok = ({1, 2} if (corrupted and cat == 'helmet')
               else {1}  if corrupted else set())

    col_map = {
        'body_armour': 'armourmod', 'gloves': 'armourmod', 'boots': 'armourmod',
        'helmet': 'armourmod', 'belt': 'armourmod',
        'weapon': 'martialweaponmod', 'bow': 'martialweaponmod',
        'crossbow': 'martialweaponmod', 'quarterstaff': 'martialweaponmod',
    }
    rune_col = {c.lower(): c for c in df_rune.columns}.get(col_map.get(cat))

    row.update({
        'iron_rune_deflator': 0.0, 'total_rune_count': 0,
        'corruption1_pattern': None, 'corruption1_value': None,
        'corruption1_base_type': None,
        'corruption1_affects_armour': False,
        'corruption1_affects_evasion': False,
        'corruption1_affects_energy_shield': False,
        'corruption2_pattern': None, 'corruption2_value': None,
        'corruption2_base_type': None,
        'corruption2_affects_armour': False,
        'corruption2_affects_evasion': False,
        'corruption2_affects_energy_shield': False,
        'leftover_pre_mods': None,
    })
    corr_slots: list[int] = []
    leftovers: list[str] = []

    def _rune_vals(core: str) -> list[float]:
        vals: list[float] = []
        for _, rr in df_rune.iterrows():
            name = re.sub(r'^(lesser |greater )', '', str(
                rr[df_rune.columns[0]]).lower()).replace(' rune', '').strip()
            if name != core:
                continue
            vals.extend(float(x) for x in num_re.findall(str(
                rr.get(rune_col, '')).lower()))
        return vals

    for i in range(len(slots) - 1, -1, -1):
        slot_no, txt = slots[i]
        lw = txt.lower()
        mnum = num_re.search(lw)
        nval = float(mnum.group(1)) if mnum else None
        matched = False

        if (nval is not None) and rune_col:
            for _, rw in df_rune.iterrows():
                rp = str(rw.get(rune_col, '')).lower()
                if not rp or parse_rolled_mod(lw)[0] != parse_unrolled_mod(rp)[0]:
                    continue
                base = re.sub(r'^(lesser |greater )', '', str(
                    rw[df_rune.columns[0]]).lower()).replace(' rune', '').strip()
                if minimal_additive_combo(nval,
                                          sorted(set(_rune_vals(base)), reverse=True)):
                    row['total_rune_count'] += 1
                    if base == 'iron':
                        row['iron_rune_deflator'] = nval
                    matched = True
                    break

        if (not matched) and (slot_no in corr_ok):
            for _, cw in df_corruption.iterrows():
                cp_txt = str(cw.get('mod', '')).lower()
                if cp_txt and parse_rolled_mod(lw)[0] == parse_unrolled_mod(cp_txt)[0]:
                    cp, cmin, *_ = parse_unrolled_mod(cp_txt)
                    cbt, cA, cE, cS = parse_unrolled_mod(cp_txt)[4:]
                    target = ('corruption1' if row['corruption1_pattern'] is None else
                              'corruption2' if (cat == 'helmet' and
                                                row['corruption2_pattern'] is None) else None)
                    if target:
                        row[f'{target}_pattern'] = cp
                        row[f'{target}_value']   = cmin
                        row[f'{target}_base_type'] = cbt
                        row[f'{target}_affects_armour'] = cA
                        row[f'{target}_affects_evasion'] = cE
                        row[f'{target}_affects_energy_shield'] = cS
                        corr_slots.append(slot_no)
                        matched = True
                        break

        if not matched:
            leftovers.append(txt)

    if cat == 'helmet' and 2 in corr_slots and 1 not in corr_slots:
        raise AssertionError("Helmet: slot 2 is corruption but slot 1 is not")

    if leftovers:
        row['leftover_pre_mods'] = leftovers
        raise AssertionError(f"{row.get('Item Title','(row)')} → leftover_pre_mods: {leftovers}")

    base_sock = {'body_armour': 2, 'gloves': 1, 'boots': 1,
                 'helmet': 1, 'belt': 0}.get(cat, 0)
    row['extra_socket_mod'] = int(row['total_rune_count'] == base_sock + 1)

    if corrupted and (row['corruption1_pattern'] or row['corruption2_pattern']):
        assert not row['extra_socket_mod'], "Corrupted item cannot have extra_socket_mod=1"
    return row


# ════════════════════════════════════════════════════════════════════════════
#  Post‑mods
# ════════════════════════════════════════════════════════════════════════════
def parse_post_mods(row: dict) -> dict:
    for i in range(1, 10):
        raw = row.get(f'mod{i}')
        pc, vc, bc = (f'mod{i}_pattern', f'mod{i}_value', f'mod{i}_base_type')
        aa, ae, es = (f'mod{i}_affects_armour',
                      f'mod{i}_affects_evasion',
                      f'mod{i}_affects_energy_shield')
        if pd.notnull(raw):
            pat, mn, *_ = parse_unrolled_mod(str(raw))
            bt, aA, aE, aS = parse_unrolled_mod(str(raw))[4:]
            row.update({pc: pat, vc: mn, bc: bt, aa: aA, ae: aE, es: aS})
        else:
            row.update({pc: None, vc: None, bc: None, aa: False, ae: False, es: False})
    return row


# ════════════════════════════════════════════════════════════════════════════
#  Collapse to unique_modN_*
# ════════════════════════════════════════════════════════════════════════════
def parse_all_mods(row: dict,
                   df_category_items: pd.DataFrame,
                   df_corruption:   pd.DataFrame,
                   df_rune:         pd.DataFrame) -> dict:
    parse_pre_mods(row, df_category_items, df_corruption, df_rune)
    parse_post_mods(row)

    combos: list[Tuple[str, float, str | None, bool, bool, bool]] = []

    if row.get('implicit_mod_pattern') is not None:
        combos.append((row['implicit_mod_pattern'],
                       float(row['implicit_mod_value'] or 0),
                       row['implicit_mod_base_type'],
                       row['implicit_mod_affects_armour'],
                       row['implicit_mod_affects_evasion'],
                       row['implicit_mod_affects_energy_shield']))

    for k in (1, 2):
        if row.get(f'corruption{k}_pattern') is not None:
            combos.append((row[f'corruption{k}_pattern'],
                           float(row[f'corruption{k}_value'] or 0),
                           row[f'corruption{k}_base_type'],
                           row[f'corruption{k}_affects_armour'],
                           row[f'corruption{k}_affects_evasion'],
                           row[f'corruption{k}_affects_energy_shield']))

    for i in range(1, 10):
        if row.get(f'mod{i}_pattern') is not None:
            combos.append((row[f'mod{i}_pattern'],
                           float(row[f'mod{i}_value'] or 0),
                           row[f'mod{i}_base_type'],
                           row[f'mod{i}_affects_armour'],
                           row[f'mod{i}_affects_evasion'],
                           row[f'mod{i}_affects_energy_shield']))

    merged: Dict[str, Dict] = {}
    for pat, val, bt, aA, aE, aS in combos:
        d = merged.setdefault(pat, {
            'value': 0.0, 'base_type': bt,
            'aff_armour': False, 'aff_evasion': False, 'aff_es': False})
        d['value'] += val
        if d['base_type'] != '#%' and bt == '#%':
            d['base_type'] = '#%'
        d['aff_armour'] |= aA
        d['aff_evasion'] |= aE
        d['aff_es']      |= aS

    for k in [c for c in row if c.startswith('unique_mod')]:
        row[k] = None

    for idx, (pat, inf) in enumerate(list(merged.items()), start=1):
        row.update({
            f'unique_mod{idx}_pattern':               pat,
            f'unique_mod{idx}_value':                 inf['value'],
            f'unique_mod{idx}_base_type':             inf['base_type'],
            f'unique_mod{idx}_affects_armour':        inf['aff_armour'],
            f'unique_mod{idx}_affects_evasion':       inf['aff_evasion'],
            f'unique_mod{idx}_affects_energy_shield': inf['aff_es'],
        })
    return row

###############################################################################
# deflator
###############################################################################
def deflator(row):
    """
    Deflate displayed defences (Armour, Evasion, Energy Shield) to approximate
    the pre-rune, pre-quality base:

       deflated = displayed / [(1 + iron_fraction + sum_pct/100)*(1 + Quality/100)] - sum_flat

    Steps:
      1) Summation of # and #% across unique_mod1..20 for armour/evasion/es.
      2) iron_fraction from lesser/normal/greater => 0.15, 0.20, 0.25 each.
      3) read Quality from row, parse float.
      4) apply formula for each defence => store in Deflated_Armour, etc.
    """
    def sf(x):
        try:
            return float(x or 0)
        except:
            return 0
    arm_f=0; arm_p=0
    eva_f=0; eva_p=0
    es_f=0;  es_p=0
    for i in range(1,21):
        b_=row.get(f"unique_mod{i}_base_type")
        v_=sf(row.get(f"unique_mod{i}_value",0))
        aA_=bool(row.get(f"unique_mod{i}_affects_armour",False))
        aE_=bool(row.get(f"unique_mod{i}_affects_evasion",False))
        aS_=bool(row.get(f"unique_mod{i}_affects_energy_shield",False))
        if b_=="#":
            if aA_: arm_f+=v_
            if aE_: eva_f+=v_
            if aS_: es_f+=v_
        elif b_=="#%":
            if aA_: arm_p+=v_
            if aE_: eva_p+=v_
            if aS_: es_p+=v_
    iron_fraction = sf(row.get("iron_rune_deflator",0))
    q_str=str(row.get("Quality","0")).strip()
    try: qv=float(q_str)
    except: qv=0
    def do_def(disp, flv, pct):
        d_=(1+iron_fraction/100 + pct/100)*(1+qv/100)
        if d_<1e-9:
            return 0
        return (disp / d_)-flv
    ar=sf(row.get("Armour",0))
    ev=sf(row.get("Evasion Rating",0))
    es=sf(row.get("Energy Shield",0))
    row["Deflated_Armour"]=do_def(ar,arm_f,arm_p)
    row["Deflated_Evasion"]=do_def(ev,eva_f,eva_p)
    row["Deflated_EnergyShield"]=do_def(es,es_f,es_p)
    return row

###############################################################################
# set_defense_and_resistance_flags  (updated – only resist_count retained)
###############################################################################
def set_defense_and_resistance_flags(row):
    """
    Sets classification flags based on the raw displayed defences:
      - If only 'Armour' >0 ⇒ ar_only=1, etc. If all three ⇒ all_three=1
      - Resist counting: how many distinct resistance mods exist with value > 0
        ⇒ row["resist_count"] only (no separate has_1/2/3_resist flags)
      - Mixed flat/% detection ⇒ row["has_flat_and_pct"]=1 if both present
    """
    def sf(x):
        try:
            return float(x or 0)
        except:
            return 0.0

    # ─── Defence type flags ─────────────────────────────────────────────
    a = sf(row.get("Armour", 0))
    e = sf(row.get("Evasion Rating", 0))
    s = sf(row.get("Energy Shield", 0))

    row["ar_only"]     = 0
    row["ev_only"]     = 0
    row["es_only"]     = 0
    row["ar_ev_only"]  = 0
    row["ar_es_only"]  = 0
    row["ev_es_only"]  = 0
    row["all_three"]   = 0

    ca = int(a > 0)
    ce = int(e > 0)
    cs = int(s > 0)
    su = ca + ce + cs

    if su == 3:
        row["all_three"] = 1
    elif su == 2:
        if ca and ce: row["ar_ev_only"] = 1
        elif ca and cs: row["ar_es_only"] = 1
        elif ce and cs: row["ev_es_only"] = 1
    elif su == 1:
        if ca: row["ar_only"] = 1
        if ce: row["ev_only"] = 1
        if cs: row["es_only"] = 1

    # ─── Resistance count (0–4 possible) ────────────────────────────────
    rc = 0
    for i in range(1, 21):
        pt = (row.get(f"unique_mod{i}_pattern", "") or "").lower()
        val = sf(row.get(f"unique_mod{i}_value", 0))
        if val > 0 and pt:
            if ("to cold resistance" in pt or
                "to fire resistance" in pt or
                "to lightning resistance" in pt or
                "to chaos resistance" in pt):
                rc += 1
    row["resist_count"] = rc

    # ─── Flat + percent mixed detection ─────────────────────────────────
    has_flat = False
    has_pct  = False
    for i in range(1, 21):
        bt = row.get(f"unique_mod{i}_base_type", "")
        val = sf(row.get(f"unique_mod{i}_value", 0))
        if val > 0 and bt:
            if bt == "#":   has_flat = True
            if bt == "#%":  has_pct = True

    row["has_flat_and_pct"] = 1 if (has_flat and has_pct) else 0

    return row

###############################################################################
# features_excel_file
###############################################################################
def features_excel_file(input_excel_file, output_excel_file):
    """
    The main pipeline function, reading from 'input_excel_file', producing an
    Excel with final columns to 'output_excel_file'.

    Steps:
      1) Load category_items => for implicit mod detection.
      2) Load corruption & rune => for parse_pre_mods logic.
      3) Read input excel.
      4) For each row => process_all_mods => deflator => set_defense_and_resistance_flags.
      5) Reorder columns so pattern+value+base_type appear after each mod col.
      6) Write final to 'Report' sheet in 'output_excel_file'.
    """
    import openpyxl

    rootdir = Path(poe2trade_root)
    cat_path = str(rootdir / "db" / "files" / "category_items.xlsx")
    if not os.path.exists(cat_path):
        raise FileNotFoundError(f"Could not locate category_items.xlsx at {cat_path}")

    xls = pd.ExcelFile(cat_path)
    cat_list=[]
    for sh in xls.sheet_names:
        ds=pd.read_excel(xls, sheet_name=sh)
        ds.columns=[c.lower() for c in ds.columns]
        ds["category"]=sh.lower()
        ds["item name"]=ds["item name"].str.lower()
        cat_list.append(ds[["category","item name","implicit mod flag"]])
    df_category_items = pd.concat(cat_list, ignore_index=True)

    mods_file = str(rootdir / "mods" / "files" / "mods_trade_updated.xlsx")
    dfc = pd.read_excel(mods_file, sheet_name="Corruption")
    dfc.columns=[c.lower() for c in dfc.columns]
    for c_ in dfc.select_dtypes(["object"]).columns:
        dfc[c_]=dfc[c_].map(lambda x:x.lower() if isinstance(x,str) else x)

    dfr = pd.read_excel(mods_file, sheet_name="Rune")
    dfr.columns=[c.lower() for c in dfr.columns]
    for c_ in dfr.select_dtypes(["object"]).columns:
        dfr[c_]=dfr[c_].map(lambda x:x.lower() if isinstance(x,str) else x)

    df_in=pd.read_excel(input_excel_file)
    orig_cols=list(df_in.columns)
    out=[]
    for i,rw in df_in.iterrows():
        dd=rw.to_dict()
        dd=parse_all_mods(dd, df_category_items, dfc, dfr)
        dd=deflator(dd)
        dd=set_defense_and_resistance_flags(dd)
        out.append(dd)

    final=pd.DataFrame(out)

    # reorder columns
    mod_cols=final.columns.tolist()
    reord=[]
    idx=0
    while idx<len(orig_cols):
        c_=orig_cols[idx]
        reord.append(c_)
        def maybe_add(e_):
            if e_ in mod_cols and e_ not in reord:
                reord.append(e_)
        if c_.startswith("pre_mod"):
            s_= c_.replace("pre_mod","")
            maybe_add(f"pre_mod{s_}_pattern")
            maybe_add(f"pre_mod{s_}_value")
            maybe_add(f"pre_mod{s_}_base_type")
            maybe_add(f"pre_mod{s_}_affects_armour")
            maybe_add(f"pre_mod{s_}_affects_evasion")
            maybe_add(f"pre_mod{s_}_affects_energy_shield")
        elif c_.startswith("mod") and "_tier" not in c_:
            s_=c_.replace("mod","")
            tcol= f"mod{s_}_tier"
            if tcol in orig_cols:
                reord.append(tcol)
            maybe_add(f"mod{s_}_pattern")
            maybe_add(f"mod{s_}_value")
            maybe_add(f"mod{s_}_base_type")
            maybe_add(f"mod{s_}_affects_armour")
            maybe_add(f"mod{s_}_affects_evasion")
            maybe_add(f"mod{s_}_affects_energy_shield")
            if idx+1<len(orig_cols) and orig_cols[idx+1]==tcol:
                idx+=1
        idx+=1

    for cc_ in mod_cols:
        if cc_ not in reord:
            reord.append(cc_)

    final=final.reindex(columns=reord)
    with pd.ExcelWriter(output_excel_file, engine="openpyxl") as w_:
        final.to_excel(w_, sheet_name="Report", index=False)