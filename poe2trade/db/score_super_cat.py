#!/usr/bin/env python
import os
import argparse
from poe2trade.db import submodule_path
from poe2trade.utils.score_super_utils import score_matrix

def main(item_categories):
    """
    For each category it looks for the parquet feature-matrix under:
        <repo_root>/files/<Category_Name>/<Category_Name>_agg_parsed_feature_matrix.parquet
    then calls score_matrix (which loads the models).
    """
    for item_category in item_categories:
        print(f"Scoring category: {item_category}")
        category_dir = item_category.replace(" ", "_")
        folder = os.path.join(submodule_path, "files", category_dir)
        if not os.path.isdir(folder):
            print(f"Category folder not found: {folder}. Skipping.")
            continue

        # we expect the matrix parquet to be named "<Category>_agg_parsed_feature_matrix.parquet"
        matrix_file = os.path.join(folder, f"{category_dir}_agg_parsed_feature_matrix_model.parquet")
        if not os.path.isfile(matrix_file):
            print(f"Matrix parquet not found: {matrix_file}. Skipping.")
            continue

        score_matrix(matrix_file, item_category)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Score items for each category with trained super-models."
    )
    parser.add_argument(
        "item_categories", nargs="+", type=str,
        help="Categories to score (e.g. 'Body_Armour')."
    )
    args = parser.parse_args()
    main(args.item_categories)
