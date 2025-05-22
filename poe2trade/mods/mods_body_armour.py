def get_unique_mods_body_armour():
    """
    Collects all Body Armour mods (prefixes & suffixes) from each dict,
    combines them into one set, and returns a sorted list of unique mods.
    Note: when it is just 2 #% increases on hybrid, its AND, else its separated without AND (uses comma below)
    """

    # Single-attribute Body Armours
    mods_body_armour_str = {
        "prefixes": [
            "# to maximum Life",
            "# to Armour",
            "#% increased Armour",
            "#% increased Armour, # to maximum Life",
            "# to Armour, #% increased Armour",
            "# to # Physical Thorns damage",
            "# to Spirit"
        ],
        "suffixes": [
            "# to Strength",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to Chaos Resistance",
            "#% reduced Attribute Requirements",
            "# to Stun Threshold",
            "# Life Regeneration per second",
            "#% reduced Bleeding Duration on you",
            "#% reduced Poison Duration on you",
            "#% reduced Ignite Duration on you"
        ]
    }

    mods_body_armour_dex = {
        "prefixes": [
            "# to maximum Life",
            "# to Evasion Rating",
            "#% increased Evasion Rating",
            "#% increased Evasion Rating, # to maximum Life, ",
            "# to Evasion Rating, #% increased Evasion Rating",
            "# to # Physical Thorns damage",
            "# to Spirit"
        ],
        "suffixes": [
            "# to Dexterity",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to Chaos Resistance",
            "#% reduced Attribute Requirements",
            "# to Stun Threshold",
            "# Life Regeneration per second",
            "#% reduced Bleeding Duration on you",
            "#% reduced Poison Duration on you",
            "#% reduced Ignite Duration on you"
        ]
    }

    mods_body_armour_int = {
        "prefixes": [
            "# to maximum Life",
            "# to maximum Energy Shield",
            "#% increased Energy Shield",
            "#% increased Energy Shield, # to maximum Life",
            "# to maximum Energy Shield, #% increased Energy Shield",
            "# to # Physical Thorns damage",
            "# to Spirit"
        ],
        "suffixes": [
            "# to Intelligence",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to Chaos Resistance",
            "#% reduced Attribute Requirements",
            "# to Stun Threshold",
            "# Life Regeneration per second",
            "#% reduced Bleeding Duration on you",
            "#% reduced Poison Duration on you",
            "#% reduced Ignite Duration on you"
        ]
    }

    # Dual-attribute Body Armours
    mods_body_armour_str_dex = {
        "prefixes": [
            "# to maximum Life",
            "# to Armour, # to Evasion Rating",
            "#% increased Armour and Evasion",
            "#% increased Armour and Evasion, # to maximum Life",
            "# to Armour, # to Evasion Rating, #% increased Armour and Evasion",
            "# to # Physical Thorns damage",
            "# to Spirit"
        ],
        "suffixes": [
            "# to Strength",
            "# to Dexterity",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to Chaos Resistance",
            "#% reduced Attribute Requirements",
            "# to Stun Threshold",
            "# Life Regeneration per second",
            "#% reduced Bleeding Duration on you",
            "#% reduced Poison Duration on you",
            "#% reduced Ignite Duration on you"
        ]
    }

    mods_body_armour_str_int = {
        "prefixes": [
            "# to maximum Life",
            "# to Armour, # to maximum Energy Shield",
            "#% increased Armour and Energy Shield",
            "#% increased Armour and Energy Shield, # to maximum Life",
            "# to Armour, # to maximum Energy Shield, #% increased Armour and Energy Shield",
            "# to # Physical Thorns damage",
            "# to Spirit"
        ],
        "suffixes": [
            "# to Strength",
            "# to Intelligence",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to Chaos Resistance",
            "#% reduced Attribute Requirements",
            "# to Stun Threshold",
            "# Life Regeneration per second",
            "#% reduced Bleeding Duration on you",
            "#% reduced Poison Duration on you",
            "#% reduced Ignite Duration on you"
        ]
    }

    mods_body_armour_dex_int = {
        "prefixes": [
            "# to maximum Life",
            "# to Evasion Rating, # to maximum Energy Shield",
            "#% increased Evasion and Energy Shield",
            "#% increased Evasion and Energy Shield, # to maximum Life",
            "# to Evasion Rating, # to maximum Energy Shield, #% increased Evasion and Energy Shield",
            "# to # Physical Thorns damage",
            "# to Spirit"
        ],
        "suffixes": [
            "# to Dexterity",
            "# to Intelligence",
            "#% to Fire Resistance",
            "#% to Cold Resistance",
            "#% to Lightning Resistance",
            "#% to Chaos Resistance",
            "#% reduced Attribute Requirements",
            "# to Stun Threshold",
            "# Life Regeneration per second",
            "#% reduced Bleeding Duration on you",
            "#% reduced Poison Duration on you",
            "#% reduced Ignite Duration on you"
        ]
    }

    # Tri-attribute Body Armour
    # mods_body_armour_str_dex_int = {
    #     "prefixes": [
    #         "# to maximum Life",
    #         "# to Armour",
    #         "# to Evasion Rating",
    #         "# to maximum Energy Shield",
    #         "# to Armour, # to Evasion Rating",
    #         "# to Armour, # to maximum Energy Shield",
    #         "# to Evasion Rating, # to maximum Energy Shield",
    #         "# Physical Thorns damage",
    #         "# to Spirit"
    #     ],
    #     "suffixes": [
    #         "# to Strength",
    #         "# to Dexterity",
    #         "# to Intelligence",
    #         "#% to Fire Resistance",
    #         "#% to Cold Resistance",
    #         "#% to Lightning Resistance",
    #         "#% to Chaos Resistance",
    #         "#% reduced Attribute Requirements",
    #         "# to Stun Threshold",
    #         "# Life Regeneration per second",
    #         "#% reduced Bleeding Duration on you",
    #         "#% reduced Poison Duration on you",
    #         "#% reduced Ignite Duration on you"
    #     ]
    # }

    all_dicts = [
        mods_body_armour_str,
        mods_body_armour_dex,
        mods_body_armour_int,
        mods_body_armour_str_dex,
        mods_body_armour_str_int,
        mods_body_armour_dex_int,
        # mods_body_armour_str_dex_int  # don't think this is in the game yet
    ]
    
    mods_all = set()
    for mod_dict in all_dicts:
        for prefix in mod_dict["prefixes"]:
            # Split on commas, strip whitespace, and ignore empty pieces
            split_prefixes = [x.strip() for x in prefix.strip().split(",") if x.strip()]
            mods_all.update(split_prefixes)

        for suffix in mod_dict["suffixes"]:
            split_suffixes = [x.strip() for x in suffix.strip().split(",") if x.strip()]
            mods_all.update(split_suffixes)

    return sorted(mods_all)