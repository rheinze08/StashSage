# train_utils.py · v12
# ─────────────────────────────────────────────────────────────────────────────
#  • Builds canonical pattern → feature map, adds defence-flag features.
#  • Trains XGB / RF / GBR (and optional SHAP explainers).
#  • If `poe2trade.score_training_flag` is True:
#       – Appends per-item predictions (XGB/RF/GBR) and their median to
#         *_scoring.xlsx files.
#       – Uses those medians to compute z-scores and three buckets
#         (Low ≤ –0.5, –0.5 < z ≤ 0.5 → Medium, z > 0.5 → High).
#       – For **each bucket** stores an **80 % confidence interval** of the
#         *actual* prices (10th / 90th percentiles) in
#             db/models/category_segment_stats.json
#         → "bucket_intervals": {"low":[lo,hi], "medium":[lo,hi], "high":[lo,hi]}
#       – Adds Bucket_Label / Bucket_Price_Low / Bucket_Price_High columns to
#         every *_scoring.xlsx.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json, pickle, re, importlib
from pathlib import Path
from threading import Lock, RLock
from typing import Dict, Tuple, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.cluster import KMeans
from sklearn.ensemble import (
    RandomForestRegressor, ExtraTreesRegressor,
    GradientBoostingRegressor, BaggingRegressor,
)
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from poe2trade import (
    poe2trade_root, divine_exalt, chaos_exalt,
    quality_feature_flag, corrupted_feature_flag,
    shap_flag, score_training_flag, hyperparameter_flag,
)

# ─────────────────────────────────────────────────────────────────────────────
# OPTIONAL SHAP
# ─────────────────────────────────────────────────────────────────────────────
shap = None
_SHAP_ENABLED = False
if shap_flag:
    try:
        shap = importlib.import_module("shap")
        _SHAP_ENABLED = True
        print("[INFO] SHAP support enabled")
    except ModuleNotFoundError:
        print("[INFO] SHAP flag True but shap not installed — continuing without SHAP")

# ─────────────────────────────────────────────────────────────────────────────
# GLOBALS / LOCKS
# ─────────────────────────────────────────────────────────────────────────────
kmeans_n_clusters = 1
_pattern_lock      = Lock()
_global_train_lock = RLock()
_shap_bg_n         = 100

_stats_path = Path(poe2trade_root) / "db" / "models" / "category_segment_stats.json"
_stats_lock = RLock()

# ----------------------------------------------------------------------------
# CONSTANT TABLES
# ----------------------------------------------------------------------------
_segment_base_candidates: dict[str, dict[str, list[str]]] = {
    "ar_only":    {"flat": ["# to armour"],           "inc": ["#% increased armour"]},
    "ev_only":    {"flat": ["# to evasion rating"],   "inc": ["#% increased evasion rating"]},
    "es_only":    {"flat": ["# to maximum energy shield"], "inc": ["#% increased energy shield"]},
    "ar_ev_only": {
        "flat": ["# to armour", "# to evasion rating"],
        "inc": ["#% increased armour",
                "#% increased evasion rating",
                "#% increased armour and evasion"],
    },
    "ar_es_only": {
        "flat": ["# to armour", "# to maximum energy shield"],
        "inc": ["#% increased armour",
                "#% increased energy shield",
                "#% increased armour and energy shield"],
    },
    "ev_es_only": {
        "flat": ["# to evasion rating", "# to maximum energy shield"],
        "inc": ["#% increased evasion rating",
                "#% increased energy shield",
                "#% increased evasion and energy shield"],
    },
    "all_three": {
        "flat": ["# to armour", "# to evasion rating", "# to maximum energy shield"],
        "inc":  ["#% increased armour",
                 "#% increased evasion rating",
                 "#% increased energy shield",
                 "#% increased armour and evasion",
                 "#% increased armour and energy shield",
                 "#% increased evasion and energy shield"],
    },
}

_resistance_candidates = [
    "#% to fire resistance",
    "#% to cold resistance",
    "#% to lightning resistance",
    "#% to chaos resistance",
]

