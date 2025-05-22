import os
import pandas as pd

from poe2trade import poe2trade_root
from poe2trade.mods import submodule_path
from poe2trade.mods.mods_body_armour import get_unique_mods_body_armour
from poe2trade.mods.mods_amulet import get_unique_mods_amulet
from poe2trade.mods.mods_ring import get_unique_mods_ring
from poe2trade.mods.mods_belt import get_unique_mods_belt
from poe2trade.mods.mods_corruption import get_unique_mods_corruption
from poe2trade.mods.mods_rune import get_unique_mods_rune
from poe2trade.utils.mods_utils import compare_mods

def main():
    """
    1) Reads mods_trade.xlsx and filters rows to keep only those with GroupName == 'Stat Filters'.
    2) Renames 'OptionText' -> 'Mod' and drops the 'GroupName' column.
    3) Creates columns 'body_armour', 'amulet', 'ring', and 'belt', setting each to 1
       if the row's 'Mod' text matches (via compare_mods) a unique mod from the
       respective get_unique_mods_* function. Otherwise, 0.
    4) Builds a 'Corruption' sheet from get_unique_mods_corruption(), listing each
       corruption mod in a single column named 'Mod'.
    5) Builds a 'Rune' sheet from get_unique_mods_rune(), listing each rune
       in columns 'RuneName', 'MartialWeaponMod', and 'ArmourMod'.
    6) Writes all three sheets ('Main', 'Corruption', 'Rune') to mods_trade_updated.xlsx.
    """

    mods_path = os.path.join(submodule_path, "files", "mods_trade.xlsx")
    df = pd.read_excel(mods_path)
    df = df[df["GroupName"] == "Stat Filters"]

    # Replace "increased attribute requirements" (case-insensitive) with "reduced attribute requirements"
    df["OptionText"] = df["OptionText"].str.replace(
        r"(?i)increased attribute requirements",
        "reduced attribute requirements",
        regex=True
    )

    mask = df["OptionText"].str.contains("(?i)on you")
    df.loc[mask, "OptionText"] = df.loc[mask, "OptionText"].str.replace(
        r"(?i)increased\s+(\w+)\s+duration\s+on\s+you",
        lambda m: f"reduced {m.group(1)} duration on you",
        regex=True
    )

    df.rename(columns={"OptionText": "Mod"}, inplace=True)
    df.drop(columns=["GroupName"], inplace=True)
    df.drop(columns=["GroupNum"], inplace=True)

    df["body_armour"] = 0
    df["amulet"] = 0
    df["ring"] = 0
    df["belt"] = 0

    body_armour_mods = set(get_unique_mods_body_armour())
    amulet_mods = set(get_unique_mods_amulet())
    ring_mods = set(get_unique_mods_ring())
    belt_mods = set(get_unique_mods_belt())

    for idx, row in df.iterrows():
        base_mod = str(row["Mod"])
        # body_armour
        for pattern in body_armour_mods:
            valid, _ = compare_mods(base_mod, pattern)
            if valid:
                df.at[idx, "body_armour"] = 1
                break
        # amulet
        for pattern in amulet_mods:
            valid, _ = compare_mods(base_mod, pattern)
            if valid:
                df.at[idx, "amulet"] = 1
                break
        # ring
        for pattern in ring_mods:
            valid, _ = compare_mods(base_mod, pattern)
            if valid:
                df.at[idx, "ring"] = 1
                break
        # belt
        for pattern in belt_mods:
            valid, _ = compare_mods(base_mod, pattern)
            if valid:
                df.at[idx, "belt"] = 1
                break

    corruption_mods = get_unique_mods_corruption()
    df_corruption = pd.DataFrame({"Mod": corruption_mods})

    rune_dict = get_unique_mods_rune()
    rune_data = []
    for rune_name, info in rune_dict.items():
        rune_data.append({
            "RuneName": rune_name,
            "MartialWeaponMod": info["Martial Weapon"],
            "ArmourMod": info["Armour"],
        })
    df_rune = pd.DataFrame(rune_data)

    output_path = os.path.join(submodule_path, "files", "mods_trade_updated.xlsx")
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Main", index=False)
        df_corruption.to_excel(writer, sheet_name="Corruption", index=False)
        df_rune.to_excel(writer, sheet_name="Rune", index=False)

if __name__ == "__main__":
    main()
