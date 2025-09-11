# File: train_super_cat.py

import os
import argparse
import time
from poe2trade.db import submodule_path
from poe2trade.utils.train_utils import train_super_model_from_matrix

def main(categories):
    """
    For each item_category this script:
      1) Builds a path to:
           poe2trade/db/files/<category>/<category>_agg_parsed_feature_matrix_model.parquet
      2) Calls train_super_model_from_matrix(...) which trains all enabled models
         (XGB, RF, GBR) and saves them under poe2trade/db/super_models/.

    Prints a single summary line with total elapsed time.
    """
    # Force quiet mode in underlying training code
    os.environ["POE2TRADE_QUIET"] = "1"

    t0 = time.perf_counter()
    trained = 0
    skipped = 0
    failed  = 0

    for category in categories:
        category_dir = category.replace(" ", "_")
        category_folder = os.path.join(submodule_path, "files", category_dir)
        if not os.path.exists(category_folder):
            skipped += 1
            continue

        file_name = f"{category_dir}_agg_parsed_feature_matrix_model.parquet"
        file_path = os.path.join(category_folder, file_name)
        if not os.path.isfile(file_path):
            skipped += 1
            continue

        try:
            train_super_model_from_matrix(
                file_path,
                category,
                quiet=True,              # suppress per-iteration logs
                parallel_segments=True,  # keep your previous behavior
            )
            trained += 1
        except Exception:
            failed += 1

    dt = time.perf_counter() - t0
    print(f"[DONE] Supervised training — trained={trained} skipped={skipped} failed={failed} elapsed={dt:.2f}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train ML models for categories on their *_agg_parsed_feature_matrix_model.parquet (quiet summary only)."
    )
    parser.add_argument(
        "item_categories", nargs="+", type=str,
        help="Categories to train models for (e.g. 'Body_Armour')."
    )
    args = parser.parse_args()
    main(args.item_categories)
