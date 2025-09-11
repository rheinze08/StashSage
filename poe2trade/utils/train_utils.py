# File: poe2trade/utils/train_utils.py

from __future__ import annotations
import json
import pickle
import importlib
import re
import os
import time
from pathlib import Path
from threading import RLock
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import xgboost as xgb

from poe2trade import (
    poe2trade_root, shap_flag, hyperparameter_flag,
    train_super_xgb, train_super_rf, train_super_gbr,
    use_previous_model_settings, knn_k, use_cuda,
)

# ──────────────────────────────────────────────────────────────
# Globals / helpers
# ──────────────────────────────────────────────────────────────
# Read global quiet switch from env; individual functions can also pass quiet=True
QUIET = os.getenv("POE2TRADE_QUIET", "0").lower() in ("1", "true", "yes")

_global_train_lock = RLock()
_SEGMENTS = (
    "ar_only", "ev_only", "es_only",
    "ar_ev_only", "ar_es_only", "ev_es_only",
    "all_three",
)

# ──────────────────────────────────────────────────────────────
# Branch detectors
# ──────────────────────────────────────────────────────────────
def _is_jewelry_branch(path_str: str) -> bool:
    p = path_str.lower()
    return any(tok in p for tok in ("ring", "amulet"))

def _is_belt_branch(path_str: str) -> bool:
    p = path_str.lower()
    return "belt" in p and not any(tok in p for tok in ("ring", "amulet"))

def _is_ring_branch(path_str: str) -> bool:
    return "ring" in path_str.lower()

def _is_amulet_branch(path_str: str) -> bool:
    return "amulet" in path_str.lower()

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _get_active_model_types() -> list[str]:
    return [
        m for m, flag in {
            "xgb": train_super_xgb,
            "rf":  train_super_rf,
            "gbr": train_super_gbr,
        }.items() if flag
    ]

# ──────────────────────────────────────────────────────────────
# SHAP (optional)
# ──────────────────────────────────────────────────────────────
shap = None
_SHAP = False
if shap_flag:
    try:
        shap = importlib.import_module("shap")
        _SHAP = True
        if not QUIET:
            print("[INFO] SHAP support enabled")
    except ModuleNotFoundError:
        if not QUIET:
            print("[INFO] shap_flag true but `shap` not installed — SHAP disabled")

# ──────────────────────────────────────────────────────────────
# Pipeline builder
# ──────────────────────────────────────────────────────────────
_SPARSE_MAX_DEPTHS, _SPARSE_MAX_DEPTH_1 = [2, 3, 5], [3]
_SHRINK_MAX_FEATURES = ["sqrt", 0.3]

