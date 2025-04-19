=== helmet seg='ar_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: 0.0788
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f3 (pattern: # to armour)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f13 (pattern: # to strength)
  f14 (pattern: #% increased armour)
  f17 (pattern: #% increased critical hit chance)
  f21 (pattern: #% increased light radius)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f9 (pattern: # to maximum life)                    importance=0.23736
 2) f25 (pattern: #% to chaos resistance)              importance=0.15267
 3) f23 (pattern: #% increased rarity of items found)  importance=0.08390
 4) f27 (pattern: #% to fire resistance)               importance=0.06602
 5) Quality (pattern: Quality)                         importance=0.06420
 6) f14 (pattern: #% increased armour)                 importance=0.05943
 7) f13 (pattern: # to strength)                       importance=0.05651
 8) f26 (pattern: #% to cold resistance)               importance=0.04503
 9) f28 (pattern: #% to lightning resistance)          importance=0.04130
10) f2 (pattern: # to accuracy rating)                 importance=0.02953
11) f10 (pattern: # to maximum mana)                   importance=0.02691
12) f6 (pattern: # to intelligence)                    importance=0.02576
13) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01729
14) f1 (pattern: # life regeneration per second)       importance=0.01555
15) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01520
16) f17 (pattern: #% increased critical hit chance)    importance=0.01416
17) f11 (pattern: # to maximum power charges)          importance=0.01215
18) f3 (pattern: # to armour)                          importance=0.00986
19) f21 (pattern: #% increased light radius)           importance=0.00825
20) f7 (pattern: # to level of all minion skills)      importance=0.00645
21) f24 (pattern: #% reduced attribute requirements)   importance=0.00642
22) f12 (pattern: # to spirit)                         importance=0.00603
