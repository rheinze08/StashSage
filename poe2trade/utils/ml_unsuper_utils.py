# File: poe2trade/utils/ml_unsuper_utils.py
# · v6.9 — feature filters + masked distance fallback (2025-09-22)
# · v6.8 — add per-file in-process caching (2025-09-11)
# · v6.7 — robust to lowercase/underscore standardization (2025-07-06)

from __future__ import annotations

import pickle
import importlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from poe2trade import poe2trade_root
from poe2trade.pricing import conversion
from poe2trade.app import config_manager
from poe2trade.utils.parse_utils import (
    SUPPORTED_WAYSTONE_SEGMENTS,
    supports_extra_socket_feature,
    waystone_segment_from_frame,
)

DEFAULT_KNN = int(config_manager.DEFAULT_CONFIG.get("knn_filtered_k", 10))

# Load the user config ONCE at import (was previously read twice, below).
_CFG = config_manager.load_config()

# ── Debug logging ──────────────────────────────────────────────
# Per-call [DEBUG] tracing is verbose and writes synchronously to the console
# (slow on Windows, pointless in the --noconsole frozen build). OFF by default;
# set STASHSAGE_DEBUG=1 to re-enable.
import os as _os
_DEBUG = _os.environ.get("STASHSAGE_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")
log = logging.getLogger(__name__)


def _dbg(*args: Any, **kwargs: Any) -> None:
    if _DEBUG:
        print(*args, **kwargs)

# ────────────────────────── helpers ───────────────────────────
def _norm_token(s: str | None) -> str | None:
    """lowercase + replace whitespace with underscores; None → None."""
    if s is None:
        return None
    return re.sub(r"\s+", "_", str(s).strip().lower())

def _to_numpy_bool(x: pd.Series | np.ndarray) -> np.ndarray:
    if isinstance(x, pd.Series):
        return x.to_numpy(dtype=bool, na_value=False)
    if isinstance(x, np.ndarray) and x.dtype != bool:
        return x.astype(bool, copy=False)
    return np.asarray(x, dtype=bool)

# ────────────────────────── price-filter globals ──────────────
_cfg_val  = _CFG.get("price_mirror_filter", "1e")
_price_filter_raw = _cfg_val
_PRICE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([ecd])\s*$", re.I)
_MODEL_DIR = Path(_os.environ.get("STASHSAGE_UNSUPER_MODELS_DIR", str(Path(poe2trade_root) / "db" / "unsuper_models")))

_ACTIVE_PACKAGE = __name__.split(".", 1)[0]
_COMPAT_PACKAGE_ALIASES = {"poe2trade", "stashsage_serve"}


class _CompatUnpickler(pickle.Unpickler):
    """Load pickles created under either downstream package name."""

    def find_class(self, module: str, name: str):
        package = module.split(".", 1)[0]
        if package in _COMPAT_PACKAGE_ALIASES and package != _ACTIVE_PACKAGE:
            module = module.replace(package, _ACTIVE_PACKAGE, 1)
        return super().find_class(module, name)


def _compat_load(file_obj):
    return _CompatUnpickler(file_obj).load()


def _unsuper_model_dirs() -> list[Path]:
    # Explicit env override stays highest priority: the db pipeline and tests
    # point this at a specific directory and must not pick up a user's set.
    env_dir = _os.environ.get("STASHSAGE_UNSUPER_MODELS_DIR")
    if env_dir:
        return [Path(env_dir)]
    try:
        asset_paths = importlib.import_module(f"{_ACTIVE_PACKAGE}.app.asset_paths")
        # The league is prepended by asset_search_dirs, so the KNN comparisons
        # follow the same selection as the price prediction beside them.
        return list(asset_paths.asset_search_dirs("unsuper_models"))
    except Exception:
        return [_MODEL_DIR]


def _parse_price(val: str | float | int) -> float:
    """Convert PoE price shorthand (e, c, d) into numeric exalt-equivalent."""
    if isinstance(val, (int, float)):
        return float(val)
    m = _PRICE_RE.fullmatch(str(val).strip())
    if not m:
        return 1.0
    amt, unit = float(m.group(1)), m.group(2).lower()
    if unit == "e":
        return amt
    if unit == "c":
        return amt * conversion.chaos
    if unit == "d":
        return amt * conversion.divine
    return amt


def _training_conversions(artifact: Mapping[str, Any]) -> Mapping[str, float] | None:
    """Return the conversion rates captured with a model artifact.

    Model prices are stored as exalt-equivalents at training time.  Keeping
    this lookup next to the artifact prevents live market refreshes from
    silently changing model filtering or presentation.
    """
    snapshot = artifact.get("training_conversion_snapshot")
    values = snapshot.get("conversions") if isinstance(snapshot, Mapping) else None
    if not isinstance(values, Mapping):
        return None
    result: dict[str, float] = {}
    for key in ("chaos", "divine"):
        try:
            value = float(values[key])
        except (KeyError, TypeError, ValueError):
            continue
        if np.isfinite(value) and value > 0:
            result[key] = value
    return result if len(result) == 2 else None