_g_base_features = [
    "Deflated_Armour",
    "Deflated_Evasion",
    "Deflated_EnergyShield",
    "extra_socket_mod",
]
if quality_feature_flag:
    _g_base_features.append("Quality")
if corrupted_feature_flag:
    _g_base_features.append("Corrupted_Flag")

_defence_flag_features = ["has_flat_and_pct", "resist_count"]

_kmeans_clustering_features = {
    "body_armour": ["flat_base", "inc_base",
                    "fire_res", "cold_res", "light_res", "chaos_res",
                    "spirit"],
    "boots":       ["flat_base", "inc_base",
                    "fire_res", "cold_res", "light_res", "chaos_res",
                    "move_speed"],
    "gloves":      ["flat_base", "inc_base",
                    "fire_res", "cold_res", "light_res", "chaos_res"],
    "helmet":      ["flat_base", "inc_base",
                    "fire_res", "cold_res", "light_res", "chaos_res"],
}

_g_pattern_dict: Dict[str, str] = {}

# ─────────────────────────────────────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
_num_re = re.compile(r'[+-]?\d+(?:\.\d+)?')
def normalise_pattern(raw: str) -> str:
    """Canonical pattern: numbers → '#', lower-case, single spaces."""
    s = _num_re.sub('#', str(raw).lower()).strip()
    return re.sub(r'\s+', ' ', s)

def _announce(fn):
    def wrapper(*a, **kw):
        print(f"\n>>> {fn.__name__}\n{(fn.__doc__ or '').strip()}\n")
        return fn(*a, **kw)
    return wrapper

def _chatter(msg: str): print(f"[DEBUG] {msg}")

def _invert(col: str) -> str:
    return {v: k for k, v in _g_pattern_dict.items()}.get(col, col)

def _fmt(col: str) -> str:
    return f"{col} (pattern: {_invert(col)})"

def _print_patterns():
    if not _g_pattern_dict:
        _chatter("Global pattern-dict empty"); return
    print("\n[DEBUG] global pattern map:")
    for p, f in sorted(_g_pattern_dict.items(), key=lambda kv: kv[1]):
        print(f"  {f:4s} ← {p}")

# ----------------------------------------------------------------------------
# STATS UPDATE – store BOTH medians and 80 % intervals
# ----------------------------------------------------------------------------
def _update_stats(
    category_segment: str,
    pred_medians: np.ndarray,
    actual_prices: np.ndarray,
) -> dict:
    """Mean/std of predictions + per-bucket median **and** 80 % CI of ACTUAL."""
    if pred_medians.size == 0 or actual_prices.size == 0:
        return {}

    mean = float(np.mean(pred_medians))
    std  = float(np.std(pred_medians, ddof=1)) or 1e-9
    z    = (pred_medians - mean) / std

    masks = {
        "low":    z <= -0.5,
        "medium": (z > -0.5) & (z <= 0.5),
        "high":   z > 0.5,
    }

    bucket_medians   : dict[str, float | None] = {}
    bucket_intervals : dict[str, list[float | None]] = {}

    for lab, m in masks.items():
        prices = actual_prices[m]
        if prices.size:
            bucket_medians[lab] = float(np.median(prices))
            lo, hi = np.percentile(prices, [10, 90])
            bucket_intervals[lab] = [float(lo), float(hi)]
        else:
            bucket_medians[lab]   = None
            bucket_intervals[lab] = [None, None]

    entry = {
        "mean": mean,
        "std":  std,
        "bucket_bounds": {"low_max": -0.5, "high_min": 0.5},
        "bucket_medians":   bucket_medians,    #  ← restored
        "bucket_intervals": bucket_intervals,  #  ← new
    }

    with _stats_lock:
        data = {}
        if _stats_path.exists():
            try:
                data = json.loads(_stats_path.read_text())
            except Exception:
                pass
        data[category_segment] = entry
        _stats_path.write_text(json.dumps(data, indent=2))
        print(f"[INFO] Stats updated → {_stats_path.name}")

    return entry

