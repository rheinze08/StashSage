# File: poe2trade/db/train_unsuper_cat.py · v2.5
#
# Fits k-nearest-neighbour reference models (unsupervised) for each supplied
# category, using the global default k (poe2trade.knn_k). Requires that
# for each category, a file named either
#   <Category_With_Underscores>_agg_parsed_feature_matrix.parquet
# or
#   <Category_With_Underscores>_agg_parsed_feature_matrix.xlsx
# already exists under db/files/<Category_With_Underscores>.
#
# Usage examples:
#   python -m poe2trade.db.train_unsuper_cat Body_Armour Boots
#
# Reads (per category):
#   poe2trade/db/files/<Category_With_Underscores>/
#     <Category_With_Underscores>_agg_parsed_feature_matrix.parquet
#   (falls back to .xlsx if no .parquet)
#
# Writes (to poe2trade/db/knn_models/):
#   <category>_<segment>_knn_model.pkl    (one model per defence-segment)
#   <category>_<segment>_knn_model_readme.txt

from __future__ import annotations

import argparse
from pathlib import Path

from poe2trade import knn_k                           # global default k
from poe2trade.db import submodule_path
from poe2trade.utils.train_utils import train_unsuper_model_from_matrix


def main(categories: list[str]) -> None:
    """
    Train unsupervised k-NN models for each specified category.

    Parameters
    ----------
    categories : list[str]
        Category folder names (e.g. ['Body_Armour', 'Boots']). Each category
        corresponds to a subfolder under db/files/.

    Behavior
    --------
    - Always uses the global k from poe2trade.knn_k.
    - For each category:
        1) Look for:
           db/files/<Category_With_Underscores>/
             <Category_With_Underscores>_agg_parsed_feature_matrix_model.parquet
           (if not found, falls back to the .xlsx version)
        2) If found, call train_unsuper_model_from_matrix(path, category).
        3) Print each generated model and README path.
        4) If missing, emit a warning and skip.
    """
    print(f"[INFO] Using k = {knn_k} for all neighbour models\n")

    for category in categories:
        # Normalize spaces to underscores
        cd = category.replace(" ", "_")
        folder = Path(submodule_path) / "files" / cd

        # prefer .parquet, fallback to .xlsx
        parquet_fp = folder / f"{cd}_agg_parsed_feature_matrix_model.parquet"

        if parquet_fp.is_file():
            matrix_path = parquet_fp
        else:
            print(f"[WARN] Matrix file missing for '{category}':")
            print(f"       looked for {parquet_fp}")
            continue

        print(f">>> {category} – training unsupervised k-NN models using:")
        print(f"       {matrix_path.name}")

        # Pass cd (normalized category) into the training util
        model_paths = train_unsuper_model_from_matrix(str(matrix_path), cd)

        for p in model_paths:
            print(f"  • {p}")
        print("✓ Done\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Train unsupervised k-NN models for one or more categories.\n"
            f"Uses global k from poe2trade.knn_k = {knn_k}."
        )
    )
    parser.add_argument(
        "categories",
        nargs="+",
        help="Category folder names, e.g. 'Body_Armour', 'Boots'."
    )
    args = parser.parse_args()
    main(args.categories)
