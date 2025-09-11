# File: poe2trade/utils/score_super_utils.py
"""
score_super_utils.py

Apply trained “super” regression models to new feature-matrices and produce
per-segment (or per-branch) scoring spreadsheets. Also updates a JSON file
with summary statistics (mean, std, bucket intervals) for later reference.

This version standardizes all column handling to lowercase (ar_norm/ev_norm/es_norm),
and aligns stats keys with ml_super_utils (jewellery uses key == category; armour uses
key == f"{category}_{segment}").

Additionally, after each scoring artifact is written, it prints a compact console
preview of 3 random scored rows (row_id, price, pred_median, bucket_label, and any
per-model predictions that exist).

UPDATED:
- Buckets are ALWAYS computed from model predictions (pred_median). The `use_z`
  flag selects the thresholding strategy:
    * use_z=True  → z-score thresholds on pred_median  (Low if z <= 1; High if z > 2; else Medium)
    * use_z=False → percentile thresholds on pred_median (Low <= p70; Medium (p70, p90]; High > p90)
  Any previous behavior that bucketed on raw prices is removed. If `percentile_on="price"`
  is passed, it is ignored with a warning and prediction-based percentiles are used.

- Plot layout flipped and clarified:
    Row 1 — normalized histograms of PRED_MEDIAN: Low / Medium / High / Overlay
    Row 2 — normalized histograms of PRICE:       Low / Medium / High / Overlay

- NEW: In addition to XLSX, each scoring output is also saved as JSON
  (sidecar file with the same base name and `.json` extension) for fast GUI loads.
  PNG plots are still saved next to these outputs.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List

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
    # Append any per-model predictions that exist
    cols += [f"pred_{m}" for m in _get_active_model_types() if f"pred_{m}" in df.columns]
    cols = [c for c in cols if c in df.columns]

    samp = df.sample(k, replace=False)  # random each run; reproducible seed not required here
    view = samp.copy()
    # Insert source row index as identifier
    try:
        view.insert(0, "row_id", samp.index)
    except Exception:
        pass

    # Format numbers to 2 decimals for readability
    def _ff(x):
        try:
            return f"{float(x):,.2f}"
        except Exception:
            return x

    print(f"[SAMPLE] {label} — {k} random item(s):")
    print(view[["row_id"] + cols].to_string(index=False, justify="left", formatters={c: _ff for c in cols}))
    print("")  # blank line for readability


# ─────────────────────────────────────────────────────────────────────────────
# Plot helpers
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
            # Shade under the step curve and draw outline
            y_edges = np.r_[dens, dens[-1]]
            ax.fill_between(pred_edges, y_edges, step="post", alpha=0.30, color=colours.get(lbl))
            ax.step(pred_edges, y_edges, where="post", linewidth=1.8, color=colours.get(lbl), label=lbl)

    ax.set_title("", fontsize=11, fontweight="bold")
    ax.set_xlabel("Predicted Values" \
    "")
    ax.set_ylabel("Number of Items")
    ax.set_xlim(m_lo, m_hi)
    ax.legend()

    try:
        fig.suptitle(title, fontsize=10)
        fig.savefig(out_path, dpi=150)
        print(f"[PLOT] saved – {out_path.name}")
    finally:
        plt.close(fig)


def _save_price_distribution_png(
    df: pd.DataFrame,
    out_path: Path,
    title: str,
    clip_percentiles: tuple[int, int] = (1, 99),
    bins: int = 30,
) -> None:
    """
    Create a 2x4 subplot figure:
      Top row: normalized histograms of PRED_MEDIAN (Low / Medium / High / Overlay)
      Bottom row: normalized histograms of PRICE      (Low / Medium / High / Overlay)

    Both rows use shared x-ranges (per row) and density=True so each histogram
    integrates to ~1. Overlay panels redraw all three buckets together.
    """
    if plt is None:  # pragma: no cover
        print(f"[PLOT] matplotlib not available; skipping → {out_path.name}")
        return
    if df.empty or "price" not in df or "bucket_label" not in df or "pred_median" not in df:
        print(f"[PLOT] nothing to plot for {title}")
        return

    buckets = ("Low", "Medium", "High")

    pred_by_bucket = {lbl: df.loc[df["bucket_label"] == lbl, "pred_median"].dropna().to_numpy() for lbl in buckets}
    price_by_bucket = {lbl: df.loc[df["bucket_label"] == lbl, "price"].dropna().to_numpy() for lbl in buckets}

    if sum(len(v) for v in pred_by_bucket.values()) == 0:
        print(f"[PLOT] no pred_median data for {title}")
        return
    if sum(len(v) for v in price_by_bucket.values()) == 0:
        print(f"[PLOT] no price data for {title}")
        return

    # ---- Shared range/bins for PRED_MEDIAN (top row)
    all_pred = np.concatenate([v for v in pred_by_bucket.values() if len(v) > 0])
    if all_pred.size >= 10:
        m_lo, m_hi = np.percentile(all_pred, clip_percentiles)
    else:
        m_lo, m_hi = float(np.min(all_pred)), float(np.max(all_pred))
    if not np.isfinite(m_lo) or not np.isfinite(m_hi) or m_lo == m_hi:
        m_lo, m_hi = float(np.min(all_pred)), float(np.max(all_pred) + 1e-9)
    pred_edges = np.linspace(m_lo, m_hi, max(5, bins))

    # ---- Shared range/bins for PRICE (bottom row)
    all_price = np.concatenate([v for v in price_by_bucket.values() if len(v) > 0])
    if all_price.size >= 10:
        p_lo, p_hi = np.percentile(all_price, clip_percentiles)
    else:
        p_lo, p_hi = float(np.min(all_price)), float(np.max(all_price))
    if not np.isfinite(p_lo) or not np.isfinite(p_hi) or p_lo == p_hi:
        p_lo, p_hi = float(np.min(all_price)), float(np.max(all_price) + 1e-9)
    price_edges = np.linspace(p_lo, p_hi, max(5, bins))

    fig, axes = plt.subplots(2, 4, figsize=(20, 8), constrained_layout=True)

    # ── Row 1: PRED_MEDIAN histograms ───────────────────────────────────────
    for i, lbl in enumerate(buckets):
        ax = axes[0, i]
        vals = pred_by_bucket[lbl]
        if len(vals):
            ax.hist(vals, bins=pred_edges, density=True, alpha=0.75)
        ax.set_title(f"Predicted (pred_median) — {lbl} (n={len(vals)})")
        ax.set_xlabel("Predicted value (pred_median)")
        ax.set_ylabel("Density")
        ax.set_xlim(m_lo, m_hi)

    ax = axes[0, 3]  # overlay (predicted)
    for lbl in buckets:
        vals = pred_by_bucket[lbl]
        if len(vals):
            ax.hist(vals, bins=pred_edges, density=True, alpha=0.5, label=lbl)
    ax.set_title("Overlay — Predicted (pred_median)")
    ax.set_xlabel("Predicted value (pred_median)")
    ax.set_ylabel("Density")
    ax.set_xlim(m_lo, m_hi)
    ax.legend()

    # ── Row 2: PRICE histograms ─────────────────────────────────────────────
    for i, lbl in enumerate(buckets):
        ax = axes[1, i]
        vals = price_by_bucket[lbl]
        if len(vals):
            ax.hist(vals, bins=price_edges, density=True, alpha=0.75)
        ax.set_title(f"Actual Price — {lbl} (n={len(vals)})")
        ax.set_xlabel("Actual price")
        ax.set_ylabel("Density")
        ax.set_xlim(p_lo, p_hi)

    ax = axes[1, 3]  # overlay (price)
    for lbl in buckets:
        vals = price_by_bucket[lbl]
        if len(vals):
            ax.hist(vals, bins=price_edges, density=True, alpha=0.5, label=lbl)
    ax.set_title("Overlay — Actual Price")
    ax.set_xlabel("Actual price")
    ax.set_ylabel("Density")
    ax.set_xlim(p_lo, p_hi)
    ax.legend()

    fig.suptitle(f"{title}\nRow 1: Predicted (pred_median) • Row 2: Actual Price", fontsize=12)
    try:
        fig.savefig(out_path, dpi=150)
        print(f"[PLOT] saved → {out_path.name}")
    finally:
        plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Public API: Score a feature-matrix with supervised models
# ─────────────────────────────────────────────────────────────────────────────
def score_matrix(
    matrix_file: str,
    category: str = "default_model",
    use_z: bool = score_with_z,
    percentile_on: str = "pred",  # kept for backward-compat; only 'pred' is honored
) -> None:
    """
    Apply trained super-regression models to the feature-matrix at `matrix_file`.

    - Detects whether the file is belt/ring/amulet (jewellery) or armour.
    - For jewellery: loads a single global model per enabled type (xgb/rf/gbr),
      computes predictions, median-ensemble, buckets, and price intervals,
      writes a branch scoring spreadsheet, and updates JSON with key == category.
      Also prints 3 random scored rows to console and saves a PNG of pred/price histograms.
    - For armour: does the same per defence combo segment, writing one XLSX
      per segment and updating JSON entries with key == f"{category}_{segment}".
      Also prints 3 random scored rows per segment to console and saves a PNG.

    Bucket method (ALWAYS based on pred_median):
      - If use_z=True (default): z-score of pred_median with thresholds <=1 (Low),
        >2 (High), else Medium.
      - If use_z=False: percentile thresholds on pred_median:
          Low = 0–70th (<= p70), Medium = (p70, p90], High = > p90)

    NOTE: `percentile_on` is retained only for backward compatibility. If set to
    "price", it is ignored with a warning and prediction percentiles are used.
    """
    if percentile_on not in ("pred", "price"):
        raise ValueError("percentile_on must be 'pred' or 'price'")

    # Load and clean data
    df = _load_matrix(matrix_file)
    model_dir = Path(poe2trade_root) / "db" / "super_models"
    cat_norm = category.lower().replace(" ", "_")

    # Determine branch
    belt_branch = _is_belt_branch(matrix_file)
    ring_branch = _is_ring_branch(matrix_file)
    amulet_branch = _is_amulet_branch(matrix_file)

    # Container for stats to merge at end
    all_stats: Dict[str, Any] = {}

    # ─── Jewellery branch: single global model ───────────────────────────────
    if belt_branch or ring_branch or amulet_branch:
        kind = "belt" if belt_branch else "ring" if ring_branch else "amulet"
        seg_df = df.copy()

        # Prepare features: drop price & defence cols
        X = seg_df.drop(columns=["price", "ar_norm", "ev_norm", "es_norm"], errors="ignore")
        # Drop any zero-variance columns
        const = X.columns[X.nunique(dropna=False) <= 1]
        if len(const):
            X = X.drop(columns=const)

        # Collect predictions from each enabled model
        preds_arr: list[np.ndarray] = []
        for mtype in _get_active_model_types():
            # jewellery model filenames omit segment in their name
            pkl_name = f"{cat_norm}_{mtype}_model.pkl"
            model_path = model_dir / pkl_name
            if not model_path.exists():
                print(f"[WARN] missing model: {pkl_name}")
                continue
            pipeline = pickle.load(model_path.open("rb"))["model_pipeline"]
            p = pipeline.predict(X)
            seg_df[f"pred_{mtype}"] = p
            preds_arr.append(p)

        if not preds_arr:
            print(f"[ERROR] no models to score for {kind}")
            return

        # Median ensemble across model types
        stacked = np.vstack(preds_arr).T
        seg_df["pred_median"] = np.median(stacked, axis=1)

        # ── Buckets (ALWAYS based on predictions) ────────────────────────────
        mean_pred = float(np.mean(seg_df["pred_median"]))
        std_pred = float(np.std(seg_df["pred_median"], ddof=1)) or 1e-9

        if use_z:
            z = (seg_df["pred_median"] - mean_pred) / std_pred
            seg_df["bucket_label"] = np.where(z <= 1, "Low", np.where(z > 2, "High", "Medium"))
        else:
            if percentile_on == "price":
                print("[WARN] percentile_on='price' is deprecated; using prediction percentiles instead.")
            qs = list(quantile_splitters or [70, 90])
            qs = qs if len(qs) == 2 else [70, 90]
            p70, p90 = np.percentile(seg_df["pred_median"].to_numpy(), qs)
            seg_df["bucket_label"] = np.where(
                seg_df["pred_median"] <= p70, "Low", np.where(seg_df["pred_median"] > p90, "High", "Medium")
            )

        # 10–90% actual-price intervals for each bucket (for reference only)
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

        # Output filename: if category already equals kind, don’t duplicate
        prefix = "" if cat_norm == kind else f"{cat_norm}_"
        out_name = f"{prefix}{kind}_scoring.xlsx"
        out_file = model_dir / out_name

        # Save XLSX
        seg_df.to_excel(out_file, index=False)
        print(f"[INFO] scoring → {out_file.name}")

        # NEW: Save JSON sidecar (fast path for GUI)
        json_file = out_file.with_suffix(".json")
        try:
            seg_df.to_json(json_file, orient="records")  # force_ascii default ok; GUI reads with pd.read_json
            print(f"[INFO] scoring → {json_file.name}")
        except Exception as exc:
            print(f"[WARN] could not write JSON {json_file.name}: {exc}")

        # Print 3 random examples to console
        _print_random_samples(seg_df, f"{cat_norm}/{kind}", k=3)

        # Plot PNG (per branch)
        png_name = f"{prefix}{kind}_price_dists.png"
        _save_predicted_overlay_png(
            seg_df,
            model_dir / png_name,
            title=f"{cat_norm}/{kind}",
        )

        # Stats key for jewellery MUST be just category (matches ml_super_utils)
        stats_key = cat_norm
        all_stats[stats_key] = {
            "mean": mean_pred,
            "std": std_pred,
            "bucket_intervals": intervals,
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
        X = seg_df.drop(columns=["price"], errors="ignore")
        # Drop defence columns that are constant on this segment
        zero_def = [c for c in ("ar_norm", "ev_norm", "es_norm") if c in X and X[c].nunique(dropna=False) <= 1]
        if zero_def:
            X = X.drop(columns=zero_def)
        # Drop any remaining zero-variance columns
        const = X.columns[X.nunique(dropna=False) <= 1]
        if len(const):
            X = X.drop(columns=const)

        # Collect predictions from each enabled model
        preds_arr: list[np.ndarray] = []
        for mtype in _get_active_model_types():
            pkl_name = f"{cat_norm}_{seg}_{mtype}_model.pkl"
            model_path = model_dir / pkl_name
            if not model_path.exists():
                print(f"[WARN] missing model: {pkl_name}")
                continue
            pipeline = pickle.load(model_path.open("rb"))["model_pipeline"]
            p = pipeline.predict(X)
            seg_df[f"pred_{mtype}"] = p
            preds_arr.append(p)

        if not preds_arr:
            print(f"[SCORE] no models for segment {seg}")
            continue

        # Median ensemble
        stacked = np.vstack(preds_arr).T
        seg_df["pred_median"] = np.median(stacked, axis=1)

        # ── Buckets (ALWAYS based on predictions) ────────────────────────────
        mean_pred = float(np.mean(seg_df["pred_median"]))
        std_pred = float(np.std(seg_df["pred_median"], ddof=1)) or 1e-9

        if use_z:
            z = (seg_df["pred_median"] - mean_pred) / std_pred
            seg_df["bucket_label"] = np.where(z <= 1, "Low", np.where(z > 2, "High", "Medium"))
        else:
            if percentile_on == "price":
                print("[WARN] percentile_on='price' is deprecated; using prediction percentiles instead.")
            qs = list(quantile_splitters or [70, 90])
            qs = qs if len(qs) == 2 else [70, 90]
            p70, p90 = np.percentile(seg_df["pred_median"].to_numpy(), qs)
            seg_df["bucket_label"] = np.where(
                seg_df["pred_median"] <= p70, "Low", np.where(seg_df["pred_median"] > p90, "High", "Medium")
            )

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

        # NEW: Save JSON sidecar (fast path for GUI)
        json_file = out_file.with_suffix(".json")
        try:
            seg_df.to_json(json_file, orient="records")
            print(f"[INFO] scoring → {json_file.name}")
        except Exception as exc:
            print(f"[WARN] could not write JSON {json_file.name}: {exc}")

        # Print 3 random examples to console for this segment
        _print_random_samples(seg_df, f"{cat_norm}/{seg}", k=3)

        # Save per-segment PNG
        png_name = f"{cat_norm}_{seg}_price_dists.png"
        _save_predicted_overlay_png(
            seg_df,
            model_dir / png_name,
            title=f"{cat_norm}/{seg}",
        )

        # Record stats for this segment (matches ml_super_utils keying)
        all_stats[f"{cat_norm}_{seg}"] = {
            "mean": mean_pred,
            "std": std_pred,
            "bucket_intervals": intervals,
        }

    # Merge all segment stats
    _write_stats(all_stats)
    print(f"[INFO] merged stats → {_stats_path.name}")
