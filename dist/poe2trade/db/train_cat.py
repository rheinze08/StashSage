import os
import argparse
import pandas as pd
from poe2trade.db import submodule_path
from poe2trade.utils.train_utils import train_model_from_excel

def main(item_categories):
    """
    For each item_category, this script:
      1) Builds a path to:
           poe2trade/db/files/<category>/<category>_agg_parsed_features.xlsx
      2) If it exists, calls train_model_from_excel(...) to train all models,
         which saves separate model artifacts for MLP, RF, and XGB.
      3) Saves the models to poe2trade/db/models/.

    The user can pass multiple categories in one call, e.g.:
      python train_script.py Body_Armour Boots Gloves
    """
    for item_category in item_categories:
        print(f"Training models for category: {item_category}")

        category_directory = item_category.replace(" ", "_")
        category_folder = os.path.join(submodule_path, "files", category_directory)
        if not os.path.exists(category_folder):
            print(f"Category folder {category_folder} does not exist. Skipping.")
            continue

        file_name = f"{category_directory}_agg_parsed_features.xlsx"
        file_path = os.path.join(category_folder, file_name)
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}. Skipping training for {item_category}.")
            continue

        train_model_from_excel(file_path, item_category)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train ML models for categories on <category>_agg_parsed_features.xlsx"
    )
    parser.add_argument(
        "item_categories", nargs="+", type=str,
        help="Categories to train models for (e.g. 'Body_Armour')."
    )
    args = parser.parse_args()
    main(args.item_categories)
