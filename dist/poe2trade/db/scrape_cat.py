import os
import argparse
from poe2trade.utils.scrape_utils import scrape_trade
from poe2trade.db import submodule_path
import pandas as pd

def get_item_list(item_category):
    excel_path = os.path.join(submodule_path, "files", "category_items.xlsx")
    df = pd.read_excel(excel_path, sheet_name=item_category)
    return df.iloc[:, 0].dropna().tolist()

def main(item_categories):
    for item_category in item_categories:
        print(f"Processing category: {item_category}")
        try:
            item_list = get_item_list(item_category)
            category_directory = item_category.replace(" ", "_")
            category_folder = os.path.join(submodule_path, "files", category_directory)
            os.makedirs(category_folder, exist_ok=True)
            
            for item in item_list:
                print(f"Scraping for item: {item}")
                sub_filters = {
                    "Item Rarity":    "Rare",
                    "Item Level":     "78",  # Minimum item level
                    "Listed":         "Up to 2 weeks ago",
                    "Identified":     "Yes",
                    "Item Category":  item_category,
                    "Searched Item":  item,
                }
                item_filename = item.replace(" ", "_")
                output_path = os.path.join(category_folder, f"{item_filename}.xlsx")
                scrape_trade(sub_filters=sub_filters, output_path=output_path)
                print(f"Scraped data saved to: {output_path}")
        except Exception as e:
            print(f"Error processing category '{item_category}': {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run item scraping workflow for one or more item categories."
    )
    parser.add_argument(
        "item_categories", nargs="+", type=str,
        help="The categories of items to process (e.g., 'Body Armour', 'Weapons')."
    )
    args = parser.parse_args()
    main(args.item_categories)