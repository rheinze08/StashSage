def get_unique_mods_belt():
    """
    Returns a sorted list of all unique Belt mods (prefixes + suffixes).
    """
    mods_belt = {
        "prefixes": [
            "# to maximum Life",
            "# to maximum Mana",
            "# to Armour",
            "# to # Physical Thorns damage",
            "#% increased Flask Life Recovery Rate",
            "#% increased Flask Mana Recovery Rate",
            "#% increased Charm Effect Duration"
        ],
        "suffixes": [
            "# to Strength",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to Chaos Resistance",
            "# to Stun Threshold",
            "# Life Regeneration per second",
            "#% increased Flask Charges gained",
            "#% reduced Flask Charges used",
            "#% reduced Charm Charges used",
            "# Charm Slot",
            "# Charm Slots"
        ]
    }

    all_mods = set(mods_belt["prefixes"]) | set(mods_belt["suffixes"])
    return sorted(all_mods)