def _build_pipeline(
    model_type: str,
    use_scaler: bool,
    *,
    inner_n_jobs: int,
    quiet: bool = False
) -> GridSearchCV:
    is_quiet = QUIET or quiet
    steps = [("scaler", StandardScaler())] if use_scaler else []

    if model_type == "rf":
        base = RandomForestRegressor(random_state=42)
        grid = ({
            "model__n_estimators":     [200, 400, 800],
            "model__max_depth":        _SPARSE_MAX_DEPTHS + [None],
            "model__max_features":     _SHRINK_MAX_FEATURES + [None],
            "model__min_samples_leaf": [1, 2, 5],
        } if hyperparameter_flag else {
            "model__n_estimators":     [400],
            "model__max_depth":        _SPARSE_MAX_DEPTH_1,
            "model__max_features":     ["sqrt"],
            "model__min_samples_leaf": [2],
        })
    elif model_type == "xgb":
        base = xgb.XGBRegressor(
            random_state=42, objective="reg:squarederror",
            tree_method="hist", device="cuda" if use_cuda else "cpu",
            enable_categorical=False,
            verbosity=0 if is_quiet else 1
        )
        grid = ({
            "model__n_estimators":      [300, 600, 900],
            "model__max_depth":         _SPARSE_MAX_DEPTHS,
            "model__learning_rate":     [0.05, 0.1, 0.2],
            "model__subsample":         [0.6, 0.8],
            "model__colsample_bytree":  [0.6, 0.8],
            "model__reg_lambda":        [1.0, 3.0],
            "model__reg_alpha":         [0.0, 0.5],
        } if hyperparameter_flag else {
            "model__n_estimators":      [600],
            "model__max_depth":         _SPARSE_MAX_DEPTH_1,
            "model__learning_rate":     [0.1],
            "model__subsample":         [0.6],
            "model__colsample_bytree":  [0.6],
            "model__reg_lambda":        [1.0],
            "model__reg_alpha":         [0.0],
        })
    elif model_type == "gbr":
        base = GradientBoostingRegressor(random_state=42)
        grid = ({
            "model__n_estimators":  [300, 600, 900],
            "model__max_depth":     [2, 3, 4],
            "model__learning_rate": [0.05, 0.1],
            "model__subsample":     [0.6, 0.8],
        } if hyperparameter_flag else {
            "model__n_estimators":  [600],
            "model__max_depth":     [3],
            "model__learning_rate": [0.1],
            "model__subsample":     [0.6],
        })
    else:
        raise ValueError(f"Unsupported model_type '{model_type}'")

    return GridSearchCV(
        Pipeline(steps + [("model", base)]),
        param_grid=grid, scoring="r2", cv=3,
        n_jobs=inner_n_jobs, verbose=(0 if is_quiet else 2), refit=True
    )

# ──────────────────────────────────────────────────────────────
# SHAP + README helpers
# ──────────────────────────────────────────────────────────────
_num_re = re.compile(r"[+-]?\d+(?:\.\d+)?")
def _fmt(col: str) -> str:
    return _num_re.sub("#", col)

def _extract_feature_importances(est):
    if isinstance(est, Pipeline):
        est = est.named_steps.get("model", est)
    if hasattr(est, "feature_importances_"):
        return np.asarray(est.feature_importances_, dtype=float)
    if hasattr(est, "coef_"):
        c = np.asarray(est.coef_, dtype=float)
        return np.abs(c).mean(axis=0) if c.ndim > 1 else np.abs(c)
    return None

def _build_and_save_shap(model, X_bg, out_path: Path, meta: dict):
    if not _SHAP:
        return
    if len(X_bg) > 100:
        X_bg = X_bg.sample(100, random_state=42)
    explainer = shap.Explainer(model.predict, X_bg)
    pickle.dump({"shap_explainer": explainer, **meta}, out_path.open("wb"))

def _write_readme(path: Path, title: str, r2: float,
                  use_scaler: bool, X: pd.DataFrame,
                  model_type: str, best_params: dict, model):
    with path.open("w", encoding="utf-8") as fh:
        fh.write(f"=== {title} ===\n\n")
        fh.write(f"Model Type        : {model_type.upper()}\n")
        fh.write(f"R² on test set    : {r2:.4f}\n")
        fh.write(f"Scaler in pipeline: {use_scaler}\n")
        fh.write(f"Hyperparameters   : {json.dumps(best_params)}\n\n")
        fh.write("Target : price\n\nFeatures :\n")
        for col in X.columns:
            fh.write(f"  {_fmt(col)}\n")
        fh.write("\n")
        fi = _extract_feature_importances(model)
        if fi is None or len(fi) != len(X.columns):
            fh.write("No supported importance / coefficients.\n")
            return
        order = np.argsort(fi)[::-1]
        fh.write("Rank-sorted importances / coefficients:\n")
        for rk, idx in enumerate(order, 1):
            fh.write(f"{rk:2d}) {_fmt(X.columns[idx]):50s} {fi[idx]:.6f}\n")

