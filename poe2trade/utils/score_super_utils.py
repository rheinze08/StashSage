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
import os
import pickle
import sys
import importlib
import hashlib
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, List, Tuple
from uuid import uuid4

import numpy as np
import pandas as pd
from poe2trade.utils.ml_super_utils import ClippedRegressor
from poe2trade.utils.parse_utils import DPS_WEAPON_CATEGORIES

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
def _artifact_category(category: str) -> str:
    """Return the one canonical category key used in scoring artifacts."""
    token = str(category or "").strip().lower().replace(" ", "_")
    return "talisman" if token == "talismans" else token


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
    plus Sceptre/Scepter/Staff/Staves/Wand/Quiver and all DPS weapon categories.
    """
    p = path_str.lower()
    # Build token set dynamically from jewel_list
    try:
        jewels = [str(j).strip().lower() for j in (jewel_list or []) if str(j).strip()]
    except Exception:
        jewels = []
    tokens = ["jewel", "sceptre", "scepter", "staff", "staves", "wand", "quiver", "tablet", "waystone", *DPS_WEAPON_CATEGORIES, *jewels]
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
    column if present, and coerce 'price' to numeric.

    Missing prices are intentionally retained. Runtime stash inference supports
    unpriced items; price is a reference/output field and is never a model
    feature. Training performs its own missing-target filtering.
    """
    df = pd.read_parquet(matrix_file)
    df.columns = [str(c).lower() for c in df.columns]
    df = df.drop(columns=["item"], errors="ignore")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df


def _actual_price_interval(df: pd.DataFrame, bucket_label: str) -> List[float | None]:
    """Return a 10th-90th percentile interval using only known actual prices."""
    vals = pd.to_numeric(
        df.loc[df["bucket_label"] == bucket_label, "price"],
        errors="coerce",
    ).dropna().to_numpy()
    if vals.size < 2:
        return [None, None]
    lo, hi = np.percentile(vals, [10, 90])
    return [float(lo), float(hi)]


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
_ACTIVE_PACKAGE = __name__.split(".", 1)[0]
_COMPAT_PACKAGE_ALIASES = {"poe2trade", "stashsage_serve"}
_last_scoring_model_sources: Dict[str, Dict[str, Dict[str, Any]]] = {}


def clear_last_scoring_model_sources() -> None:
    _last_scoring_model_sources.clear()


def last_scoring_model_sources() -> Dict[str, Dict[str, Dict[str, Any]]]:
    return {
        base_name: {model_type: dict(info) for model_type, info in model_info.items()}
        for base_name, model_info in _last_scoring_model_sources.items()
    }


def _repo_scoring_output_dir() -> Path:
    return Path(poe2trade_root) / "generated" / "super_models"


def _user_scoring_output_dir() -> Path:
    try:
        from poe2trade.app import asset_paths

        return asset_paths.generated_assets_root() / "super_models"
    except Exception:
        if sys.platform == "win32":
            base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
            return base / "StashSage" / "generated" / "super_models"
        return Path.home() / ".StashSage" / "generated" / "super_models"


def _prefer_user_generated_dir() -> bool:
    if getattr(sys, "frozen", False):
        return True
    try:
        return not os.access(Path(poe2trade_root), os.W_OK)
    except OSError:
        return False


