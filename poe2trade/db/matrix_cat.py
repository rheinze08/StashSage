# matrix_cat.py · v1.0
#
# Example:
#   python matrix_cat.py Body_Armour Boots Gloves
#
# Reads:
#   poe2trade/db/files/<category>/<category>_agg_parsed.parquet
#
# Writes:
#   poe2trade/db/files/<category>/<category>_feature_matrix.parquet
#   poe2trade/db/files/<category>/<category>_feature_matrix.xlsx
#   poe2trade/db/files/<category>/<category>_feature_matrix_overlay.parquet
#   poe2trade/db/files/<category>/<category>_feature_matrix_overlay.xlsx

from __future__ import annotations
import os
import argparse
from pathlib import Path

from poe2trade.db import submodule_path
from poe2trade.utils.matrix_utils import build_feature_matrix

def _parsed_parquet_path(cat: str) -> str:
    cd = cat.replace(" ", "_")
    return str(Path(submodule_path) / "files" / cd / f"{cd}_agg_parsed.parquet")

def main(cats: list[str]) -> None:
    for cat in cats:
        src_path = _parsed_parquet_path(cat)
        if not os.path.isfile(src_path):
            print(f"[WARN] Parsed Parquet missing for {cat}: {src_path}")
            continue

        print(f"\n>>> {cat} – building matrix files from {Path(src_path).name}")
        out_parquet, out_excel, out_parquet_overlay, out_excel_overlay = build_feature_matrix(src_path)

        print("  • feature_matrix parquet:      ", out_parquet)
        print("  • feature_matrix excel:        ", out_excel)
        print("  • feature_matrix_overlay parquet:", out_parquet_overlay)
        print("  • feature_matrix_overlay excel:  ", out_excel_overlay)
        print("✓ Done")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate *_feature_matrix(.parquet/.xlsx) files for one or more categories."
    )
    ap.add_argument("categories", nargs="+", help="e.g. Body_Armour Boots")
    args = ap.parse_args()
    main(args.categories)
