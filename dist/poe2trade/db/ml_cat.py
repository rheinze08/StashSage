import os
import argparse
import pandas as pd
from pathlib import Path
from poe2trade.db import submodule_path
from poe2trade.utils.ml_utils import call_ml
# We import call_ml_segmented so we can do cluster-based predictions for segmented categories.
from poe2trade.utils.gui_utils import call_ml_segmented


###############################################################################
# 1) Define which categories are segmented
###############################################################################
SEGMENTED_CATEGORIES = ["body_armour", "gloves", "boots", "helmet"]

def ensure_models_trained(item_category, features_file_path):
    """
    Checks if all three single-model (MLP, RF, XGB) .pkl files exist for item_category.
    If any are missing, trains them from the Excel file.

    HOWEVER, if item_category is in SEGMENTED_CATEGORIES, we skip single-model checks
    because we rely on the cluster-based submodels for that category.
    """
    cat_norm = item_category.lower().replace(" ", "_")

    # 2) If category is segmented, do NOT attempt to train single-model .pkl
    if cat_norm in SEGMENTED_CATEGORIES:
        print(f"[DEBUG ml_cat] Category '{item_category}' is segmented => skip single-model check.")
        return

    model_dir = Path(submodule_path) / "models"
    model_files = {
        "mlp": model_dir / f"{cat_norm}_mlp_model.pkl",
        "rf":  model_dir / f"{cat_norm}_rf_model.pkl",
        "xgb": model_dir / f"{cat_norm}_xgb_model.pkl"
    }

    missing = [m_type for m_type, path in model_files.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing single-models for category '{item_category}': {missing}. "
                                f"Please train the models manually using: {features_file_path}")
    else:
        print(f"[DEBUG ml_cat] All single-models already trained for category '{item_category}'.")


def main(item_categories):
    """
    Applies the correct ML predictions to each category:
      - If category is segmented (body_armour, gloves, boots, helmet), skip ensure_models_trained,
        and call call_ml_segmented(...) on each row => cluster-based approach.
      - Else, ensure single-model .pkl exist => run call_ml(...) for each row => single-model approach.

    Writes the output to <category>_agg_parsed_features_ml.xlsx in the same folder.
    """
    for item_category in item_categories:
        print(f"Processing category: {item_category}")
        try:
            category_directory = item_category.replace(" ", "_")
            category_folder = os.path.join(submodule_path, "files", category_directory)
            if not os.path.exists(category_folder):
                print(f"Category folder {category_folder} does not exist. Skipping...")
                continue

            features_file_name = f"{category_directory}_agg_parsed_features.xlsx"
            features_file_path = os.path.join(category_folder, features_file_name)
            if not os.path.isfile(features_file_path):
                print(f"No parsed features file found for '{item_category}': {features_file_path}")
                continue

            # 1) Decide if category is segmented or not
            cat_norm = category_directory.lower()
            segmented = (cat_norm in SEGMENTED_CATEGORIES)

            # 2) For segmented => skip single-model check. Otherwise => ensure single-model present
            if not segmented:
                ensure_models_trained(item_category, features_file_path)
            else:
                print(f"[DEBUG ml_cat] '{item_category}' is segmented => skip single-model training check")

            df = pd.read_excel(features_file_path, sheet_name="Report")
            if df.empty:
                print(f"No rows in {features_file_path}. Skipping...")
                continue

            # We collect predictions into lists => same final columns
            preds_mlp = []
            preds_rf = []
            preds_xgb = []
            preds_min = []
            preds_max = []
            preds_avg = []
            actual_prices = []

            # 3) Depending on segmented or not, call call_ml_segmented(...) or call_ml(...)
            for i, (_, row_data) in enumerate(df.iterrows()):
                row_dict = row_data.to_dict()

                if segmented:
                    result = call_ml_segmented(row_dict)
                else:
                    result = call_ml(row_dict, record_index=i)

                if result is None:
                    preds_mlp.append(None)
                    preds_rf.append(None)
                    preds_xgb.append(None)
                    preds_min.append(None)
                    preds_max.append(None)
                    preds_avg.append(None)
                    actual_prices.append(None)
                else:
                    predictions = result.get("predictions", {})
                    preds_mlp.append(predictions.get("mlp"))
                    preds_rf.append(predictions.get("rf"))
                    preds_xgb.append(predictions.get("xgb"))
                    preds_min.append(result.get("min"))
                    preds_max.append(result.get("max"))
                    preds_avg.append(result.get("average"))
                    actual_prices.append(result.get("actual"))

            # 4) Add the new columns => same naming for consistency
            df["Predicted_MLP"] = preds_mlp
            df["Predicted_RF"]  = preds_rf
            df["Predicted_XGB"] = preds_xgb
            df["Predicted_Min"] = preds_min
            df["Predicted_Max"] = preds_max
            df["Predicted_Avg"] = preds_avg
            df["Actual_Price"]  = actual_prices

            output_file_name = f"{category_directory}_agg_parsed_features_ml.xlsx"
            output_file_path = os.path.join(category_folder, output_file_name)
            df.to_excel(output_file_path, index=False, sheet_name="Report")
            print(f"ML predictions saved to: {output_file_path}")

        except Exception as e:
            print(f"Error processing category '{item_category}': {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run ML predictions for categories on <category>_agg_parsed_features.xlsx"
    )
    parser.add_argument(
        "item_categories", nargs="+", type=str,
        help="Categories to run ML on (e.g. 'Body_Armour')."
    )
    args = parser.parse_args()
    main(args.item_categories)