def _parse_price_for_artifact(val: str | float | int, artifact: Mapping[str, Any]) -> float:
    """Parse a threshold in the model's training conversion space."""
    if isinstance(val, (int, float)):
        return float(val)
    values = _training_conversions(artifact)
    if values is None:
        return _parse_price(val)
    match = _PRICE_RE.fullmatch(str(val).strip())
    if not match:
        return 1.0
    amount, unit = float(match.group(1)), match.group(2).lower()
    if unit == "e":
        return amount
    return amount * values.get({"c": "chaos", "d": "divine"}[unit], 1.0)


def _artifact_price_bounds(artifact: Mapping[str, Any], min_price: str | float | int | None = None) -> tuple[float, float]:
    """Resolve both global and per-call bounds in one artifact's price space."""
    low = _parse_price_for_artifact(_price_filter_raw if min_price is None else min_price, artifact)
    high = _parse_price_for_artifact(_max_price_filter_raw, artifact)
    return low, high

price_filter: float = _parse_price(_cfg_val)

def set_price_filter(val: str | float) -> None:
    """Update the numeric price_filter at runtime."""
    global price_filter, _price_filter_raw
    _price_filter_raw = val
    price_filter = _parse_price(val)

_cfg_max_val = _CFG.get("price_mirror_max_filter", "100d")
_max_price_filter_raw = _cfg_max_val
max_price_filter: float = _parse_price(_cfg_max_val)

def set_max_price_filter(val: str | float) -> None:
    """Update the numeric max_price_filter at runtime."""
    global max_price_filter, _max_price_filter_raw
    _max_price_filter_raw = val
    max_price_filter = _parse_price(val)

# --- runtime KNN limit (inference truncation) ---
_cfg_knn = _CFG.get("knn_filtered_k", DEFAULT_KNN)

def _parse_knn_limit(val: Any) -> int:
    try:
        v = int(val)
    except (TypeError, ValueError):
        try:
            v = int(float(val))
        except (TypeError, ValueError):
            return DEFAULT_KNN
    return v if v > 0 else DEFAULT_KNN

knn_runtime_k: int = _parse_knn_limit(_cfg_knn)

def set_knn_runtime_k(val: Any) -> None:
    """Update the runtime KNN truncation size used at inference."""
    global knn_runtime_k
    knn_runtime_k = _parse_knn_limit(val)

def _resolve_knn_runtime_k(top: Optional[int]) -> tuple[int, int]:
    """Return (runtime_limit, query_limit) given a requested top."""
    runtime = knn_runtime_k if knn_runtime_k > 0 else DEFAULT_KNN
    query = runtime
    if top is not None:
        try:
            top_val = int(top)
        except (TypeError, ValueError):
            top_val = None
        if top_val and top_val > 0:
            query = max(runtime, top_val)
    return runtime, query


def _nearest_indices(dists: np.ndarray, take: int) -> np.ndarray:
    """Indices of the `take` smallest distances, in ascending-distance order.

    np.argpartition selects the k nearest in O(n) instead of argsort's
    O(n log n) over the whole training set; only the selected k entries are
    then fully sorted.
    """
    if take <= 0:
        return np.empty(0, dtype=np.intp)
    if take >= dists.size:
        return np.argsort(dists)
    part = np.argpartition(dists, take - 1)[:take]
    return part[np.argsort(dists[part])]


def _dists_to_query(scaled_rows: np.ndarray, sq_norms: np.ndarray, qv: np.ndarray) -> np.ndarray:
    """Euclidean distance from each pre-scaled training row to the query.

    Uses the ||x-q||^2 = ||x||^2 - 2 x·q + ||q||^2 expansion (the same trick
    sklearn's euclidean_distances uses) so a single BLAS matvec replaces the
    (n x d) diff temporary that was previously allocated on every call.
    `sq_norms` is memoized per bundle by the caller.
    """
    q = np.asarray(qv, dtype=np.float32).ravel()
    cross = scaled_rows @ q
    d2 = sq_norms - 2.0 * cross.astype(np.float64) + float(np.dot(q, q))
    np.maximum(d2, 0.0, out=d2)  # clamp tiny negatives from float rounding
    return np.sqrt(d2, out=d2)


