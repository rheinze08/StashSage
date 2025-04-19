import os
import re
import pickle
import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    BaggingRegressor,
)
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import r2_score
from sklearn.neural_network import MLPRegressor
import xgboost as xgb

from poe2trade import poe2trade_root, divine_exalt, chaos_exalt

# ----------------------------------------------------------------------------
# Constants / pattern dictionaries – unchanged
# ----------------------------------------------------------------------------
_segment_base_candidates = {
    "ar_only": {"flat": ["# to armour"], "inc": ["#% increased armour"]},
    "ev_only": {"flat": ["# to evasion rating"], "inc": ["#% increased evasion rating"]},
    "es_only": {"flat": ["# to maximum energy shield"], "inc": ["#% increased energy shield"]},
    "ar_ev_only": {
        "flat": ["# to armour", "# to evasion rating"],
        "inc": [
            "#% increased armour",
            "#% increased evasion rating",
            "#% increased armour and evasion",
        ],
    },
    "ar_es_only": {
        "flat": ["# to armour", "# to maximum energy shield"],
        "inc": [
            "#% increased armour",
            "#% increased energy shield",
            "#% increased armour and energy shield",
        ],
    },
    "ev_es_only": {
        "flat": ["# to evasion rating", "# to maximum energy shield"],
        "inc": [
            "#% increased evasion rating",
            "#% increased energy shield",
            "#% increased evasion and energy shield",
        ],
    },
    "all_three": {
        "flat": [
            "# to armour",
            "# to evasion rating",
            "# to maximum energy shield",
        ],
        "inc": [
            "#% increased armour",
            "#% increased evasion rating",
            "#% increased energy shield",
            "#% increased armour and evasion",
            "#% increased armour and energy shield",
            "#% increased evasion and energy shield",
        ],
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
    "Quality",
    "Corrupted_Flag",
]

_g_pattern_dict: dict[str, str] = {}

# ----------------------------------------------------------------------------
# KMeans clustering feature configuration per category
# ----------------------------------------------------------------------------
_kmeans_clustering_features = {
    # Default features for clustering by segment
    "body_armour": ["flat_base", "inc_base", "fire_res", "cold_res", "light_res", "chaos_res"],
    "boots":        ["flat_base", "inc_base", "fire_res", "cold_res", "light_res", "chaos_res", "move_speed"],
    "gloves":       ["flat_base", "inc_base", "fire_res", "cold_res", "light_res", "chaos_res"],
    "helmet":       ["flat_base", "inc_base", "fire_res", "cold_res", "light_res", "chaos_res"],
}

# ----------------------------------------------------------------------------
# Helper functions (unchanged except for k‑means README writer)
# ----------------------------------------------------------------------------
def _inverted_pattern_lookup(col_name: str) -> str:
    inv_map = {v: k for k, v in _g_pattern_dict.items()}
    return inv_map.get(col_name, col_name)


def _format_drop_name(col_name: str) -> str:
    pat_str = _inverted_pattern_lookup(col_name)
    return f"{col_name} (pattern: {pat_str})"


def _load_excel_with_price_in_exalts(excel_file: str, exalt_divine: float, exalt_chaos: float):
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        print(f"[DEBUG] Error reading file => '{excel_file}', {e}")
        return None

    if "Price" not in df.columns or "Currency" not in df.columns:
        print("[DEBUG] Excel missing 'Price' or 'Currency' => can't proceed.")
        return None

    df["Price_in_Exalts"] = np.nan
    c_lower = df["Currency"].astype(str).str.lower()

    df.loc[c_lower == "exalted", "Price_in_Exalts"] = df["Price"]
    df.loc[c_lower == "divine",  "Price_in_Exalts"] = df["Price"] * exalt_divine
    df.loc[c_lower == "chaos",   "Price_in_Exalts"] = df["Price"] * exalt_chaos

    df.dropna(subset=["Price_in_Exalts"], inplace=True)
    df = df[df["Price_in_Exalts"] > 0]
    if df.empty:
        print("[DEBUG] No valid priced rows => can't train.")
        return None
    return df


# ----------------------------------------------------------------------------
# Main training entry
# ----------------------------------------------------------------------------
def train_model_from_excel(
    input_excel_file: str,
    category: str = "default_model",
    exalt_divine: float = divine_exalt,
    exalt_chaos: float = chaos_exalt,
    use_scaler: bool = True,
):
    """
    Orchestrates reading the Excel of items, extracting features, and training
    either a single-model or segmented (K‑Means + per-cluster) models.

    1) Load and trim prices -> Price_in_Exalts
    2) Build feature DataFrame (unique mod patterns + base features)
    3) If segmented category (body_armour, boots, gloves, helmet):
         • run K‑Means segmentation
         • train per-cluster regressors
       Else:
         • train a single regression pipeline (MLP, RF, XGB, ET, GBR)
    """
    df = _load_excel_with_price_in_exalts(input_excel_file, exalt_divine, exalt_chaos)
    if df is None or df.empty:
        print("[DEBUG] => No valid data after reading => abort.")
        return

    # Trim outliers in Price_in_Exalts
    lower_bound = df["Price_in_Exalts"].quantile(0.05)
    upper_bound = df["Price_in_Exalts"].quantile(0.95)
    df = df[(df["Price_in_Exalts"] >= lower_bound) & (df["Price_in_Exalts"] <= upper_bound)]
    if df.empty:
        print("[DEBUG] => all data was out of range => abort.")
        return
    print(
        f"[DEBUG] => after outlier trim => {len(df)} rows remain => "
        f"range => {df['Price_in_Exalts'].min():.2f}..{df['Price_in_Exalts'].max():.2f}"
    )

    cat_norm = category.lower().replace(" ", "_")

    # Build the features
    model_df, feature_cols = _build_feature_dataframe(df)
    if model_df is None or feature_cols is None:
        print("[DEBUG] => failed to build features => abort.")
        return

    _print_all_patterns()

    # If this category supports segmentation, delegate to segmented trainer
    if cat_norm in ["body_armour", "boots", "gloves", "helmet"]:
        print(f"[SEGMENTED] => Category='{cat_norm}' => calling _train_segmented_models(...)")
        _train_segmented_models(model_df, cat_norm, use_scaler)
        return

    # Single-model pipeline (no segmentation)
    print(f"[DEBUG] => single-model approach => cat='{cat_norm}' => building X, y")
    X = model_df[feature_cols]
    y = model_df["Price_in_Exalts"]
    if len(X) < 5:
        print(f"[DEBUG] => not enough rows => {len(X)} => skip.")
        return

    # Drop zero‑variance features once
    zc = X.columns[X.nunique(dropna=False) <= 1]
    if len(zc) > 0:
        print("[DEBUG] => dropping zero-variance =>")
        for col_ in zc:
            print(f"   {_format_drop_name(col_)}")
        X = X.drop(columns=zc)
        feature_cols = [c for c in feature_cols if c not in zc]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model_dir = Path(poe2trade_root) / "db" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    print(f"[DEBUG] => saving single-model artifacts => {model_dir}")

    for model_type in ["mlp", "rf", "xgb", "et", "gbr"]:
        pipeline_or_search = _build_pipeline(model_type, use_scaler)
        pipeline_or_search.fit(X_train, y_train)
        if hasattr(pipeline_or_search, "best_estimator_"):
            final_model = pipeline_or_search.best_estimator_
            print(f"[DEBUG] => {model_type.upper()} => best params => {pipeline_or_search.best_params_}")
        else:
            final_model = pipeline_or_search

        y_pred = final_model.predict(X_test)
        r2_val = r2_score(y_test, y_pred)
        print(f"[DEBUG] => single-model => {model_type.upper()}, R^2={r2_val:.4f}")

        artifacts = {
            "model_pipeline": final_model,
            "pattern_dict": _g_pattern_dict.copy(),
            "base_features": _g_base_features,
            "feature_cols": list(X.columns),
            "use_scaler": use_scaler,
            "model_type": model_type,
        }
        mpath = model_dir / f"{cat_norm}_{model_type}_model.pkl"
        with open(mpath, "wb") as f_:
            pickle.dump(artifacts, f_)
        print(f"[DEBUG] => saved => {mpath}")

        # Write a README summarizing the model
        readme_path = model_dir / f"{cat_norm}_{model_type}_model_readme.txt"
        model_est_ = final_model.named_steps["model"]
        with open(readme_path, "w", encoding="utf-8") as r_:
            r_.write(f"=== {cat_norm} Model Readme ===\n\n")
            r_.write(f"Model Type: {model_type.upper()}\n")
            r_.write(f"R^2 on test set: {r2_val:.4f}\n")
            r_.write(f"use_scaler: {use_scaler}\n\n")
            r_.write("Target => Price_in_Exalts\n\n")
            r_.write("Features =>\n")
            for feat in X.columns:
                r_.write(f"  {_format_drop_name(feat)}\n")
            r_.write("\n")
            if hasattr(model_est_, "feature_importances_"):
                fi = model_est_.feature_importances_
                sidx = np.argsort(fi)[::-1]
                r_.write("Feature Importances:\n")
                for rank_, idx_ in enumerate(sidx, start=1):
                    c_ = X.columns[idx_]
                    r_.write(f"{rank_:2d}) {_format_drop_name(c_):50s} importance={fi[idx_]:.5f}\n")
            else:
                r_.write("Feature importances not available.\n")


# ----------------------------------------------------------------------------
# Segmented training (K‑Means + per‑cluster regressors)
# ----------------------------------------------------------------------------
def _train_segmented_models(df_all: pd.DataFrame, cat_norm: str, use_scaler: bool):
    """
    For a given category, segments the data by defense combination (ar_only, etc.),
    drops zero‑variance features at the segment level, then for each segment:
      1) Builds clustering features via _build_multi_base_kmeans_features(...)
      2) Runs KMeans(n_clusters=3)
      3) Trains a regressor per cluster (mlp, rf, xgb, et, gbr)
      4) Saves artifacts and READMEs.
    """
    model_dir = Path(poe2trade_root) / "db" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    segs = [
        "ar_only",
        "ev_only",
        "es_only",
        "ar_ev_only",
        "ar_es_only",
        "ev_es_only",
        "all_three",
    ]
    for seg_name in segs:
        mask = _segment_filter(df_all, seg_name)
        seg_df = df_all[mask].copy()
        if seg_df.empty:
            print(f"[SEGMENTED] => seg='{seg_name}', no rows => skip.")
            continue
        scount = len(seg_df)
        print(f"[SEGMENTED] => seg='{seg_name}', {scount} rows.")
        if scount < 5:
            print(f"[SEGMENTED] => not enough => skip seg='{seg_name}'")
            continue

        # Drop zero‑variance at segment level once
        zc = seg_df.columns[seg_df.nunique(dropna=False) <= 1]
        if len(zc) > 0:
            print(f"[SEGMENTED] => seg='{seg_name}', removing zero-variance =>")
            for c_ in zc:
                print(f"   {_format_drop_name(c_)}")
            seg_df.drop(columns=zc, inplace=True)

        # Build clustering features, now category-specific
        kmeans_df, kmeans_map = _build_multi_base_kmeans_features(seg_df, seg_name, cat_norm)
        if kmeans_df is None or kmeans_df.empty:
            print(f"[SEGMENTED] => seg='{seg_name}', no KMeans features => skip.")
            continue

        print(f"[SEGMENTED] => seg='{seg_name}', KMeans features =>")
        for col_ in kmeans_df.columns:
            patlist_ = sorted(kmeans_map[col_])
            print(f"   {col_} => {patlist_}")

        if kmeans_df.sum().sum() == 0.0:
            print(f"[SEGMENTED] => seg='{seg_name}', sum=0 => skip.")
            continue

        # Fit and assign clusters
        km = KMeans(n_clusters=3, random_state=42)
        km.fit(kmeans_df)
        labs = km.predict(kmeans_df)
        seg_df["cluster_label"] = labs

        vc = seg_df["cluster_label"].value_counts().sort_index()
        for cidx in vc.index:
            print(f"[SEGMENTED] => seg='{seg_name}', cluster={cidx} => {vc[cidx]} rows")

        # Save the KMeans artifact
        artifact = {
            "kmeans_model": km,
            "features_for_kmeans": list(kmeans_df.columns),
        }
        kpath = model_dir / f"{cat_norm}_{seg_name}_kmeans.pkl"
        with open(kpath, "wb") as fk:
            pickle.dump(artifact, fk)
        print(f"[SEGMENTED] => saved => {kpath}\n")

        # Write KMeans README
        readme_km = model_dir / f"{cat_norm}_{seg_name}_kmeans_readme.txt"
        with open(readme_km, "w", encoding="utf-8") as rk:
            rk.write(f"=== {cat_norm} • segment '{seg_name}' • K‑Means summary ===\n\n")
            rk.write("Features used:\n")
            for feat in kmeans_df.columns:
                rk.write(f"  {feat}\n")
            rk.write("\nCluster sizes:\n")
            for cid_, n_ in vc.items():
                rk.write(f"  Cluster {cid_}: {n_} rows\n")
            rk.write("\nCentroids (same feature order as above):\n")
            for cid_, center in enumerate(km.cluster_centers_):
                center_str = ", ".join(f"{val:.4f}" for val in center)
                rk.write(f"  Cluster {cid_}: [{center_str}]\n")
        print(f"[SEGMENTED] => README (kmeans) => {readme_km}\n")

        # Train per‑cluster models (keep same feature set as segment)
        for cid_ in range(3):
            subRows = seg_df[seg_df["cluster_label"] == cid_].copy()
            if subRows.empty:
                print(f"[SEGMENTED] => seg='{seg_name}', cluster={cid_} => 0 rows => skip.")
                continue
            if "Price_in_Exalts" not in subRows.columns:
                print(f"[SEGMENTED] => seg='{seg_name}', cluster={cid_}, missing Price_in_Exalts => skip.")
                continue

            subY = subRows["Price_in_Exalts"]
            subX = subRows.drop(columns=["Price_in_Exalts", "cluster_label"])

            if len(subX) < 5:
                print(f"[SEGMENTED] => seg='{seg_name}', cluster={cid_}, not enough after filtering => skip.")
                continue
            print(f"[SEGMENTED] => training => seg='{seg_name}', cluster={cid_}, {len(subX)} rows")

            X_train, X_test, y_train, y_test = train_test_split(
                subX, subY, test_size=0.2, random_state=42
            )

            for model_type in ["mlp", "rf", "xgb", "et", "gbr"]:
                pipeline_or_search = _build_pipeline(model_type, use_scaler)
                pipeline_or_search.fit(X_train, y_train)
                if hasattr(pipeline_or_search, "best_estimator_"):
                    final_model = pipeline_or_search.best_estimator_
                    print(f"[SEGMENTED] => seg='{seg_name}', cluster={cid_}, model={model_type.upper()} => best={pipeline_or_search.best_params_}")
                else:
                    final_model = pipeline_or_search

                y_pred = final_model.predict(X_test)
                r2_ = r2_score(y_test, y_pred)
                print(f"[SEGMENTED] => seg='{seg_name}', cluster={cid_}, model={model_type.upper()}, R^2={r2_:.4f}")

                out_path = model_dir / f"{cat_norm}_{seg_name}_cluster{cid_}_{model_type}_model.pkl"
                artifact2 = {
                    "model_pipeline": final_model,
                    "pattern_dict": _g_pattern_dict.copy(),
                    "base_features": _g_base_features,
                    "feature_cols": list(subX.columns),
                    "use_scaler": use_scaler,
                    "model_type": model_type,
                    "segment_name": seg_name,
                    "cluster_id": cid_,
                }
                with open(out_path, "wb") as ff_:
                    pickle.dump(artifact2, ff_)
                print(f"[SEGMENTED] => saved => {out_path}")

                # Write cluster-model README
                readme_path = model_dir / f"{cat_norm}_{seg_name}_cluster{cid_}_{model_type}_model_readme.txt"
                model_est_ = final_model.named_steps["model"]
                with open(readme_path, "w", encoding="utf-8") as r_:
                    r_.write(f"=== {cat_norm} seg='{seg_name}' cluster={cid_} Model Readme ===\n\n")
                    r_.write(f"Model Type: {model_type.upper()}\n")
                    r_.write(f"R^2 on test set: {r2_:.4f}\n")
                    r_.write(f"use_scaler: {use_scaler}\n\n")
                    r_.write("Target => Price_in_Exalts\n\nFeatures =>\n")
                    for feat_ in subX.columns:
                        r_.write(f"  {_format_drop_name(feat_)}\n")
                    if hasattr(model_est_, "feature_importances_"):
                        fi = model_est_.feature_importances_
                        sidx = np.argsort(fi)[::-1]
                        r_.write("\nFeature Importances:\n")
                        for rank_, idxval_ in enumerate(sidx, start=1):
                            col_ = subX.columns[idxval_]
                            r_.write(f"{rank_:2d}) {_format_drop_name(col_):50s} importance={fi[idxval_]:.5f}\n")
                    else:
                        r_.write("\nFeature importances not available.\n")
                print(f"[SEGMENTED] => readme => {readme_path}\n")


# ----------------------------------------------------------------------------
# K‑Means helper with category-specific features
# ----------------------------------------------------------------------------
def _build_multi_base_kmeans_features(seg_df: pd.DataFrame, seg_name: str, cat_norm: str):
    """
    Builds a DataFrame of clustering features based on the segment (e.g. 'ar_only')
    and the item category (cat_norm).  We look up which features to compute from
    _kmeans_clustering_features[cat_norm], then populate:
      - flat_base, inc_base from _segment_base_candidates
      - fire_res, cold_res, light_res, chaos_res from _resistance_candidates
      - optional move_speed (for boots) from pattern '#% increased movement speed'

    Returns (dataframe_of_features, pattern_map).
    """
    if seg_name not in _segment_base_candidates:
        print(f"[SEGMENTED] => unknown seg_name='{seg_name}' => skip.")
        return None, None

    clustering_feats = _kmeans_clustering_features.get(cat_norm)
    if not clustering_feats:
        print(f"[SEGMENTED] => no clustering config for category '{cat_norm}' => skip.")
        return None, None

    # Initialize all clustering columns to zero
    out_df = pd.DataFrame(index=seg_df.index, columns=clustering_feats, data=0.0)
    pattern_map = {col: set() for col in clustering_feats}
    inv_map = _g_pattern_dict  # pattern -> feature column name

    # Populate flat & inc base values
    for pat_ in _segment_base_candidates[seg_name]["flat"]:
        if pat_ in inv_map:
            fcol = inv_map[pat_]
            if fcol in seg_df.columns and "flat_base" in out_df:
                out_df["flat_base"] += seg_df[fcol]
                pattern_map["flat_base"].add(pat_)

    for pat_ in _segment_base_candidates[seg_name]["inc"]:
        if pat_ in inv_map:
            fcol = inv_map[pat_]
            if fcol in seg_df.columns and "inc_base" in out_df:
                out_df["inc_base"] += seg_df[fcol]
                pattern_map["inc_base"].add(pat_)

    # Populate resistances
    for rp in _resistance_candidates:
        if rp in inv_map:
            fcol = inv_map[rp]
            if fcol in seg_df.columns:
                if "fire_res" in out_df and "fire" in rp:
                    out_df["fire_res"] += seg_df[fcol]; pattern_map["fire_res"].add(rp)
                if "cold_res" in out_df and "cold" in rp:
                    out_df["cold_res"] += seg_df[fcol]; pattern_map["cold_res"].add(rp)
                if "light_res" in out_df and "lightning" in rp:
                    out_df["light_res"] += seg_df[fcol]; pattern_map["light_res"].add(rp)
                if "chaos_res" in out_df and "chaos" in rp:
                    out_df["chaos_res"] += seg_df[fcol]; pattern_map["chaos_res"].add(rp)

    # Optional: movement speed for boots
    if "move_speed" in clustering_feats:
        mv_pat = "#% increased movement speed"
        if mv_pat in inv_map:
            fcol = inv_map[mv_pat]
            if fcol in seg_df.columns:
                out_df["move_speed"] += seg_df[fcol]
                pattern_map["move_speed"].add(mv_pat)

    # If all zeros, skip
    if out_df.sum().sum() == 0.0:
        return None, None

    return out_df, pattern_map


# ----------------------------------------------------------------------------
# Pattern & feature DF builders – unchanged
# ----------------------------------------------------------------------------
def _print_all_patterns():
    if not _g_pattern_dict:
        print("[DEBUG] => no patterns in _g_pattern_dict")
        return

    print("\n[DEBUG] => global pattern map =>")
    sorted_pairs = sorted(_g_pattern_dict.items(), key=lambda kv: kv[1])
    for pat_text, f_col in sorted_pairs:
        print(f"  {f_col} (pattern: {pat_text})")


def _build_feature_dataframe(df: pd.DataFrame):
    global _g_pattern_dict
    _g_pattern_dict.clear()

    df["Corrupted_Flag"] = np.where(df.get("Corrupted", "").str.lower() == "yes", 1.0, 0.0)
    df["Quality"] = pd.to_numeric(df.get("Quality", 0), errors="coerce").fillna(0.0)

    max_mod = 0
    for col_ in df.columns:
        if col_.startswith("unique_mod") and col_.endswith("_pattern"):
            try:
                idx_ = int(col_.replace("unique_mod", "").replace("_pattern", ""))
                if idx_ > max_mod:
                    max_mod = idx_
            except Exception:
                pass

    all_patterns = set()
    for i in range(1, max_mod + 1):
        pat_col = f"unique_mod{i}_pattern"
        if pat_col in df.columns:
            for pval in df[pat_col].dropna().unique():
                all_patterns.add(str(pval))

    print(f"[DEBUG] => found {len(all_patterns)} distinct patterns across 'unique_mod' columns")

    idx = 1
    for pat_ in sorted(all_patterns):
        _g_pattern_dict[pat_] = f"f{idx}"
        idx += 1

    base_cols = _g_base_features
    all_feat_cols = base_cols + list(_g_pattern_dict.values())
    out_df = pd.DataFrame(index=df.index, columns=all_feat_cols, data=0.0)

    for bc_ in base_cols:
        if bc_ in df.columns:
            out_df[bc_] = df[bc_].fillna(0).astype(float)

    for idx_, row_ in df.iterrows():
        for j_ in range(1, max_mod + 1):
            pat_col = f"unique_mod{j_}_pattern"
            val_col = f"unique_mod{j_}_value"
            pat_str = row_.get(pat_col)
            val_ = float(row_.get(val_col, 0) or 0)
            if pat_str is not None:
                fcol = _g_pattern_dict.get(str(pat_str))
                if fcol in out_df.columns:
                    out_df.at[idx_, fcol] += val_

    if "Price_in_Exalts" not in df.columns:
        print("[DEBUG] => missing 'Price_in_Exalts' => cannot train.")
        return None, None

    out_df["Price_in_Exalts"] = df["Price_in_Exalts"]
    out_df.dropna(subset=["Price_in_Exalts"], inplace=True)
    if out_df.empty:
        print("[DEBUG] => no rows left => can't train => empty DF.")
        return None, None

    print("\n[DEBUG] => final feature columns => (excluding Price_in_Exalts):")
    for c_ in all_feat_cols:
        print(f"   {c_} => pattern: {_inverted_pattern_lookup(c_)}")

    return out_df, all_feat_cols


def _segment_filter(df: pd.DataFrame, seg_name: str) -> pd.Series:
    ar = df.get("Deflated_Armour", 0)
    ev = df.get("Deflated_Evasion", 0)
    es = df.get("Deflated_EnergyShield", 0)

    if seg_name == "ar_only":
        return (ar > 0) & (ev == 0) & (es == 0)
    elif seg_name == "ev_only":
        return (ev > 0) & (ar == 0) & (es == 0)
    elif seg_name == "es_only":
        return (es > 0) & (ar == 0) & (ev == 0)
    elif seg_name == "ar_ev_only":
        return (ar > 0) & (ev > 0) & (es == 0)
    elif seg_name == "ar_es_only":
        return (ar > 0) & (es > 0) & (ev == 0)
    elif seg_name == "ev_es_only":
        return (ev > 0) & (es > 0) & (ar == 0)
    elif seg_name == "all_three":
        return (ar > 0) & (ev > 0) & (es > 0)
    else:
        return pd.Series(False, index=df.index)


# ----------------------------------------------------------------------------
# Pipeline builder: Bagged‑MLP + grids – unchanged
# ----------------------------------------------------------------------------
def _build_pipeline(model_type: str, use_scaler: bool):
    steps = []
    if use_scaler:
        steps.append(("scaler", StandardScaler()))

    if model_type == "rf":
        base_model = RandomForestRegressor(random_state=42)
        param_grid = {
            "model__n_estimators": [100, 200, 300],
            "model__max_depth": [None, 6, 12],
            "model__min_samples_split": [2, 5, 10],
        }
    elif model_type == "xgb":
        base_model = xgb.XGBRegressor(random_state=42, objective="reg:squarederror")
        param_grid = {
            "model__n_estimators": [100, 200, 400],
            "model__max_depth": [3, 6, 10],
            "model__learning_rate": [0.01, 0.05, 0.1],
            "model__subsample": [0.8, 1.0],
            "model__colsample_bytree": [0.8, 1.0],
        }
    elif model_type == "et":
        base_model = ExtraTreesRegressor(random_state=42)
        param_grid = {
            "model__n_estimators": [100, 200, 300],
            "model__max_depth": [None, 6, 12],
            "model__min_samples_split": [2, 5, 10],
        }
    elif model_type == "gbr":
        base_model = GradientBoostingRegressor(random_state=42)
        param_grid = {
            "model__n_estimators": [100, 200, 400],
            "model__max_depth": [3, 6, 10],
            "model__learning_rate": [0.01, 0.05, 0.1],
            "model__subsample": [0.8, 1.0],
        }
    else:  # 'mlp'
        base_mlp = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation="relu",
            solver="adam",
            learning_rate_init=0.001,
            alpha=0.0005,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=25,
            max_iter=5000,
            verbose=False,
        )

        base_model = BaggingRegressor(
            estimator=base_mlp,
            n_estimators=10,
            max_samples=0.8,
            max_features=1.0,
            bootstrap=True,
            n_jobs=-1,
            random_state=42,
            verbose=0,
        )

        param_grid = {
            "model__n_estimators": [5, 10, 15],
            "model__estimator__hidden_layer_sizes": [
                (128, 64, 32),
                (160, 80, 40),
                (200, 100, 50),
            ],
            "model__estimator__alpha": [0.0001, 0.0005, 0.001],
            "model__estimator__learning_rate_init": [0.0005, 0.001, 0.002],
        }

    pipeline = Pipeline(steps + [("model", base_model)])
    gs = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        scoring="r2",
        cv=3,
        n_jobs=-1,
        verbose=0,
        refit=True,
    )
    return gs
