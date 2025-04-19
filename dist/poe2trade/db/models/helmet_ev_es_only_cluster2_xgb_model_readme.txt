=== helmet seg='ev_es_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0026
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f4 (pattern: # to dexterity)
  f5 (pattern: # to evasion rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f8 (pattern: # to maximum energy shield)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f17 (pattern: #% increased critical hit chance)
  f19 (pattern: #% increased evasion and energy shield)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f2 (pattern: # to accuracy rating)                 importance=0.07204
 2) f25 (pattern: #% to chaos resistance)              importance=0.06680
 3) f19 (pattern: #% increased evasion and energy shield) importance=0.06548
 4) f26 (pattern: #% to cold resistance)               importance=0.06453
 5) f27 (pattern: #% to fire resistance)               importance=0.06343
 6) f28 (pattern: #% to lightning resistance)          importance=0.05446
 7) f23 (pattern: #% increased rarity of items found)  importance=0.04988
 8) f9 (pattern: # to maximum life)                    importance=0.04944
 9) Quality (pattern: Quality)                         importance=0.04923
10) f6 (pattern: # to intelligence)                    importance=0.04706
11) f10 (pattern: # to maximum mana)                   importance=0.04635
12) f8 (pattern: # to maximum energy shield)           importance=0.04546
13) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04093
14) f24 (pattern: #% reduced attribute requirements)   importance=0.03842
15) f4 (pattern: # to dexterity)                       importance=0.03819
16) f5 (pattern: # to evasion rating)                  importance=0.03704
17) f17 (pattern: #% increased critical hit chance)    importance=0.03436
18) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03316
19) f7 (pattern: # to level of all minion skills)      importance=0.03280
20) f1 (pattern: # life regeneration per second)       importance=0.03042
21) f21 (pattern: #% increased light radius)           importance=0.02727
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01325
23) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