def get_scoring_output_dir() -> Path:
    """Return the writable directory for generated scoring artifacts."""
    env_dir = os.environ.get("STASHSAGE_SCORING_OUTPUT_DIR")
    output_dir = Path(env_dir) if env_dir else (
        _user_scoring_output_dir() if _prefer_user_generated_dir() else _repo_scoring_output_dir()
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback_dir = _user_scoring_output_dir()
        if env_dir or output_dir == fallback_dir:
            raise
        output_dir = fallback_dir
        output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _stats_file_path() -> Path:
    return get_scoring_output_dir() / "category_segment_stats.json"


_stats_lock = RLock()


def _temp_sibling(path: Path) -> Path:
    return path.with_name(f"{path.stem}.tmp-{os.getpid()}-{uuid4().hex}{path.suffix}")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _write_price_distribution_plots() -> bool:
    if _env_flag("STASHSAGE_SKIP_PRICE_DISTS", False):
        return False
    return _env_flag("STASHSAGE_EXPORT_PRICE_DISTS", True)


def _compact_scoring_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only runtime/validation fields in scoring sidecars."""
    keep = [
        "row_index",
        "price",
        "pred_median",
        "bucket_label",
        "bucket_price_low",
        "bucket_price_high",
    ]
    keep.extend(c for c in df.columns if str(c).startswith("pred_") and c not in keep)
    cols = [c for c in keep if c in df.columns]
    return df.loc[:, cols].copy()


def _atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _temp_sibling(path)
    try:
        tmp.write_text(text, encoding=encoding)
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _atomic_write_dataframe_json(df: pd.DataFrame, path: Path, *, orient: str = "records") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _temp_sibling(path)
    try:
        df.to_json(tmp, orient=orient)
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _atomic_write_scoring_json(df: pd.DataFrame, path: Path) -> None:
    _atomic_write_dataframe_json(_compact_scoring_dataframe(df), path, orient="records")


def _atomic_write_excel(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _temp_sibling(path)
    try:
        with pd.ExcelWriter(
            tmp,
            engine="xlsxwriter",
            engine_kwargs={
                "options": {
                    "constant_memory": True,
                    "tmpdir": str(path.parent),
                    "use_zip64": True,
                }
            },
        ) as writer:
            df.to_excel(writer, index=False)
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


class _CompatUnpickler(pickle.Unpickler):
    """Load model pickles created under older package/module names."""

    def find_class(self, module: str, name: str):
        package = module.split(".", 1)[0]
        if package in _COMPAT_PACKAGE_ALIASES and package != _ACTIVE_PACKAGE:
            module = module.replace(package, _ACTIVE_PACKAGE, 1)
        if module == f"{_ACTIVE_PACKAGE}.utils.train_utils" and name == "ClippedRegressor":
            return ClippedRegressor
        return super().find_class(module, name)


def _load_model_artifact(model_path: Path) -> Dict[str, Any]:
    with model_path.open("rb") as fh:
        return _CompatUnpickler(fh).load()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _super_model_dirs() -> List[Path]:
    env_dir = os.environ.get("STASHSAGE_SUPER_MODELS_DIR")
    if env_dir:
        return [Path(env_dir)]

    try:
        asset_paths = importlib.import_module(f"{_ACTIVE_PACKAGE}.app.asset_paths")
        return list(asset_paths.asset_search_dirs("super_models"))
    except Exception:
        dirs: List[Path] = []
        generated_dir = _repo_scoring_output_dir()
        if generated_dir.is_dir():
            dirs.append(generated_dir)
        dirs.append(Path(poe2trade_root) / "db" / "super_models")
        return dirs


def _load_first_model_artifact(base_name: str, mtype: str) -> Tuple[Dict[str, Any], Path] | Tuple[None, None]:
    for model_dir in _super_model_dirs():
        model_path = model_dir / f"{base_name}_{mtype}_model.pkl"
        if not model_path.exists():
            continue
        try:
            artifact = _load_model_artifact(model_path)
            if not isinstance(artifact, dict) or "model_pipeline" not in artifact:
                raise ValueError("model artifact must be a dict with 'model_pipeline'")
            stat = model_path.stat()
            _last_scoring_model_sources.setdefault(base_name, {})[mtype] = {
                "path": str(model_path.resolve()),
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "sha256": _file_sha256(model_path),
            }
            return artifact, model_path
        except Exception as exc:
            print(f"[WARN] unusable model {model_path.name} in {model_dir}: {exc}")
            continue
    return None, None


def _write_stats(new_stats: Dict[str, Any]) -> Path:
    """
    Merge `new_stats` into the existing stats JSON on disk (or create it
    if missing). Uses a lock to prevent concurrent writes.
    """
    with _stats_lock:
        stats_path = _stats_file_path()
        if stats_path.exists():
            try:
                current = json.loads(stats_path.read_text())
            except (json.JSONDecodeError, OSError):
                current = {}
        else:
            current = {}

        if any(str(key).startswith("waystone_t") for key in new_stats):
            current.pop("waystone", None)
        current.update(new_stats)
        _atomic_write_text(stats_path, json.dumps(current, indent=2))
        return stats_path


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
def _prediction_bucket_intervals(cuts: Dict[str, Any]) -> Dict[str, List[float | None]]:
    """Return Low/Medium/High intervals in prediction-value space."""
    method = cuts.get("method", "percentile")
    if method == "z":
        low_hi = cuts.get("t_low")
        high_lo = cuts.get("t_high")
    else:
        pv = cuts.get("percentile_values")
        low_hi = pv[0] if isinstance(pv, (list, tuple)) and len(pv) > 0 else None
        high_lo = pv[1] if isinstance(pv, (list, tuple)) and len(pv) > 1 else None

    def _num(v: Any) -> float | None:
        try:
            f = float(v)
            return f if np.isfinite(f) else None
        except Exception:
            return None

    low_hi_f = _num(low_hi)
    high_lo_f = _num(high_lo)
    return {
        "low": [None, low_hi_f],
        "medium": [low_hi_f, high_lo_f],
        "high": [high_lo_f, None],
    }


def _build_distribution_profile(
    df: pd.DataFrame,
    *,
    bins: int = 30,
    clip_percentiles: tuple[int, int] = (1, 99),
) -> Dict[str, Any] | None:
    """Build a compact, deterministic histogram profile for runtime rendering."""
    if df.empty or "bucket_label" not in df or "pred_median" not in df:
        return None

    buckets = ("Low", "Medium", "High")
    pred_by_bucket = {
        lbl: pd.to_numeric(
            df.loc[df["bucket_label"] == lbl, "pred_median"],
            errors="coerce",
        ).dropna().to_numpy()
        for lbl in buckets
    }
    if sum(len(v) for v in pred_by_bucket.values()) == 0:
        return None

    all_pred = np.concatenate([v for v in pred_by_bucket.values() if len(v) > 0])
    if all_pred.size >= 10:
        m_lo, m_hi = np.percentile(all_pred, clip_percentiles)
    else:
        m_lo, m_hi = float(np.min(all_pred)), float(np.max(all_pred))
    if not np.isfinite(m_lo) or not np.isfinite(m_hi) or m_lo == m_hi:
        m_lo, m_hi = float(np.min(all_pred)), float(np.max(all_pred) + 1e-9)

    edges = np.linspace(float(m_lo), float(m_hi), max(5, bins))
    counts: Dict[str, List[int]] = {}
    totals: Dict[str, int] = {}
    visible_totals: Dict[str, int] = {}
    for lbl in buckets:
        vals = pred_by_bucket[lbl]
        totals[lbl.lower()] = int(len(vals))
        if len(vals):
            bucket_counts, _ = np.histogram(vals, bins=edges)
            counts[lbl.lower()] = [int(v) for v in bucket_counts.tolist()]
            visible_totals[lbl.lower()] = int(bucket_counts.sum())
        else:
            counts[lbl.lower()] = [0 for _ in range(len(edges) - 1)]
            visible_totals[lbl.lower()] = 0

    return {
        "version": 1,
        "value_column": "pred_median",
        "bucket_column": "bucket_label",
        "bins": int(bins),
        "clip_percentiles": [int(clip_percentiles[0]), int(clip_percentiles[1])],
        "x_min": float(edges[0]),
        "x_max": float(edges[-1]),
        "bin_edges": [float(v) for v in edges.tolist()],
        "bucket_counts": counts,
        "bucket_totals": totals,
        "visible_bucket_totals": visible_totals,
        "total": int(sum(totals.values())),
        "visible_total": int(sum(visible_totals.values())),
    }


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

    print(f"[SAMPLE] {label} - {k} random item(s):")
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
        print(f"[PLOT] matplotlib not available; skipping - {out_path.name}")
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
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = _temp_sibling(out_path)
        try:
            fig.savefig(tmp, dpi=150)
            os.replace(tmp, out_path)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
        print(f"[PLOT] saved - {out_path.name}")
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
    *,
    model_segment: str | None = None,
) -> List[Path]:
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

    clear_last_scoring_model_sources()

    # Special-case: if caller passed the generic 'Jewel' category, expand to
    # concrete jewel subtypes using `jewel_list` and score each subtype's
    # matrix independently. This avoids any hardcoded subtype names here and
    # works whether the caller expanded categories or not.
    cat_norm = _artifact_category(category)
    artifact_stem = cat_norm if model_segment is None else f"{cat_norm}_{model_segment}"
    written: List[Path] = []
    if cat_norm == "jewel":
        try:
            mpath = Path(matrix_file)
            files_dir = mpath.parent.parent  # .../db/files
            subtypes = [str(j).strip() for j in (jewel_list or []) if str(j).strip()]
            progressed = False
            for jt in subtypes:
                jt_cap = jt
                jt_dir = files_dir / jt_cap
                jt_matrix = jt_dir / f"{jt_cap}_agg_parsed_feature_matrix_model.parquet"
                if jt_matrix.is_file():
                    written.extend(score_matrix(str(jt_matrix), jt_cap, use_z=use_z, percentile_on=percentile_on))
                    progressed = True
                else:
                    # Try overlay naming fallback (.xlsx not supported here by design)
                    pass
            if progressed:
                return written
        except Exception:
            # Fall through to normal handling if expansion fails
            pass

    # Load and clean data
    df = _load_matrix(matrix_file)
    output_dir = get_scoring_output_dir()
    cat_norm = _artifact_category(category)
    if cat_norm == "waystone" and model_segment is not None:
        for legacy_name in (
            "waystone_scoring.json",
            "waystone_scoring.xlsx",
            "waystone_price_dists.png",
        ):
            try:
                (output_dir / legacy_name).unlink(missing_ok=True)
            except OSError:
                pass

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
            pkl_name = f"{artifact_stem}_{mtype}_model.pkl"
            artifact, model_path = _load_first_model_artifact(artifact_stem, mtype)
            if artifact is None or model_path is None:
                print(f"[WARN] missing model: {pkl_name}")
                continue
            pipeline = artifact["model_pipeline"]
            X_aligned = _align_features_to_model(X_base.copy(), pipeline)
            if X_aligned.empty:
                print(f"[WARN] aligned feature set empty for model {pkl_name}; skipping.")
                continue
            p = pipeline.predict(X_aligned)
            seg_df[f"pred_{mtype}"] = p
            preds_arr.append(p)

        if not preds_arr:
            print(f"[ERROR] no models to score for {kind}")
            return written

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
            intervals[lbl.lower()] = _actual_price_interval(seg_df, lbl)

        # Annotate interval columns on the dataframe
        seg_df["bucket_price_low"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][0])
        seg_df["bucket_price_high"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][1])

        # Output filename: if category already equals kind, don’t duplicate
        out_name = f"{artifact_stem}_scoring.xlsx"
        out_file = output_dir / out_name

        # Save XLSX + JSON sidecar
        _atomic_write_excel(_compact_scoring_dataframe(seg_df), out_file)
        written.append(out_file)
        print(f"[INFO] scoring -> {out_file.name}")
        json_file = out_file.with_suffix(".json")
        try:
            _atomic_write_scoring_json(seg_df, json_file)
            written.append(json_file)
            print(f"[INFO] scoring -> {json_file.name}")
        except Exception as exc:
            print(f"[WARN] could not write JSON {json_file.name}: {exc}")

        # Print 3 random examples to console
        _print_random_samples(seg_df, f"{cat_norm}/{kind}", k=3)

        # Plot PNG (per branch) only when explicitly requested. Runtime charts
        # prefer distribution_profile in category_segment_stats.json.
        if _write_price_distribution_plots():
            png_name = f"{artifact_stem}_price_dists.png"
            png_path = output_dir / png_name
            _save_predicted_overlay_png(seg_df, png_path, title=f"{cat_norm}/{kind}")
            if png_path.exists():
                written.append(png_path)

        # Stats key for jewellery MUST be just category (matches ml_super_utils)
        stats_key = artifact_stem
        all_stats[stats_key] = {
            "method": cuts["method"],
            "mean": cuts["mean"],
            "std": cuts["std"],
            "t_low": cuts["t_low"],
            "t_high": cuts["t_high"],
            "percentile_splitters": cuts.get("percentile_splitters"),
            "percentile_values": cuts.get("percentile_values"),
            "bucket_intervals": intervals,  # on ACTUAL prices
            "prediction_bucket_intervals": _prediction_bucket_intervals(cuts),
            "distribution_profile": _build_distribution_profile(seg_df),
        }

        stats_path = _write_stats(all_stats)
        written.append(stats_path)
        print(f"[INFO] merged stats -> {stats_path.name}")
        return written

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
            artifact, model_path = _load_first_model_artifact(f"{cat_norm}_{seg}", mtype)
            if artifact is None or model_path is None:
                print(f"[WARN] missing model: {pkl_name}")
                continue
            pipeline = artifact["model_pipeline"]
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
            intervals[lbl.lower()] = _actual_price_interval(seg_df, lbl)

        # Annotate interval columns
        seg_df["bucket_price_low"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][0])
        seg_df["bucket_price_high"] = seg_df["bucket_label"].map(lambda b: intervals[b.lower()][1])

        # Save per-segment Excel
        out_name = f"{cat_norm}_{seg}_scoring.xlsx"
        out_file = output_dir / out_name
        _atomic_write_excel(_compact_scoring_dataframe(seg_df), out_file)
        written.append(out_file)
        print(f"[INFO] scoring -> {out_file.name}")

        # Save JSON sidecar
        json_file = out_file.with_suffix(".json")
        try:
            _atomic_write_scoring_json(seg_df, json_file)
            written.append(json_file)
            print(f"[INFO] scoring -> {json_file.name}")
        except Exception as exc:
            print(f"[WARN] could not write JSON {json_file.name}: {exc}")

        # Print 3 random examples to console
        _print_random_samples(seg_df, f"{cat_norm}/{seg}", k=3)

        # Save per-segment PNG only when explicitly requested. Runtime charts
        # prefer distribution_profile in category_segment_stats.json.
        if _write_price_distribution_plots():
            png_name = f"{cat_norm}_{seg}_price_dists.png"
            png_path = output_dir / png_name
            _save_predicted_overlay_png(seg_df, png_path, title=f"{cat_norm}/{seg}")
            if png_path.exists():
                written.append(png_path)

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
            "prediction_bucket_intervals": _prediction_bucket_intervals(cuts),
            "distribution_profile": _build_distribution_profile(seg_df),
        }

    # Merge all segment stats
    stats_path = _write_stats(all_stats)
    written.append(stats_path)
    print(f"[INFO] merged stats -> {stats_path.name}")
    return written
