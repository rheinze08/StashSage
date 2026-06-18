# File: poe2trade/utils/score_super_utils.py
"""
score_super_utils.py

Apply trained “super” regression models to new feature-matrices and produce
per-segment (or per-branch) scoring spreadsheets. Also updates a JSON file
with summary statistics and the EXACT bucket cutoffs derived from predictions
so downstream code can classify any single value without recomputing.

Key points:
- Buckets are ALWAYS computed from model predictions (pred_median).
- Strategy is singular, controlled by `use_z`:
    * use_z=True  → z-score style via value cutoffs:
        t_low  = mean + 1*std   (≤ t_low → Low)
        t_high = mean + 2*std   (> t_high → High)
        else Medium
    * use_z=False → percentile thresholds on pred_median using `quantile_splitters`
        quantile_splitters = [low_top_percent, medium_top_percent] (e.g., [50, 80])
        (≤ value_at(low_top_percent) → Low),
        (> value_at(medium_top_percent) → High),
        else Medium

- We persist the exact cutoffs into category_segment_stats.json:
    {
      "method": "z" | "percentile",
      "mean": <float>, "std": <float>,
      "t_low": <float or null>, "t_high": <float or null>,
      "percentile_splitters": [<int>, <int>] | null,  # e.g., [50, 80]
      "percentile_values":    [<float>, <float>] | null,  # values at those percentiles on pred_median
      "bucket_intervals": { "low":[lo,hi], "medium":[lo,hi], "high":[lo,hi] }  # on ACTUAL prices (10–90%)
    }

Additionally:
- Standardizes lowercase columns (ar_norm/ev_norm/es_norm).
- Jewellery stats key == category; armour stats key == f"{category}_{segment}".
- After writing each artifact, prints three random scored rows (row_id, price, pred_median, bucket_label, and any per-model preds).
- Saves XLSX and JSON (row-wise) sidecars; PNG plots as before.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

# Ensure printing never crashes on Windows console encodings
try:  # pragma: no cover
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Matplotlib is optional; plotting gracefully degrades if unavailable
try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # type: ignore

from poe2trade import (
    poe2trade_root,
    train_super_xgb,
    train_super_rf,
    train_super_gbr,
    score_with_z,
    quantile_splitters,
    jewel_list,
)

# ─────────────────────────────────────────────────────────────────────────────
# Which supervised models are enabled?
# ─────────────────────────────────────────────────────────────────────────────
def _get_active_model_types() -> List[str]:
    """Return enabled model types based on configuration flags."""
    flags = {
        "xgb": train_super_xgb,
        "rf":  train_super_rf,
        "gbr": train_super_gbr,
    }
    return [m for m, enabled in flags.items() if enabled]


# ─────────────────────────────────────────────────────────────────────────────
# Branch detectors for jewellery vs. armour
# ─────────────────────────────────────────────────────────────────────────────
def _is_belt_branch(path_str: str) -> bool:
    p = path_str.lower()
    return "belt" in p and not any(tok in p for tok in ("ring", "amulet"))


def _is_ring_branch(path_str: str) -> bool:
    return "ring" in path_str.lower()


def _is_amulet_branch(path_str: str) -> bool:
    return "amulet" in path_str.lower()

def _is_simple_branch(path_str: str) -> bool:
    """Simple categories using a single global model (no armour segments).

    Dynamic: treats Jewel and all entries from `poe2trade.jewel_list` as simple,
    plus Sceptre/Scepter/Wand.
    """
    p = path_str.lower()
    # Build token set dynamically from jewel_list
    try:
        jewels = [str(j).strip().lower() for j in (jewel_list or []) if str(j).strip()]
    except Exception:
        jewels = []
    tokens = ["jewel", "sceptre", "scepter", "wand", "quiver"] + jewels
    return any(tok in p for tok in tokens)


# ─────────────────────────────────────────────────────────────────────────────
# Defence-combo segments for armour branch
# ─────────────────────────────────────────────────────────────────────────────
_SEGMENTS = (
    "ar_only",
    "ev_only",
    "es_only",
    "ar_ev_only",
    "ar_es_only",
    "ev_es_only",
    "all_three",
)


def _segment_mask(df: pd.DataFrame, seg: str) -> pd.Series:
    """
    Given a DataFrame with optional ar_norm, ev_norm, es_norm columns,
    return a boolean mask selecting rows that belong to the requested
    defence-combo segment.
    """
    default = pd.Series(0, index=df.index)
    ar = df.get("ar_norm", default)
    ev = df.get("ev_norm", default)
    es = df.get("es_norm", default)

    if seg == "ar_only":
        return (ar > 0) & (ev == 0) & (es == 0)
    if seg == "ev_only":
        return (ev > 0) & (ar == 0) & (es == 0)
    if seg == "es_only":
        return (es > 0) & (ar == 0) & (ev == 0)
    if seg == "ar_ev_only":
        return (ar > 0) & (ev > 0) & (es == 0)
    if seg == "ar_es_only":
        return (ar > 0) & (es > 0) & (ev == 0)
    if seg == "ev_es_only":
        return (ev > 0) & (es > 0) & (ar == 0)
    if seg == "all_three":
        return (ar > 0) & (ev > 0) & (es > 0)
    # Fallback: nothing selected
    return pd.Series(False, index=df.index, dtype=bool)


# ─────────────────────────────────────────────────────────────────────────────
# Load and clean a feature-matrix parquet
# ─────────────────────────────────────────────────────────────────────────────
def _load_matrix(matrix_file: str) -> pd.DataFrame:
    """
    Read a .parquet feature-matrix, lowercase columns, drop the 'item' helper
    column if present, coerce 'price' to numeric, and drop any rows with
    missing price.
    """
    df = pd.read_parquet(matrix_file)
    df.columns = [str(c).lower() for c in df.columns]
    df = df.drop(columns=["item"], errors="ignore")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df.dropna(subset=["price"])


# ─────────────────────────────────────────────────────────────────────────────
# Percentile splitter validation
# ─────────────────────────────────────────────────────────────────────────────
def _validated_splitters() -> Tuple[int, int]:
    """
    Validate and normalize the global `quantile_splitters` into a sorted pair of ints in [0,100].
    Falls back to [70,90] if invalid.
    """
    default = [70, 90]
    try:
        qs = list(quantile_splitters or default)
    except Exception:
        print("[WARN] quantile_splitters not accessible; using default [70, 90]")
        return 70, 90

    if len(qs) != 2:
        print(f"[WARN] quantile_splitters must have two values; got {qs!r}. Using default [70, 90].")
        return 70, 90

    try:
        a, b = float(qs[0]), float(qs[1])
    except Exception:
        print(f"[WARN] non-numeric quantile_splitters {qs!r}; using default [70, 90].")
        return 70, 90

    if not (0 <= a <= 100 and 0 <= b <= 100) or not (a < b):
        print(f"[WARN] invalid quantile_splitters {qs!r}; must satisfy 0<=a<b<=100. Using default [70, 90].")
        return 70, 90

    return int(round(a)), int(round(b))


# ─────────────────────────────────────────────────────────────────────────────
# Persisted summary-stats JSON and lock for thread safety
# ─────────────────────────────────────────────────────────────────────────────
_stats_path = Path(poe2trade_root) / "db" / "super_models" / "category_segment_stats.json"
_stats_lock = RLock()


def _write_stats(new_stats: Dict[str, Any]) -> None:
    """
    Merge `new_stats` into the existing stats JSON on disk (or create it
    if missing). Uses a lock to prevent concurrent writes.
    """
    with _stats_lock:
        if _stats_path.exists():
            try:
                current = json.loads(_stats_path.read_text())
            except (json.JSONDecodeError, OSError):
                current = {}
        else:
            current = {}

        current.update(new_stats)
        _stats_path.write_text(json.dumps(current, indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: thresholds & labeling (single source of truth)
# ─────────────────────────────────────────────────────────────────────────────
def _compute_pred_cutoffs(pred: np.ndarray, *, use_z: bool) -> Dict[str, Any]:
    """
    Compute bucket cutoffs on pred_median, according to the single chosen strategy.

    Returns a dict with:
      method: "z" | "percentile"
      mean, std: floats (always provided; std≥1e-9)
      t_low, t_high: floats or None  (z mode)
      percentile_splitters: [low_top_percent, medium_top_percent] or None
      percentile_values:    [value_at_low_top, value_at_medium_top] or None
    """
    pred = np.asarray(pred, dtype=float)
    mean = float(np.mean(pred)) if pred.size else 0.0
    std = float(np.std(pred, ddof=1)) if pred.size else 1.0
    if not np.isfinite(std) or std == 0.0:
        std = 1e-9

    if use_z:
        t_low = mean + 1.0 * std
        t_high = mean + 2.0 * std
        return {
            "method": "z",
            "mean": mean,
            "std": std,
            "t_low": float(t_low),
            "t_high": float(t_high),
            "percentile_splitters": None,
            "percentile_values": None,
        }

    # Percentile mode (via quantile_splitters)
    low_p, med_p = _validated_splitters()
    if pred.size:
        v_low, v_med = np.percentile(pred, [low_p, med_p])
        v_low = float(v_low)
        v_med = float(v_med)
    else:
        v_low, v_med = None, None  # no data
    return {
        "method": "percentile",
        "mean": mean,
        "std": std,
        "t_low": None,
        "t_high": None,
        "percentile_splitters": [low_p, med_p],
        "percentile_values": [v_low, v_med],
    }


def _assign_buckets_from_cutoffs(values: np.ndarray, cuts: Dict[str, Any]) -> np.ndarray:
    """
    Assign Low/Medium/High using the provided cutoffs (already derived from pred_median).

    Conventions (mutually exclusive):
      Z-mode:       value ≤ t_low → Low ; value > t_high → High ; else Medium
      Percentile:   value ≤ percentile_values[0] → Low ;
                    value >  percentile_values[1] → High ; else Medium
    """
    v = np.asarray(values, dtype=float)
    method = cuts.get("method", "percentile")
    out = np.empty(v.shape, dtype=object)

    if method == "z":
        t_low = float(cuts["t_low"])
        t_high = float(cuts["t_high"])
        out[:] = "Medium"
        out[v <= t_low] = "Low"
        out[v >  t_high] = "High"
        return out

    pv = cuts.get("percentile_values")
    if not pv or pv[0] is None or pv[1] is None:
        # No valid percentiles; default everyone to Medium
        out[:] = "Medium"
        return out

    low_val = float(pv[0])
    high_val = float(pv[1])
    out[:] = "Medium"
    out[v <= low_val] = "Low"
    out[v >  high_val] = "High"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Pretty console preview of a few random scored rows
# ─────────────────────────────────────────────────────────────────────────────
def _print_random_samples(df: pd.DataFrame, label: str, k: int = 3) -> None:
    """
    Print a compact table for k random rows from `df` showing:
    row_id, price, pred_median, bucket_label, and any available per-model preds.
    """
    if df.empty:
        print(f"[SAMPLE] {label}: no rows")
        return

    k = min(k, len(df))
    cols = ["price", "pred_median", "bucket_label"]
    cols += [f"pred_{m}" for m in _get_active_model_types() if f"pred_{m}" in df.columns]
    cols = [c for c in cols if c in df.columns]

    samp = df.sample(k, replace=False)
    view = samp.copy()
    try:
        view.insert(0, "row_id", samp.index)
    except Exception:
        pass

    def _ff(x):
        try:
            return f"{float(x):,.2f}"
        except Exception:
            return x

    print(f"[SAMPLE] {label} — {k} random item(s):")
    print(view[["row_id"] + cols].to_string(index=False, justify="left", formatters={c: _ff for c in cols}))
    print("")


# ─────────────────────────────────────────────────────────────────────────────
# Plot helpers (unchanged visuals; fixed label string)
# ─────────────────────────────────────────────────────────────────────────────
def _save_predicted_overlay_png(
    df: pd.DataFrame,
    out_path: Path,
    title: str,
    clip_percentiles: tuple[int, int] = (1, 99),
    bins: int = 30,
) -> None:
    if plt is None:  # pragma: no cover
        print(f"[PLOT] matplotlib not available; skipping – {out_path.name}")
        return
    if df.empty or "bucket_label" not in df or "pred_median" not in df:
        print(f"[PLOT] nothing to plot for {title}")
        return

    buckets = ("Low", "Medium", "High")
    pred_by_bucket = {
        lbl: df.loc[df["bucket_label"] == lbl, "pred_median"].dropna().to_numpy()
        for lbl in buckets
    }
    if sum(len(v) for v in pred_by_bucket.values()) == 0:
        print(f"[PLOT] no pred_median data for {title}")
        return

    all_pred = np.concatenate([v for v in pred_by_bucket.values() if len(v) > 0])
    if all_pred.size >= 10:
        m_lo, m_hi = np.percentile(all_pred, clip_percentiles)
    else:
        m_lo, m_hi = float(np.min(all_pred)), float(np.max(all_pred))
    if not np.isfinite(m_lo) or not np.isfinite(m_hi) or m_lo == m_hi:
        m_lo, m_hi = float(np.min(all_pred)), float(np.max(all_pred) + 1e-9)
    pred_edges = np.linspace(m_lo, m_hi, max(5, bins))

    fig, ax = plt.subplots(1, 1, figsize=(10, 4), constrained_layout=True)
    colours = {"Low": "#E74C3C", "Medium": "#F39C12", "High": "#27AE60"}

    # Weighted densities so each bucket integrates to its fraction of the whole
    total_n = sum(len(v) for v in pred_by_bucket.values()) or 1
    widths = np.diff(pred_edges)
    for lbl in buckets:
        vals = pred_by_bucket[lbl]
        if len(vals):
            counts, _ = np.histogram(vals, bins=pred_edges)
            dens = counts / (total_n * widths)
            y_edges = np.r_[dens, dens[-1]]
            ax.fill_between(pred_edges, y_edges, step="post", alpha=0.30, color=colours.get(lbl))
            ax.step(pred_edges, y_edges, where="post", linewidth=1.8, color=colours.get(lbl), label=lbl)

    ax.set_title("", fontsize=11, fontweight="bold")
    ax.set_xlabel("Predicted Values")
    ax.set_ylabel("Number of Items")
    ax.set_xlim(m_lo, m_hi)
    ax.legend()

    try:
        fig.suptitle(title, fontsize=10)
        fig.savefig(out_path, dpi=150)
        print(f"[PLOT] saved – {out_path.name}")
    finally:
        plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Public API: Score a feature-matrix with supervised models
# ─────────────────────────────────────────────────────────────────────────────
def _expected_feature_names(pipeline, fallback: Iterable[str]) -> List[str]:
    """Extract expected feature names from a fitted sklearn pipeline/estimator."""
    if hasattr(pipeline, "feature_names_in_"):
        return [str(c) for c in pipeline.feature_names_in_]
    named_steps = getattr(pipeline, "named_steps", {})
    if isinstance(named_steps, dict):
        for step in named_steps.values():
            if hasattr(step, "feature_names_in_"):
                return [str(c) for c in step.feature_names_in_]
    return [str(c) for c in fallback]


def _align_features_to_model(X: pd.DataFrame, pipeline) -> pd.DataFrame:
    """Ensure X has the same feature columns (order, presence) expected by the estimator."""
    if not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(X)
    expected = _expected_feature_names(pipeline, X.columns)
    for col in expected:
        if col not in X.columns:
            X[col] = 0.0
    extra = [c for c in X.columns if c not in expected]
    if extra:
        X = X.drop(columns=extra, errors="ignore")
    X = X.reindex(columns=expected)
    for col in X.columns:
        if not np.issubdtype(X[col].dtype, np.number):
            X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0)
    return X


def score_matrix(
    matrix_file: str,
    category: str = "default_model",
    use_z: bool = score_with_z,
    percentile_on: str = "pred",  # retained for compat; ignored unless use_z=False
) -> None:
    """
    Apply trained super-regression models to the feature-matrix at `matrix_file`.

    - Detects whether the file is belt/ring/amulet (jewellery) or armour.
    - For jewellery: loads a single global model per enabled type (xgb/rf/gbr),
      computes predictions, median-ensemble, buckets (via the single chosen strategy),
      writes a branch scoring spreadsheet, and updates JSON with key == category.
    - For armour: does the same per defence combo segment, writing one XLSX
      per segment and updating JSON entries with key == f"{category}_{segment}".

    Bucket method (ALWAYS based on pred_median):
      - If use_z=True (default): thresholds at mean+1*std (Low boundary) and mean+2*std (High boundary).
      - If use_z=False: percentile thresholds at the configured `quantile_splitters`
        (≤ value_at(splitters[0]) → Low), (> value_at(splitters[1]) → High), else Medium.

    NOTE: If percentile_on == "price" is passed with use_z=False, it is ignored with a warning;
          percentile thresholds are always computed on predictions.
    """
    if percentile_on not in ("pred", "price"):
        raise ValueError("percentile_on must be 'pred' or 'price'")

    # Special-case: if caller passed the generic 'Jewel' category, expand to
    # concrete jewel subtypes using `jewel_list` and score each subtype's
    # matrix independently. This avoids any hardcoded subtype names here and
    # works whether the caller expanded categories or not.
    cat_norm = category.lower().replace(" ", "_")
    if cat_norm == "jewel":
        try:
            mpath = Path(matrix_file)
            files_dir = mpath.parent.parent  # .../db/files
            subtypes = [str(j).strip() for j in (jewel_list or []) if str(j).strip()]
            progressed = False
            for jt in subtypes:
                jt_cap = jt.capitalize()
                jt_dir = files_dir / jt_cap
                jt_matrix = jt_dir / f"{jt_cap}_agg_parsed_feature_matrix_model.parquet"
                if jt_matrix.is_file():
                    score_matrix(str(jt_matrix), jt_cap, use_z=use_z, percentile_on=percentile_on)
                    progressed = True
                else:
                    # Try overlay naming fallback (.xlsx not supported here by design)
                    pass
            if progressed:
                return
        except Exception:
            # Fall through to normal handling if expansion fails
            pass

    # Load and clean data
    df = _load_matrix(matrix_file)
    model_dir = Path(poe2trade_root) / "db" / "super_models"
    cat_norm = category.lower().replace(" ", "_")

    # Determine branch
    belt_branch   = _is_belt_branch(matrix_file)
    ring_branch   = _is_ring_branch(matrix_file)
    simple_branch = _is_simple_branch(matrix_file)
    amulet_branch = _is_amulet_branch(matrix_file)

    # Container for stats to merge at end
    all_stats: Dict[str, Any] = {}

    # Jewellery & simple branch: single global model
    if belt_branch or ring_branch or amulet_branch or simple_branch:
        kind = ("belt" if belt_branch else ("ring" if ring_branch else ("amulet" if amulet_branch else cat_norm)))
        seg_df = df.copy()

        # Prepare features: drop price & defence cols
        X_base = seg_df.drop(columns=["price", "ar_norm", "ev_norm", "es_norm"], errors="ignore")
        if X_base.empty:
            raise ValueError(f"No usable features for scoring '{kind}' (segment collapsed to 0 columns).")

        # Collect predictions from each enabled model
        preds_arr: list[np.ndarray] = []
        for mtype in _get_active_model_types():
            pkl_name = f"{cat_norm}_{mtype}_model.pkl"  # jewellery omits segment in filename
            model_path = model_dir / pkl_name
            if not model_path.exists():
                print(f"[WARN] missing model: {pkl_name}")
                continue
            pipeline = pickle.load(model_path.open("rb"))["model_pipeline"]
            X_aligned = _align_features_to_model(X_base.copy(), pipeline)
            if X_aligned.empty:
                print(f"[WARN] aligned feature set empty for model {pkl_name}; skipping.")
                continue
            p = pipeline.predict(X_aligned)
            seg_df[f"pred_{mtype}"] = p
            preds_arr.append(p)

        if not preds_arr:
            print(f"[ERROR] no models to score for {kind}")
            return

        # Median ensemble across model types
        stacked = np.vstack(preds_arr).T
        seg_df["pred_median"] = np.median(stacked, axis=1)
        seg_df["row_index"] = seg_df.index.astype(int)

        # ── Single-strategy cutoffs on predictions ───────────────────────────
        cuts = _compute_pred_cutoffs(seg_df["pred_median"].to_numpy(), use_z=use_z)
        if (not use_z) and percentile_on == "price":
            print("[WARN] percentile_on='price' is deprecated; using prediction percentiles instead.")

        # Label buckets from those cutoffs (mutually exclusive)
        seg_df["bucket_label"] = _assign_buckets_from_cutoffs(seg_df["pred_median"].to_numpy(), cuts)

        # 10–90% actual-price intervals for each bucket (for reference only)
        intervals: Dict[str, List[float | None]] = {}
        for lbl in ("Low", "Medium", "High"):
            vals = seg_df.loc[seg_df["bucket_label"] == lbl, "price"].to_numpy()
            if vals.size >= 2:
                lo, hi = np.percentile(vals, [10, 90])
                intervals[lbl.lower()] = [float(lo), float(hi)]
            else:
                intervals[lbl.lower()] = [None, None]

        # Annotate interval columns on the dataframe
        seg_df["bucket_price_low"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][0])
        seg_df["bucket_price_high"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][1])

        # Output filename: if category already equals kind, don’t duplicate
        prefix = "" if cat_norm == kind else f"{cat_norm}_"
        out_name = f"{prefix}{kind}_scoring.xlsx"
        out_file = model_dir / out_name

        # Save XLSX + JSON sidecar
        seg_df.to_excel(out_file, index=False)
        print(f"[INFO] scoring → {out_file.name}")
        json_file = out_file.with_suffix(".json")
        try:
            seg_df.to_json(json_file, orient="records")
            print(f"[INFO] scoring → {json_file.name}")
        except Exception as exc:
            print(f"[WARN] could not write JSON {json_file.name}: {exc}")

        # Print 3 random examples to console
        _print_random_samples(seg_df, f"{cat_norm}/{kind}", k=3)

        # Plot PNG (per branch)
        png_name = f"{prefix}{kind}_price_dists.png"
        _save_predicted_overlay_png(seg_df, model_dir / png_name, title=f"{cat_norm}/{kind}")

        # Stats key for jewellery MUST be just category (matches ml_super_utils)
        stats_key = cat_norm
        all_stats[stats_key] = {
            "method": cuts["method"],
            "mean": cuts["mean"],
            "std": cuts["std"],
            "t_low": cuts["t_low"],
            "t_high": cuts["t_high"],
            "percentile_splitters": cuts.get("percentile_splitters"),
            "percentile_values": cuts.get("percentile_values"),
            "bucket_intervals": intervals,  # on ACTUAL prices
        }

        _write_stats(all_stats)
        print(f"[INFO] merged stats → {_stats_path.name}")
        return

    # ─── Armour branch: per-segment scoring ─────────────────────────────────
    for seg in _SEGMENTS:
        mask = _segment_mask(df, seg)
        seg_df = df.loc[mask].copy()
        if seg_df.empty:
            print(f"[SCORE] {seg} skipped (no rows)")
            continue

        # Prepare features
        X_base = seg_df.drop(columns=["price"], errors="ignore")
        if X_base.empty:
            print(f"[SCORE] {seg} skipped (no usable features)")
            continue

        # Collect predictions from each enabled model
        preds_arr: list[np.ndarray] = []
        for mtype in _get_active_model_types():
            pkl_name = f"{cat_norm}_{seg}_{mtype}_model.pkl"
            model_path = model_dir / pkl_name
            if not model_path.exists():
                print(f"[WARN] missing model: {pkl_name}")
                continue
            pipeline = pickle.load(model_path.open("rb"))["model_pipeline"]
            X_aligned = _align_features_to_model(X_base.copy(), pipeline)
            if X_aligned.empty:
                print(f"[WARN] aligned feature set empty for model {pkl_name}; skipping.")
                continue
            p = pipeline.predict(X_aligned)
            seg_df[f"pred_{mtype}"] = p
            preds_arr.append(p)

        if not preds_arr:
            print(f"[SCORE] no models for segment {seg}")
            continue

        # Median ensemble
        stacked = np.vstack(preds_arr).T
        seg_df["pred_median"] = np.median(stacked, axis=1)
        seg_df["row_index"] = seg_df.index.astype(int)

        # ── Single-strategy cutoffs on predictions ───────────────────────────
        cuts = _compute_pred_cutoffs(seg_df["pred_median"].to_numpy(), use_z=use_z)
        if (not use_z) and percentile_on == "price":
            print("[WARN] percentile_on='price' is deprecated; using prediction percentiles instead.")

        # Label buckets from those cutoffs
        seg_df["bucket_label"] = _assign_buckets_from_cutoffs(seg_df["pred_median"].to_numpy(), cuts)

        # 10–90% price intervals per bucket
        intervals: Dict[str, List[float | None]] = {}
        for lbl in ("Low", "Medium", "High"):
            vals = seg_df.loc[seg_df["bucket_label"] == lbl, "price"].to_numpy()
            if vals.size >= 2:
                lo, hi = np.percentile(vals, [10, 90])
                intervals[lbl.lower()] = [float(lo), float(hi)]
            else:
                intervals[lbl.lower()] = [None, None]

        # Annotate interval columns
        seg_df["bucket_price_low"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][0])
        seg_df["bucket_price_high"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][1])

        # Save per-segment Excel
        out_name = f"{cat_norm}_{seg}_scoring.xlsx"
        out_file = model_dir / out_name
        seg_df.to_excel(out_file, index=False)
        print(f"[INFO] scoring → {out_file.name}")

        # Save JSON sidecar
        json_file = out_file.with_suffix(".json")
        try:
            seg_df.to_json(json_file, orient="records")
            print(f"[INFO] scoring → {json_file.name}")
        except Exception as exc:
            print(f"[WARN] could not write JSON {json_file.name}: {exc}")

        # Print 3 random examples to console
        _print_random_samples(seg_df, f"{cat_norm}/{seg}", k=3)

        # Save per-segment PNG
        png_name = f"{cat_norm}_{seg}_price_dists.png"
        _save_predicted_overlay_png(seg_df, model_dir / png_name, title=f"{cat_norm}/{seg}")

        # Record stats for this segment (matches ml_super_utils keying)
        all_stats[f"{cat_norm}_{seg}"] = {
            "method": cuts["method"],
            "mean": cuts["mean"],
            "std": cuts["std"],
            "t_low": cuts["t_low"],
            "t_high": cuts["t_high"],
            "percentile_splitters": cuts.get("percentile_splitters"),
            "percentile_values": cuts.get("percentile_values"),
            "bucket_intervals": intervals,  # ACTUAL price ranges
        }

    # Merge all segment stats
    _write_stats(all_stats)
    print(f"[INFO] merged stats → {_stats_path.name}")
