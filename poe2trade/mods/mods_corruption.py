def get_unique_mods_corruption():
    """
    Returns a sorted list of all unique Corruption mods.
    """

    mods_corruption = [
        "(15-25)% increased Armour",  # 1
        "(15-25)% increased Evasion Rating",  # 2
        "(15-25)% increased Energy Shield",  # 3
        "(15-25)% increased Armour and Evasion",  # 4
        "(15-25)% increased Armour and Energy Shield",  # 5
        "(15-25)% increased Evasion and Energy Shield",  # 6
        "(10-20)% reduced Attribute Requirements",  # 7
        "(3-5)% additional Physical Damage Reduction",  # 8
        "(10-20)% of Damage taken Recouped as Life",  # 9
        "(10-20)% of Damage taken Recouped as Mana",  # 10
        "Leech 3% of Physical Attack Damage as Life",  # 11
        "Leech 2% of Physical Attack Damage as Mana",  # 12
        "+1% to all Maximum Elemental Resistances",  # 13
        "+(30-40) to maximum Life",  # 14
        "+(20-25) to maximum Mana",  # 15
        "(15-25)% increased Evasion Rating",  # 16
        "(15-25)% increased maximum Energy Shield",  # 17
        "(40-50)% increased Thorns damage",  # 18
        "+(13-19)% to Chaos Resistance",  # 19
        "+(20-25)% to Fire Resistance",  # 20
        "+(20-25)% to Cold Resistance",  # 21
        "+(20-25)% to Lightning Resistance",  # 22
        "+(1-3)% to Maximum Fire Resistance",  # 23
        "+(1-3)% to Maximum Cold Resistance",  # 24
        "+(1-3)% to Maximum Lightning Resistance",  # 25
        "+(20-30) to Spirit",  # 26
        "Damage Penetrates (10-15)% Fire Resistance",  # 27
        "Damage Penetrates (10-15)% Cold Resistance",  # 28
        "Damage Penetrates (10-15)% Lightning Resistance",  # 29
        "Break (10-15)% increased Armour",  # 30
        "+1 to Maximum Endurance Charges",  # 31
        "+1 to Maximum Power Charges",  # 32
        "+1 to Maximum Frenzy Charges",  # added 20250503
        "+(50-100) to Accuracy Rating",  # 33
        "(3-5)% increased Movement Speed",  # 34
        "(20-30)% increased Stun Threshold",  # 35
        "(20-30)% increased Freeze Threshold",  # 36
        "(20-30)% reduced Slowing Potency of Debuffs on You",  # 37
        "Regenerate (1-2)% of Life per second",  # 38
        "(15-25)% increased Life Regeneration rate",  # added 20250503
        "(20-30)% increased Mana Regeneration Rate",  # 39
        "(20-30)% increased Block chance",  # 40
        "+3% to maximum Block chance",  # 41
        "(20-25) Life gained when you Block",  # 42
        "(10-15) Mana gained when you Block",  # 43
        "+(5-10)% to all Elemental Resistances",  # 44
        "+1 to Level of all Fire Spell Skills",  # 45
        "+1 to Level of all Cold Spell Skills",  # 46
        "+1 to Level of all Lightning Spell Skills",  # 47
        "+1 to Level of all Chaos Spell Skills",  # 48
        "+1 to Level of all Physical Spell Skills",  # 49
        "+1 to Level of all Minion Skills",  # 50
        "+1 to Level of all Melee Skills",  # 51
        "+1 to Level of all Trap Skill Gems",  # 52
        "(10-15)% increased Rarity of Items found",  # 53
        "(20-30)% increased Damage",  # 54
        "(4-6)% increased Skill Speed",  # 55
        "(15-20)% increased Critical Damage Bonus",  # 56
        "+1 to Level of all Skills",  # 57
        "+(10-15) to Strength",  # 58
        "+(10-15) to Dexterity",  # 59
        "+(10-15) to Intelligence",  # 60
        "Debuffs you inflict have (20-30)% increased Slow Magnitude",  # 61
        "(20-30)% increased Weapon Swap Speed",  # 62
        "Life Flasks gain (0.08-0.17) charges per Second",  # 63
        "Mana Flasks gain (0.08-0.17) charges per Second",  # 64
        "Charms gain (0.08-0.17) charges per Second",  # 65
        "(15-25)% increased Physical Damage",  # 66
        "(20-30)% increased Spell Damage",  # 67
        "(40-50)% increased Spell Damage",  # 68
        "(15-25)% increased Spirit",  # 69
        "Adds (9-14) to (15-22) Fire Damage",  # 70
        "Adds (13-20) to (21-31) Fire Damage",  # 71
        "Adds (8-12) to (13-19) Cold Damage",  # 72
        "Adds (11-17) to (18-26) Cold Damage",  # 73
        "Adds (1-2) to (29-43) Lightning Damage",  # 74
        "Adds (1-3) to (41-61) Lightning Damage",  # 75
        "Adds (7-11) to (12-18) Chaos Damage",  # 76
        "Adds (10-16) to (17-25) Chaos Damage",  # 77
        "(6-8)% increased Attack Speed",  # 78
        "+(10-15)% to Critical Damage Bonus",  # 79
        "Causes (20-30)% increased Stun Buildup",  # 80
        "(10-20)% increased Range",  # 81
        "(10-15)% chance to cause Bleeding on Hit",  # 82
        "(10-15)% chance to Poison on Hit",  # 83
        "Gain 1 Rage on Hit",  # 84
        "(10-15)% chance to Maim on Hit",  # 85
        "(5-10)% chance to Blind Enemies on hit",  # 86
        "(20-30)% increased Elemental Damage with Attacks",  # 87
        "(40-50)% increased Elemental Damage with Attacks",  # 88
        "Bow Attacks fire an additional Arrow",  # 89
        "Loads an additional bolt",  # 90
        "(20-30)% increased chance to Ignite",  # 91
        "(20-30)% increased Freeze Buildup",  # 92
        "(20-30)% increased chance to Shock",  # 93
        "(20-30)% increased Critical Hit Chance for Spells",  # 94
        "Gain (20-25) Life per Enemy Killed",  # 95
        "Gain (10-15) Mana per Enemy Killed",  # 96
        "(10-15)% increased Cast Speed",  # 97
        "(20-30)% faster start of Energy Shield Recharge",  # 98
        "Allies in your Presence deal (20-30)% increased Damage",  # 99
        "Allies in your Presence have (5-10)% increased Attack Speed",  # 100
        "Allies in your Presence have (5-10)% increased Cast Speed",  # 101
        "Allies in your Presence have (10-15)% increased Critical Damage Bonus",  # 102
        "(20-30)% chance to Pierce an Enemy",  # 103
        "Projectiles have (10-20)% chance to Chain an additional time from terrain",  # 104
        "(15-25)% increased Presence Area of effect",  # added 20250503
        "Meta Skills Gain (20-30)% increased Energy",  # added 20250503
        "(5-10)% increased quantity of gold dropped by slain enemies",  # added 20250503
        "(15-25)% increased skill effect duration",  # added 20250509
        "(5-10)% increased curse magnitudes",  # added 20250509
        "Gain (5-8)% of damage as extra chaos damage",  # added 20250509
        "(8-12)% increased cooldown recovery rate", # added 20250509
    ]

    all_mods = set(mods_corruption)
    return sorted(all_mods)