# ----------------------------------------------------------------------------
# FEATURE IMPORTANCE / README / SHAP HELPERS  (unchanged)
# ----------------------------------------------------------------------------
def _extract_feature_importances(est) -> Optional[np.ndarray]:
    if isinstance(est, Pipeline):
        est = est.named_steps.get("model", est)
    if hasattr(est, "feature_importances_"):
        return np.asarray(est.feature_importances_, dtype=float)
    if hasattr(est, "coef_"):
        c = np.asarray(est.coef_, dtype=float)
        return np.abs(c).mean(axis=0) if c.ndim > 1 else np.abs(c)
    if hasattr(est, "estimators_"):
        mats = [imp for sub in est.estimators_
                if (imp := _extract_feature_importances(sub)) is not None]
        return np.mean(mats, axis=0) if mats else None
    return None

def _write_readme(path: Path, title: str, r2: float, scaler: bool,
                  X: pd.DataFrame, model_type: str, model):
    est = model.named_steps["model"] if isinstance(model, Pipeline) else model
    fi = _extract_feature_importances(est)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(f"=== {title} ===\n\n")
        fh.write(f"Model Type        : {model_type.upper()}\n")
        fh.write(f"R² on test set    : {r2:.4f}\n")
        fh.write(f"Scaler in pipeline: {scaler}\n\n")
        fh.write("Target : Price_in_Exalts\n\nFeatures :\n")
        for c in X.columns:
            fh.write(f"  {_fmt(c)}\n")
        fh.write("\n")
        if fi is None or len(fi) != len(X.columns):
            fh.write("No supported importance / coefficients.\n")
            return
        order = np.argsort(fi)[::-1]
        fh.write("Rank-sorted importances / coefficients:\n")
        for rk, idx in enumerate(order, 1):
            fh.write(f"{rk:2d}) {_fmt(X.columns[idx]):50s} {fi[idx]:.6f}\n")

def _build_and_save_shap(final_model: Pipeline | any,
                         X_background: pd.DataFrame,
                         out_path: Path,
                         meta: dict):
    if not _SHAP_ENABLED:
        return
    if len(X_background) > _shap_bg_n:
        X_background = X_background.sample(_shap_bg_n, random_state=42)
    model_callable = (final_model.predict if isinstance(final_model, Pipeline)
                      else final_model)
    explainer = shap.Explainer(model_callable, X_background)
    with out_path.open("wb") as fh:
        pickle.dump({"shap_explainer": explainer, **meta}, fh)

# ----------------------------------------------------------------------------
# DATA INGEST
# ----------------------------------------------------------------------------
@_announce
def _load_excel_with_price_in_exalts(excel_file: str,
                                     exalt_divine: float,
                                     exalt_chaos:  float) -> pd.DataFrame | None:
    """Read Excel and normalise all prices to Exalts."""
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        _chatter(f"read_excel error → {e}")
        return None
    if {"Price", "Currency"} - set(df.columns):
        _chatter("Missing Price/Currency")
        return None
    df["Price_in_Exalts"] = np.nan
    c = df["Currency"].astype(str).str.lower()
    df.loc[c == "exalted",  "Price_in_Exalts"] = df["Price"]
    df.loc[c == "divine",   "Price_in_Exalts"] = df["Price"] * exalt_divine
    df.loc[c == "chaos",    "Price_in_Exalts"] = df["Price"] * exalt_chaos
    df = df[df["Price_in_Exalts"] > 0]
    _chatter(f"Loaded {len(df)} priced rows")
    return df if not df.empty else None

# ----------------------------------------------------------------------------
# PUBLIC TRAIN ENTRY-POINT
# ----------------------------------------------------------------------------
@_announce
def train_model_from_excel(input_excel_file: str,
                           category: str = "default_model",
                           exalt_divine: float = divine_exalt,
                           exalt_chaos:  float = chaos_exalt,
                           use_scaler: bool = True):
    """Main entry: one Excel file → models (+ optional stats)."""
    with _global_train_lock:
        df = _load_excel_with_price_in_exalts(input_excel_file,
                                              exalt_divine,
                                              exalt_chaos)
        if df is None:
            return
        low, high = df["Price_in_Exalts"].quantile([.05, .95])
        df = df[(df["Price_in_Exalts"] >= low) & (df["Price_in_Exalts"] <= high)]
        _chatter(f"Data after outlier trim: {df.shape}")
        cat_norm = category.lower().replace(" ", "_")
        feat_df, _ = _build_feature_dataframe(df, cat_norm)
        if feat_df is None:
            return
        _print_patterns()
        if cat_norm in {"body_armour", "boots", "gloves", "helmet"}:
            _train_segmented_models(feat_df, cat_norm, use_scaler, input_excel_file)
        else:
            _single_model_path(feat_df, cat_norm, use_scaler, input_excel_file)

