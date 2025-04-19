=== helmet seg='ar_es_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0188
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f3 (pattern: # to armour)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f8 (pattern: # to maximum energy shield)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f13 (pattern: # to strength)
  f15 (pattern: #% increased armour and energy shield)
  f17 (pattern: #% increased critical hit chance)
  f21 (pattern: #% increased light radius)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f9 (pattern: # to maximum life)                    importance=0.12066
 2) f26 (pattern: #% to cold resistance)               importance=0.10486
 3) f2 (pattern: # to accuracy rating)                 importance=0.10236
 4) Deflated_Armour (pattern: Deflated_Armour)         importance=0.08854
 5) f17 (pattern: #% increased critical hit chance)    importance=0.07366
 6) f28 (pattern: #% to lightning resistance)          importance=0.06961
 7) f12 (pattern: # to spirit)                         importance=0.06282
 8) f23 (pattern: #% increased rarity of items found)  importance=0.06115
 9) f25 (pattern: #% to chaos resistance)              importance=0.05493
10) f27 (pattern: #% to fire resistance)               importance=0.04579
11) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04345
12) f13 (pattern: # to strength)                       importance=0.03957
13) f10 (pattern: # to maximum mana)                   importance=0.03799
14) f15 (pattern: #% increased armour and energy shield) importance=0.03729
15) f6 (pattern: # to intelligence)                    importance=0.02946
16) f24 (pattern: #% reduced attribute requirements)   importance=0.01380
17) f1 (pattern: # life regeneration per second)       importance=0.01021
18) f3 (pattern: # to armour)                          importance=0.00186
19) f7 (pattern: # to level of all minion skills)      importance=0.00166
20) Quality (pattern: Quality)                         importance=0.00032
21) f8 (pattern: # to maximum energy shield)           importance=0.00001
22) f21 (pattern: #% increased light radius)           importance=0.00000
23) f11 (pattern: # to maximum power charges)          importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
