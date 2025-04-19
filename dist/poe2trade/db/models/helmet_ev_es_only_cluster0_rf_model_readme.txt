=== helmet seg='ev_es_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: -0.0061
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
 1) f9 (pattern: # to maximum life)                    importance=0.14382
 2) f27 (pattern: #% to fire resistance)               importance=0.10410
 3) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.09633
 4) f28 (pattern: #% to lightning resistance)          importance=0.09449
 5) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.06871
 6) f26 (pattern: #% to cold resistance)               importance=0.06440
 7) f8 (pattern: # to maximum energy shield)           importance=0.05000
 8) f23 (pattern: #% increased rarity of items found)  importance=0.04746
 9) f5 (pattern: # to evasion rating)                  importance=0.04694
10) f19 (pattern: #% increased evasion and energy shield) importance=0.04607
11) f25 (pattern: #% to chaos resistance)              importance=0.04393
12) f6 (pattern: # to intelligence)                    importance=0.03891
13) f17 (pattern: #% increased critical hit chance)    importance=0.03525
14) f10 (pattern: # to maximum mana)                   importance=0.03201
15) f2 (pattern: # to accuracy rating)                 importance=0.03072
16) f4 (pattern: # to dexterity)                       importance=0.01627
17) f1 (pattern: # life regeneration per second)       importance=0.01532
18) Quality (pattern: Quality)                         importance=0.01189
19) f24 (pattern: #% reduced attribute requirements)   importance=0.00953
20) f21 (pattern: #% increased light radius)           importance=0.00168
21) f7 (pattern: # to level of all minion skills)      importance=0.00161
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00057
23) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