# ----------------------------------------------------------------------------
# SINGLE-MODEL PATH (non-segmented categories)
# ----------------------------------------------------------------------------
def _single_model_path(feat_df: pd.DataFrame,
                       cat_norm: str,
                       use_scaler: bool,
                       excel_file: str):
    X = feat_df.drop(columns="Price_in_Exalts")
    y = feat_df["Price_in_Exalts"]
    zc = X.columns[X.nunique(dropna=False) <= 1]
    if len(zc):
        X = X.drop(columns=zc)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.2, random_state=42)

    model_dir = Path(poe2trade_root) / "db" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    preds: dict[str, np.ndarray] = {}

    # ── train XGB / RF / GBR ────────────────────────────────────────────
    for mtype in ("xgb", "rf", "gbr"):
        print(f"\n[INFO] >>> Fitting {mtype.upper()} …")
        gs = _build_pipeline(mtype, use_scaler)
        gs.fit(Xtr, ytr)
        final = gs.best_estimator_
        r2 = r2_score(yte, final.predict(Xte))
        print(f"[RESULT] {mtype.upper()}  R²={r2:.4f}")

        meta = {"pattern_dict": _g_pattern_dict.copy(),
                "base_features": _g_base_features,
                "feature_cols": list(X.columns),
                "use_scaler": use_scaler,
                "model_type": mtype}

        pkl = model_dir / f"{cat_norm}_{mtype}_model.pkl"
        with pkl.open("wb") as fh:
            pickle.dump({"model_pipeline": final, **meta}, fh)

        _build_and_save_shap(final, Xtr,
                             model_dir / f"{cat_norm}_{mtype}_shap.pkl", meta)

        _write_readme(model_dir / f"{pkl.stem}_readme.txt",
                      f"{cat_norm} single-model", r2, use_scaler, X, mtype, final)

        if score_training_flag:
            preds[mtype] = final.predict(X)

    # ── scoring Excel + stats ───────────────────────────────────────────
    if score_training_flag and preds:
        try:
            raw_df = pd.read_excel(excel_file)
        except Exception as e:
            print(f"[WARN] Reload scoring df failed: {e}")
            raw_df = pd.DataFrame(index=X.index)

        # attach predictions & median
        for mt, arr in preds.items():
            raw_df[f"Pred_{mt.upper()}"] = pd.Series(arr, index=X.index)
        raw_df["Pred_MEDIAN"] = raw_df[["Pred_XGB", "Pred_RF", "Pred_GBR"]].median(axis=1)

        # attach actual price
        raw_df["Price_in_Exalts"] = y.values

        stats = _update_stats(
            cat_norm,
            raw_df["Pred_MEDIAN"].to_numpy(),
            raw_df["Price_in_Exalts"].to_numpy(),
        )

        mean, std = stats.get("mean"), stats.get("std")
        z = (raw_df["Pred_MEDIAN"] - mean) / std if std else 0
        bucket = np.where(z <= -0.5, "Low",
                 np.where(z > 0.5, "High", "Medium"))
        raw_df["Bucket_Label"] = bucket
        intv = stats.get("bucket_intervals", {})
        raw_df["Bucket_Price_Low"]  = [intv.get(b.lower(), [None, None])[0] for b in bucket]
        raw_df["Bucket_Price_High"] = [intv.get(b.lower(), [None, None])[1] for b in bucket]

        out_path = model_dir / f"{cat_norm}_scoring.xlsx"
        raw_df.to_excel(out_path, index=False)
        print(f"[INFO] Scoring file → {out_path.name}")

