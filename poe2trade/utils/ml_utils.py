# ml_utils.py · v12 — optional-SHAP + z-score “Value Indicator” (fully self-contained)
# ─────────────────────────────────────────────────────────────────────────────
#  • Single-model & segmented inference identical to v10.
#  • V11 additions retained:
#        – z-score bucket look-up (Low / Medium / High).
#        – value_indicator string (“High -- 62” etc.).
#  • Now includes the full _build_single_row helper so NameError is gone.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import pickle, re, importlib, json
from pathlib import Path
from typing import Any, Dict, Tuple, Optional, List

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline

from poe2trade import (
    poe2trade_root, chaos_exalt, divine_exalt,
    quality_feature_flag, corrupted_feature_flag, shap_flag,
)
from poe2trade.utils.train_utils import normalise_pattern   # shared helper

# ───────────────────────────── optional SHAP ──────────────────────────────
shap = None
_SHAP_ENABLED = False
if shap_flag:
    try:
        shap = importlib.import_module("shap")
        _SHAP_ENABLED = True
        print("[INFO] SHAP support enabled for inference")
    except ModuleNotFoundError:
        print("[INFO] SHAP flag True but shap package not installed — continuing without SHAP")

# ───────────────────────────── bucket stats loader ───────────────────────
_STATS_PATH = Path(poe2trade_root) / "db" / "models" / "category_segment_stats.json"
_bucket_cache: Optional[dict] = None

def _load_bucket_stats() -> dict:
    global _bucket_cache
    if _bucket_cache is None:
        if _STATS_PATH.is_file():
            try:
                _bucket_cache = json.loads(_STATS_PATH.read_text())
            except Exception:
                _bucket_cache = {}
        else:
            _bucket_cache = {}
    return _bucket_cache

def _bucketise(cat_seg_key: str, median_val: float) -> Optional[dict]:
    stats = _load_bucket_stats().get(cat_seg_key)
    if not stats:
        return None

    mean, std = stats["mean"], stats["std"]
    z = 0.0 if std == 0 else (median_val - mean) / std

    if z <= -0.5:
        label_key = "low"
    elif z <= 0.5:
        label_key = "medium"
    else:
        label_key = "high"

    # ── fetch data (works with old or new files) ───────────────────────
    bucket_median = (
        stats.get("bucket_medians", {})
             .get(label_key)
    )
    lo, hi = (
        stats.get("bucket_intervals", {})
             .get(label_key, [None, None])
    )

    return {
        "z": z,
        "bucket": label_key.capitalize(),    # Low / Medium / High
        "bucket_median": bucket_median,
        "bucket_low":  lo,
        "bucket_high": hi,
        "value_indicator": (
            f"{label_key.capitalize()} -- {bucket_median:.0f}"
            if bucket_median is not None else label_key.capitalize()
        ),
    }


# ───────────────────────────── utilities ────────────────────────────────
def _sf(x: Any) -> float:
    try:
        return float(x or 0)
    except Exception:
        return 0.0

def _actual_price(row: dict) -> float | None:
    if "Price_in_Exalts" in row:
        return _sf(row["Price_in_Exalts"])
    if "Price" in row and "Currency" in row:
        cur = str(row["Currency"]).strip().lower()
        val = _sf(row["Price"])
        if cur == "exalted": return val
        if cur == "divine":  return val * divine_exalt
        if cur == "chaos":   return val * chaos_exalt
    return None

# ─────────────────────────── pattern-dict loader ───────────────────────
def _load_pattern_dict(pickle_path: Path) -> Optional[Dict[str, str]]:
    if not pickle_path.is_file():
        return None
    with pickle_path.open("rb") as fh:
        art = pickle.load(fh)
    return art.get("pattern_dict")

# ──────────────────── SHAP console print helper (unchanged) ─────────────
def _print_shap(
    shap_values: "shap._explanation.Explanation",   # type: ignore[name-defined]
    feature_names: List[str],
    inverse_map: Dict[str, str],
    model_tag: str,
    top: int | None = 15,
):
    print(f"\n[SHAP] contributions for {model_tag}\n")
    base = shap_values.base_values
    if isinstance(base, (list, np.ndarray)):
        base = base[0]
    print(f"  base_value: {base:.5f}")
    row_vals = shap_values.values if shap_values.values.ndim == 1 else shap_values.values[0]
    contribs = sorted(zip(feature_names, row_vals),
                      key=lambda t: t[1], reverse=True)
    if top is not None:
        contribs = contribs[:top]
    for feat, val in contribs:
        if abs(val) < 1e-6:
            continue
        label = f"{feat} ({inverse_map.get(feat, '')})".rstrip()
        print(f"  {label:<50s} {val:+.5f}")
    print()

