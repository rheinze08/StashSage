# File: poe2trade/utils/matrix_utils.py

"""
Build overlay & model feature matrices from parsed item parquet dumps.

Conventions ensured here:
- All column names are lowercase.
- Armour/evasion/energy-shield helpers: ar_base/ev_base/es_base and ar_norm/ev_norm/es_norm.
- Overlay and model outputs written as both .xlsx and .parquet.
"""

import os
import re
import warnings
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from poe2trade import chaos_exalt, divine_exalt, poe2trade_root

# suppress “no numeric roll” warnings emitted by parse_rolled_mod
warnings.filterwarnings("ignore", message="no numeric roll")

from poe2trade.utils.parse_utils import parse_rolled_mod


def _is_jewelry_branch(path_str: str) -> bool:
    """True for Belt/Ring/Amulet, False for Body-Armour/Gloves/Helmet (by path heuristics)."""
    p = path_str.lower()
    return any(tok in p for tok in ("belt", "ring", "amulet")) and not any(
        tok in p for tok in ("body_armour", "gloves", "helmet")
    )


def build_feature_matrix(src_parquet: str) -> Tuple[str, str, str, str]:
    """
    Build overlay & model feature matrices from a parsed-items parquet.
    Returns (model_parquet, model_xlsx, overlay_parquet, overlay_xlsx).
    """
    src_path = Path(src_parquet)
    jewelry_branch = _is_jewelry_branch(str(src_path))
    belt_branch = jewelry_branch and "belt" in src_path.stem.lower()

    # 0 ─── read parsed items, enforce lowercase columns for robustness
    df = pd.read_parquet(src_path)
    df.columns = [str(c).lower() for c in df.columns]

    # 0.5 ── compute raw charm slots (two columns) for belts only (harmless if missing)
    if belt_branch:
        has_slot = df.get("has # charm slot", pd.Series(0, index=df.index)).fillna(0).astype(int)
        has_slots = df.get("has # charm slots", pd.Series(0, index=df.index)).fillna(0).astype(int)
        df["has # charm slots"] = pd.concat([has_slot, has_slots], axis=1).max(axis=1).clip(lower=1)

    # 1 ─── convenience column
    df["item"] = df.get("name", "").astype(str) + " " + df.get("base", "").astype(str)

    # 2 ─── quality info (plain vs typed)
    qual_series = pd.to_numeric(df.get("quality", pd.Series(np.nan, index=df.index)), errors="coerce")
    qtype_series = df.get("quality_type", pd.Series(np.nan, index=df.index))
    df["_plain_quality"] = qual_series.where(qtype_series.isna(), np.nan)
    df["_qtype"] = qtype_series
    df["_qtype_pct"] = qual_series.where(qtype_series.notna(), np.nan)

    # 3 ─── drop raw property_* columns (legacy)
    prop_cols = [c for c in df.columns if re.match(r"property_\d+_", c)]
    df.drop(columns=prop_cols, inplace=True, errors="ignore")

    # 4 ─── gather all rolled-mod patterns to define the feature set
    pattern_cols = [c for c in df.columns if re.match(r".+_mod_\d+_pattern$", c)]
    all_patterns: list[str] = []
    for c in pattern_cols:
        all_patterns.extend(df[c].dropna().astype(str).tolist())
    feature_set = sorted({parse_rolled_mod(p)[0] for p in all_patterns})

    # 5 ─── initialize base_df (data without the mod slot columns) + zeroed feature columns
    mod_cols = [c for c in df.columns if "_mod_" in c]
    base_df = df.drop(columns=mod_cols, errors="ignore").copy()
    for feat in feature_set:
        base_df[feat] = 0.0

    # 6 ─── fill in feature columns by summing values for matched patterns
    for i in range(1, 51):
        for pref in ("explicit", "implicit", "enchant", "rune"):
            pcol = f"{pref}_mod_{i}_pattern"
            vcol = f"{pref}_mod_{i}_value"
            if pcol in df.columns and vcol in df.columns:
                pats = df[pcol].dropna().astype(str).map(lambda s: parse_rolled_mod(s)[0])
                vals = pd.to_numeric(df[vcol], errors="coerce").fillna(0.0)
                for idx, pat in pats.items():
                    if pat in base_df.columns:
                        base_df.at[idx, pat] += vals.loc[idx]

    # 7 ─── collapse any charm-slot pattern columns into final 'has # charm slots' for belts only
    if belt_branch:
        charm_feats = [c for c in base_df.columns if re.fullmatch(r"has # charm slots?", c)]
        if charm_feats:
            base_df["has # charm slots"] = base_df[charm_feats].max(axis=1).clip(lower=1)
        # drop leftover charm variants
        for c in ["has # charm slot", "# charm slots", "# charm slot"]:
            base_df.drop(columns=[c], inplace=True, errors="ignore")

    # 8 ─── armour branch: compute normalized defences
    if not jewelry_branch:
        pct_cols = [
            "#% increased armour",
            "#% increased armour and energy shield",
            "#% increased armour and evasion",
            "#% increased energy shield",
            "#% increased evasion and energy shield",
            "#% increased evasion rating",
            "#% increased armour, evasion and energy shield",
        ]
        for col in pct_cols:
            if col not in base_df:
                base_df[col] = 0.0

        base_df["explicit_mod_%"] = base_df[pct_cols].max(axis=1)

        target = "#% increased armour, evasion and energy shield"
        rune_pct = []
        for _, r in df.iterrows():
            val = 0.0
            for j in range(1, 7):
                if r.get(f"rune_mod_{j}_pattern") == target:
                    val = float(r.get(f"rune_mod_{j}_value") or 0)
                    break
            rune_pct.append(val)
        base_df["rune_mod_%"] = rune_pct

        # ensure flat defence columns exist and are numeric (from parse_utils: 'ar','ev','es')
        for col in ("ar", "ev", "es"):
            if col not in base_df.columns:
                base_df[col] = 0.0
            else:
                base_df[col] = (
                    pd.to_numeric(
                        base_df[col].astype(str).str.extract(r"([+-]?\d+(?:\.\d+)?)")[0],
                        errors="coerce"
                    ).fillna(0.0)
                )

        Q  = base_df["_plain_quality"].fillna(0.0)
        EM = base_df["explicit_mod_%"]
        RM = base_df["rune_mod_%"]
        A  = base_df.get("ar", 0.0)
        E  = base_df.get("ev", 0.0)
        S  = base_df.get("es", 0.0)
        fA = base_df.get("# to armour", 0.0)
        fE = base_df.get("# to evasion rating", 0.0)
        fS = base_df.get("# to maximum energy shield", 0.0)

        denom = (1 + Q / 100.0) * (1 + (EM + RM) / 100.0)
        denom = denom.replace(0, 1)

        # base values (pre-quality/pre-%)
        base_df["ar_base"] = A.div(denom).sub(fA)
        base_df["ev_base"] = E.div(denom).sub(fE)
        base_df["es_base"] = S.div(denom).sub(fS)

        # normalized values (apply explicits only to compare across runes/quality)
        base_df["ar_norm"] = (base_df["ar_base"] + fA) * (1 + EM / 100.0)
        base_df["ev_norm"] = (base_df["ev_base"] + fE) * (1 + EM / 100.0)
        base_df["es_norm"] = (base_df["es_base"] + fS) * (1 + EM / 100.0)

    # 9 ─── jewelry branch: deflate typed-quality patterns using lookup
    else:
        q_lookup = os.path.join(poe2trade_root, "db", "files", "ring_amulet_quality_lookup.xlsx")
        lut = pd.read_excel(q_lookup)
        # normalize LUT headers to lowercase so we can depend on "quality"
        lut.columns = [str(c).strip().lower() for c in lut.columns]
        key_col = "quality" if "quality" in lut.columns else lut.columns[0]
        patt_cols = [c for c in lut.columns if c != key_col]
        norm_map = {c: parse_rolled_mod(str(c))[0] for c in patt_cols}
        lut.rename(columns=norm_map, inplace=True)
        patterns = [pat for pat in norm_map.values() if pat in base_df.columns]
        type_to_pats = {
            str(r[key_col]).strip().title(): [p for p in patterns if bool(r.get(p, 0))]
            for _, r in lut.iterrows()
        }
        for idx, (qtype, qpct) in base_df[["_qtype", "_qtype_pct"]].iterrows():
            if pd.notna(qtype) and pd.notna(qpct):
                factor = 1 + qpct / 100.0
                if factor and factor != 0:
                    for pat in type_to_pats.get(str(qtype).title(), []):
                        base_df.at[idx, pat] /= factor

    # 10 ─── drop helpers & raw cols, round
    base_df.drop(
        columns=[
            "_plain_quality", "_qtype", "_qtype_pct",
            "name", "base", "category",
            "quality", "quality_type"
        ],
        inplace=True, errors="ignore"
    )
    base_df = base_df.round(4)

    # 10.5 ── standardize ALL column names to lowercase (idempotent)
    base_df.rename(columns=lambda c: str(c).lower(), inplace=True)

    # 11 ─── write overlay (lowercase, and drop *_base + % helpers; keep ar/ev/es)
    overlay_drop = ["explicit_mod_%", "rune_mod_%", "ar_base", "ev_base", "es_base"]
    overlay_df = base_df.drop(columns=overlay_drop, inplace=False, errors="ignore")
    # Jewellery overlay does not use raw ar/ev/es as features; drop them
    if jewelry_branch:
        overlay_df.drop(columns=["ar", "ev", "es"], inplace=True, errors="ignore")

    overlay_xlsx = src_path.with_name(f"{src_path.stem}_feature_matrix_overlay.xlsx")
    overlay_parquet = src_path.with_name(f"{src_path.stem}_feature_matrix_overlay.parquet")
    overlay_df.to_excel(overlay_xlsx, index=False)
    overlay_df.to_parquet(overlay_parquet, index=False)

    # 12 ─── convert price → exalts for the MODEL dataframe
    def _to_exalt(row):
        amt, cur = row.get("price", 0), str(row.get("currency", "")).lower()
        try:
            val = float(amt)
        except Exception:
            return 0.0
        if cur == "exalted":
            return val
        if cur == "chaos":
            return val * chaos_exalt
        if cur == "divine":
            return val * divine_exalt
        return 0.0

    base_df["price"] = df.apply(_to_exalt, axis=1)
    base_df.drop(columns=["currency"], inplace=True, errors="ignore")

    # 13 ─── prune for model file:
    #       • original pruning rules
    #       • plus drop: ar, ev, es, explicit_mod_%, rune_mod_%, ar_base, ev_base, es_base
    drop_model_common = ["item"]
    if jewelry_branch:
        drop_model = drop_model_common
    else:
        drop_model = drop_model_common + [
            "# to armour", "# to evasion rating", "# to maximum energy shield",
            "#% increased armour", "#% increased armour and energy shield",
            "#% increased armour and evasion", "#% increased energy shield",
            "#% increased evasion and energy shield", "#% increased evasion rating",
            "#% increased armour, evasion and energy shield",
        ]
    drop_model += ["ar", "ev", "es", "explicit_mod_%", "rune_mod_%", "ar_base", "ev_base", "es_base"]

    model_df = base_df.drop(columns=[c for c in drop_model if c in base_df.columns], errors="ignore")

    # 14 ─── write model (all-lowercase)
    model_xlsx = src_path.with_name(f"{src_path.stem}_feature_matrix_model.xlsx")
    model_parquet = src_path.with_name(f"{src_path.stem}_feature_matrix_model.parquet")
    model_df.to_excel(model_xlsx, index=False)
    model_df.to_parquet(model_parquet, index=False)

    return (
        str(model_parquet),
        str(model_xlsx),
        str(overlay_parquet),
        str(overlay_xlsx),
    )