def _dists_to_queries(scaled_rows: np.ndarray, sq_norms: np.ndarray, qv: np.ndarray) -> np.ndarray:
    """Euclidean distances from each query row to all pre-scaled training rows."""
    q = np.asarray(qv, dtype=np.float32)
    if q.ndim == 1:
        q = q.reshape(1, -1)
    cross = q @ scaled_rows.T
    q_norms = np.einsum("ij,ij->i", q, q, dtype=np.float64)
    d2 = sq_norms[None, :] - 2.0 * cross.astype(np.float64) + q_norms[:, None]
    np.maximum(d2, 0.0, out=d2)
    return np.sqrt(d2, out=d2)


def _resolve_feature_weights(art: Dict[str, Any], feat_cols: list[str]) -> Optional[np.ndarray]:
    weights = art.get("feature_weights")
    if not weights or not isinstance(weights, (list, tuple)) or len(weights) != len(feat_cols):
        return None
    w = np.asarray(weights, dtype=np.float32)
    w = np.where(np.isfinite(w), w, 0.0)
    total = float(w.sum())
    if total <= 0:
        return None
    return w / total

# ───────────────────────── model-path resolution ──────────────
def _strict_meta_pickle(cat: str, seg: Optional[str], directory: Path) -> Optional[Path]:
    """
    Look up the unsupervised‐model pickle by its exact filename.

    Naming conventions after training:
      - Jewellery branches (ring/amulet/belt): no segment in filename
          → '{category}_knn_model.pkl'
      - Armour segments: include segment key
          → '{category}_{segment}_knn_model.pkl'
    """
    if seg is None:
        fname = f"{cat}_knn_model.pkl"
    else:
        fname = f"{cat}_{seg}_knn_model.pkl"

    expected = directory / fname
    if expected.exists():
        _dbg(f"[DEBUG] _strict_meta_pickle: found '{expected.name}'")
        return expected

    _dbg(f"[DEBUG] _strict_meta_pickle: no file named '{fname}' in {directory}")
    # A tier is a hard routing boundary. Never substitute another tier's data.
    if cat == "waystone" and seg is not None and str(seg).startswith("t"):
        return None
    # Fallback: try any model for this category (any segment) to keep overlay usable
    try:
        cand = sorted(directory.glob(f"{cat}_*_knn_model.pkl"))
        if cand:
            _dbg(f"[DEBUG] _strict_meta_pickle: falling back to '{cand[0].name}'")
            return cand[0]
    except Exception:
        pass
    return None

# ───────────────────────── NEW: in-process cache ─────────────
_bundle_cache: Dict[Tuple[str, str, Optional[str]], Dict[str, Any]] = {}
_bundle_mtime: Dict[Tuple[str, str, Optional[str]], float] = {}
_SEGMENT_SUFFIXES = (
    "ar_only",
    "ev_only",
    "es_only",
    "ar_ev_only",
    "ar_es_only",
    "ev_es_only",
    "all_three",
)

