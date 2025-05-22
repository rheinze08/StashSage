def get_unique_mods_amulet():
    """
    Returns a sorted list of all unique Amulet mods (prefixes + suffixes).
    """
    
    mods_amulet = {
        "prefixes": [
            "# to maximum Life",
            "#% increased Maximum Life",
            "# to maximum Mana",
            "#% increased Maximum Mana",
            "# to maximum Energy Shield",
            "#% increased Armour",
            "#% increased Evasion Rating",
            "#% increased Maximum Energy Shield",
            "# to Accuracy Rating",
            "#% increased Rarity of Items Found",
            "# to Spirit",
            "#% increased Spell Damage",
        ],
        "suffixes": [
            "# to Strength",
            "# to Dexterity",
            "# to Intelligence",
            "# to all Attributes",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to all Elemental Resistances",
            "#% to Chaos Resistance",
            "# to Level of all Spell Skills",
            "# to Level of all Minion Skills",
            "# to Level of all Melee Skills",
            "# to Level of all Projectile Skills",
            "# Life Regeneration per second",
            "#% increased Mana Regeneration Rate",
            "#% increased Cast Speed",
            "#% increased Critical Hit Chance",
            "#% increased Critical Damage Bonus",
            "#% increased Rarity of Items Found",
            "#% of Damage taken Recouped as Life",
            "#% of Damage taken Recouped as Mana",
        ]
    }

    all_mods = set(mods_amulet["prefixes"]) | set(mods_amulet["suffixes"])
    return sorted(all_mods)