# ----------------------------------------------------------------------------
# SEGMENTED PATH (body armour / boots / gloves / helmet)
# ----------------------------------------------------------------------------
@_announce
def _train_segmented_models(df_all: pd.DataFrame,
                            cat_norm: str,
                            use_scaler: bool,
                            excel_file: str):
    model_dir = Path(poe2trade_root) / "db" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    raw_df: Optional[pd.DataFrame] = None
    if score_training_flag:
        try:
            raw_df = pd.read_excel(excel_file)
        except Exception as e:
            print(f"[WARN] Reload scoring df failed: {e}")

    for seg in _segment_base_candidates:
        mask = _segment_filter(df_all, seg)
        mask_aligned = (mask.reindex(raw_df.index, fill_value=False)
                        if raw_df is not None else mask)
        segdf = df_all[mask]
        print(f"\n[SEG] {seg} rows={len(segdf)}")
        if len(segdf) < 5:
            continue

        nz = segdf.columns.difference(["Price_in_Exalts"])
        zero = nz[segdf[nz].nunique(dropna=False) <= 1]
        if len(zero):
            segdf = segdf.drop(columns=zero)

        km_df, _ = _build_multi_base_kmeans_features(segdf, seg, cat_norm)
        km_path = model_dir / f"{cat_norm}_{seg}_kmeans.pkl"
        if (km_df is None or kmeans_n_clusters == 1 or
                (km_df.values == 0).all() or km_df.var().sum() == 0):
            segdf["cluster_label"] = 0
            with km_path.open("wb") as fk:
                pickle.dump({"kmeans_model": None,
                             "features_for_kmeans": [] if km_df is None else list(km_df.columns)}, fk)
        else:
            km = KMeans(n_clusters=kmeans_n_clusters, random_state=42)
            segdf["cluster_label"] = km.fit_predict(km_df)
            with km_path.open("wb") as fk:
                pickle.dump({"kmeans_model": km,
                             "features_for_kmeans": list(km_df.columns)}, fk)

        if score_training_flag and raw_df is not None:
            seg_preds = {m: pd.Series(index=segdf.index, dtype=float)
                         for m in ("xgb", "rf", "gbr")}

        # ── cluster loop ─────────────────────────────────────────────────
        for cid in segdf["cluster_label"].unique():
            sub = segdf[segdf["cluster_label"] == cid]
            if len(sub) < 5:
                continue

            Xtr, Xte, ytr, yte = train_test_split(
                sub.drop(columns=["Price_in_Exalts", "cluster_label"]),
                sub["Price_in_Exalts"], test_size=.2, random_state=42)

            for mtype in ("xgb", "rf", "gbr"):
                print(f"[SEG] {seg} cluster {cid} → {mtype.upper()}")
                gs = _build_pipeline(mtype, use_scaler)
                gs.fit(Xtr, ytr)
                final = gs.best_estimator_
                r2 = r2_score(yte, final.predict(Xte))
                print(f"[SEG-RESULT] {seg}/{cid}/{mtype.upper()} R²={r2:.4f}")

                meta = {"pattern_dict": _g_pattern_dict.copy(),
                        "base_features": _g_base_features,
                        "feature_cols": list(Xtr.columns),
                        "use_scaler": use_scaler,
                        "model_type": mtype,
                        "segment_name": seg,
                        "cluster_id": cid}

                out = model_dir / f"{cat_norm}_{seg}_cluster{cid}_{mtype}_model.pkl"
                with out.open("wb") as fo:
                    pickle.dump({"model_pipeline": final, **meta}, fo)

                _build_and_save_shap(final, Xtr,
                                     model_dir / f"{cat_norm}_{seg}_cluster{cid}_{mtype}_shap.pkl",
                                     meta)

                _write_readme(model_dir / f"{out.stem}_readme.txt",
                              f"{cat_norm}/{seg}/cluster{cid}",
                              r2, use_scaler, Xtr, mtype, final)

                if score_training_flag and raw_df is not None:
                    sub_X = sub.drop(columns=["Price_in_Exalts", "cluster_label"])
                    seg_preds[mtype].loc[sub.index] = final.predict(sub_X)

        # ── segment-level scoring / stats ───────────────────────────────
        if score_training_flag and raw_df is not None:
            scoring_df = raw_df.loc[mask_aligned].copy()
            scoring_df["Pred_XGB"] = seg_preds["xgb"]
            scoring_df["Pred_RF"]  = seg_preds["rf"]
            scoring_df["Pred_GBR"] = seg_preds["gbr"]
            scoring_df["Pred_MEDIAN"] = scoring_df[["Pred_XGB", "Pred_RF", "Pred_GBR"]].median(axis=1)
            scoring_df["Price_in_Exalts"] = df_all.loc[mask, "Price_in_Exalts"].values

            stats = _update_stats(
                f"{cat_norm}_{seg}",
                scoring_df["Pred_MEDIAN"].to_numpy(),
                scoring_df["Price_in_Exalts"].to_numpy(),
            )

            mean, std = stats.get("mean"), stats.get("std")
            z = (scoring_df["Pred_MEDIAN"] - mean) / std if std else 0
            bucket = np.where(z <= -0.5, "Low",
                     np.where(z > 0.5, "High", "Medium"))
            scoring_df["Bucket_Label"] = bucket
            intv = stats.get("bucket_intervals", {})
            scoring_df["Bucket_Price_Low"]  = [intv.get(b.lower(), [None, None])[0] for b in bucket]
            scoring_df["Bucket_Price_High"] = [intv.get(b.lower(), [None, None])[1] for b in bucket]

            out_path = model_dir / f"{cat_norm}_{seg}_scoring.xlsx"
            scoring_df.to_excel(out_path, index=False)
            print(f"[INFO] Scoring file → {out_path.name}")

