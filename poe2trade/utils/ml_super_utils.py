# File: poe2trade/utils/ml_super_utils.py
# · v25 — add per-file in-process caching with mtime invalidation (2025-09-11)
# · v24 — robust to lowercase/underscore standardization (2025-07-06)

from __future__ import annotations

import json
import pickle
import importlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from poe2trade import (
    poe2trade_root,
    shap_flag,
    train_super_xgb,
    train_super_rf,
    train_super_gbr,
)

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _norm_token(s: str | None) -> str | None:
    """lowercase + replace whitespace with underscores; None → None."""
    if s is None:
        return None
    return re.sub(r"\s+", "_", str(s).strip().lower())


# ── OPTIONAL SHAP SUPPORT ─────────────────────────────────────
# If shap_flag is set, we try to import shap for feature‐importance explanations.
shap = None
_SHAP_ENABLED = False
if shap_flag:
    try:
        shap = importlib.import_module("shap")
        _SHAP_ENABLED = True
        print("[INFO] SHAP support enabled for inference")
    except ModuleNotFoundError:
        print("[INFO] shap_flag True but shap package not installed — continuing without SHAP")

# ── WHICH MODELS TO LOAD ──────────────────────────────────────
# Only load the model types whose training flags are enabled.
_active_models = [
    m for m, flag in {
        "xgb": train_super_xgb,
        "rf":  train_super_rf,
        "gbr": train_super_gbr,
    }.items() if flag
]
print(f"[DEBUG] Active model types for inference: {_active_models}")

# ── BUCKET STATS LOADER ───────────────────────────────────────
# Loads precomputed bucket intervals & stats for each category_segment.
_STATS_PATH = Path(poe2trade_root) / "db" / "super_models" / "category_segment_stats.json"
_bucket_cache: Optional[Dict[str, Any]] = None

def _load_bucket_stats() -> Dict[str, Any]:
    """Memoized JSON loader for bucket stats."""
    global _bucket_cache
    if _bucket_cache is None:
        print(f"[DEBUG] Loading bucket stats from {_STATS_PATH}")
        if _STATS_PATH and _STATS_PATH.is_file():
            try:
                _bucket_cache = json.loads(_STATS_PATH.read_text())
                print(f"[DEBUG] Loaded bucket stats for {len(_bucket_cache)} category-segment keys")
            except Exception as e:
                print(f"[ERROR] Failed to parse {_STATS_PATH}: {e!r}")
                _bucket_cache = {}
        else:
            print(f"[DEBUG] Stats file not found at {_STATS_PATH}, initializing empty cache")
            _bucket_cache = {}
    else:
        print("[DEBUG] Using cached bucket stats")
    return _bucket_cache

def _bucketise(cat_seg_key: str, median_val: float) -> Optional[Dict[str, Any]]:
    """
    Given a category_segment key and a predicted median value, select which
    bucket (Low/Medium/High) it falls into based on precomputed intervals.
    Returns a dict with bucket, bucket_low, bucket_high, and z-score.
    """
    print(f"[DEBUG] Bucketising for key '{cat_seg_key}' with median {median_val:.5f}")
    stats = _load_bucket_stats().get(cat_seg_key)
    if not stats:
        print(f"[DEBUG] No stats entry for '{cat_seg_key}', skipping bucketise")
        return None

    intervals: Dict[str, List[Optional[float]]] = stats.get("bucket_intervals", {})

    bucket = None
    bucket_low = None
    bucket_high = None

    # 1) Try to find an interval containing median_val
    for name, pair in intervals.items():
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        lo, hi = pair
        if lo is not None and hi is not None and lo <= median_val <= hi:
            bucket = name.capitalize()
            bucket_low, bucket_high = lo, hi
            break

    # 2) If none matched, classify as below Low or above High, else Medium
    if bucket is None:
        low_lo, low_hi   = intervals.get("low",    [None, None])
        med_lo, med_hi   = intervals.get("medium", [None, None])
        high_lo, high_hi = intervals.get("high",   [None, None])
        if low_hi is not None and median_val <= low_hi:
            bucket, (bucket_low, bucket_high) = "Low", (low_lo, low_hi)
        elif high_lo is not None and median_val >= high_lo:
            bucket, (bucket_low, bucket_high) = "High", (high_lo, high_hi)
        else:
            bucket, (bucket_low, bucket_high) = "Medium", (med_lo, med_hi)

    print(f"[DEBUG] Assigned bucket '{bucket}' with interval [{bucket_low}, {bucket_high}]")

    # 3) Compute z-score relative to stats.mean/std to gauge extremeness
    mean = stats.get("mean", 0.0)
    std  = stats.get("std", 0.0) or 1e-9
    z    = (median_val - mean) / std

    return {
        "z":           z,
        "bucket":      bucket,
        "bucket_low":  bucket_low,
        "bucket_high": bucket_high,
    }

