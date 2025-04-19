import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
import xgboost as xgb

from poe2trade import poe2trade_root, chaos_exalt, divine_exalt

def _format_drop_name(col_name: str) -> str:
    """
    Simple helper for debug printing columns or features.  If you wish,
    you can map them to textual patterns.  For demonstration, we just
    return the col_name.  In 'train_utils', we had a more elaborate function
    that appended '(pattern: #...)' details.
    """
    return col_name

def _build_single_row_segmented(row: dict):
    """
    Creates a single-row DataFrame that matches the format used
    by the segmented training pipeline (body_armour, gloves, boots, helmet).

    Steps:
      1) We read from row => 'Deflated_Armour','Deflated_Evasion','Deflated_EnergyShield',
         'extra_socket_mod','Quality','Corrupted' => sets 'Corrupted_Flag'=1 if 'Yes' else 0.
      2) We gather all unique_mod{i}_pattern => local fX columns, so that the row’s
         patterns can map to numeric columns the same as in train_utils does.
      3) We fill the row with the pattern-based numeric values from unique_mod{i}_value,
         summing them if the same pattern appears multiple times.
      4) We also set row["ar_only"], row["ev_only"], etc. to identify the sub-segment
         just like the training code does, so we can figure out which cluster we belong to.

    Returns:
      (DataFrame with 1 row of numeric columns, local_pattern_map)
      If we want to see which patterns became "f1","f2", etc., we can examine local_pattern_map.
    """
    import pandas as pd

    def sfloat(v):
        try:
            return float(v or 0)
        except:
            return 0.0

    # Step A) Determine how many 'unique_modN' we have
    max_mod = 0
    for k_ in row.keys():
        if k_.startswith("unique_mod") and k_.endswith("_pattern"):
            try:
                idx_ = int(k_.replace("unique_mod","").replace("_pattern",""))
                if idx_ > max_mod:
                    max_mod = idx_
            except:
                pass

    # Step B) Gather up the distinct patterns
    unique_pats = set()
    for i_ in range(1, max_mod+1):
        pat_ = row.get(f"unique_mod{i_}_pattern", None)
        if pat_:
            unique_pats.add(pat_)

    # Step C) Build local pattern->fX mapping
    local_patterns = {}
    idx2 = 1
    for p_ in sorted(unique_pats):
        local_patterns[p_] = f"f{idx2}"
        idx2 += 1

    # Step D) The base columns we always expect from train_utils for segmented approach
    base_cols = [
        "Deflated_Armour", "Deflated_Evasion", "Deflated_EnergyShield",
        "extra_socket_mod", "Quality", "Corrupted_Flag"
    ]
    all_cols = base_cols + list(local_patterns.values())

    # Build single row of zeros
    single_df = pd.DataFrame(columns=all_cols)
    single_df.loc[0] = 0.0

    # Step E) Fill the base columns
    single_df.at[0, "Deflated_Armour"]       = sfloat(row.get("Deflated_Armour", 0))
    single_df.at[0, "Deflated_Evasion"]      = sfloat(row.get("Deflated_Evasion", 0))
    single_df.at[0, "Deflated_EnergyShield"] = sfloat(row.get("Deflated_EnergyShield", 0))
    single_df.at[0, "extra_socket_mod"]      = sfloat(row.get("extra_socket_mod", 0))
    single_df.at[0, "Quality"]               = sfloat(row.get("Quality", 0))

    cstr = str(row.get("Corrupted","No")).lower()
    single_df.at[0, "Corrupted_Flag"] = 1.0 if cstr == "yes" else 0.0

    # Step F) Fill pattern-based numeric columns
    for i2 in range(1, max_mod+1):
        pcol = f"unique_mod{i2}_pattern"
        vcol = f"unique_mod{i2}_value"
        pat_v = row.get(pcol, None)
        val_v = sfloat(row.get(vcol, 0))
        if pat_v and pat_v in local_patterns:
            fcol = local_patterns[pat_v]
            single_df.at[0, fcol] += val_v

    # Step G) Mark single-row segmentation flags (ar_only, es_only, etc.)
    #         This is purely for demonstration so we can do the same logic that
    #         train_utils uses to decide sub-segment.
    single_df["ar_only"]    = 0
    single_df["ev_only"]    = 0
    single_df["es_only"]    = 0
    single_df["ar_ev_only"] = 0
    single_df["ar_es_only"] = 0
    single_df["ev_es_only"] = 0
    single_df["all_three"]  = 0

    ar = single_df.at[0, "Deflated_Armour"]
    ev = single_df.at[0, "Deflated_Evasion"]
    es = single_df.at[0, "Deflated_EnergyShield"]

    if ar > 0 and ev == 0 and es == 0:
        single_df.at[0, "ar_only"] = 1
    elif ar == 0 and ev > 0 and es == 0:
        single_df.at[0, "ev_only"] = 1
    elif ar == 0 and ev == 0 and es > 0:
        single_df.at[0, "es_only"] = 1
    elif ar > 0 and ev > 0 and es == 0:
        single_df.at[0, "ar_ev_only"] = 1
    elif ar > 0 and es > 0 and ev == 0:
        single_df.at[0, "ar_es_only"] = 1
    elif ev > 0 and es > 0 and ar == 0:
        single_df.at[0, "ev_es_only"] = 1
    elif ar > 0 and ev > 0 and es > 0:
        single_df.at[0, "all_three"] = 1

    return single_df, local_patterns

