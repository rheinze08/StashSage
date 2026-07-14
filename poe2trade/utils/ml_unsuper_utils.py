# File: poe2trade/utils/ml_unsuper_utils.py
# · v6.9 — feature filters + masked distance fallback (2025-09-22)
# · v6.8 — add per-file in-process caching (2025-09-11)
# · v6.7 — robust to lowercase/underscore standardization (2025-07-06)

from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from poe2trade import poe2trade_root, chaos_exalt, divine_exalt, annul_exalt
from poe2trade.app import config_manager

DEFAULT_KNN = int(config_manager.DEFAULT_CONFIG.get("knn_filtered_k", 10))

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
_cfg_val  = config_manager.load_config().get("price_mirror_filter", "1e")
_PRICE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([ecda])\s*$", re.I)

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
        return amt * chaos_exalt
    if unit == "d":
        return amt * divine_exalt
    if unit == "a":
        return amt * annul_exalt
    return amt

price_filter: float = _parse_price(_cfg_val)

def set_price_filter(val: str | float) -> None:
    """Update the numeric price_filter at runtime."""
    global price_filter
    price_filter = _parse_price(val)

# --- runtime KNN limit (inference truncation) ---
_cfg_knn = config_manager.load_config().get("knn_filtered_k", DEFAULT_KNN)

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
        print(f"[DEBUG] _strict_meta_pickle: found '{expected.name}'")
        return expected

    print(f"[DEBUG] _strict_meta_pickle: no file named '{fname}' in {directory}")
    # Fallback: try any model for this category (any segment) to keep overlay usable
    try:
        cand = sorted(directory.glob(f"{cat}_*_knn_model.pkl"))
        if cand:
            print(f"[DEBUG] _strict_meta_pickle: falling back to '{cand[0].name}'")
            return cand[0]
    except Exception:
        pass
    return None

# ───────────────────────── NEW: in-process cache ─────────────
_bundle_cache: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
_bundle_mtime: Dict[Tuple[str, Optional[str]], float] = {}

