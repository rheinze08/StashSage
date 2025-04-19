=== helmet seg='ar_es_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.9078
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
 1) f25 (pattern: #% to chaos resistance)              importance=0.13682
 2) f28 (pattern: #% to lightning resistance)          importance=0.11750
 3) f9 (pattern: # to maximum life)                    importance=0.10369
 4) Quality (pattern: Quality)                         importance=0.07557
 5) f17 (pattern: #% increased critical hit chance)    importance=0.06963
 6) f3 (pattern: # to armour)                          importance=0.06512
 7) f23 (pattern: #% increased rarity of items found)  importance=0.05436
 8) f27 (pattern: #% to fire resistance)               importance=0.05251
 9) f8 (pattern: # to maximum energy shield)           importance=0.05046
10) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04224
11) f2 (pattern: # to accuracy rating)                 importance=0.03236
12) f7 (pattern: # to level of all minion skills)      importance=0.03173
13) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03068
14) f15 (pattern: #% increased armour and energy shield) importance=0.02596
15) f26 (pattern: #% to cold resistance)               importance=0.02568
16) f10 (pattern: # to maximum mana)                   importance=0.02469
17) f13 (pattern: # to strength)                       importance=0.02209
18) f24 (pattern: #% reduced attribute requirements)   importance=0.01679
19) f6 (pattern: # to intelligence)                    importance=0.00931
20) f1 (pattern: # life regeneration per second)       importance=0.00853
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00293
22) f21 (pattern: #% increased light radius)           importance=0.00135
23) f12 (pattern: # to spirit)                         importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