# ──────────────────────────────────────────────────────────────
# Segment logic (armour path)
# ──────────────────────────────────────────────────────────────
def _segment_mask(df: pd.DataFrame, seg: str) -> pd.Series:
    ar = df.get("ar_norm", 0)
    ev = df.get("ev_norm", 0)
    es = df.get("es_norm", 0)
    if not (hasattr(ar, "__len__") and hasattr(ev, "__len__") and hasattr(es, "__len__")):
        return pd.Series(False, index=df.index)
    match seg:
        case "ar_only":    return (ar > 0) & (ev == 0) & (es == 0)
        case "ev_only":    return (ev > 0) & (ar == 0) & (es == 0)
        case "es_only":    return (es > 0) & (ar == 0) & (ev == 0)
        case "ar_ev_only": return (ar > 0) & (ev > 0) & (es == 0)
        case "ar_es_only": return (ar > 0) & (es > 0) & (ev == 0)
        case "ev_es_only": return (ev > 0) & (es > 0) & (ar == 0)
        case "all_three":  return (ar > 0) & (ev > 0) & (es > 0)
    return pd.Series(False, index=df.index)

# ──────────────────────────────────────────────────────────────
# Core per-segment training (armour)
# ──────────────────────────────────────────────────────────────
def _train_one_segment(
    seg: str, seg_df: pd.DataFrame, *,
    cat_norm: str, model_dir: Path,
    use_scaler: bool, test_size: float,
    random_state: int, inner_n_jobs: int, quiet: bool
):
    is_quiet = QUIET or quiet
    if len(seg_df) < 5:
        if not is_quiet:
            print(f"[SEG] {seg} skipped (rows={len(seg_df)})")
        return

    y = seg_df["price"].astype(float)
    # numeric-only features for safety
    X = seg_df.drop(columns=["price"]).select_dtypes(include=[np.number])
    zero_def = [c for c in ("ar_norm", "ev_norm", "es_norm")
                if c in X and X[c].nunique(dropna=False) <= 1]
    if zero_def:
        X = X.drop(columns=zero_def)
    const_cols = X.columns[X.nunique(dropna=False) <= 1]
    if len(const_cols) > 0:
        X = X.drop(columns=const_cols)

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    for mtype in _get_active_model_types():
        if not is_quiet:
            print(f"[{seg.upper()}] → {mtype.upper()}")

        best_params = {}
        prev_path = model_dir / f"{cat_norm}_{seg}_{mtype}_model.pkl"
        if use_previous_model_settings and prev_path.exists():
            prev = pickle.load(prev_path.open("rb"))
            best_params = prev.get("best_params", {})
            stripped = {k.replace("model__", ""): v for k, v in best_params.items()}

            if mtype == "rf":
                base = RandomForestRegressor(random_state=42, **stripped)
            elif mtype == "xgb":
                base = xgb.XGBRegressor(
                    random_state=42, objective="reg:squarederror",
                    tree_method="hist", device="cuda" if use_cuda else "cpu",
                    enable_categorical=False,
                    verbosity=0,  # silent in quiet mode and default
                    **{k: v for k, v in stripped.items() if k != "verbosity"}
                )
            else:  # gbr
                base = GradientBoostingRegressor(random_state=42, **stripped)

            pipeline = Pipeline(
                ([("scaler", StandardScaler())] if use_scaler else []) + [("model", base)]
            )
            final = pipeline.fit(Xtr, ytr)
        else:
            gs = _build_pipeline(mtype, use_scaler, inner_n_jobs=inner_n_jobs, quiet=is_quiet)
            gs.fit(Xtr, ytr)
            final = gs.best_estimator_
            best_params = getattr(final, "best_params_", {})

        r2val = r2_score(yte, final.predict(Xte))
        if not is_quiet:
            print(f"[{seg.upper()}] {mtype.upper()}  R²={r2val:.4f}")

        meta = {
            "base_features": ["ar_norm", "ev_norm", "es_norm"],
            "feature_cols":  list(X.columns),
            "use_scaler":    use_scaler,
            "model_type":    mtype,
            "best_params":   best_params,
            "segment_name":  seg,
        }

        with _global_train_lock:
            pkl_path = model_dir / f"{cat_norm}_{seg}_{mtype}_model.pkl"
            pickle.dump({"model_pipeline": final, **meta}, pkl_path.open("wb"))
            _build_and_save_shap(
                final, Xtr, model_dir / f"{cat_norm}_{seg}_{mtype}_shap.pkl", meta
            )
            _write_readme(
                model_dir / f"{pkl_path.stem}_readme.txt",
                f"{cat_norm}/{seg} → {mtype.upper()}",
                r2val, use_scaler, X, mtype, best_params, final
            )

