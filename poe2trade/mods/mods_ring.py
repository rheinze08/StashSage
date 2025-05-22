mods_ring = {
    "prefixes": [
        "# to maximum Life",
        "# to maximum Mana",
        "# to Evasion Rating",
        "Adds # to # Physical Damage to Attacks",
        "Adds # to # Fire Damage to Attacks",
        "Adds # to # Cold Damage to Attacks",
        "Adds # to # Lightning Damage to Attacks",
        "# to Accuracy Rating",
        "#% increased Rarity of Items Found",
        "#% increased Fire Damage",
        "#% increased Cold Damage",
        "#% increased Lightning Damage",
        "#% increased Chaos Damage",
    ],
    "suffixes": [
        "# to Strength",
        "# to Dexterity",
        "# to Intelligence",
        "# to All Attributes",
        "#% to Fire Resistance",
        "#% to Cold Resistance",
        "#% to Lightning Resistance",
        "#% to all Elemental Resistances",
        "#% to Chaos Resistance",
        "# Life Regeneration per second",
        "#% increased Mana Regeneration Rate",
        "Leech #% of Physical Attack Damage as Life",
        "Leech #% of Physical Attack Damage as Mana",
        "Gain # Life per Enemy Killed",
        "Gain # Mana per Enemy Killed",
        "#% increased Cast Speed",
        "#% increased Rarity of Items Found",
        "#% increased Mana Regeneration Rate, #% Increased Light Radius",
    ]
}

def get_unique_mods_ring():
    """
    Returns a sorted list of all unique Ring mods (prefixes + suffixes),
    splitting comma-separated entries into individual mods.
    """
    ring_mods = set()
    
    for prefix in mods_ring["prefixes"]:
        split_prefixes = [x.strip() for x in prefix.strip().split(",") if x.strip()]
        ring_mods.update(split_prefixes)

    for suffix in mods_ring["suffixes"]:
        split_suffixes = [x.strip() for x in suffix.strip().split(",") if x.strip()]
        ring_mods.update(split_suffixes)

    return sorted(ring_mods)