# ----------------------------------------------------------------------------
# K-MEANS FEATURE BUILDER
# ----------------------------------------------------------------------------
@_announce
def _build_multi_base_kmeans_features(seg_df: pd.DataFrame,
                                      seg_name: str,
                                      cat_norm: str
) -> Tuple[pd.DataFrame | None, dict | None]:
    """Return numeric frame for K-Means clustering (per segment subset)."""
    if seg_name not in _segment_base_candidates:
        return None, None
    feats = _kmeans_clustering_features.get(cat_norm)
    if not feats:
        return None, None

    out_df = pd.DataFrame(index=seg_df.index, columns=feats, data=0.0)
    inv = _g_pattern_dict

    # flat / inc bases
    for pat in _segment_base_candidates[seg_name]["flat"]:
        if pat in inv and inv[pat] in seg_df.columns:
            out_df["flat_base"] += seg_df[inv[pat]]
    for pat in _segment_base_candidates[seg_name]["inc"]:
        if pat in inv and inv[pat] in seg_df.columns:
            out_df["inc_base"] += seg_df[inv[pat]]

    # resistances
    for rp in _resistance_candidates:
        if rp not in inv or inv[rp] not in seg_df.columns:
            continue
        if   "fire"      in rp and "fire_res"  in out_df.columns:
            out_df["fire_res"]  += seg_df[inv[rp]]
        elif "cold"      in rp and "cold_res"  in out_df.columns:
            out_df["cold_res"]  += seg_df[inv[rp]]
        elif "lightning" in rp and "light_res" in out_df.columns:
            out_df["light_res"] += seg_df[inv[rp]]
        elif "chaos"     in rp and "chaos_res" in out_df.columns:
            out_df["chaos_res"] += seg_df[inv[rp]]

    # extras
    if "move_speed" in feats:
        mv = "#% increased movement speed"
        if mv in inv and inv[mv] in seg_df.columns:
            out_df["move_speed"] += seg_df[inv[mv]]
    if "spirit" in feats:
        sp = "# to spirit"
        if sp in inv and inv[sp] in seg_df.columns:
            out_df["spirit"] += seg_df[inv[sp]]

    out_df = out_df.loc[:, out_df.var() > 0]
    if out_df.empty:
        return None, None
    _chatter(f"kmeans feats → {list(out_df.columns)}")
    return out_df, None