def call_ml_segmented(row: dict) -> dict or None:
    """
    Inference for segmented items (e.g. 'body_armour', 'gloves', etc.).
    1) Build a single-row DataFrame with the same columns used at training time.
    2) Determine the sub-segment (ar_only, ev_only, etc.) from the displayed defences.
    3) Load the KMeans artifact => produce cluster_label.
    4) For each model type (mlp, rf, xgb, et, gbr), load that submodel => predict.
    5) Return min, max, median, mean, plus raw predictions.
    """
    from sklearn.cluster import KMeans

    cat_norm = row["Item Category"].lower().replace(" ", "_")
    single_df, _ = _build_single_row_segmented(row)
    if single_df is None or single_df.empty:
        return None

    # Figure out segment
    ar = single_df.at[0, "Deflated_Armour"]
    ev = single_df.at[0, "Deflated_Evasion"]
    es = single_df.at[0, "Deflated_EnergyShield"]

    if   ar>0 and ev==0 and es==0: seg_name="ar_only"
    elif ar==0 and ev>0 and es==0: seg_name="ev_only"
    elif ar==0 and ev==0 and es>0: seg_name="es_only"
    elif ar>0 and ev>0 and es==0:  seg_name="ar_ev_only"
    elif ar>0 and es>0 and ev==0:  seg_name="ar_es_only"
    elif ev>0 and es>0 and ar==0:  seg_name="ev_es_only"
    elif ar>0 and ev>0 and es>0:   seg_name="all_three"
    else:
        return None

    model_dir = Path(poe2trade_root)/"db"/"models"
    kmeans_path = model_dir / f"{cat_norm}_{seg_name}_kmeans.pkl"
    if not kmeans_path.is_file():
        return None

    with open(kmeans_path, "rb") as fk_:
        kmeans_art = pickle.load(fk_)

    if "kmeans_model" not in kmeans_art or "features_for_kmeans" not in kmeans_art:
        return None

    km_model: KMeans = kmeans_art["kmeans_model"]
    cluster_features = kmeans_art["features_for_kmeans"]

    cluster_df = single_df.reindex(columns=cluster_features, fill_value=0.0)
    cluster_label = km_model.predict(cluster_df)[0]

    # Now try multiple model types
    # We'll include the same 5 used in train_utils: mlp, rf, xgb, et, gbr.
    model_types = ["mlp","rf","xgb","et","gbr"]

    predictions = {}
    for model_type in model_types:
        sub_path = model_dir / f"{cat_norm}_{seg_name}_cluster{cluster_label}_{model_type}_model.pkl"
        if not sub_path.is_file():
            continue

        with open(sub_path, "rb") as f_:
            sub_art = pickle.load(f_)
        pipeline = sub_art["model_pipeline"]
        sub_feats = sub_art["feature_cols"]
        test_df = single_df.reindex(columns=sub_feats, fill_value=0.0)
        preds_ = pipeline.predict(test_df)
        predictions[model_type] = float(preds_[0])

    if not predictions:
        return None

    vals_ = list(predictions.values())
    min_ = min(vals_)
    max_ = max(vals_)
    mean_ = sum(vals_)/len(vals_)
    median_ = float(np.median(vals_))

    # Attempt to compute actual if present
    actual_val = row.get("Price_in_Exalts", None)
    if actual_val is None:
        if "Price" in row and "Currency" in row:
            c_ = str(row["Currency"]).lower()
            p_ = float(row["Price"] or 0)
            if c_ == "exalted":
                actual_val = p_
            elif c_ == "divine":
                actual_val = p_ * divine_exalt
            elif c_ == "chaos":
                actual_val = p_ * chaos_exalt

    # Return dictionary
    return {
        "predictions": predictions,
        "min": min_,
        "max": max_,
        "mean": mean_,
        "average": median_,   # <--- Now "average" is the median
        "actual": actual_val,
        "segment": seg_name,
        "cluster": cluster_label
    }

