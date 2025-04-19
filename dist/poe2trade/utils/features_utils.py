import pandas as pd
import re
import os
from pathlib import Path
from poe2trade import poe2trade_root

###############################################################################
# parse_rolled_mod
###############################################################################
def parse_rolled_mod(mod_str: str):
    """
    Parses a fully "rolled" mod string, for example:
      "+20% increased Armour, Evasion and Energy Shield"

    Steps:
      1. Remove any leading '+'.
      2. Find all numeric substrings. The first is 'min_value', the last is 'max_value'.
         If none found, default them to 1.0.
      3. Build a 'pattern' by replacing digits with '#', e.g. "15% -> '#%'."
      4. Check if the mod references "armour, evasion, energy shield" while ignoring certain
         keywords like 'recharge' that might appear in other contexts.
      5. If it references defences and has '#%', base_type="#%". If it references defences
         and has '#', base_type="#". Otherwise None.
      6. Returns:
         (pattern, min_value, max_value, base_type,
          affects_armour, affects_evasion, affects_energy_shield).
    """
    raw = mod_str.lower().strip()
    raw = re.sub(r"^\+(\s*)", "", raw)
    nums = re.findall(r"(\d+(\.\d+)?)", raw)
    if nums:
        arr = [float(x[0]) for x in nums]
        mn = arr[0]
        mx = arr[-1]
    else:
        mn = mx = 1.0

    pat = re.sub(r"\d+(\.\d+)?", "#", raw)

    bad = ["recharge", "break", "penetrate"]
    references_defence = (
        ("armour" in raw or "evasion" in raw or "energy shield" in raw)
        and not any(b in raw for b in bad)
    )

    aA = ("armour" in raw) and references_defence
    aE = ("evasion" in raw) and references_defence
    aS = ("energy shield" in raw) and references_defence

    if references_defence and "#%" in pat:
        bt = "#%"
    elif references_defence and "#" in pat:
        bt = "#"
    else:
        bt = None

    return (pat, mn, mx, bt, aA, aE, aS)

