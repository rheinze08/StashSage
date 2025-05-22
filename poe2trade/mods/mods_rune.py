def get_unique_mods_rune():
    """
    Returns a sorted list of all unique Rune mods.
    """

    mods_rune = {
        # Desert
        "Lesser Desert Rune": {
            "Martial Weapon": "Adds 4 to 6 Fire Damage",
            "Armour": "+10% to Fire Resistance"
        },
        "Desert Rune": {
            "Martial Weapon": "Adds 7 to 11 Fire Damage",
            "Armour": "+12% to Fire Resistance"
        },
        "Greater Desert Rune": {
            "Martial Weapon": "Adds 13 to 16 Fire Damage",
            "Armour": "+14% to Fire Resistance"
        },

        # Storm
        "Lesser Storm Rune": {
            "Martial Weapon": "Adds 1 to 10 Lightning Damage",
            "Armour": "+10% to Lightning Resistance"
        },
        "Storm Rune": {
            "Martial Weapon": "Adds 1 to 20 Lightning Damage",
            "Armour": "+12% to Lightning Resistance"
        },
        "Greater Storm Rune": {
            "Martial Weapon": "Adds 1 to 30 Lightning Damage",
            "Armour": "+14% to Lightning Resistance"
        },

        # Glacial
        "Lesser Glacial Rune": {
            "Martial Weapon": "Adds 3 to 5 Cold Damage",
            "Armour": "+10% to Cold Resistance"
        },
        "Glacial Rune": {
            "Martial Weapon": "Adds 6 to 10 Cold Damage",
            "Armour": "+12% to Cold Resistance"
        },
        "Greater Glacial Rune": {
            "Martial Weapon": "Adds 9 to 15 Cold Damage",
            "Armour": "+14% to Cold Resistance"
        },

        # Iron
        "Lesser Iron Rune": {
            "Martial Weapon": "15% Increased Physical Damage",
            "Armour": "15% Increased Armour, Evasion and Energy Shield"
        },
        "Iron Rune": {
            "Martial Weapon": "20% Increased Physical Damage",
            "Armour": "20% Increased Armour, Evasion and Energy Shield"
        },
        "Greater Iron Rune": {
            "Martial Weapon": "25% Increased Physical Damage",
            "Armour": "25% Increased Armour, Evasion and Energy Shield"
        },

        # Body
        "Lesser Body Rune": {
            "Martial Weapon": "Leeches 2% of Physical Damage as Life",
            "Armour": "+20 to Maximum Life"
        },
        "Body Rune": {
            "Martial Weapon": "Leeches 2.5% of Physical Damage as Life",
            "Armour": "+30 to Maximum Life"
        },
        "Greater Body Rune": {
            "Martial Weapon": "Leeches 3% of Physical Damage as Life",
            "Armour": "+40 to Maximum Life"
        },

        # Mind
        "Lesser Mind Rune": {
            "Martial Weapon": "Leeches 1.5% of Physical Damage as Mana",
            "Armour": "+15 to Maximum Mana"
        },
        "Mind Rune": {
            "Martial Weapon": "Leeches 2% of Physical Damage as Mana",
            "Armour": "+25 to Maximum Mana"
        },
        "Greater Mind Rune": {
            "Martial Weapon": "Leeches 2.5% of Physical Damage as Mana",
            "Armour": "+35 to Maximum Mana"
        },

        # Rebirth
        "Lesser Rebirth Rune": {
            "Martial Weapon": "Gain 10 Life per Enemy Killed",
            "Armour": "Regenerate 0.25% of Maximum Life per second"
        },
        "Rebirth Rune": {
            "Martial Weapon": "Gain 20 Life per Enemy Killed",
            "Armour": "Regenerate 0.30% of Maximum Life per second"
        },
        "Greater Rebirth Rune": {
            "Martial Weapon": "Gain 30 Life per Enemy Killed",
            "Armour": "Regenerate 0.35% of Maximum Life per second"
        },

        # Inspiration
        "Lesser Inspiration Rune": {
            "Martial Weapon": "Gain 8 Mana per Enemy Killed",
            "Armour": "12% Increased Mana Regeneration Rate"
        },
        "Inspiration Rune": {
            "Martial Weapon": "Gain 16 Mana per Enemy Killed",
            "Armour": "15% Increased Mana Regeneration Rate"
        },
        "Greater Inspiration Rune": {
            "Martial Weapon": "Gain 24 Mana per Enemy Killed",
            "Armour": "18% Increased Mana Regeneration Rate"
        },

        # Stone
        "Lesser Stone Rune": {
            "Martial Weapon": "Causes 20% Increased Stun Buildup",
            "Armour": "+30 to Stun Threshold"
        },
        "Stone Rune": {
            "Martial Weapon": "Causes 25% Increased Stun Buildup",
            "Armour": "+40 to Stun Threshold"
        },
        "Greater Stone Rune": {
            "Martial Weapon": "Causes 30% Increased Stun Buildup",
            "Armour": "+50 to Stun Threshold"
        },

        # Vision
        "Lesser Vision Rune": {
            "Martial Weapon": "+50 to Accuracy Rating",
            "Armour": "+8% Life and Mana Recovery from Flasks"
        },
        "Vision Rune": {
            "Martial Weapon": "+80 to Accuracy Rating",
            "Armour": "10% Increased Life and Mana Recovery from Flasks"
        },
        "Greater Vision Rune": {
            "Martial Weapon": "+110 to Accuracy Rating",
            "Armour": "12% Increased Life and Mana Recovery from Flasks"
        },

        # Resolve Rune
        "Lesser Resolve Rune": {
            "Martial Weapon": "+6 to Intelligence",
            "Armour": "+6 to Intelligence"
        },
        "Resolve Rune": {
            "Martial Weapon": "+8 to Intelligence",
            "Armour": "+8 to Intelligence"
        },
        "Greater Resolve Rune": {
            "Martial Weapon": "+10 to Intelligence",
            "Armour": "+10 to Intelligence"
        },

        # Robust Rune
        "Lesser Robust Rune": {
            "Martial Weapon": "+6 to Strength",
            "Armour": "+6 to Strength"
        },
        "Robust Rune": {
            "Martial Weapon": "+8 to Strength",
            "Armour": "+8 to Strength"
        },
        "Greater Robust Rune": {
            "Martial Weapon": "+10 to Strength",
            "Armour": "+10 to Strength"
        },

        # Adept Rune
        "Lesser Adept Rune": {
            "Martial Weapon": "+6 to Dexterity",
            "Armour": "+6 to Dexterity"
        },
        "Adept Rune": {
            "Martial Weapon": "+8 to Dexterity",
            "Armour": "+8 to Dexterity"
        },
        "Greater Adept Rune": {
            "Martial Weapon": "+10 to Dexterity",
            "Armour": "+10 to Dexterity"
        },

        # Newly added Greater Runes in Dawn of the Hunt
        "Greater Rune of Alacrity": {
            "Martial Weapon": "8% increased Skill Speed",
            "Armour": "Debuffs on you expire 8% faster"
        },
        "Greater Rune of Leadership": {
            "Martial Weapon": "Minions gain 10% of their Physical Damage as Extra Lightning Damage",
            "Armour": "Minions take 10% of Physical Damage as Lightning Damage"
        },
        "Greater Rune of Nobility": {
            "Martial Weapon": "Attacks with this Weapon have 10% to inflict Lightning Exposure",
            "Armour": "10% reduced effect of Shock on you"
        },
        "Greater Rune of Tithing": {
            "Martial Weapon": "Meta Skills gain 10% increased Energy",
            "Armour": "1 to 100 Lightning Thorns Damage"
        },

        # Talismans added in Dawn of the Hunt
        "Bear Talisman": {
            "Armour": "8% increased Area of Effect",
            "Martial Weapon": "Allies in your Presence deal 12 to 18 additional Attack Physical Damage"
        },
        "Boar Talisman": {
            "Armour": "Gain 1 Rage on Melee Hit",
            "Martial Weapon": "Allies in Your Presence Regenerate 8 Life per Second"
        },
        "Ox Talisman": {
            "Armour": "20% increased Presence Area of Effect",
            "Martial Weapon": "Allies in your Presence have +8% to All Elemental Resistances"
        },
        "Cat Talisman": {
            "Armour": "Hits against you have 15% reduced Critical Damage Bonus",
            "Martial Weapon": "Allies in your Presence have 14% increased Critical Hit Chance"
        },
        "Stag Talisman": {
            "Armour": "8% increased Exposure Effect",
            "Martial Weapon": "Allies in your Presence have +100 to Accuracy Rating"
        },
        "Wolf Talisman": {
            "Armour": "10% increased Magnitude of Bleeding you inflict",
            "Martial Weapon": "Allies in your Presence have 14% increased Critical Damage Bonus"
        },
        "Owl Talisman": {
            "Armour": "5% increased Cooldown Recovery Rate",
            "Martial Weapon": "Allies in your Presence have 8% increased Cast Speed"
        },
        "Primate Talisman": {
            "Armour": "Minions have 12% increased Maximum Life",
            "Martial Weapon": "Allies in your Presence deal 30% increased Damage"
        },
        "Serpent Talisman": {
            "Armour": "5% increased Curse Magnitudes",
            "Martial Weapon": "Allies in your Presence have 8% increased Attack Speed"
        },
        "Fox Talisman": {
            "Armour": "+2% to Quality of All Skills",
            "Martial Weapon": "20% increased Presence Area of Effect"
        },
        "Rabbit Talisman": {
            "Armour": "8% increased Rarity of Items Found",
            "Martial Weapon": "10% increased Spirit"
        },

        # Soul Cores
        "Soul Core of Topotante": {
            "Martial Weapon": "Attacks with this Weapon penetrate 15% Elemental Resistances",
            "Armour": "15% Increased Elemental Ailment Threshold"
        },
        "Soul Core of Tacati": {
            "Martial Weapon": "15% chance to Poison on Hit",
            "Armour": "+7% to Chaos Resistance"
        },
        "Soul Core of Opiloti": {
            "Martial Weapon": "15% chance to cause Bleeding on Hit",
            "Armour": "10% Increased Charm Charges gained"
        },
        "Soul Core of Jiquani": {
            "Martial Weapon": "Recover 2% of Life on Kill",
            "Armour": "2% Increased Maximum Life"
        },
        "Soul Core of Zalatl": {
            "Martial Weapon": "Recover 2% of Mana on Kill",
            "Armour": "2% Increased Maximum Mana"
        },
        "Soul Core of Citaqualotl": {
            "Martial Weapon": "30% Increased Elemental Damage with Attacks",
            "Armour": "+5% to all Elemental Resistances"
        },
        "Soul Core of Puhuarte": {
            "Martial Weapon": "30% Increased chance to Ignite",
            "Armour": "+1% to Maximum Fire Resistance"
        },
        "Soul Core of Tzamoto": {
            "Martial Weapon": "20% Increased Freeze Buildup",
            "Armour": "+1% to Maximum Cold Resistance"
        },
        "Soul Core of Xopec": {
            "Martial Weapon": "30% Increased chance to Shock",
            "Armour": "+1% to Maximum Lightning Resistance"
        },
        "Soul Core of Quipolatl": {
            "Martial Weapon": "5% increased Attack Speed",
            "Armour": "10% Reduced Slowing Potency of Debuffs on you"
        },
        "Soul Core of Ticaba": {
            "Martial Weapon": "+12% to Critical Damage Bonus",
            "Armour": "Hits against you have 10% reduced Critical Damage Bonus"
        },
        "Soul Core of Atmohua": {
            "Martial Weapon": "Convert 20% of Requirements to Strength",
            "Armour": "Convert 20% of Requirements to Strength"
        },
        "Soul Core of Cholotl": {
            "Martial Weapon": "Convert 20% of Requirements to Dexterity",
            "Armour": "Convert 20% of Requirements to Dexterity"
        },
        "Soul Core of Zantipi": {
            "Martial Weapon": "Convert 20% of Requirements to Intelligence",
            "Armour": "Convert 20% of Requirements to Intelligence"
        },
        "Soul Core of Azcapa": {
            "Martial Weapon": "+15 Spirit",
            "Armour": "5% Increased quantity of gold dropped by slain enemies"
        },
    }

    return mods_rune
