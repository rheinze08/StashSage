import os
import glob
import argparse
import pandas as pd
from poe2trade.db import submodule_path
from poe2trade.utils.features_utils import features_excel_file

def main(item_categories):
    """
    This script runs feature extraction for each category by calling
    features_excel_file(...), producing e.g. <category>_agg_parsed_features.xlsx.

    Steps:
      1) For each item_category passed on the command line:
         a) Identify the category folder in poe2trade/db/files/<category>.
         b) Look for a single Excel file named "<category>_agg_parsed.xlsx".
         c) If found, read it, apply features_excel_file(...),
            and save the result as "<category>_agg_parsed_features.xlsx".
         d) If the file is not found or an error occurs, print a message and skip.

    Usage examples:
      python -m poe2trade.db.features_cat Body Armour
      python -m poe2trade.db.features_cat "Body Armour" "Weapons"
    """
    for item_category in item_categories:
        print(f"[INFO] Processing category: {item_category}")
        try:
            category_directory = item_category.replace(" ", "_")
            category_folder = os.path.join(submodule_path, "files", category_directory)
            if not os.path.exists(category_folder):
                print(f"[WARN] Category folder {category_folder} does not exist. Skipping...")
                continue

            # Input is named "<category>_agg_parsed.xlsx"
            input_file_name = f"{category_directory}_agg_parsed.xlsx"
            input_file_path = os.path.join(category_folder, input_file_name)
            print(f"[INFO] Looking for file: {input_file_path}")

            if not os.path.isfile(input_file_path):
                print(f"[WARN] No parsed file found for category '{item_category}': {input_file_path}")
                continue

            # Output => "<category>_agg_parsed_features.xlsx"
            output_file_name = f"{category_directory}_agg_parsed_features.xlsx"
            output_file_path = os.path.join(category_folder, output_file_name)
            print(f"[INFO] Will output to: {output_file_path}")

            print("[INFO] Running features_excel_file(...) now.")
            features_excel_file(input_file_path, output_file_path)
            print(f"[INFO] Features extracted and saved to: {output_file_path}")

        except Exception as e:
            print(f"[ERROR] Error processing category '{item_category}': {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run feature extraction for one or more categories on <category>_agg_parsed.xlsx."
    )
    parser.add_argument(
        "item_categories", nargs="+", type=str,
        help="The categories of items to process (e.g., 'Body_Armour', 'Weapons')."
    )
    args = parser.parse_args()
    main(args.item_categories)