# ──────────────────────────────────────────────────────────────
# PUBLIC: supervised training
# ──────────────────────────────────────────────────────────────
def train_super_model_from_matrix(
    matrix_file: str,
    category: str = "default_model",
    use_scaler: bool = True,
    test_size: float = 0.2,
    random_state: int = 42,
    *,
    parallel_segments: bool = True,
    max_workers: int | None = None,
    quiet: bool = False
):
    """
    Trains supervised models. In quiet=True mode, suppresses per-iteration logs.
    Does NOT print a final timer line; let the caller handle timing/summary.
    """
    is_quiet = QUIET or quiet
    df = pd.read_parquet(matrix_file).drop(columns=["item"], errors="ignore")
    # force lowercase columns in case upstream changes
    df.columns = [str(c).lower() for c in df.columns]

    if "price" not in df.columns:
        raise KeyError("No 'price' column")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df.dropna(subset=["price"], inplace=True)

    belt_branch   = _is_belt_branch(matrix_file)
    ring_branch   = _is_ring_branch(matrix_file)
    amulet_branch = _is_amulet_branch(matrix_file)
    model_dir     = Path(poe2trade_root) / "db" / "super_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    cat_norm = category.lower().replace(" ", "_")

    # --- single-model for belt/ring/amulet ---
    if belt_branch or ring_branch or amulet_branch:
        kind = ("belt" if belt_branch else "ring" if ring_branch else "amulet")
        if not is_quiet:
            print(f"[INFO] {kind.capitalize()} branch detected — training single global model")

        df2 = df.drop(columns=["ar_norm", "ev_norm", "es_norm"], errors="ignore")
        y = df2["price"].astype(float)
        # numeric-only features for safety
        X = df2.drop(columns=["price"]).select_dtypes(include=[np.number])
        const_cols = X.columns[X.nunique(dropna=False) <= 1]
        if len(const_cols) > 0:
            X = X.drop(columns=const_cols)

        Xtr, Xte, ytr, yte = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        for mtype in _get_active_model_types():
            if not is_quiet:
                print(f"[{kind.upper()}] → {mtype.upper()}")
            gs = _build_pipeline(mtype, use_scaler, inner_n_jobs=-1, quiet=is_quiet)
            gs.fit(Xtr, ytr)
            final = gs.best_estimator_
            best_params = getattr(final, "best_params_", {})
            r2val = r2_score(yte, final.predict(Xte))
            if not is_quiet:
                print(f"[{kind.upper()}] {mtype.upper()}  R²={r2val:.4f}")

            meta = {
                "base_features": [],
                "feature_cols":  list(X.columns),
                "use_scaler":    use_scaler,
                "model_type":    mtype,
                "best_params":   best_params,
                "segment_name":  kind,
            }

            with _global_train_lock:
                pkl_path = model_dir / f"{cat_norm}_{mtype}_model.pkl"
                pickle.dump({"model_pipeline": final, **meta}, pkl_path.open("wb"))
                _build_and_save_shap(
                    final, Xtr, model_dir / f"{cat_norm}_{mtype}_shap.pkl", meta
                )
                _write_readme(
                    model_dir / f"{pkl_path.stem}_readme.txt",
                    f"{cat_norm}/{kind} → {mtype.upper()}",
                    r2val, use_scaler, X, mtype, best_params, final
                )
        return

    # --- armour branch: per-segment ---
    if not is_quiet:
        print("[INFO] Armour branch detected — segment-wise training")

    tasks = [(seg, df[_segment_mask(df, seg)].copy()) for seg in _SEGMENTS]
    inner_n_jobs = 1 if parallel_segments else -1

    if not parallel_segments:
        for seg, seg_df in tasks:
            _train_one_segment(
                seg, seg_df, cat_norm=cat_norm, model_dir=model_dir,
                use_scaler=use_scaler, test_size=test_size,
                random_state=random_state, inner_n_jobs=inner_n_jobs, quiet=is_quiet
            )
    else:
        max_workers = max_workers or min(os.cpu_count() or 1, len(tasks))
        if not is_quiet:
            print(f"[PAR] training segments in parallel (workers={max_workers})")
        errors: list[Exception] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = [
                pool.submit(
                    _train_one_segment, seg, seg_df,
                    cat_norm=cat_norm, model_dir=model_dir,
                    use_scaler=use_scaler, test_size=test_size,
                    random_state=random_state, inner_n_jobs=inner_n_jobs, quiet=is_quiet
                )
                for seg, seg_df in tasks
            ]
            for f in as_completed(futs):
                exc = f.exception()
                if exc:
                    if not is_quiet:
                        print(f"[PAR] worker raised: {exc!r}")
                    errors.append(exc)
        if errors:
            # Raise a summarized error so callers can handle/report once.
            raise RuntimeError(f"{len(errors)} training segment(s) failed; first error: {errors[0]!r}")

