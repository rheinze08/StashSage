# File: parse_cat.py

import os
import glob
import argparse
from typing import List

import pandas as pd

from poe2trade import poe2trade_root
from poe2trade.utils.parse_utils import parse_item_json


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
_ALWAYS_KEEP = [
    "price", "currency", "base", "name",
    "quality", "quality_type", "ar", "ev", "es",
]

def _concat_safely(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatenate parsed DataFrames while avoiding the FutureWarning about
    empty/all-NA entries, and preserving canonical columns even if all-NA.
    """
    frames: list[pd.DataFrame] = []
    for df in dfs:
        if not isinstance(df, pd.DataFrame):
            continue
        if df.empty:
            continue
        if df.isna().all(axis=None):  # entire frame all-NA
            continue

        # Drop all-NA cols, but make a copy so we can safely assign
        df2 = df.dropna(axis=1, how="all").copy()

        # Force-keep canonical cols (even if all-NA)
        for col in _ALWAYS_KEEP:
            if col in df and col not in df2:
                df2[col] = df[col]

        if df2.empty:
            continue
        frames.append(df2)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True, sort=False, copy=False)

def _cast_canonical_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce common columns into stable dtypes (when present)."""
    cast_map = {
        "price": "float64",
        "quality": "float64",
        "ar": "float64",
        "ev": "float64",
        "es": "float64",
        "currency": "string",
        "base": "string",
        "name": "string",
        "quality_type": "string",
    }
    for col, target in cast_map.items():
        if col not in df.columns:
            continue
        if target.startswith("float"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].astype(target)
    return df


def _order_mod_columns(cols: list[str]) -> list[str]:
    """
    Stable order for mod columns:
      enchant → implicit → explicit → rune,
      by mod index (1..N),
      then field: text, pattern, value.
    """
    import re
    pref_order = {"enchant": 0, "implicit": 1, "explicit": 2, "rune": 3}
    field_order = {"": 0, "pattern": 1, "value": 2}
    rx = re.compile(r"^(enchant|implicit|explicit|rune)_mod_(\d+)(?:_(pattern|value))?$")

    def key(c: str):
        m = rx.match(c)
        if not m:
            return (999, 9999, 9, c)
        pref, idx, fld = m.group(1), int(m.group(2)), m.group(3) or ""
        return (pref_order[pref], idx, field_order[fld], c)

    mod_cols = [c for c in cols if rx.match(c)]
    mod_cols.sort(key=key)
    return mod_cols


def _reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    price, currency, base, name, quality, quality_type, ar, ev, es,
    then mods (ordered), then any remaining columns.
    """
    front = ["price", "currency", "base", "name",
             "quality", "quality_type", "ar", "ev", "es"]
    existing_front = [c for c in front if c in df.columns]

    mod_cols = _order_mod_columns(list(df.columns))
    rest = [c for c in df.columns if c not in existing_front and c not in mod_cols and c != "Category"]

    new_order = existing_front + mod_cols + rest
    return df.reindex(columns=new_order)


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main(categories: list[str]):
    """
    Parse all JSON exports for each category folder, aggregate, reorder, write files.
    """
    for category in categories:
        print(f"Processing category: {category}")

        dir_name = category.replace(" ", "_")
        folder = os.path.join(poe2trade_root, "db", "files", dir_name)

        if not os.path.isdir(folder):
            print(f"  → Category folder not found: {folder}. Skipping.")
            continue

        json_files = glob.glob(os.path.join(folder, "*.json"))
        if not json_files:
            print(f"  → No JSON files to parse in '{category}'.")
            continue

        dfs: list[pd.DataFrame] = []
        for json_file in json_files:
            try:
                df = parse_item_json(item_json_file_path=json_file, category=category)
                df.drop(columns=["Category"], inplace=True, errors="ignore")
                dfs.append(df)
                print(f"  ✔ Parsed: {os.path.basename(json_file)}")
            except Exception as e:
                print(f"  ✖ Error parsing '{json_file}': {e}")

        if not dfs:
            print(f"  → No data parsed for '{category}'.")
            continue

        agg_df = _concat_safely(dfs)
        if agg_df.empty:
            print(f"  → No rows to aggregate for '{category}' (all inputs empty/all-NA). Skipping writes.")
            continue

        agg_df.drop(columns=["Category"], inplace=True, errors="ignore")
        agg_df = _cast_canonical_dtypes(agg_df)
        agg_df = _reorder_columns(agg_df)

        excel_path = os.path.join(folder, f"{dir_name}_agg_parsed.xlsx")
        try:
            agg_df.to_excel(excel_path, index=False)
            print(f"  → Aggregated Excel written to: {excel_path}")
        except Exception as e:
            print(f"  ✖ Failed writing Excel for '{category}': {e}")

        parquet_path = os.path.splitext(excel_path)[0] + ".parquet"
        try:
            agg_df.to_parquet(parquet_path, index=False)
            print(f"  → Aggregated Parquet written to: {parquet_path}")
        except Exception as e:
            print(f"  ✖ Failed writing Parquet for '{category}': {e}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse and aggregate PoE2 item JSON exports by category."
    )
    parser.add_argument(
        "categories", nargs="+",
        help="One or more category names (e.g. 'Body Armour', 'Weapons')."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.categories)
