=== helmet seg='ar_es_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: -0.8076
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
 1) f9 (pattern: # to maximum life)                    importance=0.14351
 2) f28 (pattern: #% to lightning resistance)          importance=0.11135
 3) f27 (pattern: #% to fire resistance)               importance=0.09772
 4) f25 (pattern: #% to chaos resistance)              importance=0.09109
 5) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.07754
 6) f8 (pattern: # to maximum energy shield)           importance=0.07314
 7) f3 (pattern: # to armour)                          importance=0.06481
 8) f23 (pattern: #% increased rarity of items found)  importance=0.05819
 9) f17 (pattern: #% increased critical hit chance)    importance=0.04488
10) f15 (pattern: #% increased armour and energy shield) importance=0.03774
11) f26 (pattern: #% to cold resistance)               importance=0.03363
12) f10 (pattern: # to maximum mana)                   importance=0.03088
13) Deflated_Armour (pattern: Deflated_Armour)         importance=0.02759
14) f2 (pattern: # to accuracy rating)                 importance=0.02691
15) f6 (pattern: # to intelligence)                    importance=0.02357
16) Quality (pattern: Quality)                         importance=0.02074
17) f7 (pattern: # to level of all minion skills)      importance=0.01118
18) f24 (pattern: #% reduced attribute requirements)   importance=0.00993
19) f1 (pattern: # life regeneration per second)       importance=0.00557
20) f13 (pattern: # to strength)                       importance=0.00486
21) f21 (pattern: #% increased light radius)           importance=0.00463
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00052
23) f12 (pattern: # to spirit)                         importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