def call_ml(row: dict) -> dict or None:
    """
    Infers a single row's price in Exalts using the single-model approach
    from train_utils.py. We expect:
      - Category => e.g. "body_armour" or "default_model"
      - 'Deflated_Armour','Deflated_Evasion','Deflated_EnergyShield','extra_socket_mod','Quality','Corrupted'
      - 'unique_mod{i}_pattern','unique_mod{i}_value'

    We now look for up to 5 model types: mlp, rf, xgb, et, gbr.
    We'll return min, max, median, mean, plus the raw predictions if found.
    """
    cat_norm = row.get("Item Category","default_model").lower().replace(" ","_") or "default_model"
    model_dir = Path(poe2trade_root)/"db"/"models"

    # Find any single-model pickles for that category
    # We'll parse the pattern_dict from the first model file we find
    model_files = list(model_dir.glob(f"{cat_norm}_*_model.pkl"))
    if not model_files:
        return None

    with open(model_files[0],"rb") as f:
        artifacts = pickle.load(f)
    pattern_dict = artifacts["pattern_dict"]
    feature_cols = artifacts["feature_cols"]

    # Build single row
    single_df = pd.DataFrame(columns=feature_cols, index=[0], data=0.0)

    def sfloat(x):
        try:
            return float(x or 0)
        except:
            return 0.0

    single_df.at[0,"Deflated_Armour"]       = sfloat(row.get("Deflated_Armour",0))
    single_df.at[0,"Deflated_Evasion"]      = sfloat(row.get("Deflated_Evasion",0))
    single_df.at[0,"Deflated_EnergyShield"] = sfloat(row.get("Deflated_EnergyShield",0))
    single_df.at[0,"extra_socket_mod"]      = sfloat(row.get("extra_socket_mod",0))
    single_df.at[0,"Quality"]               = sfloat(row.get("Quality",0))
    cstr = str(row.get("Corrupted","No")).lower()
    single_df.at[0,"Corrupted_Flag"] = 1.0 if cstr=="yes" else 0.0

    # See how many unique_mod we have
    max_mod = 0
    for k_ in row.keys():
        if k_.startswith("unique_mod") and k_.endswith("_pattern"):
            try:
                idx_ = int(k_.replace("unique_mod","").replace("_pattern",""))
                if idx_>max_mod:
                    max_mod = idx_
            except:
                pass

    # Fill pattern columns
    for i_ in range(1, max_mod+1):
        pat_ = row.get(f"unique_mod{i_}_pattern", None)
        val_ = sfloat(row.get(f"unique_mod{i_}_value", 0))
        if pat_ in pattern_dict:
            fcol = pattern_dict[pat_]
            if fcol in single_df.columns:
                single_df.at[0, fcol] += val_

    # Attempt all 5 model types
    model_types = ["mlp","rf","xgb","et","gbr"]
    predictions = {}
    for model_type in model_types:
        p_ = model_dir/f"{cat_norm}_{model_type}_model.pkl"
        if not p_.is_file():
            continue
        with open(p_,"rb") as fm:
            art_ = pickle.load(fm)
        pipeline = art_["model_pipeline"]
        needed_cols = art_["feature_cols"]
        for nc in needed_cols:
            if nc not in single_df.columns:
                single_df[nc] = 0.0

        preds_ = pipeline.predict(single_df[needed_cols])
        predictions[model_type] = float(preds_[0])

    if not predictions:
        return None

    vals_ = list(predictions.values())
    min_pred = min(vals_)
    max_pred = max(vals_)
    mean_ = sum(vals_)/len(vals_)
    median_ = float(np.median(vals_))

    actual_val = row.get("Price_in_Exalts", None)
    if actual_val is None:
        if "Price" in row and "Currency" in row:
            c_ = str(row["Currency"]).lower().strip()
            p_ = sfloat(row["Price"])
            if c_=="exalted":
                actual_val = p_
            elif c_=="divine":
                actual_val = p_*divine_exalt
            elif c_=="chaos":
                actual_val = p_*chaos_exalt

    return {
        "predictions": predictions,
        "min": min_pred,
        "max": max_pred,
        "mean": mean_,
        "average": median_,  # median is used as "average"
        "actual": actual_val
    }
