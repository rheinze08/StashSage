import os
import glob
import argparse
import pandas as pd
from poe2trade.db import submodule_path
from poe2trade import poe2trade_root
from poe2trade.utils.parse_utils import parse_excel_file

def main(item_categories):
    """
    For each category:
      1) Determine the category folder (db/files/CategoryName).
      2) Find all *.xlsx files that do not contain 'parsed' in the filename.
      3) Parse each file in-memory using parse_excel_file.
      4) Concatenate them into a single DataFrame for that category.
      5) Write that category's aggregated result => CategoryName_agg_parsed.xlsx.
    """
    for item in item_categories:
        print(f"Processing category: {item}")
        category_directory = item.replace(" ", "_")
        category_folder = os.path.join(poe2trade_root, "db", "files", category_directory)
        if not os.path.exists(category_folder):
            print(f"Category folder {category_folder} does not exist. Skipping '{item}'.")
            continue

        scraped_files = glob.glob(os.path.join(category_folder, "*.xlsx"))
        # skip files with 'parsed' or 'agg_parsed' in the name
        scraped_files = [
            f for f in scraped_files
            if "parsed" not in os.path.basename(f).lower()
               and "agg_parsed" not in os.path.basename(f).lower()
        ]
        if not scraped_files:
            print(f"No scraped Excel files found for category '{item}'.")
            continue

        all_parsed_dfs = []
        for scraped_file in scraped_files:
            try:
                temp_df = parse_excel_file(input_excel_file=scraped_file, output_excel_file=None)
                print(f"Parsed file: {scraped_file}")
                temp_df["Category"] = item
                all_parsed_dfs.append(temp_df)
            except Exception as e:
                print(f"Error processing file '{scraped_file}': {e}")

        if not all_parsed_dfs:
            print(f"No data to aggregate for '{item}'.")
            continue

        # Aggregate for this single category
        agg_df = pd.concat(all_parsed_dfs, ignore_index=True)
        agg_output_path = os.path.join(
            poe2trade_root,
            "db",
            "files",
            category_directory,
            f"{category_directory}_agg_parsed.xlsx"
        )

        agg_df.to_excel(agg_output_path, index=False, sheet_name="Report")
        print(f"Aggregated parsed report for '{item}' saved to: {agg_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run parsing and aggregation workflow for one or more item categories."
    )
    parser.add_argument(
        "item_categories", nargs="+", type=str,
        help="The categories of items to process (e.g., 'Body_Armour', 'Weapons')."
    )
    args = parser.parse_args()
    main(args.item_categories)