# ──────────────────────────────────────────────────────────────
# PUBLIC: unsupervised (KNN) training
# ──────────────────────────────────────────────────────────────
def train_unsuper_model_from_matrix(
    matrix_file: str,
    category: str,
    quiet: bool = False
) -> list[str]:
    """
    • Armour branch : train one KNN per defence segment
    • Belt/Ring/Amulet : single global KNN
    In quiet=True mode, suppresses per-iteration logs.
    """
    output_paths: list[str] = []
    is_quiet = QUIET or quiet

    with _global_train_lock:
        model_path = Path(matrix_file)
        cat_norm = category.lower().replace(" ", "_")

        overlay_path = model_path.with_name(
            model_path.stem.replace(
                "_feature_matrix_model",
                "_feature_matrix_overlay"
            ) + model_path.suffix
        )

        df_model   = pd.read_parquet(model_path)
        df_overlay = pd.read_parquet(overlay_path)
        # ensure lowercase columns in case of external sources
        df_model.columns   = [str(c).lower() for c in df_model.columns]
        df_overlay.columns = [str(c).lower() for c in df_overlay.columns]

        belt_branch   = _is_belt_branch(matrix_file)
        ring_branch   = _is_ring_branch(matrix_file)
        amulet_branch = _is_amulet_branch(matrix_file)

        model_dir = Path(poe2trade_root) / "db" / "unsuper_models"
        model_dir.mkdir(parents=True, exist_ok=True)

        # --- Single‐KNN for belt/ring/amulet ---
        if belt_branch or ring_branch or amulet_branch:
            kind = "belt" if belt_branch else ("ring" if ring_branch else "amulet")
            if not is_quiet:
                print(f"[UNSUP] {kind.capitalize()} branch — single global KNN")

            df_feats = (
                df_model
                .drop(columns=["price"], errors="ignore")
                .drop(columns=["ar_norm", "ev_norm", "es_norm"], errors="ignore")
            )
            Xnum = df_feats.select_dtypes(include=[np.number]).fillna(0.0)

            scaler = StandardScaler().fit(Xnum)
            Xproc  = scaler.transform(Xnum)

            nn = NearestNeighbors(n_neighbors=knn_k, algorithm="auto", leaf_size=30)
            nn.fit(Xproc)

            bundle = {
                "nn_model":     nn,
                "scaler":       scaler,
                "scaler_data":  {"mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist()},
                "feature_cols": list(Xnum.columns),
                "segment":      kind,
                "row_indices":  df_model.index.tolist(),
                "X_all":        Xnum.to_numpy(dtype=np.float32),
                "model_price":  df_model["price"].to_numpy(dtype=np.float32),
                "overlay_df":   df_overlay,
                "n_neighbors":  nn.n_neighbors,
                "algorithm":    nn.algorithm,
                "leaf_size":    nn.leaf_size,
            }

            pkl_path = model_dir / f"{cat_norm}_knn_model.pkl"
            with pkl_path.open("wb") as fh:
                pickle.dump(bundle, fh)
            output_paths.append(str(pkl_path))

            readme = model_dir / f"{cat_norm}_knn_model_readme.txt"
            with readme.open("w", encoding="utf-8") as fh:
                fh.write(f"Segment: {kind} ({kind.capitalize()})\n")
                fh.write("Model  : Unsupervised NearestNeighbors\n")
                fh.write(f"n_neighbors: {nn.n_neighbors}\n")
                fh.write(f"algorithm  : {nn.algorithm}\n")
                fh.write(f"leaf_size  : {nn.leaf_size}\n\n")
                fh.write("Features:\n")
                for col in Xnum.columns:
                    fh.write(f"  {col}\n")
            output_paths.append(str(readme))

            if not is_quiet:
                print(f"[UNSUP] {kind} → KNN model saved as {pkl_path.name}")
            return output_paths

        # --- Armour segments: one KNN per defence segment ---
        if not is_quiet:
            print("[UNSUP] Armour branch — segment-wise KNN")
        df_feats = df_model.drop(columns=["price"], errors="ignore")

        for seg in _SEGMENTS:
            mask         = _segment_mask(df_feats, seg)
            seg_feats    = df_feats[mask].copy()
            seg_model_df = df_model[mask].copy()
            seg_overlay  = df_overlay[mask].copy()

            if len(seg_feats) < knn_k + 1:
                if not is_quiet:
                    print(f"[UNSUP] {seg} skipped (rows={len(seg_feats)})")
                continue

            drop0 = [
                c for c in ("ar_norm", "ev_norm", "es_norm")
                if c in seg_feats and seg_feats[c].nunique(dropna=False) <= 1
            ]
            tmp   = seg_feats.drop(columns=drop0)
            const = [c for c in tmp.columns if tmp[c].nunique(dropna=False) <= 1]
            Xdf   = tmp.drop(columns=const)

            Xnum   = Xdf.select_dtypes(include=[np.number]).fillna(0.0)
            scaler = StandardScaler().fit(Xnum)
            Xproc  = scaler.transform(Xnum)

            nn = NearestNeighbors(n_neighbors=knn_k, algorithm="auto", leaf_size=30)
            nn.fit(Xproc)

            bundle = {
                "nn_model":     nn,
                "scaler":       scaler,
                "scaler_data":  {"mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist()},
                "feature_cols": list(Xnum.columns),
                "segment":      seg,
                "row_indices":  seg_model_df.index.tolist(),
                "X_all":        Xnum.to_numpy(dtype=np.float32),
                "model_price":  seg_model_df["price"].to_numpy(dtype=np.float32),
                "overlay_df":   seg_overlay,
                "n_neighbors":  nn.n_neighbors,
                "algorithm":    nn.algorithm,
                "leaf_size":    nn.leaf_size,
            }

            pkl_path = model_dir / f"{cat_norm}_{seg}_knn_model.pkl"
            with pkl_path.open("wb") as fh:
                pickle.dump(bundle, fh)
            output_paths.append(str(pkl_path))

            readme = model_dir / f"{cat_norm}_{seg}_knn_model_readme.txt"
            with readme.open("w", encoding="utf-8") as fh:
                fh.write(f"Segment: {seg}\n")
                fh.write("Model  : Unsupervised NearestNeighbors\n")
                fh.write(f"n_neighbors: {nn.n_neighbors}\n")
                fh.write(f"algorithm  : {nn.algorithm}\n")
                fh.write(f"leaf_size  : {nn.leaf_size}\n\n")
                fh.write("Features:\n")
                for col in Xnum.columns:
                    fh.write(f"  {col}\n")
            output_paths.append(str(readme))

            if not is_quiet:
                print(f"[UNSUP] {seg} → KNN model saved as {pkl_path.name}")

    return output_paths