# ──────────────────── SINGLE-ROW FEATURE MATRIX BUILDER ─────────────────
def _build_single_row(
    row: dict, pattern_dict: Dict[str, str]
) -> Tuple[pd.DataFrame, list[str], Dict[str, str]]:
    """
    Re-creates the numeric feature layout used in training for a single item.
    Returns the feature-frame, the ordered list of pattern feature columns,
    and an inverse map {f123: "original pattern"} for SHAP pretty-printing.
    """
    base_cols = [
        "Deflated_Armour",
        "Deflated_Evasion",
        "Deflated_EnergyShield",
        "extra_socket_mod",
    ]
    if quality_feature_flag:
        base_cols.append("Quality")
    if corrupted_feature_flag:
        base_cols.append("Corrupted_Flag")

    cat_norm = str(row.get("Item Category", "")).lower().replace(" ", "_")
    if cat_norm in {"body_armour", "gloves", "boots", "helmet"}:
        base_cols.extend(["has_flat_and_pct", "resist_count"])

    df = pd.DataFrame(columns=base_cols + list(pattern_dict.values()),
                      index=[0], data=0.0)

    # scalar bases
    df.at[0, "Deflated_Armour"]       = _sf(row.get("Deflated_Armour"))
    df.at[0, "Deflated_Evasion"]      = _sf(row.get("Deflated_Evasion"))
    df.at[0, "Deflated_EnergyShield"] = _sf(row.get("Deflated_EnergyShield"))
    df.at[0, "extra_socket_mod"]      = _sf(row.get("extra_socket_mod"))

    if quality_feature_flag:
        df.at[0, "Quality"] = _sf(row.get("Quality"))
    if corrupted_feature_flag:
        df.at[0, "Corrupted_Flag"] = (
            1.0 if str(row.get("Corrupted", "no")).lower() == "yes" else 0.0
        )
    if cat_norm in {"body_armour", "gloves", "boots", "helmet"}:
        df.at[0, "resist_count"]     = _sf(row.get("resist_count"))
        df.at[0, "has_flat_and_pct"] = _sf(row.get("has_flat_and_pct"))

    # mods → numeric cols
    for i in range(1, 50):
        raw_pat = row.get(f"unique_mod{i}_pattern")
        if raw_pat is None:
            continue
        pat  = normalise_pattern(raw_pat)
        fcol = pattern_dict.get(pat)
        if not fcol:
            continue
        val = _sf(row.get(f"unique_mod{i}_value"))
        df.at[0, fcol] += val

    inverse_map = {v: k for k, v in pattern_dict.items()}
    return df, list(pattern_dict.values()), inverse_map

