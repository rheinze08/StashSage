# File: poe2trade/utils/ml_unsuper_utils.py
# · v6.8 — add per-file in-process caching (2025-09-11)
# · v6.7 — robust to lowercase/underscore standardization (2025-07-06)

from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from poe2trade import poe2trade_root, knn_k, chaos_exalt, divine_exalt
from poe2trade.app import config_manager

# ────────────────────────── helpers ───────────────────────────
def _norm_token(s: str | None) -> str | None:
    """lowercase + replace whitespace with underscores; None → None."""
    if s is None:
        return None
    return re.sub(r"\s+", "_", str(s).strip().lower())

# ────────────────────────── price-filter globals ──────────────
_cfg_val  = config_manager.load_config().get("price_mirror_filter", "1e")
_PRICE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([ecd])\s*$", re.I)

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
    return amt

price_filter: float = _parse_price(_cfg_val)

def set_price_filter(val: str | float) -> None:
    """Update the numeric price_filter at runtime."""
    global price_filter
    price_filter = _parse_price(val)

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

    b = pickle.load(p.open("rb"))
    _bundle_cache[key] = b
    _bundle_mtime[key] = mt
    print(f"[DEBUG] Loaded KNN bundle '{p.name}' into cache")
    return b

# ───────────────────────── public API ─────────────────────────
def call_ml(
    category: str,
    segment: Optional[str],
    X: pd.DataFrame,
    top: int = knn_k
) -> Optional[pd.DataFrame]:
    """
    Unsupervised KNN lookup.

    Parameters
    ----------
    category : str
        Normalized category name (underscores, lowercase).
    segment : Optional[str]
        Defence-segment key for armour, or None for jewellery.
    X : pd.DataFrame
        One-row feature-DataFrame matching trained feature_cols.
    top : int
        Maximum number of neighbours to return.

    Returns
    -------
    pd.DataFrame or None
        Overlay data of up to `top` nearest neighbours after price-filter, or
        None if no model or no neighbours pass the filter.
    """
    # normalize inputs and lower-case input columns (robust to standardization)
    category_n = _norm_token(category)
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

    nn: NearestNeighbors = art["nn_model"]
    mean         = np.asarray(art["scaler_data"]["mean"], dtype=np.float32)
    scale        = np.asarray(art["scaler_data"]["scale"], dtype=np.float32)
    # defensive: avoid divide-by-zero if any scale elements are 0
    scale        = np.where(scale == 0, 1.0, scale)

    feat_cols    = art["feature_cols"]
    X_all        = art["X_all"]
    model_price  = np.asarray(art.get("model_price", []), dtype=np.float32)
    overlay_df   = art["overlay_df"]
    row_indices  = art["row_indices"]

    # 1) Reindex query to match training features & scale
    print(f"[DEBUG] call_ml_unsuper: reindexing query X to feat_cols ({len(feat_cols)} cols)")
    q = X.reindex(columns=feat_cols, fill_value=0.0)
    qv = (q.to_numpy(dtype=np.float32) - mean) / scale

    # 2) Run KNN
    n_query = min(top, len(X_all))
    print(f"[DEBUG] call_ml_unsuper: running KNN (k={n_query})")
    dist, ix = nn.kneighbors(qv, n_neighbors=n_query)
    dists = dist.flatten()
    idxs  = ix.flatten()

    # 3) Apply price filter (keep neighbors whose model_price >= threshold)
    print(f"[DEBUG] call_ml_unsuper: applying price_filter >= {price_filter}")
    mask = model_price[idxs] >= price_filter
    idxs = idxs[mask]
    dists = dists[mask]
    if len(idxs) == 0:
        print("[DEBUG] call_ml_unsuper: no neighbors passed price_filter")
        return None

    # 4) Select top by ascending distance
    order = np.argsort(dists)
    sel   = order[:top]
    local = idxs[sel]
    print(f"[DEBUG] call_ml_unsuper: selected local indices {local.tolist()} with distances {dists[sel].tolist()}")

    # 5) Map back to overlay_df via row_indices and return
    global_idx = [row_indices[i] for i in local]
    print(f"[DEBUG] call_ml_unsuper: mapping to overlay_df indices {global_idx}")
    return overlay_df.loc[global_idx].reset_index(drop=True)