def _load_unsuper_bundle(cat: str, seg: Optional[str], mdl_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Load and cache the unsuper bundle for (category, segment) with mtime-based invalidation.
    """
    p = _strict_meta_pickle(cat, seg, mdl_dir)
    if p is None:
        return None

    key = (cat, seg)
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
    fh = p.open("rb")
    try:
        b = pickle.load(fh)
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
                fh.seek(0)
                b = pickle.load(fh)
                print("[DEBUG] Applied pandas StringDtype compatibility shim during unpickle")
            finally:
                try:
                    pd.StringDtype.__init__ = orig_init  # type: ignore[attr-defined]
                except Exception:
                    pass
        else:
            raise
    _bundle_cache[key] = b
    _bundle_mtime[key] = mt
    print(f"[DEBUG] Loaded KNN bundle '{p.name}' into cache")
    return b

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
    X_all: np.ndarray,
    feat_cols: list[str],
    where: Optional[Dict[str, Tuple[str, Any]]]
) -> Optional[np.ndarray]:
    """Build mask over rows using filters on trained features."""
    if not where:
        return None
    # work in a DataFrame for ergonomic ops
    Xdf = pd.DataFrame(X_all, columns=[str(c).lower() for c in feat_cols])
    mask = np.ones(len(Xdf), dtype=bool)
    for col, spec in where.items():
        col_l = str(col).lower()
        if col_l not in Xdf.columns:
            print(f"[DEBUG] feature filter skipped: unknown column '{col_l}'")
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
            print(f"[DEBUG] overlay filter skipped: unknown column '{col_l}'")
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
    if category_n == "quivers":
        category_n = "quiver"
    if category_n == "rings":
        category_n = "ring"
    if category_n == "amulets":
        category_n = "amulet"
    if category_n == "belts":
        category_n = "belt"
    segment_n  = _norm_token(segment) if segment is not None else None

    X = X.copy()
    X.columns = [str(c).lower() for c in X.columns]

    mdl_dir = Path(poe2trade_root) / "db" / "unsuper_models"
    print(f"[DEBUG] call_ml_unsuper: looking in '{mdl_dir}' for category '{category_n}' segment '{segment_n}'")

    # load cached bundle (no directory listing)
    art = _load_unsuper_bundle(category_n, segment_n, mdl_dir)
    if art is None:
        print(f"[DEBUG] call_ml_unsuper: No unsuper_model pickle for segment '{segment_n}' in {mdl_dir}")
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

    # 1) Reindex query to match training features & scale
    print(f"[DEBUG] call_ml_unsuper: reindexing query X to feat_cols ({len(feat_cols)} cols)")
    q = X.reindex(columns=feat_cols, fill_value=0.0)
    qv = (q.to_numpy(dtype=np.float32) - mean) / scale
    w = _resolve_feature_weights(art, feat_cols)
    if w is not None:
        qv = qv * np.sqrt(w)

    # decide path: fast (sklearn index) vs filtered (manual distances)
    # Auto-route unknown filter keys to overlay space so the GUI can pass
    # a single filter dict based on what the user sees in the mirror cells.
    where = where or {}
    where_overlay = where_overlay or {}
    feat_cols_l = [str(c).lower() for c in feat_cols]
    ov_cols_l   = [str(c).lower() for c in overlay_df.columns]
    routed_feat: Dict[str, Tuple[str, Any]] = {}
    routed_ov: Dict[str, Tuple[str, Any]] = {}

    for col, spec in (where or {}).items():
        cl = str(col).lower()
        if cl in feat_cols_l:
            routed_feat[cl] = spec
        elif cl in ov_cols_l:
            routed_ov[cl] = spec
        else:
            print(f"[DEBUG] call_ml_unsuper: unknown filter column '{col}' -> ignored")

    # Merge any explicit overlay filters provided by callers
    for col, spec in (where_overlay or {}).items():
        cl = str(col).lower()
        if cl in feat_cols_l and cl not in routed_feat:
            routed_feat[cl] = spec
        elif cl in ov_cols_l:
            routed_ov[cl] = spec
        else:
            print(f"[DEBUG] call_ml_unsuper: unknown overlay filter column '{col}' -> ignored")

    has_feature_filters = bool(routed_feat)
    has_overlay_filters = bool(routed_ov)
    has_per_call_price  = (min_price is not None)
    runtime_k, query_k = _resolve_knn_runtime_k(top)

    if not (has_feature_filters or has_overlay_filters or has_per_call_price):
        # -- FAST PATH: brute-force distances over all rows, then post-apply price filter --
        if X_all.size == 0:
            print("[DEBUG] call_ml_unsuper: empty X_all")
            return None
        Xsub = (X_all.astype(np.float32) - mean) / scale
        if w is not None:
            Xsub = Xsub * np.sqrt(w)
        diff = Xsub - qv
        dists = np.sqrt(np.sum(diff * diff, axis=1))
        order = np.argsort(dists)
        take = min(query_k, dists.size)
        idxs = order[:take]

        # price filter (post-distance to preserve legacy semantics)
        print(f"[DEBUG] call_ml_unsuper: applying price_filter >= {price_filter}")
        if model_price.size == len(X_all):
            mask = model_price[idxs] >= price_filter
            idxs = idxs[mask]
            if idxs.size == 0:
                # Fallback: if no neighbors pass the price filter, ignore the filter
                print("[DEBUG] call_ml_unsuper: no neighbors passed price_filter; falling back to unfiltered KNN")
                idxs = order[:take]
        else:
            print("[WARN] model_price length mismatch; skipping price filter")

        sel = idxs[:min(runtime_k, len(idxs))]
        local = sel
        print(f"[DEBUG] call_ml_unsuper: selected local indices {local.tolist()} with distances {dists[local].tolist()}")

        global_idx = [row_indices[i] for i in local]
        print(f"[DEBUG] call_ml_unsuper: mapping to overlay_df indices {global_idx}")
        result = overlay_df.loc[global_idx].reset_index(drop=True)
        if runtime_k > 0 and len(result) > runtime_k:
            result = result.head(runtime_k).reset_index(drop=True)
        return result

    # ── FILTERED PATH: build candidate mask, then brute-force distances on subset ──
    n = len(X_all)
    cand = np.ones(n, dtype=bool)

    # 0) price filter (pre-apply to reduce work)
    thr = _parse_price(min_price) if has_per_call_price else float(price_filter)
    print(f"[DEBUG] call_ml_unsuper: applying pre price_filter >= {thr}")
    if model_price.size == n:
        cand &= (model_price >= float(thr))
    else:
        print("[WARN] model_price length mismatch; skipping price filter")

    # 1) feature-based filters (on trained features)
    fm = _build_feature_mask(X_all, feat_cols, routed_feat)
    if fm is not None:
        cand &= fm

    # 2) overlay-based filters (attributes that live only in overlay_df)
    om = _build_overlay_mask(overlay_df, row_indices, routed_ov)
    if om is not None:
        cand &= om

    if not cand.any():
        print("[DEBUG] call_ml_unsuper: no candidates after filters")
        return None

    cand_idx = np.flatnonzero(cand)
    print(f"[DEBUG] call_ml_unsuper: {cand_idx.size} candidates after filters (of {n})")

    # 3) Compute distances on the filtered subset (Euclidean; same metric as sklearn default)
    #    Scale both sides with stored mean/scale. X_all is unscaled, like training input pre-scaler.
    Xsub = (X_all[cand_idx].astype(np.float32) - mean) / scale
    if w is not None:
        Xsub = Xsub * np.sqrt(w)
    # qv is already scaled, shape (1, d). Compute distances to each candidate row.
    # Using sqrt is not necessary for ranking, but we print comparable numbers; keep it.
    diff  = Xsub - qv
    dists = np.sqrt(np.sum(diff * diff, axis=1))

    # 4) Take nearest top
    take = min(query_k, dists.size)
    if take == 0:
        print("[DEBUG] call_ml_unsuper: no distances computed")
        return None

    order = np.argsort(dists)[:take]
    local = cand_idx[order]
    picked_dists = dists[order]
    print(f"[DEBUG] call_ml_unsuper: selected local indices {local.tolist()} with distances {picked_dists.tolist()}")

    # 5) Map back to overlay_df via row_indices and return
    global_idx = [row_indices[i] for i in local]
    print(f"[DEBUG] call_ml_unsuper: mapping to overlay_df indices {global_idx}")
    result = overlay_df.loc[global_idx].reset_index(drop=True)
    if runtime_k > 0 and len(result) > runtime_k:
        result = result.head(runtime_k).reset_index(drop=True)
    if model_price.size:
        try:
            result = result.copy()
            result["price_in_exalts"] = model_price[local]
        except Exception:
            pass
    return result