# ───────────────────────────── segmented path ───────────────────────────
def call_ml_segmented(row: dict) -> dict | None:
    cat = row.get("Item Category", "default_model").lower().replace(" ", "_")
    cat = {"boot": "boots", "glove": "gloves"}.get(cat, cat)
    mdir = Path(poe2trade_root) / "db" / "models"

    candidate_pkl = next(iter(mdir.glob(f"{cat}_*_model.pkl")), None)
    if candidate_pkl is None:
        return None
    pattern_dict = _load_pattern_dict(candidate_pkl)
    if not pattern_dict:
        return None

    df, _, inverse_map = _build_single_row(row, pattern_dict)

    ar, ev, es = (df.at[0, "Deflated_Armour"],
                  df.at[0, "Deflated_Evasion"],
                  df.at[0, "Deflated_EnergyShield"])
    seg = (
        "ar_only"    if ar > 0 and ev == 0 and es == 0 else
        "ev_only"    if ev > 0 and ar == 0 and es == 0 else
        "es_only"    if es > 0 and ar == 0 and ev == 0 else
        "ar_ev_only" if ar > 0 and ev > 0 and es == 0 else
        "ar_es_only" if ar > 0 and es > 0 and ev == 0 else
        "ev_es_only" if ev > 0 and es > 0 and ar == 0 else
        "all_three"  if ar > 0 and ev > 0 and es > 0 else None
    )
    if seg is None:
        return None

    km_pkl = mdir / f"{cat}_{seg}_kmeans.pkl"
    if not km_pkl.is_file():
        return None
    with km_pkl.open("rb") as fh:
        km_art = pickle.load(fh)
    km: KMeans | None = km_art.get("kmeans_model")
    feat_for_km = km_art.get("features_for_kmeans", [])
    cluster_label = 0 if km is None else int(
        km.predict(df.reindex(columns=feat_for_km, fill_value=0.0))[0]
    )

    preds: Dict[str, float] = {}
    for mtype in ("xgb", "rf", "gbr"):
        pkl = mdir / f"{cat}_{seg}_cluster{cluster_label}_{mtype}_model.pkl"
        if not pkl.is_file():
            continue

        with pkl.open("rb") as fh:
            art = pickle.load(fh)
        pipe: Pipeline = art["model_pipeline"]
        feats          = art["feature_cols"]
        df_pred        = df.reindex(columns=feats, fill_value=0.0)
        preds[mtype]   = float(pipe.predict(df_pred)[0])

        if _SHAP_ENABLED:
            shp = pkl.with_name(pkl.name.replace("_model.pkl", "_shap.pkl"))
            if shp.is_file():
                with shp.open("rb") as sfh:
                    shap_art = pickle.load(sfh)
                explainer = shap_art["shap_explainer"]
                df_shap  = df.reindex(columns=shap_art.get("feature_cols", feats),
                                      fill_value=0.0)
                _print_shap(
                    explainer(df_shap),
                    df_shap.columns.tolist(),
                    inverse_map,
                    shp.name,
                )

    if not preds:
        return None

    median = float(np.median(list(preds.values())))
    binfo  = _bucketise(f"{cat}_{seg}", median)

    return {
        "predictions": preds,
        "min":     min(preds.values()),
        "max":     max(preds.values()),
        "mean":    sum(preds.values()) / len(preds),
        "median":  median,
        "average": sum(preds.values()) / len(preds),
        "actual":  _actual_price(row),
        "segment": seg,
        "cluster": cluster_label,
        **(binfo or {}),
    }

# ───────────────────────────── single-model path ─────────────────────────
def call_ml(row: dict) -> dict | None:
    cat = row.get("Item Category", "default_model").lower().replace(" ", "_")
    cat = {"boot": "boots", "glove": "gloves"}.get(cat, cat)

    mdir  = Path(poe2trade_root) / "db" / "models"
    files = list(mdir.glob(f"{cat}_*_model.pkl"))
    if not files:
        return None

    pattern_dict = _load_pattern_dict(files[0])
    if not pattern_dict:
        return None

    df, _, inverse_map = _build_single_row(row, pattern_dict)
    preds: Dict[str, float] = {}

    for f in files:
        mtype = f.stem.split("_")[-2]  # xgb / rf / gbr
        with f.open("rb") as fh:
            art = pickle.load(fh)
        pipe: Pipeline = art["model_pipeline"]
        feats          = art["feature_cols"]
        df_pred        = df.reindex(columns=feats, fill_value=0.0)
        preds[mtype]   = float(pipe.predict(df_pred)[0])

        if _SHAP_ENABLED:
            shp = f.with_name(f.name.replace("_model.pkl", "_shap.pkl"))
            if shp.is_file():
                with shp.open("rb") as sfh:
                    shap_art = pickle.load(sfh)
                explainer = shap_art["shap_explainer"]
                df_shap  = df.reindex(columns=shap_art.get("feature_cols", feats),
                                      fill_value=0.0)
                _print_shap(
                    explainer(df_shap),
                    df_shap.columns.tolist(),
                    inverse_map,
                    shp.name,
                )

    if not preds:
        return None

    median = float(np.median(list(preds.values())))
    binfo  = _bucketise(cat, median)

    return {
        "predictions": preds,
        "min":     min(preds.values()),
        "max":     max(preds.values()),
        "mean":    sum(preds.values()) / len(preds),
        "median":  median,
        "average": sum(preds.values()) / len(preds),
        "actual":  _actual_price(row),
        **(binfo or {}),
    }