###############################################################################
# parse_unrolled_mod
###############################################################################
def parse_unrolled_mod(mod_str: str):
    """
    Parses an "unrolled" mod string (e.g. "15% increased armour, evasion and energy shield"),
    possibly with bracketed/dash-based ranges:
      "[13 - 16]% increased Evasion" => pattern "#% increased evasion"

    Steps:
      1. Strip leading '+'.
      2. Remove parentheses.
      3. Replace dash-based numeric ranges (X - Y) with X, purely to build a pattern.
      4. Replace digits with '#' in the text => pattern (e.g. "15% -> '#%'").
      5. If the original text had a dash, multiplicity_allowed=False; else True.
      6. Extract numeric substrings for min_value & max_value. If none => 1.0 each.
      7. Check references to armour/evasion/energy shield.
      8. base_type="#%" if it's a % defence mod, "#" if flat defence mod, else None.
      9. Returns:
         (pattern, min_value, max_value, multiplicity_allowed,
          base_type, affects_armour, affects_evasion, affects_energy_shield)
    """
    raw = mod_str.lower().strip()
    raw = re.sub(r"^\+(\s*)", "", raw)
    no_paren = re.sub(r"[()]", "", raw)
    mid = re.sub(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", r"\1", no_paren)
    pat = re.sub(r"\d+(\.\d+)?", "#", mid)

    dash_found = re.search(r"\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?", mod_str)
    multiplicity_allowed = not bool(dash_found)

    nums = re.findall(r"(\d+(?:\.\d+)?)", mod_str)
    if nums:
        mn = float(nums[0])
        mx = float(nums[-1])
    else:
        mn = mx = 1.0

    bad = ["recharge", "break", "penetrate"]
    references_defence = (
        ("armour" in raw or "evasion" in raw or "energy shield" in raw)
        and not any(b in raw for b in bad)
    )

    aA = ("armour" in raw) and references_defence
    aE = ("evasion" in raw) and references_defence
    aS = ("energy shield" in raw) and references_defence

    if references_defence and "#%" in pat:
        btype = "#%"
    elif references_defence and "#" in pat:
        btype = "#"
    else:
        btype = None

    return (pat, mn, mx, multiplicity_allowed, btype, aA, aE, aS)

###############################################################################
# compare_mods
###############################################################################
def compare_mods(rolled_str: str, unrolled_str: str):
    """
    Checks if a "rolled" mod (e.g. '+45% increased armour, evasion and energy shield')
    matches an "unrolled" pattern (e.g. '15% increased armour, evasion and energy shield')
    using integer multiples or range checks.

    Steps:
      1. parse_rolled_mod(rolled_str) => (bp, bmin, bmax, ...)
      2. parse_unrolled_mod(unrolled_str) => (cp, cmin, cmax, allow_mult, ...)
      3. If bp != cp => (False, None).
      4. If not allow_mult, we check if bmin..bmax overlaps or is contained by cmin..cmax
         or vice versa => (True, None) if so, else (False, None).
      5. If allow_mult==True, we see if bmin/cmin is an integer => (True, that_int).
         Otherwise => (False, None).

    Returns (BoolMatch, integerMultipleOrNone).
    """
    (bp, bmin, bmax, _, _, _, _) = parse_rolled_mod(rolled_str)
    (cp, cmin, cmax, allow_mult, _, _, _, _) = parse_unrolled_mod(unrolled_str)

    if bp != cp:
        return (False, None)

    if not allow_mult:
        in_a = (bmin >= cmin and bmax <= cmax)
        in_b = (cmin >= bmin and cmax <= bmax)
        if in_a or in_b:
            return (True, None)
        return (False, None)
    else:
        if abs(cmin) < 1e-9:
            return (False, None)
        ratio = bmin / cmin
        ni = round(ratio)
        if abs(ratio - ni) <= 1e-9:
            return (True, ni)
        return (False, None)

###############################################################################
# rune/socket count helper function
###############################################################################
def minimal_additive_combo(total: int, variants: list[int], max_runes: int = 3) -> list[int]:
    """
    Return the *shortest* list of variant values summing to `total`, or [].
    Uses BFS‐like recursion to find minimal socket usage.
    """
    variants = sorted(variants, reverse=True)
    def dfs(rem: int, start: int, path: list[int]):
        if rem == 0:
            return path[:]
        if len(path) == max_runes:
            return None
        for i in range(start, len(variants)):
            v = variants[i]
            if v > rem:
                continue
            res = dfs(rem - v, i, path + [v])
            if res:
                return res
        return None
    return dfs(total, 0, []) or []

###############################################################################
# parse_pre_mods
###############################################################################
def parse_pre_mods(row, df_category_items, df_corruption_mods, df_rune_mods):
    """
    Scans an item row’s pre‑mods, detects implicit lines, rune lines (all bases
    incl. Iron), and corruption lines. For rune lines it determines the
    minimal number of runes (across grades) needed to achieve the rolled value.
    If the matched base is an Iron Rune, its rolled % is recorded as
    `iron_rune_deflator`.

    Also adds:
      - total_rune_count
      - iron_rune_deflator
      - extra_socket_mod: 1 if total_rune_count == base_socket_count + 1, else 0

    Assertion checks:
      • corrupted items cannot have both a corruption_pattern and extra_socket_mod=1
      • there are no leftover_pre_mods
      • total_rune_count ≤ base + 1

    Rune matching logic:
      We do **not** use `compare_mods(...)` for rune matching because it is designed
      to check 1:1 or clean integer multiple alignment of values. Rune lines are often
      a *sum* of multiple rune rolls (e.g., +12% + 14% = 26%), which `compare_mods` cannot
      account for. Instead, we use `parse_rolled_mod` and `parse_unrolled_mod` to match
      patterns structurally, and then use additive logic (`minimal_additive_combo`) to
      verify the value is achievable from available rune variants.
    """
    import re
    import pandas as pd

    # 1) collect pre_mod1..pre_mod5
    premods = []
    for i in range(1, 6):
        v = row.get(f"pre_mod{i}")
        if v and pd.notnull(v):
            s = str(v).strip()
            if s:
                premods.append(s)

    # 2) implicit-mod detection
    cat_ = (row.get("Item Category", "") or row.get("Category", "")).lower().replace(" ", "_")
    name_ = str(row.get("Item Name", "")).lower()
    flags = df_category_items[
        (df_category_items["category"] == cat_) &
        (df_category_items["item name"] == name_)
    ]["implicit mod flag"]
    implicit_str = None
    if not flags.empty and int(flags.iloc[0]) == 1 and premods:
        implicit_str = premods.pop()

    row["implicit_mod_pattern"] = None
    row["implicit_mod_value"] = None
    row["implicit_mod_base_type"] = None
    row["implicit_mod_affects_armour"] = False
    row["implicit_mod_affects_evasion"] = False
    row["implicit_mod_affects_energy_shield"] = False
    if implicit_str:
        p, mn, mx, bt, aA, aE, aS = parse_rolled_mod(implicit_str.lower())
        row["implicit_mod_pattern"] = p
        row["implicit_mod_value"] = mn
        row["implicit_mod_base_type"] = bt
        row["implicit_mod_affects_armour"] = aA
        row["implicit_mod_affects_evasion"] = aE
        row["implicit_mod_affects_energy_shield"] = aS

    # 3) init counters & flags
    row["iron_rune_deflator"] = 0
    row["total_rune_count"] = 0
    row["leftover_pre_mods"] = None
    corrupted = str(row.get("Corrupted", "")).lower() == "yes"
    row["corruption_pattern"] = None
    row["corruption_value"] = None
    row["corruption_base_type"] = None
    row["corruption_affects_armour"] = False
    row["corruption_affects_evasion"] = False
    row["corruption_affects_energy_shield"] = False

    # 4) determine which rune column to use
    cat_to_runef = {
        "body_armour": "armourmod",
        "gloves": "armourmod",
        "boots": "armourmod",
        "helmet": "armourmod",
        "belt": "armourmod",
        "weapon": "martialweaponmod",
        "bow": "martialweaponmod",
        "crossbow": "martialweaponmod",
        "quarterstaff": "martialweaponmod",
    }
    runef = cat_to_runef.get(cat_)
    lc = {c.lower(): c for c in df_rune_mods.columns}
    rune_col = lc.get(runef) if runef else None

    # 5) scan pre_mods from last to first
    leftovers = []
    for idx in range(len(premods) - 1, -1, -1):
        line = premods[idx]
        lw = line.lower()
        m = re.search(r"(\d+)", lw)
        if not m:
            leftovers.append(line)
            continue
        val = int(m.group(1))
        matched = False

        # 5a) rune detection using pattern comparison only (not compare_mods)
        if rune_col:
            for _, rw in df_rune_mods.iterrows():
                base_name = str(rw[df_rune_mods.columns[0]]).lower()
                pat = str(rw.get(rune_col, "")).lower()
                if not pat:
                    continue

                rp, *_ = parse_rolled_mod(lw)
                up, *_ = parse_unrolled_mod(pat)
                if rp != up:
                    continue

                base_norm = re.sub(r"^(lesser |greater )", "", base_name).replace(" rune", "").strip()

                values = []
                for _, rw2 in df_rune_mods.iterrows():
                    nm2 = str(rw2[df_rune_mods.columns[0]]).lower()
                    nm2_norm = re.sub(r"^(lesser |greater )", "", nm2).replace(" rune", "").strip()
                    if nm2_norm != base_norm:
                        continue
                    txt = str(rw2.get(rune_col, "")).lower()
                    values += [int(x) for x in re.findall(r"(\d+)", txt)]

                values = sorted(set(values), reverse=True)
                combo = minimal_additive_combo(val, values)
                if combo:
                    row["total_rune_count"] += len(combo)
                    if base_norm == "iron":
                        row["iron_rune_deflator"] = val
                matched = True
                break

        # 5b) corruption detection (only top-line)
        if not matched and corrupted and idx == 0:
            for _, cc in df_corruption_mods.iterrows():
                cm = str(cc.get("mod", "")).lower()
                if not cm:
                    continue
                rp, *_ = parse_rolled_mod(lw)
                up, *_ = parse_unrolled_mod(cm)
                if rp != up:
                    continue
                cp, cmin, _, _, cbt, cA, cE, cS = parse_unrolled_mod(cm)
                row["corruption_pattern"] = cp
                row["corruption_value"] = cmin
                row["corruption_base_type"] = cbt
                row["corruption_affects_armour"] = cA
                row["corruption_affects_evasion"] = cE
                row["corruption_affects_energy_shield"] = cS
                matched = True
                break

        if not matched:
            leftovers.append(line)

    if leftovers:
        leftovers.reverse()
        row["leftover_pre_mods"] = leftovers

    # 6) extra_socket_mod & assertions
    base_sockets = {
        "body_armour": 2,
        "gloves": 1,
        "boots": 1,
        "helmet": 1,
        "belt": 0,
    }
    base_count = base_sockets.get(cat_, 0)
    row["extra_socket_mod"] = 1 if row["total_rune_count"] == base_count + 1 else 0

    if corrupted:
        assert not (
            row["corruption_pattern"] and row["extra_socket_mod"] == 1
        ), f"Item '{row.get('Item Title')}' is corrupted but has both corruption_pattern and extra_socket_mod=1"
    assert not row.get("leftover_pre_mods"), f"Item '{row.get('Item Title')}' has leftover_pre_mods: {row['leftover_pre_mods']}"
    assert row["total_rune_count"] <= base_count + 1, f"Item '{row.get('Item Title')}' has total_rune_count {row['total_rune_count']} > base+1 ({base_count + 1})"

    return row

###############################################################################
# parse_post_mods
###############################################################################
def parse_post_mods(row):
    """
    Parses 'mod1..mod9' lines (typical affix lines).

    For each modN:
      - If row[modN] is not null, parse_unrolled_mod it and store in modN_pattern, modN_value, ...
      - Else set them to None/False.
    """
    mod_cols = ["mod9","mod8","mod7","mod6","mod5","mod4","mod3","mod2","mod1"]
    for col in mod_cols:
        pc= col+"_pattern"
        vc= col+"_value"
        bc= col+"_base_type"
        aa= col+"_affects_armour"
        ae= col+"_affects_evasion"
        as_= col+"_affects_energy_shield"
        if col in row and pd.notnull(row[col]):
            txt = str(row[col])
            (p_,mn_,mx_,mul_,bt_,aA_,aE_,aS_) = parse_unrolled_mod(txt)
            row[pc]=p_
            row[vc]=mn_
            row[bc]=bt_
            row[aa]=aA_
            row[ae]=aE_
            row[as_]=aS_
        else:
            row[pc]=None
            row[vc]=None
            row[bc]=None
            row[aa]=False
            row[ae]=False
            row[as_]=False

###############################################################################
# parse_all_mods
###############################################################################
def parse_all_mods(row, df_category_items, df_corruption_mods, df_rune_mods):
    """
    Main function for a single item:
      1) parse_pre_mods => interpret pre_mod1..5 (implicit, runes, corruption).
      2) process_post_mods => interpret mod1..mod9 lines.
      3) unify everything into unique_mod1..N by pattern.

    Returns updated row.
    """
    parse_pre_mods(row, df_category_items, df_corruption_mods, df_rune_mods)
    parse_post_mods(row)

    # gather them
    combos=[]
    # implicit
    if row.get("implicit_mod_pattern") and row.get("implicit_mod_value") is not None:
        combos.append((
            row["implicit_mod_pattern"],
            float(row["implicit_mod_value"] or 0),
            row["implicit_mod_base_type"],
            bool(row["implicit_mod_affects_armour"]),
            bool(row["implicit_mod_affects_evasion"]),
            bool(row["implicit_mod_affects_energy_shield"])
        ))
    # corruption
    if row.get("corruption_pattern") and row.get("corruption_value") is not None:
        combos.append((
            row["corruption_pattern"],
            float(row["corruption_value"] or 0),
            row["corruption_base_type"],
            bool(row["corruption_affects_armour"]),
            bool(row["corruption_affects_evasion"]),
            bool(row["corruption_affects_energy_shield"])
        ))
    # mod1..mod9
    for i in range(1,10):
        pc = f"mod{i}_pattern"
        vc = f"mod{i}_value"
        bc = f"mod{i}_base_type"
        aa = f"mod{i}_affects_armour"
        ae = f"mod{i}_affects_evasion"
        as_ = f"mod{i}_affects_energy_shield"
        if row.get(pc) and row.get(vc) is not None:
            combos.append((
                row[pc],
                float(row[vc] or 0),
                row.get(bc),
                bool(row.get(aa,False)),
                bool(row.get(ae,False)),
                bool(row.get(as_,False))
            ))

    # unify by pattern => sum up
    dct={}
    for (pt,vv,bt,aA_,aE_,aS_) in combos:
        if pt not in dct:
            dct[pt]={
                "value":vv,
                "base_type":bt,
                "aff_armour":aA_,
                "aff_evasion":aE_,
                "aff_es":aS_
            }
        else:
            dct[pt]["value"]+=vv
            if dct[pt]["base_type"]!="#%" and bt=="#%":
                dct[pt]["base_type"]="#%"
            dct[pt]["aff_armour"]|=aA_
            dct[pt]["aff_evasion"]|=aE_
            dct[pt]["aff_es"]|=aS_

    # clear old unique_mod
    for k_ in list(row.keys()):
        if k_.startswith("unique_mod") and any(k_.endswith(x) for x in [
           "_pattern","_value","_base_type","_affects_armour","_affects_evasion","_affects_energy_shield"]):
            row[k_]=None

    idx=1
    for p_,inf_ in dct.items():
        row[f"unique_mod{idx}_pattern"]=p_
        row[f"unique_mod{idx}_value"]=inf_["value"]
        row[f"unique_mod{idx}_base_type"]=inf_["base_type"]
        row[f"unique_mod{idx}_affects_armour"]=inf_["aff_armour"]
        row[f"unique_mod{idx}_affects_evasion"]=inf_["aff_evasion"]
        row[f"unique_mod{idx}_affects_energy_shield"]=inf_["aff_es"]
        idx+=1

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
# set_defense_and_resistance_flags
###############################################################################
def set_defense_and_resistance_flags(row):
    """
    Sets classification flags based on the raw displayed defences:
      - If only 'Armour' >0 => ar_only=1, etc. If all three => all_three=1, etc.
      - Resist counting: how many distinct "resistance" mods are in unique_modN_pattern
        with a positive value => row["resist_count"], plus has_1_resist, has_2_resist, etc.
      - If the item has at least one # (flat) and one #% (percent) across the unique_mod
        fields => row["has_flat_and_pct"]=1, else 0.
    """
    def sf(x):
        try: return float(x or 0)
        except: return 0
    a_=sf(row.get("Armour",0))
    e_=sf(row.get("Evasion Rating",0))
    s_=sf(row.get("Energy Shield",0))
    row["ar_only"]=0
    row["ev_only"]=0
    row["es_only"]=0
    row["ar_ev_only"]=0
    row["ar_es_only"]=0
    row["ev_es_only"]=0
    row["all_three"]=0
    ca=1 if a_>0 else 0
    ce=1 if e_>0 else 0
    cs=1 if s_>0 else 0
    su=ca+ce+cs
    if su==3:
        row["all_three"]=1
    elif su==2:
        if ca and ce:row["ar_ev_only"]=1
        elif ca and cs:row["ar_es_only"]=1
        elif ce and cs:row["ev_es_only"]=1
    elif su==1:
        if ca:row["ar_only"]=1
        if ce:row["ev_only"]=1
        if cs:row["es_only"]=1
    rc=0
    for i in range(1,21):
        pt_= (row.get(f"unique_mod{i}_pattern","")or"").lower()
        va_= sf(row.get(f"unique_mod{i}_value",0))
        if va_>0 and pt_:
            if ("to cold resistance" in pt_ or "to fire resistance" in pt_ or
                "to lightning resistance" in pt_ or "to chaos resistance" in pt_):
                rc+=1
    row["resist_count"]=rc
    row["has_1_resist"]=1 if rc==1 else 0
    row["has_2_resist"]=1 if rc==2 else 0
    row["has_3_resist"]=1 if rc>=3 else 0
    hf=False
    hp=False
    for i in range(1,21):
        bt_=row.get(f"unique_mod{i}_base_type","")
        va_=sf(row.get(f"unique_mod{i}_value",0))
        if va_>0 and bt_:
            if bt_=="#":hf=True
            elif bt_=="#%":hp=True
    row["has_flat_and_pct"]=1 if (hf and hp) else 0
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