def _load_unsuper_bundle(cat: str, seg: Optional[str], mdl_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Load and cache the unsuper bundle for (category, segment) with mtime-based invalidation.
    """
    p = _strict_meta_pickle(cat, seg, mdl_dir)
    if p is None:
        return None

    key = (str(p.resolve()), cat, seg)
    mt  = p.stat().st_mtime
    b   = _bundle_cache.get(key)
    if b is not None and _bundle_mtime.get(key) == mt:
        return b

    # Older pandas pickles may encode StringDtype with an extra positional
    # argument (e.g., legacy na_value). Newer pandas versions (>=2.x)
    # reject that, raising:
    #   TypeError: StringDtype.__init__() takes from 1 to 2 positional arguments but 3 were given
    # To keep distributed model bundles compatible across environments,
    # patch StringDtype.__init__ at load time to ignore extra args, then restore.
    try:
        with p.open("rb") as fh:
            b = _compat_load(fh)
    except TypeError as e:
        if "StringDtype.__init__" in str(e):
            try:
                orig_init = pd.StringDtype.__init__

                def _compat_init(self, storage="python", *args, **kwargs):
                    # Ignore legacy extra positional args (e.g., na_value)
                    try:
                        return orig_init(self, storage)
                    except TypeError:
                        # Some pandas versions require keyword form
                        return orig_init(self, storage=storage)

                pd.StringDtype.__init__ = _compat_init  # type: ignore[attr-defined]
                with p.open("rb") as fh:
                    b = _compat_load(fh)
                _dbg("[DEBUG] Applied pandas StringDtype compatibility shim during unpickle")
            except Exception as exc:
                log.warning("Skipping unusable KNN bundle %s: %s", p, exc)
                _dbg(f"[DEBUG] Failed to load KNN bundle {p}: {exc!r}")
                return None
            finally:
                try:
                    pd.StringDtype.__init__ = orig_init  # type: ignore[attr-defined]
                except Exception:
                    pass
        else:
            log.warning("Skipping unusable KNN bundle %s: %s", p, e)
            _dbg(f"[DEBUG] Failed to load KNN bundle {p}: {e!r}")
            return None
    except Exception as exc:
        log.warning("Skipping unusable KNN bundle %s: %s", p, exc)
        _dbg(f"[DEBUG] Failed to load KNN bundle {p}: {exc!r}")
        return None
    required = ("scaler_data", "feature_cols", "X_all", "overlay_df", "row_indices")
    if not isinstance(b, dict) or any(key not in b for key in required):
        log.warning("Skipping invalid KNN bundle %s: missing required fields", p)
        return None
    _bundle_cache[key] = b
    _bundle_mtime[key] = mt
    _dbg(f"[DEBUG] Loaded KNN bundle '{p.name}' into cache")
    return b


def _prepare_bundle_runtime_cache(art: Dict[str, Any]) -> None:
    """Populate per-bundle arrays used by the fast KNN distance path."""
    mean = np.asarray(art["scaler_data"]["mean"], dtype=np.float32)
    scale = np.asarray(art["scaler_data"]["scale"], dtype=np.float32)
    scale = np.where(scale == 0, 1.0, scale)
    feat_cols = art["feature_cols"]
    X_all = art["X_all"]

    if "_sqrt_feature_weights" not in art:
        w = _resolve_feature_weights(art, feat_cols)
        art["_sqrt_feature_weights"] = np.sqrt(w) if w is not None else None
    sqrt_w = art.get("_sqrt_feature_weights")

    if "_feat_cols_l" not in art:
        art["_feat_cols_l"] = [str(c).lower() for c in feat_cols]
    overlay_df = art.get("overlay_df")
    if overlay_df is not None and "_ov_cols_l" not in art:
        art["_ov_cols_l"] = [str(c).lower() for c in overlay_df.columns]

    scaled_all = art.get("_scaled_X_all")
    if scaled_all is None:
        if X_all.size == 0:
            scaled_all = X_all.astype(np.float32)
        else:
            scaled_all = (X_all.astype(np.float32) - mean) / scale
            if sqrt_w is not None:
                scaled_all = scaled_all * sqrt_w
        art["_scaled_X_all"] = scaled_all

    if art.get("_scaled_sq_norms") is None:
        if scaled_all.size == 0:
            sq_norms = np.zeros(scaled_all.shape[0] if scaled_all.ndim else 0)
        else:
            sq_norms = np.einsum("ij,ij->i", scaled_all, scaled_all, dtype=np.float64)
        art["_scaled_sq_norms"] = sq_norms


def _parse_bundle_name(path: Path) -> tuple[str, Optional[str]] | None:
    suffix = "_knn_model.pkl"
    name = path.name
    if not name.endswith(suffix):
        return None
    base = name[: -len(suffix)]
    for seg in _SEGMENT_SUFFIXES:
        seg_suffix = f"_{seg}"
        if base.endswith(seg_suffix):
            return base[: -len(seg_suffix)], seg
    return base, None


def _prewarm_unsuper_bundles(mdl_dir: Path | None = None) -> int:
    """Load all installed KNN bundles and populate runtime caches."""
    warmed = 0
    directories = [mdl_dir] if mdl_dir is not None else _unsuper_model_dirs()
    for directory in directories:
        if not directory.is_dir():
            continue
        for pkl in directory.glob("*_knn_model.pkl"):
            parsed = _parse_bundle_name(pkl)
            if parsed is None:
                continue
            cat, seg = parsed
            try:
                art = _load_unsuper_bundle(cat, seg, directory)
                if art is not None:
                    _prepare_bundle_runtime_cache(art)
                    warmed += 1
            except Exception as exc:
                _dbg(f"[DEBUG] prewarm skipped {pkl.name}: {exc!r}")
    return warmed


def clear_runtime_caches() -> None:
    """Clear loaded KNN bundles after model assets are refreshed."""
    _bundle_cache.clear()
    _bundle_mtime.clear()

# ──────────────── filtering helpers (features & overlay) ─────────────────

def _apply_op_series(s: pd.Series, op: str, val: Any) -> np.ndarray:
    """Return boolean mask for a pandas Series with the given operator."""
    op_l = str(op).strip().lower()

    # Numeric ops: pandas will handle dtype coercion where possible
    if op_l in (">", ">=", "<", "<=", "==", "!="):
        if   op_l == ">":  return (s >  val).to_numpy(dtype=bool, na_value=False)
        if   op_l == ">=": return (s >= val).to_numpy(dtype=bool, na_value=False)
        if   op_l == "<":  return (s <  val).to_numpy(dtype=bool, na_value=False)
        if   op_l == "<=": return (s <= val).to_numpy(dtype=bool, na_value=False)
        if   op_l == "==": return (s == val).to_numpy(dtype=bool, na_value=False)
        if   op_l == "!=": return (s != val).to_numpy(dtype=bool, na_value=False)

    # Range
    if op_l == "between":
        try:
            lo, hi = val
        except Exception as e:
            raise ValueError("between expects a (lo, hi) tuple/list") from e
        return (s >= lo).to_numpy(dtype=bool, na_value=False) & (s <= hi).to_numpy(dtype=bool, na_value=False)

    # Membership (treat val as collection)
    if op_l in ("in", "not in"):
        arr = set(val if isinstance(val, (list, tuple, set)) else [val])
        m = s.isin(arr).to_numpy(dtype=bool, na_value=False)
        return ~m if op_l == "not in" else m

    # String contains / prefix / suffix
    if s.dtype == object or pd.api.types.is_string_dtype(s):
        sval = s.fillna("").astype(str)
        if op_l == "contains":
            return sval.str.contains(str(val), case=False, na=False).to_numpy()
        if op_l == "startswith":
            return sval.str.startswith(str(val), na=False).to_numpy()
        if op_l == "endswith":
            return sval.str.endswith(str(val), na=False).to_numpy()

    raise ValueError(f"Unsupported operator {op!r}")

def _build_feature_mask(
    Xdf: pd.DataFrame,
    where: Optional[Dict[str, Tuple[str, Any]]]
) -> Optional[np.ndarray]:
    """Build mask over rows using filters on trained features.

    `Xdf` is the (lowercase-columned) feature DataFrame; callers pass a cached
    frame so it isn't rebuilt from the raw matrix on every filtered call.
    """
    if not where:
        return None
    mask = np.ones(len(Xdf), dtype=bool)
    for col, spec in where.items():
        col_l = str(col).lower()
        if col_l not in Xdf.columns:
            _dbg(f"[DEBUG] feature filter skipped: unknown column '{col_l}'")
            continue
        try:
            op, val = spec
        except Exception:
            raise ValueError(f"Filter spec for '{col}' must be a tuple like ('>=', 20)")
        mask &= _apply_op_series(Xdf[col_l], op, val)
    return mask

def _build_overlay_mask(
    overlay_df: pd.DataFrame,
    row_indices: list[int],
    where_overlay: Optional[Dict[str, Tuple[str, Any]]]
) -> Optional[np.ndarray]:
    """Build mask over rows using filters on overlay_df columns (aligned to model rows)."""
    if not where_overlay:
        return None
    # align overlay rows to the training row order
    ov = overlay_df.reindex(row_indices)
    mask = np.ones(len(ov), dtype=bool)
    for col, spec in where_overlay.items():
        col_l = str(col).lower()
        if col_l not in ov.columns.str.lower():
            _dbg(f"[DEBUG] overlay filter skipped: unknown column '{col_l}'")
            continue
        # robust access irrespective of original column case
        real_col = next((c for c in ov.columns if c.lower() == col_l), None)
        try:
            op, val = spec
        except Exception:
            raise ValueError(f"Overlay filter spec for '{col}' must be a tuple like ('in', ['Elder','Shaper'])")
        mask &= _apply_op_series(ov[real_col], op, val)
    return mask

# ───────────────────────── public API ─────────────────────────
def call_ml(
    category: str,
    segment: Optional[str],
    X: pd.DataFrame,
    top: Optional[int] = None,
    *,
    model_dirs: Optional[list[Path]] = None,
    where: Optional[Dict[str, Tuple[str, Any]]] = None,
    where_overlay: Optional[Dict[str, Tuple[str, Any]]] = None,
    min_price: Optional[float | str] = None
) -> Optional[pd.DataFrame]:
    """
    Unsupervised KNN lookup with optional pre-filtering.

    Parameters
    ----------
    category : str
        Normalized category name (underscores, lowercase).
    segment : Optional[str]
        Defence-segment key for armour, or None for jewellery.
    X : pd.DataFrame
        One-row feature-DataFrame matching trained feature_cols.
    top : int | None
        Requested number of neighbours (runtime truncation still applies).
    where : dict[str, (op, val)]
        Filters on trained features (feature_cols). Example: {"fire_resistance": (">=", 30)}.
    where_overlay : dict[str, (op, val)]
        Filters on overlay_df columns (attributes not in feature_cols).
    min_price : float | str | None
        Optional per-call price threshold. Accepts 1.0, "25c", "1.5e", "2d", etc.

    Returns
    -------
    pd.DataFrame or None
        Overlay data of up to the runtime KNN limit after filters, or
        None if no model or no neighbours pass the filters.
    """
    # normalize inputs and lower-case input columns (robust to standardization)
    category_n = _norm_token(category)
    if category_n == "scepter":
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
            return None

    X = X.copy()
    X.columns = [str(c).lower() for c in X.columns]
    if category_n == "waystone":
        X.drop(columns=["waystone_tier"], inplace=True, errors="ignore")

    model_dirs = [Path(p).resolve() for p in model_dirs] if model_dirs is not None else _unsuper_model_dirs()
    _dbg(
        f"[DEBUG] call_ml_unsuper: looking in '{model_dirs}' for category "
        f"'{category_n}' segment '{segment_n}'"
    )

    # Columns that must be present in overlay_df for a bundle to be considered
    # fully current.  A bundle missing these was built before the columns were
    # added to the parse/matrix pipeline; prefer a later directory's bundle.
    _REQUIRED_OVERLAY_COLS = (
        frozenset({"extra_sockets"})
        if supports_extra_socket_feature(category_n)
        else frozenset()
    )

    # load cached bundle (no directory listing); prefer bundles whose overlay
    # contains all required metadata columns over older/incomplete ones.
    art = None
    art_fallback = None
    for mdl_dir in model_dirs:
        candidate = _load_unsuper_bundle(category_n, segment_n, mdl_dir)
        if candidate is None:
            continue
        ov = candidate.get("overlay_df")
        ov_cols = set(ov.columns) if hasattr(ov, "columns") else set()
        if _REQUIRED_OVERLAY_COLS <= ov_cols:
            art = candidate
            break
        if art_fallback is None:
            art_fallback = candidate
    if art is None:
        art = art_fallback
    if art is None:
        _dbg(f"[DEBUG] call_ml_unsuper: No unsuper_model pickle for segment '{segment_n}' in {model_dirs}")
        return None

    mean         = np.asarray(art["scaler_data"]["mean"], dtype=np.float32)
    scale        = np.asarray(art["scaler_data"]["scale"], dtype=np.float32)
    # defensive: avoid divide-by-zero if any scale elements are 0
    scale        = np.where(scale == 0, 1.0, scale)

    feat_cols    = art["feature_cols"]
    X_all        = art["X_all"]  # unscaled numeric training matrix
    model_price  = np.asarray(art.get("model_price", []), dtype=np.float32)
    overlay_df   = art["overlay_df"]
    row_indices  = art["row_indices"]
    _prepare_bundle_runtime_cache(art)

    # 1) Reindex query to match training features & scale
    _dbg(f"[DEBUG] call_ml_unsuper: reindexing query X to feat_cols ({len(feat_cols)} cols)")
    q = X.reindex(columns=feat_cols, fill_value=0.0)
    qv = (q.to_numpy(dtype=np.float32) - mean) / scale
    sqrt_w = art.get("_sqrt_feature_weights")
    if sqrt_w is not None:
        qv = qv * sqrt_w

    scaled_all = art["_scaled_X_all"]
    sq_norms = art["_scaled_sq_norms"]

    # decide path: fast (sklearn index) vs filtered (manual distances)
    # Auto-route unknown filter keys to overlay space so the GUI can pass
    # a single filter dict based on what the user sees in the mirror cells.
    where = where or {}
    where_overlay = where_overlay or {}
    feat_cols_l = art.get("_feat_cols_l") or [str(c).lower() for c in feat_cols]
    ov_cols_l   = art.get("_ov_cols_l") or [str(c).lower() for c in overlay_df.columns]
    routed_feat: Dict[str, Tuple[str, Any]] = {}
    routed_ov: Dict[str, Tuple[str, Any]] = {}

    for col, spec in (where or {}).items():
        cl = str(col).lower()
        if cl in feat_cols_l:
            routed_feat[cl] = spec
        elif cl in ov_cols_l:
            routed_ov[cl] = spec
        else:
            _dbg(f"[DEBUG] call_ml_unsuper: unknown filter column '{col}' -> ignored")

    # Merge any explicit overlay filters provided by callers
    for col, spec in (where_overlay or {}).items():
        cl = str(col).lower()
        if cl in feat_cols_l and cl not in routed_feat:
            routed_feat[cl] = spec
        elif cl in ov_cols_l:
            routed_ov[cl] = spec
        else:
            _dbg(f"[DEBUG] call_ml_unsuper: unknown overlay filter column '{col}' -> ignored")

    has_feature_filters = bool(routed_feat)
    has_overlay_filters = bool(routed_ov)
    has_per_call_price  = (min_price is not None)
    model_min_price, model_max_price = _artifact_price_bounds(art, min_price)
    runtime_k, query_k = _resolve_knn_runtime_k(top)

    if not (has_feature_filters or has_overlay_filters or has_per_call_price):
        # -- FAST PATH: brute-force distances over all rows, then post-apply price filter --
        if X_all.size == 0:
            _dbg("[DEBUG] call_ml_unsuper: empty X_all")
            return None
        # pre-scaled matrix + memoized row norms: one BLAS matvec, no n x d temp
        dists = _dists_to_query(scaled_all, sq_norms, qv)
        take = min(query_k, dists.size)
        nearest = _nearest_indices(dists, take)
        idxs = nearest

        # price filter (post-distance to preserve legacy semantics)
        _dbg(f"[DEBUG] call_ml_unsuper: applying model price filter >= {model_min_price}, <= {model_max_price}")
        if model_price.size == len(X_all):
            mask = (model_price[idxs] >= model_min_price) & (model_price[idxs] <= model_max_price)
            idxs = idxs[mask]
            if idxs.size == 0:
                # Fallback: if no neighbors pass the price filter, ignore the filter
                _dbg("[DEBUG] call_ml_unsuper: no neighbors passed price_filter; falling back to unfiltered KNN")
                idxs = nearest
        else:
            print("[WARN] model_price length mismatch; skipping price filter")

        sel = idxs[:min(runtime_k, len(idxs))]
        local = sel
        _dbg(f"[DEBUG] call_ml_unsuper: selected local indices {local.tolist()} with distances {dists[local].tolist()}")

        global_idx = [row_indices[i] for i in local]
        _dbg(f"[DEBUG] call_ml_unsuper: mapping to overlay_df indices {global_idx}")
        result = overlay_df.loc[global_idx].reset_index(drop=True)
        if model_price.size == len(X_all):
            result["price_in_exalts"] = model_price[local]
        result.attrs["training_conversion_snapshot"] = art.get("training_conversion_snapshot")
        if runtime_k > 0 and len(result) > runtime_k:
            result = result.head(runtime_k).reset_index(drop=True)
        return result

    # ── FILTERED PATH: build candidate mask, then brute-force distances on subset ──
    n = len(X_all)
    cand = np.ones(n, dtype=bool)

    # 0) price filter (pre-apply to reduce work)
    thr = model_min_price
    _dbg(f"[DEBUG] call_ml_unsuper: applying pre model price_filter >= {thr}, <= {model_max_price}")
    if model_price.size == n:
        cand &= (model_price >= float(thr)) & (model_price <= float(model_max_price))
    else:
        print("[WARN] model_price length mismatch; skipping price filter")

    # 1) feature-based filters (on trained features)
    if routed_feat:
        feat_df = art.get("_feat_df")
        if feat_df is None:
            feat_df = pd.DataFrame(X_all, columns=[str(c).lower() for c in feat_cols])
            art["_feat_df"] = feat_df  # memoized once per cached bundle
        fm = _build_feature_mask(feat_df, routed_feat)
        if fm is not None:
            cand &= fm

    # 2) overlay-based filters (attributes that live only in overlay_df)
    om = _build_overlay_mask(overlay_df, row_indices, routed_ov)
    if om is not None:
        cand &= om

    if not cand.any():
        _dbg("[DEBUG] call_ml_unsuper: no candidates after filters")
        return None

    cand_idx = np.flatnonzero(cand)
    _dbg(f"[DEBUG] call_ml_unsuper: {cand_idx.size} candidates after filters (of {n})")

    # 3) Compute distances on the filtered subset (Euclidean; same metric as sklearn default)
    #    Reuse the pre-scaled training matrix and memoized row norms, indexing
    #    only the candidate rows (one BLAS matvec, no n x d diff temporary).
    Xsub = scaled_all[cand_idx]
    dists = _dists_to_query(Xsub, sq_norms[cand_idx], qv)

    # 4) Take nearest top
    take = min(query_k, dists.size)
    if take == 0:
        _dbg("[DEBUG] call_ml_unsuper: no distances computed")
        return None

    order = _nearest_indices(dists, take)
    local = cand_idx[order]
    picked_dists = dists[order]
    _dbg(f"[DEBUG] call_ml_unsuper: selected local indices {local.tolist()} with distances {picked_dists.tolist()}")

    # 5) Map back to overlay_df via row_indices and return
    global_idx = [row_indices[i] for i in local]
    _dbg(f"[DEBUG] call_ml_unsuper: mapping to overlay_df indices {global_idx}")
    result = overlay_df.loc[global_idx].reset_index(drop=True)
    if runtime_k > 0 and len(result) > runtime_k:
        result = result.head(runtime_k).reset_index(drop=True)
    if model_price.size:
        try:
            result = result.copy()
            result["price_in_exalts"] = model_price[local]
            result.attrs["training_conversion_snapshot"] = art.get("training_conversion_snapshot")
        except Exception:
            pass
    return result


def call_ml_batch(
    category: str,
    segment: Optional[str],
    X: pd.DataFrame,
    top: Optional[int] = None,
    *,
    model_dirs: Optional[list[Path]] = None,
    where: Optional[Dict[str, Tuple[str, Any]]] = None,
    where_overlay: Optional[Dict[str, Tuple[str, Any]]] = None,
    min_price: Optional[float | str] = None
) -> list[Optional[pd.DataFrame]]:
    """
    Batched variant of call_ml.

    The unfiltered path computes distances for all query rows in one matrix
    multiply. Filtered lookups fall back to call_ml per row to preserve existing
    semantics for less common GUI-driven queries.
    """
    if X is None or len(X) == 0:
        return []
    if where or where_overlay or min_price is not None:
        return [
            call_ml(
                category,
                segment,
                X.iloc[[i]].copy(),
                top,
                where=where,
                model_dirs=model_dirs,
                where_overlay=where_overlay,
                min_price=min_price,
            )
            for i in range(len(X))
        ]

    category_n = _norm_token(category)
    if category_n == "scepter":
        category_n = "sceptre"
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
    if category_n == "talismans":
        category_n = "talisman"
    if category_n == "rings":
        category_n = "ring"
    if category_n == "amulets":
        category_n = "amulet"
    if category_n == "belts":
        category_n = "belt"
    segment_n = _norm_token(segment) if segment is not None else None
    if category_n == "waystone":
        segment_n = segment_n or waystone_segment_from_frame(X)
        if segment_n not in SUPPORTED_WAYSTONE_SEGMENTS:
            return [None] * len(X)

    X = X.copy()
    X.columns = [str(c).lower() for c in X.columns]
    if category_n == "waystone":
        X.drop(columns=["waystone_tier"], inplace=True, errors="ignore")

    required_overlay_cols = (
        frozenset({"extra_sockets"})
        if supports_extra_socket_feature(category_n)
        else frozenset()
    )

    art = None
    art_fallback = None
    for mdl_dir in (model_dirs if model_dirs is not None else _unsuper_model_dirs()):
        candidate = _load_unsuper_bundle(category_n, segment_n, mdl_dir)
        if candidate is None:
            continue
        ov = candidate.get("overlay_df")
        ov_cols = set(ov.columns) if hasattr(ov, "columns") else set()
        if required_overlay_cols <= ov_cols:
            art = candidate
            break
        if art_fallback is None:
            art_fallback = candidate
    if art is None:
        art = art_fallback
    if art is None:
        return [None] * len(X)

    mean = np.asarray(art["scaler_data"]["mean"], dtype=np.float32)
    scale = np.asarray(art["scaler_data"]["scale"], dtype=np.float32)
    scale = np.where(scale == 0, 1.0, scale)
    feat_cols = art["feature_cols"]
    X_all = art["X_all"]
    model_price = np.asarray(art.get("model_price", []), dtype=np.float32)
    overlay_df = art["overlay_df"]
    row_indices = art["row_indices"]
    _prepare_bundle_runtime_cache(art)
    model_min_price, model_max_price = _artifact_price_bounds(art)

    if X_all.size == 0:
        return [None] * len(X)

    q = X.reindex(columns=feat_cols, fill_value=0.0)
    qv = (q.to_numpy(dtype=np.float32) - mean) / scale
    sqrt_w = art.get("_sqrt_feature_weights")
    if sqrt_w is not None:
        qv = qv * sqrt_w

    dists_all = _dists_to_queries(art["_scaled_X_all"], art["_scaled_sq_norms"], qv)
    runtime_k, query_k = _resolve_knn_runtime_k(top)
    take = min(query_k, len(X_all))
    results: list[Optional[pd.DataFrame]] = []

    warned_price_mismatch = False
    for row_dists in dists_all:
        nearest = _nearest_indices(row_dists, take)
        idxs = nearest
        if model_price.size == len(X_all):
            mask = (model_price[idxs] >= model_min_price) & (model_price[idxs] <= model_max_price)
            idxs = idxs[mask]
            if idxs.size == 0:
                idxs = nearest
        elif not warned_price_mismatch:
            print("[WARN] model_price length mismatch; skipping price filter")
            warned_price_mismatch = True

        sel = idxs[:min(runtime_k, len(idxs))]
        if len(sel) == 0:
            results.append(None)
            continue
        global_idx = [row_indices[i] for i in sel]
        result = overlay_df.loc[global_idx].reset_index(drop=True)
        if model_price.size == len(X_all):
            result["price_in_exalts"] = model_price[sel]
        result.attrs["training_conversion_snapshot"] = art.get("training_conversion_snapshot")
        if runtime_k > 0 and len(result) > runtime_k:
            result = result.head(runtime_k).reset_index(drop=True)
        results.append(result)
    return results