# ── OPTIONAL SHAP PRINTING ────────────────────────────────────
def _print_shap(
    shap_values: "shap._explanation.Explanation",
    feature_names: List[str],
    inverse_map: Dict[str, str],
    model_tag: str,
    top: int | None = 15,
):
    """
    Dump the top‐N feature contributions from a SHAP explanation object.
    """
    print(f"\n[SHAP] contributions for {model_tag}\n")
    base = shap_values.base_values
    if isinstance(base, (list, np.ndarray)):
        base = base[0]
    print(f"  base_value: {base:.5f}")

    vals = shap_values.values
    if hasattr(vals, "ndim") and vals.ndim > 1:
        vals = vals[0]
    contribs = sorted(zip(feature_names, vals), key=lambda t: t[1], reverse=True)

    shown = 0
    for feat, val in contribs:
        if abs(val) < 1e-6:
            continue
        label = f"{feat} ({inverse_map.get(feat,'')})".rstrip()
        print(f"  {label:<50s} {val:+.5f}")
        shown += 1
        if top is not None and shown >= top:
            break
    print()

# ──────────────────────────────────────────────────────────────
# NEW: in-process cache for supervised model artifacts
# ──────────────────────────────────────────────────────────────
_model_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
_model_mtime: Dict[Tuple[str, str], float] = {}

def _load_model(model_dir: Path, base_name: str, mtype: str) -> Optional[Dict[str, Any]]:
    """
    Load and cache '{base_name}_{mtype}_model.pkl' with mtime-based invalidation.
    If the file hasn't changed since last load, reuse the cached artifact.
    """
    p = model_dir / f"{base_name}_{mtype}_model.pkl"
    if not p.is_file():
        print(f"[DEBUG] {mtype} model not found at {p}")
        return None

    key = (base_name, mtype)
    mt  = p.stat().st_mtime
    art = _model_cache.get(key)
    if art is not None and _model_mtime.get(key) == mt:
        # cached and fresh
        return art

    # (re)load
    art = pickle.load(p.open("rb"))
    _model_cache[key] = art
    _model_mtime[key] = mt
    print(f"[DEBUG] Loaded {mtype} model '{p.name}' into cache")
    return art