# ----------------------------------------------------------------------------
# FEATURE-MATRIX BUILDER
# ----------------------------------------------------------------------------
@_announce
def _build_feature_dataframe(df: pd.DataFrame,
                             cat_norm: str
) -> Tuple[pd.DataFrame | None, list[str] | None]:
    """Convert raw item table → numeric feature matrix w/ canonical columns."""
    with _pattern_lock:
        _g_pattern_dict.clear()

        # optional columns
        if quality_feature_flag:
            df["Quality"] = pd.to_numeric(df.get("Quality", 0),
                                          errors="coerce").fillna(0.0)
        else:
            df = df.drop(columns=["Quality"], errors="ignore")

        if corrupted_feature_flag:
            df["Corrupted_Flag"] = np.where(
                df.get("Corrupted", "").str.lower() == "yes", 1.0, 0.0)
        else:
            df = df.drop(columns=["Corrupted_Flag"], errors="ignore")

        # build global pattern map
        max_mod = max([int(m.group()) for c in df.columns
                       if (m := re.search(r"\d+", c))
                       and c.startswith("unique_mod")
                       and c.endswith("_pattern")] or [0])
        patterns = {normalise_pattern(p)
                    for i in range(1, max_mod + 1)
                    for p in df.get(f"unique_mod{i}_pattern", [])
                              .dropna().astype(str)}
        for idx, pat in enumerate(sorted(patterns), 1):
            _g_pattern_dict[pat] = f"f{idx}"

        extra_flags = (_defence_flag_features
                       if cat_norm in {"body_armour", "gloves", "boots", "helmet"}
                       else [])

        all_feats = _g_base_features + extra_flags + list(_g_pattern_dict.values())
        out = pd.DataFrame(index=df.index, columns=all_feats, data=0.0)

        for bc in _g_base_features:
            if bc in df.columns:
                out[bc] = df[bc].fillna(0).astype(float)
        for flag in extra_flags:
            if flag in df.columns:
                out[flag] = df[flag].fillna(0).astype(float)

        # iterate mods
        for ridx, row in df.iterrows():
            for j in range(1, max_mod + 1):
                raw_pat = row.get(f"unique_mod{j}_pattern")
                if pd.isna(raw_pat):
                    continue
                pat = normalise_pattern(raw_pat)
                fcol = _g_pattern_dict.get(pat)
                if fcol is None:
                    continue
                val = float(row.get(f"unique_mod{j}_value", 0) or 0)
                out.at[ridx, fcol] += val

        if "Price_in_Exalts" not in df.columns:
            _chatter("Price_in_Exalts missing")
            return None, None
        out["Price_in_Exalts"] = df["Price_in_Exalts"]
        out.dropna(subset=["Price_in_Exalts"], inplace=True)
        _chatter(f"Feature df shape {out.shape}")
        return out, list(out.drop(columns="Price_in_Exalts").columns)

# ----------------------------------------------------------------------------
# SEGMENT FILTER
# ----------------------------------------------------------------------------
def _segment_filter(df: pd.DataFrame, seg: str) -> pd.Series:
    """Boolean mask selecting rows for a defence combination segment."""
    ar = df.get("Deflated_Armour", 0)
    ev = df.get("Deflated_Evasion", 0)
    es = df.get("Deflated_EnergyShield", 0)
    match seg:
        case "ar_only":    return (ar > 0) & (ev == 0) & (es == 0)
        case "ev_only":    return (ev > 0) & (ar == 0) & (es == 0)
        case "es_only":    return (es > 0) & (ar == 0) & (ev == 0)
        case "ar_ev_only": return (ar > 0) & (ev > 0) & (es == 0)
        case "ar_es_only": return (ar > 0) & (es > 0) & (ev == 0)
        case "ev_es_only": return (ev > 0) & (es > 0) & (ar == 0)
        case "all_three":  return (ar > 0) & (ev > 0) & (es > 0)
    return pd.Series(False, index=df.index)

