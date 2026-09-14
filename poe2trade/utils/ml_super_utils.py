# File: poe2trade/utils/ml_super_utils.py
# · v25 — add per-file in-process caching with mtime invalidation (2025-09-11)
# · v24 — robust to lowercase/underscore standardization (2025-07-06)

from __future__ import annotations

import json
import pickle
import importlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from poe2trade.utils.parse_utils import (
    SUPPORTED_WAYSTONE_SEGMENTS,
    waystone_segment_from_frame,
)

# NOTE: sklearn is intentionally NOT imported at module level. Importing it adds
# ~1 s to cold startup, and this module is pulled in transitively by the GUI
# before any prediction is requested. The actual estimators are restored from
# pickles at first inference (which loads sklearn on demand); we only need the
# Pipeline symbol for type hints, so it is referenced lazily/as a string.

from poe2trade import (
    poe2trade_root,
    shap_flag,
    train_super_xgb,
    train_super_rf,
    train_super_gbr,
)
from poe2trade.utils.pricing_conversions import load_model_conversions, read_conversion_manifest

# ──────────────────────────────────────────────────────────────
# Debug logging
# ──────────────────────────────────────────────────────────────
# Per-prediction [DEBUG] tracing is verbose and writes synchronously to the
# console (slow on Windows, and pointless in the --noconsole frozen build).
# It is OFF by default; set STASHSAGE_DEBUG=1 to re-enable for diagnostics.
import os as _os
_DEBUG = _os.environ.get("STASHSAGE_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")
_ACTIVE_PACKAGE = __name__.split(".", 1)[0]
_COMPAT_PACKAGE_ALIASES = {"poe2trade", "stashsage_serve"}
log = logging.getLogger(__name__)


def _dbg(*args: Any, **kwargs: Any) -> None:
    if _DEBUG:
        print(*args, **kwargs)


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
        print("[INFO] shap_flag True but shap package not installed - continuing without SHAP")

# ── WHICH MODELS TO LOAD ──────────────────────────────────────
# Only load the model types whose training flags are enabled.
_active_models = [
    m for m, flag in {
        "xgb": train_super_xgb,
        "rf":  train_super_rf,
        "gbr": train_super_gbr,
    }.items() if flag
]
_dbg(f"[DEBUG] Active model types for inference: {_active_models}")

# Match poe2trade.app.gui.constants.BUCKET_COLOURS. Keep this local to the
# shared ML utility so serve/API exports do not need to import GUI modules.
BUCKET_COLOURS = {
    "low": "#B94A48",
    "medium": "#B9770E",
    "high": "#21885A",
}


def bucket_display_for_label(label: Any) -> Optional[Dict[str, Any]]:
    """Return GUI-matched display metadata for a Low/Medium/High bucket."""
    if not isinstance(label, str):
        return None
    bucket = label.strip().capitalize()
    if not bucket:
        return None
    color_hex = BUCKET_COLOURS.get(bucket.lower())
    if not color_hex:
        return None
    return {
        "label": bucket,
        "color_hex": color_hex,
        "color_swatch": "[#]",
        "color_square": {
            "shape": "square",
            "color_hex": color_hex,
            "css": (
                "display:inline-block;width:12px;height:12px;"
                f"background-color:{color_hex};"
            ),
        },
    }