# ── MAIN INFERENCE ENTRYPOINT ─────────────────────────────────
def call_ml(
    category: str,
    segment: str,
    X: pd.DataFrame
) -> Dict[str, Any] | None:
    """
    Load each active model for the given category & segment, run predictions,
    aggregate results, bucketise the median, and return a summary dict.
    """
    # normalize inputs and lower-case input columns (robust to standardization)
    print(f"[DEBUG] call_ml_super: category={category!r}, segment={segment!r}")
    category_n = _norm_token(category)
    # normalize common aliases
    if category_n in ("scepter",):
        category_n = "sceptre"
    segment_n  = _norm_token(segment) if segment is not None else None
    print(f"[DEBUG] call_ml_super: normalized category={category_n!r}, segment={segment_n!r}")

    X = X.copy()
    X.columns = [str(c).lower() for c in X.columns]

    model_dir = Path(poe2trade_root) / "db" / "super_models"
    print(f"[DEBUG] call_ml_super: model_dir='{model_dir}' exists={model_dir.is_dir()}")
    preds: Dict[str, float] = {}

    # If segment is None, omit it from filenames
    base_name = category_n if segment_n is None else f"{category_n}_{segment_n}"
    print(f"[DEBUG] call_ml_super: base_name='{base_name}'")

    # 1) Loop through xgb/rf/gbr models as configured (using cached loader)
    for mtype in _active_models:
        p = model_dir / f"{base_name}_{mtype}_model.pkl"
        print(f"[DEBUG] Looking for {mtype} model for base '{base_name}' at '{p.name}' (exists={p.is_file()})")
        art = _load_model(model_dir, base_name, mtype)
        if art is None:
            continue

        # 2) Load the pipeline and feature list
        pipe: Pipeline = art["model_pipeline"]
        cols: List[str] = art.get("feature_cols", X.columns.tolist())
        print(f"[DEBUG] Loaded {mtype} pipeline type={type(pipe).__name__}; feature_cols={len(cols)}")
        # Show brief feature alignment info
        x_cols = [str(c).lower() for c in X.columns]
        missing = [c for c in cols if c not in x_cols]
        extra   = [c for c in x_cols if c not in cols]
        if missing:
            head = ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else "")
            print(f"[DEBUG] Input is missing {len(missing)} feature(s): {head}")
        if extra:
            head = ", ".join(extra[:8]) + (" ..." if len(extra) > 8 else "")
            print(f"[DEBUG] Input has {len(extra)} extra column(s) not used by model: {head}")

        # 3) Align our input X to the expected features
        x_in = X.reindex(columns=cols, fill_value=0.0)

        # 4) Predict and record
        print(f"[DEBUG] Predicting with {mtype}: {len(cols)} features")
        val = float(pipe.predict(x_in)[0])
        preds[mtype] = val
        print(f"[DEBUG] {mtype} => {val:.5f}")

        # 5) Optionally show SHAP if enabled
        if _SHAP_ENABLED:
            shap_file = (model_dir / f"{base_name}_{mtype}_model.pkl").with_name(
                f"{base_name}_{mtype}_model_shap.pkl"
            )
            if shap_file.is_file():
                try:
                    shap_art = pickle.load(shap_file.open("rb"))
                    expl = shap_art["shap_explainer"]
                    cols_shap = shap_art.get("feature_cols", cols)
                    shap_df = X.reindex(columns=cols_shap, fill_value=0.0)
                    inv_map = {c: c for c in shap_df.columns}
                    _print_shap(expl(shap_df), shap_df.columns.tolist(), inv_map, shap_file.name)
                except Exception as e:
                    print(f"[DEBUG] SHAP explanation failed: {e!r}")

    # If we didn’t load any models, bail out
    if not preds:
        print("[DEBUG] No supervised models loaded; returning None")
        return None

    # 6) Aggregate predictions
    vals   = list(preds.values())
    mn     = min(vals)
    mx     = max(vals)
    mean   = sum(vals) / len(vals)
    median = float(np.median(vals))
    print(f"[DEBUG] Aggregated: min={mn:.5f}, max={mx:.5f}, mean={mean:.5f}, median={median:.5f}")

    result: Dict[str, Any] = {
        "predictions": preds,
        "min":         float(mn),
        "max":         float(mx),
        "mean":        float(mean),
        "median":      median,
        "average":     float(mean),
        "segment":     segment_n,
    }

    # 7) Bucketise using the normalized base_name
    binfo = _bucketise(base_name, median)
    if binfo:
        result.update(binfo)

    return result