# ─────────────────────────────────────────────────────────────────────────────
#  PIPELINE BUILDER  (fixed for all sklearn versions)
# ─────────────────────────────────────────────────────────────────────────────
def _build_pipeline(model_type: str, use_scaler: bool) -> GridSearchCV:
    """
    Return a GridSearchCV-wrapped Pipeline.
    • hyperparameter_flag == True  -> full v11 grids (unchanged).
    • hyperparameter_flag == False -> ultra-fast *two-value-per-parameter* grids
      (each value in a list, so ParameterGrid never raises).
    """
    steps = [("scaler", StandardScaler())] if use_scaler else []

    if model_type == "rf":
        base = RandomForestRegressor(random_state=42)
        if hyperparameter_flag:                         # full search
            grid = {
                "model__n_estimators":    [100, 300, 600],
                "model__max_depth":       [None, 10, 20],
                "model__max_features":    ["sqrt", 0.8, None],
                "model__min_samples_leaf":[1, 2, 4],
            }
        else:                                           # super-fast
            grid = {
                "model__n_estimators":    [200, 400],     # ← two choices
                "model__max_depth":       [None],         # ← fixed
                "model__max_features":    ["sqrt"],       # ← fixed
                "model__min_samples_leaf":[1],            # ← fixed
            }

    elif model_type == "xgb":
        base = xgb.XGBRegressor(random_state=42,
                                objective="reg:squarederror",
                                tree_method="hist")
        if hyperparameter_flag:
            grid = {
                "model__n_estimators":     [200, 400, 800],
                "model__max_depth":        [4, 6, 10],
                "model__learning_rate":    [0.03, 0.1, 0.2],
                "model__subsample":        [0.7, 1.0],
                "model__colsample_bytree": [0.8, 1.0],
                "model__reg_lambda":       [1.0, 3.0],
            }
        else:
            grid = {
                "model__n_estimators":     [300, 600],
                "model__max_depth":        [6],           # fixed
                "model__learning_rate":    [0.1],         # fixed
                "model__subsample":        [0.7],         # fixed
                "model__colsample_bytree": [0.8],         # fixed
                "model__reg_lambda":       [1.0],         # fixed
            }

    elif model_type == "gbr":
        base = GradientBoostingRegressor(random_state=42)
        if hyperparameter_flag:
            grid = {
                "model__n_estimators":  [200, 400, 800],
                "model__max_depth":     [3, 5],
                "model__learning_rate": [0.03, 0.1],
                "model__subsample":     [0.7, 1.0],
            }
        else:
            grid = {
                "model__n_estimators":  [300, 600],
                "model__max_depth":     [3],
                "model__learning_rate": [0.1],
                "model__subsample":     [0.7],
            }

    elif model_type == "et":
        base = ExtraTreesRegressor(random_state=42)
        if hyperparameter_flag:
            grid = {
                "model__n_estimators": [300, 600],
                "model__max_depth":    [None, 20],
                "model__max_features": ["sqrt", 0.8, None],
                "model__min_samples_leaf":[1, 2],
            }
        else:
            grid = {
                "model__n_estimators": [300, 600],   # still 2×2 grid
                "model__max_depth":    [None, 20],
                "model__max_features": ["sqrt"],     # fixed
                "model__min_samples_leaf":[1],       # fixed
            }

    else:  # Bagged-MLP
        mlp = MLPRegressor(hidden_layer_sizes=(128, 64, 32),
                           activation="relu", solver="adam",
                           learning_rate_init=0.001, alpha=0.0005,
                           random_state=42, early_stopping=True,
                           validation_fraction=0.1,
                           n_iter_no_change=25, max_iter=5000)
        base = BaggingRegressor(estimator=mlp, n_estimators=10,
                                max_samples=0.8, max_features=1.0,
                                bootstrap=True, n_jobs=-1,
                                random_state=42)
        if hyperparameter_flag:
            grid = {
                "model__n_estimators": [5, 10, 20],
                "model__estimator__hidden_layer_sizes":[(128, 64, 32),
                                                        (160, 80, 40)],
                "model__estimator__alpha":              [0.0001, 0.0005],
                "model__estimator__learning_rate_init": [0.0005, 0.001],
            }
        else:
            grid = {
                "model__n_estimators": [6, 12],
                "model__estimator__hidden_layer_sizes":[(128, 64, 32)],
                "model__estimator__alpha":              [0.0005],
                "model__estimator__learning_rate_init": [0.001],
            }

    return GridSearchCV(
        Pipeline(steps + [("model", base)]),
        param_grid=grid,
        scoring="r2",
        cv=3,
        n_jobs=-1,
        verbose=2,
        refit=True,
    )