def _prediction_display(
    *,
    model_type: str,
    prediction: float,
    bucket_info: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    label = bucket_info.get("bucket") if isinstance(bucket_info, dict) else None
    display = bucket_display_for_label(label)
    out: Dict[str, Any] = {
        "model": model_type,
        "prediction": float(prediction),
        "bucket": label,
        "bucket_low": bucket_info.get("bucket_low") if isinstance(bucket_info, dict) else None,
        "bucket_high": bucket_info.get("bucket_high") if isinstance(bucket_info, dict) else None,
    }
    if isinstance(display, dict):
        out.update(display)
    return out

# ── BUCKET STATS LOADER ───────────────────────────────────────
# Loads precomputed bucket intervals & stats for each category_segment.
_BUNDLED_MODEL_DIR = Path(poe2trade_root) / "db" / "super_models"
_bucket_cache: Optional[Dict[str, Any]] = None
_bucket_cache_path: Optional[Path] = None
_SCORING_COMPACTED = False


def _generated_super_models_dir() -> Path:
    try:
        asset_paths = importlib.import_module(f"{_ACTIVE_PACKAGE}.app.asset_paths")
        return asset_paths.generated_assets_root() / "super_models"
    except Exception:
        return Path(poe2trade_root) / "generated" / "super_models"


def _super_model_dirs() -> List[Path]:
    # Explicit env override stays highest priority: the db pipeline and tests
    # point this at a specific directory and must not pick up a user's set.
    env_dir = _os.environ.get("STASHSAGE_SUPER_MODELS_DIR")
    if env_dir:
        return [Path(env_dir)]

    try:
        asset_paths = importlib.import_module(f"{_ACTIVE_PACKAGE}.app.asset_paths")
        # The selected league is prepended by asset_search_dirs itself, so every
        # consumer of db/super_models follows the picker, not just this one.
        return list(asset_paths.asset_search_dirs("super_models"))
    except Exception:
        dirs: List[Path] = []
        generated_dir = _generated_super_models_dir()
        if generated_dir.is_dir():
            dirs.append(generated_dir)
        dirs.append(_BUNDLED_MODEL_DIR)
        return dirs


def _stats_path() -> Path:
    for model_dir in _super_model_dirs():
        candidate = model_dir / "category_segment_stats.json"
        if candidate.is_file():
            return candidate
    return _BUNDLED_MODEL_DIR / "category_segment_stats.json"


def _model_dir_for(base_name: str, model_types: List[str]) -> Path:
    for model_dir in _super_model_dirs():
        if any((model_dir / f"{base_name}_{mtype}_model.pkl").is_file() for mtype in model_types):
            return model_dir
    return _super_model_dirs()[0]


def clear_runtime_caches() -> None:
    """Clear loaded model/stat caches after model assets are refreshed."""
    global _bucket_cache, _bucket_cache_path, _SCORING_COMPACTED
    _bucket_cache = None
    _bucket_cache_path = None
    _SCORING_COMPACTED = False
    _model_cache.clear()
    _model_mtime.clear()
    _feature_alignment_cache.clear()


def _filter_scoring_row(row: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Return a view of the row containing only index/pred/bucket columns."""
    keep: Dict[str, Any] = {}
    has_pred = False

    for key, value in row.items():
        key_norm = str(key).lower()
        if key_norm == "row_index":
            keep[key] = value
            continue
        if key_norm.startswith("pred_"):
            keep[key] = value
            has_pred = True
            continue
        if key_norm.startswith("bucket_"):
            keep[key] = value

    if not has_pred:
        return row, False

    if "bucket_label" in row and "bucket_label" not in keep:
        keep["bucket_label"] = row["bucket_label"]
    if "row_index" in row and "row_index" not in keep:
        keep["row_index"] = row["row_index"]

    return keep, keep != row


def _compact_scoring_json(json_path: Path) -> bool:
    """Strip mod/value columns from a scoring JSON in-place."""
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        _dbg(f"[DEBUG] Skipping {json_path.name}: load failed ({exc!r})")
        return False

    if not isinstance(payload, list) or not payload:
        return False

    filtered_rows: List[Dict[str, Any]] = []
    changed = False
    valid_rows = 0

    for row in payload:
        if not isinstance(row, dict):
            return False
        filtered, row_changed = _filter_scoring_row(row)
        filtered_rows.append(filtered)
        changed = changed or row_changed

        if isinstance(filtered, dict):
            has_pred = any(str(k).lower().startswith("pred_") for k in filtered)
            if has_pred and "row_index" in filtered:
                valid_rows += 1

    if not changed or valid_rows == 0:
        return False

    tmp_path = json_path.with_suffix(json_path.suffix + ".tmp")
    try:
        tmp_path.write_text(json.dumps(filtered_rows, separators=(",", ":")), encoding="utf-8")
        tmp_path.replace(json_path)
        return True
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _maybe_compact_scoring_jsons() -> None:
    """Retain compatibility with callers without mutating packaged assets.

    Scoring sidecars are compacted by the scoring/release pipeline. Rewriting
    either downloaded or bundled copies at runtime invalidates checksums and
    leaves source/deployment checkouts dirty, which can block later updates.
    """
    global _SCORING_COMPACTED
    if _SCORING_COMPACTED:
        return
    _SCORING_COMPACTED = True

def _load_bucket_stats() -> Dict[str, Any]:
    """Memoized JSON loader for bucket stats."""
    global _bucket_cache, _bucket_cache_path
    stats_path = _stats_path()
    if _bucket_cache is None or _bucket_cache_path != stats_path:
        _maybe_compact_scoring_jsons()
        _dbg(f"[DEBUG] Loading bucket stats from {stats_path}")
        if stats_path and stats_path.is_file():
            try:
                _bucket_cache = json.loads(stats_path.read_text())
                _bucket_cache_path = stats_path
                _dbg(f"[DEBUG] Loaded bucket stats for {len(_bucket_cache)} category-segment keys")
            except Exception as e:
                print(f"[ERROR] Failed to parse {stats_path}: {e!r}")
                _bucket_cache = {}
        else:
            _dbg(f"[DEBUG] Stats file not found at {stats_path}, initializing empty cache")
            _bucket_cache = {}
    else:
        _dbg("[DEBUG] Using cached bucket stats")
    return _bucket_cache

def _bucketise(cat_seg_key: str, median_val: float, *, stats_data=None) -> Optional[Dict[str, Any]]:
    """
    Given a category_segment key and a predicted median value, select which
    bucket (Low/Medium/High) it falls into based on precomputed intervals.
    Returns a dict with bucket, bucket_low, bucket_high, and z-score.
    """
    _dbg(f"[DEBUG] Bucketising for key '{cat_seg_key}' with median {median_val:.5f}")
    stats = (_load_bucket_stats() if stats_data is None else stats_data).get(cat_seg_key)
    if not stats:
        _dbg(f"[DEBUG] No stats entry for '{cat_seg_key}', skipping bucketise")
        return None

    intervals: Dict[str, List[Optional[float]]] = stats.get("bucket_intervals", {})
    pred_intervals: Dict[str, List[Optional[float]]] = stats.get("prediction_bucket_intervals", {})
    if not pred_intervals:
        method = stats.get("method", "percentile")
        if method == "z":
            pred_intervals = {
                "low": [None, stats.get("t_low")],
                "medium": [stats.get("t_low"), stats.get("t_high")],
                "high": [stats.get("t_high"), None],
            }
        else:
            pv = stats.get("percentile_values")
            if isinstance(pv, (list, tuple)) and len(pv) >= 2:
                pred_intervals = {
                    "low": [None, pv[0]],
                    "medium": [pv[0], pv[1]],
                    "high": [pv[1], None],
                }

    bucket = None
    bucket_low = None
    bucket_high = None

    # 1) Classify by prediction-value cutoffs.
    for name, pair in pred_intervals.items():
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        lo, hi = pair
        lo_ok = lo is None or median_val >= float(lo)
        hi_ok = hi is None or median_val <= float(hi)
        if lo_ok and hi_ok:
            bucket = name.capitalize()
            break

    # 2) If none matched, classify as below Low or above High, else Medium.
    if bucket is None:
        low_lo, low_hi   = pred_intervals.get("low",    [None, None])
        high_lo, high_hi = pred_intervals.get("high",   [None, None])
        if low_hi is not None and median_val <= low_hi:
            bucket = "Low"
        elif high_lo is not None and median_val >= high_lo:
            bucket = "High"
        else:
            bucket = "Medium"

    display_pair = intervals.get(bucket.lower(), [None, None]) if bucket else [None, None]
    if not isinstance(display_pair, (list, tuple)) or len(display_pair) != 2:
        display_pair = pred_intervals.get(bucket.lower(), [None, None]) if bucket else [None, None]
    bucket_low, bucket_high = display_pair

    _dbg(f"[DEBUG] Assigned bucket '{bucket}' with interval [{bucket_low}, {bucket_high}]")

    # 3) Compute z-score relative to stats.mean/std to gauge extremeness
    mean = stats.get("mean", 0.0)
    std  = stats.get("std", 0.0) or 1e-9
    z    = (median_val - mean) / std

    return {
        "z":           z,
        "bucket":      bucket,
        "bucket_low":  bucket_low,
        "bucket_high": bucket_high,
        "method":      stats.get("method"),
        "percentile_splitters": stats.get("percentile_splitters"),
        "percentile_values":    stats.get("percentile_values"),
        "bucket_intervals":     intervals,
        "prediction_bucket_intervals": pred_intervals,
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
_model_cache: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
_model_mtime: Dict[Tuple[str, str, str], float] = {}
_feature_alignment_cache: Dict[
    Tuple[Tuple[str, ...], Tuple[str, ...]],
    Tuple[List[str], List[str]],
] = {}

class ClippedRegressor:
    """Runtime shim for models pickled with train_utils.ClippedRegressor."""

    _estimator_type = "regressor"

    def fit(self, X, y=None):
        raise RuntimeError("ClippedRegressor runtime shim only supports prediction")

    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        return {
            "base_estimator": getattr(self, "base_estimator", None),
            "clip_q": getattr(self, "clip_q", 0.01),
            "margin": getattr(self, "margin", 0.05),
            "log_target": getattr(self, "log_target", False),
        }

    def set_params(self, **params: Any):
        for key, value in params.items():
            setattr(self, key, value)
        return self

    def __sklearn_is_fitted__(self) -> bool:
        return hasattr(self, "base_estimator_")

    def __sklearn_tags__(self):
        from sklearn.utils import RegressorTags, Tags, TargetTags

        return Tags(
            estimator_type="regressor",
            target_tags=TargetTags(required=True),
            regressor_tags=RegressorTags(),
        )

    def predict(self, X):
        pred = self.base_estimator_.predict(X)
        lo = getattr(self, "_lo_", None)
        hi = getattr(self, "_hi_", None)
        if lo is not None and hi is not None:
            pred = np.clip(pred, lo, hi)

        # Invert the log transform back to original (exalt) units when the model
        # was trained on log1p(price). Matches train_utils.ClippedRegressor.predict.
        if getattr(self, "_log_target_", False):
            pred = np.expm1(pred)

        enforce_nonneg = getattr(self, "_non_negative_target_", None)
        if enforce_nonneg is None:
            target_min = getattr(self, "_target_min_", None)
            if target_min is not None:
                enforce_nonneg = target_min >= 0.0
            elif hi is not None:
                enforce_nonneg = hi >= 0.0
            else:
                enforce_nonneg = False

        if enforce_nonneg:
            pred = np.maximum(pred, 0.0)
        return pred

    def __setstate__(self, state):
        self.__dict__.update(state)
        if "_log_target_" not in state:
            self._log_target_ = bool(self.__dict__.get("log_target", False))
        if "_non_negative_target_" not in state:
            target_min = self.__dict__.get("_target_min_", None)
            if target_min is not None:
                self._non_negative_target_ = target_min >= 0.0
            else:
                hi = self.__dict__.get("_hi_", None)
                self._non_negative_target_ = hi is not None and hi >= 0.0


class _CompatUnpickler(pickle.Unpickler):
    """Load pickles created under either downstream package name."""

    def find_class(self, module: str, name: str):
        package = module.split(".", 1)[0]
        if package in _COMPAT_PACKAGE_ALIASES and package != _ACTIVE_PACKAGE:
            module = module.replace(package, _ACTIVE_PACKAGE, 1)
        if module == f"{_ACTIVE_PACKAGE}.utils.train_utils" and name == "ClippedRegressor":
            return ClippedRegressor
        return super().find_class(module, name)


def _compat_load(file_obj):
    return _CompatUnpickler(file_obj).load()


def _load_model(model_dir: Path, base_name: str, mtype: str) -> Optional[Dict[str, Any]]:
    """
    Load and cache '{base_name}_{mtype}_model.pkl' with mtime-based invalidation.
    If the file hasn't changed since last load, reuse the cached artifact.
    """
    p = model_dir / f"{base_name}_{mtype}_model.pkl"
    if not p.is_file():
        _dbg(f"[DEBUG] {mtype} model not found at {p}")
        return None

    try:
        key = (str(p.resolve()), base_name, mtype)
        mt  = p.stat().st_mtime
        art = _model_cache.get(key)
        if art is not None and _model_mtime.get(key) == mt:
            # cached and fresh
            return art

        # (re)load
        with p.open("rb") as fh:
            art = _compat_load(fh)
        if not isinstance(art, dict) or "model_pipeline" not in art:
            raise ValueError("model artifact must be a dict with 'model_pipeline'")
        _model_cache[key] = art
        _model_mtime[key] = mt
        _dbg(f"[DEBUG] Loaded {mtype} model '{p.name}' into cache")
        return art
    except Exception as exc:
        log.warning("Skipping unusable supervised model %s: %s", p, exc)
        _dbg(f"[DEBUG] Failed to load {p}: {exc!r}")
        return None


def model_feature_columns(category: str, segment: str | None) -> set[str]:
    """Return the union of feature columns used by installed active models."""
    category_n = _norm_token(category) or "default_model"
    aliases = {
        "scepter": "sceptre", "foci": "focus", "shields": "shield",
        "bucklers": "buckler", "helmets": "helmet", "body_armours": "body_armour",
        "jewels": "jewel", "wands": "wand", "staves": "staff", "staffs": "staff",
        "quivers": "quiver", "tablets": "tablet", "waystones": "waystone", "bows": "bow", "crossbows": "crossbow",
        "one_hand_maces": "mace_one_hand_mace", "one_handed_maces": "mace_one_hand_mace",
        "two_hand_maces": "mace_two_hand_mace", "two_handed_maces": "mace_two_hand_mace",
        "quarterstaves": "quarterstaff", "spears": "spear", "talismans": "talisman", "rings": "ring", "amulets": "amulet",
        "belts": "belt",
    }
    category_n = aliases.get(category_n, category_n)
    segment_n = _norm_token(segment) if segment is not None else None
    base_name = category_n if segment_n is None else f"{category_n}_{segment_n}"
    columns: set[str] = set()
    for mtype in _active_models:
        for model_dir in _super_model_dirs():
            art = _load_model(model_dir, base_name, mtype)
            if art is not None:
                columns.update(str(col).lower() for col in art.get("feature_cols", ()))
                break
    return columns

# ── MAIN INFERENCE ENTRYPOINT ─────────────────────────────────
def _alignment_diagnostics(
    input_cols: Tuple[str, ...],
    model_cols: Tuple[str, ...],
) -> Tuple[List[str], List[str]]:
    """Return cached missing/extra feature names for an input/model signature."""
    key = (input_cols, model_cols)
    cached = _feature_alignment_cache.get(key)
    if cached is not None:
        return cached

    input_set = set(input_cols)
    model_set = set(model_cols)
    missing = [c for c in model_cols if c not in input_set]
    extra = [c for c in input_cols if c not in model_set]
    cached = (missing, extra)
    _feature_alignment_cache[key] = cached
    return cached


def call_ml(
    category: str,
    segment: str,
    X: pd.DataFrame,
    *,
    model_dirs: Optional[List[Path]] = None,
) -> Dict[str, Any] | None:
    """
    Load each active model for the given category & segment, run predictions,
    aggregate results, bucketise the median, and return a summary dict.
    """
    # normalize inputs and lower-case input columns (robust to standardization)
    _dbg(f"[DEBUG] call_ml_super: category={category!r}, segment={segment!r}")
    category_n = _norm_token(category)
    # normalize common aliases
    if category_n in ("scepter",):
        category_n = "sceptre"
    # plural → singular normalization for robustness
    if category_n == "foci":
        category_n = "focus"
    if category_n == "shields":
        category_n = "shield"
    if category_n == "bucklers":
        category_n = "buckler"
    if category_n == "helmets":
        category_n = "helmet"
    if category_n == "body_armours":
        category_n = "body_armour"
    if category_n == "jewels":
        category_n = "jewel"
    if category_n == "wands":
        category_n = "wand"
    if category_n in ("staves", "staffs"):
        category_n = "staff"
    if category_n == "quivers":
        category_n = "quiver"
    if category_n == "tablets":
        category_n = "tablet"
    if category_n == "waystones":
        category_n = "waystone"
    if category_n == "bows":
        category_n = "bow"
    if category_n == "crossbows":
        category_n = "crossbow"
    if category_n in ("one_hand_maces", "one_handed_maces"):
        category_n = "mace_one_hand_mace"
    if category_n in ("two_hand_maces", "two_handed_maces"):
        category_n = "mace_two_hand_mace"
    if category_n == "quarterstaves":
        category_n = "quarterstaff"
    if category_n == "spears":
        category_n = "spear"
    if category_n == "talismans":
        category_n = "talisman"
    if category_n == "rings":
        category_n = "ring"
    if category_n == "amulets":
        category_n = "amulet"
    if category_n == "belts":
        category_n = "belt"
    segment_n  = _norm_token(segment) if segment is not None else None
    if category_n == "waystone":
        segment_n = segment_n or waystone_segment_from_frame(X)
        if segment_n not in SUPPORTED_WAYSTONE_SEGMENTS:
            _dbg("[DEBUG] call_ml_super: unsupported or missing waystone tier")
            return None
    _dbg(f"[DEBUG] call_ml_super: normalized category={category_n!r}, segment={segment_n!r}")

    X = X.copy()
    X.columns = [str(c).lower() for c in X.columns]
    if category_n == "waystone":
        X.drop(columns=["waystone_tier"], inplace=True, errors="ignore")

    preds: Dict[str, float] = {}
    model_artifacts: Dict[str, str] = {}
    conversions_by_model: Dict[str, Dict[str, Any]] = {}

    # If segment is None, omit it from filenames
    base_name = category_n if segment_n is None else f"{category_n}_{segment_n}"
    _dbg(f"[DEBUG] call_ml_super: base_name='{base_name}'")
    explicit_dirs = model_dirs is not None
    model_dirs = [Path(p).resolve() for p in model_dirs] if explicit_dirs else _super_model_dirs()
    _dbg(f"[DEBUG] call_ml_super: model_dirs={model_dirs!r}")

    # 1) Loop through xgb/rf/gbr models as configured (using cached loader)
    for mtype in _active_models:
        art = None
        loaded_model_dir = None
        p = None
        for candidate_dir in model_dirs:
            candidate = candidate_dir / f"{base_name}_{mtype}_model.pkl"
            _dbg(
                f"[DEBUG] Looking for {mtype} model for base '{base_name}' "
                f"at '{candidate}' (exists={candidate.is_file()})"
            )
            if not candidate.is_file():
                continue
            art = _load_model(candidate_dir, base_name, mtype)
            if art is not None:
                loaded_model_dir = candidate_dir
                p = candidate
                break
        if art is None:
            continue
        model_dir = loaded_model_dir or model_dirs[0]
        p = p or (model_dir / f"{base_name}_{mtype}_model.pkl")

        # 2) Load the pipeline and feature list
        pipe: "Pipeline" = art["model_pipeline"]  # noqa: F821 (sklearn loaded via pickle)
        cols: List[str] = art.get("feature_cols", X.columns.tolist())
        _dbg(f"[DEBUG] Loaded {mtype} pipeline type={type(pipe).__name__}; feature_cols={len(cols)}")
        # Show brief feature alignment info. Cache diagnostics because hotkey
        # inference repeatedly aligns the same category/segment feature shapes.
        x_cols = tuple(str(c).lower() for c in X.columns)
        model_cols = tuple(cols)
        missing, extra = _alignment_diagnostics(x_cols, model_cols)
        if missing:
            head = ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else "")
            _dbg(f"[DEBUG] Input is missing {len(missing)} feature(s): {head}")
        if extra:
            head = ", ".join(extra[:8]) + (" ..." if len(extra) > 8 else "")
            _dbg(f"[DEBUG] Input has {len(extra)} extra column(s) not used by model: {head}")

        # 3) Align our input X to the expected features
        x_in = X.reindex(columns=cols, fill_value=0.0)

        # 4) Predict and record
        _dbg(f"[DEBUG] Predicting with {mtype}: {len(cols)} features")
        try:
            val = float(pipe.predict(x_in)[0])
        except Exception as exc:
            log.warning("Prediction failed for supervised model %s: %s", p, exc)
            _dbg(f"[DEBUG] Prediction failed for {p}: {exc!r}")
            continue
        preds[mtype] = val
        model_artifacts[mtype] = str(p)
        # Explicit server routing requires this artifact's own frozen rates.
        # Legacy desktop calls retain the historical missing-sidecar fallback.
        conversions_by_model[mtype] = (
            read_conversion_manifest(p.with_suffix(".pricing.json"))
            if explicit_dirs else load_model_conversions(p, model_dirs)
        )
        _dbg(f"[DEBUG] {mtype} => {val:.5f}")

        # 5) Optionally show SHAP if enabled
        if _SHAP_ENABLED:
            shap_file = (model_dir / f"{base_name}_{mtype}_model.pkl").with_name(
                f"{base_name}_{mtype}_model_shap.pkl"
            )
            if shap_file.is_file():
                try:
                    with shap_file.open("rb") as fh:
                        shap_art = _compat_load(fh)
                    expl = shap_art["shap_explainer"]
                    cols_shap = shap_art.get("feature_cols", cols)
                    shap_df = X.reindex(columns=cols_shap, fill_value=0.0)
                    inv_map = {c: c for c in shap_df.columns}
                    _print_shap(expl(shap_df), shap_df.columns.tolist(), inv_map, shap_file.name)
                except Exception as e:
                    _dbg(f"[DEBUG] SHAP explanation failed: {e!r}")

    # If we didn’t load any models, bail out
    if not preds:
        _dbg("[DEBUG] No supervised models loaded; returning None")
        return None

    # 6) Aggregate predictions
    vals   = list(preds.values())
    mn     = min(vals)
    mx     = max(vals)
    mean   = sum(vals) / len(vals)
    median = float(np.median(vals))
    _dbg(f"[DEBUG] Aggregated: min={mn:.5f}, max={mx:.5f}, mean={mean:.5f}, median={median:.5f}")

    result: Dict[str, Any] = {
        "predictions": preds,
        "min":         float(mn),
        "max":         float(mx),
        "mean":        float(mean),
        "median":      median,
        "average":     float(mean),
        "segment":     segment_n,
        # The GUI worker uses this resolved artifact path to retrieve the
        # matching frozen training-conversion snapshot without opening models.
        "model_artifacts": model_artifacts,
        # Read on every prediction so a hot-updated model directory immediately
        # reports the conversions that were used to train that model set.
        "currency_conversions_by_model": conversions_by_model,
        "currency_conversions": (
            conversions_by_model.get("xgb")
            or next(iter(conversions_by_model.values()))
        ),
    }

    # 7) Bucketise using the normalized base_name
    # A server request must never consult the desktop/global stats selection.
    # Keep this data local: the legacy single-slot cache can race across leagues.
    bucket_kwargs = {}
    if explicit_dirs:
        stats_path = Path(next(iter(model_artifacts.values()))).parent / "category_segment_stats.json"
        bucket_kwargs["stats_data"] = json.loads(stats_path.read_text(encoding="utf-8-sig"))
    binfo = _bucketise(base_name, median, **bucket_kwargs)
    if binfo:
        result.update(binfo)
        display = bucket_display_for_label(binfo.get("bucket"))
        if display:
            result["bucket_display"] = display
            result["bucket_color_hex"] = display["color_hex"]

    # The GUI's XGBoost section displays predictions.xgb first, then colors the
    # dataset badge from the derived Low/Medium/High bucket. Mirror that exact
    # value source for API consumers instead of assuming the aggregate median.
    if "xgb" in preds:
        xgb_binfo = _bucketise(base_name, preds["xgb"], **bucket_kwargs) or binfo
        xgb_display = _prediction_display(
            model_type="xgb",
            prediction=preds["xgb"],
            bucket_info=xgb_binfo,
        )
        result["xgboost"] = xgb_display
        result["xgb_display"] = xgb_display

    return result

