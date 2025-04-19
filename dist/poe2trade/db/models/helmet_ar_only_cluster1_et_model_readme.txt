=== helmet seg='ar_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.0152
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
 1) Quality (pattern: Quality)                         importance=0.18200
 2) Deflated_Armour (pattern: Deflated_Armour)         importance=0.15385
 3) f14 (pattern: #% increased armour)                 importance=0.12943
 4) f10 (pattern: # to maximum mana)                   importance=0.07341
 5) f25 (pattern: #% to chaos resistance)              importance=0.06535
 6) f9 (pattern: # to maximum life)                    importance=0.05460
 7) f1 (pattern: # life regeneration per second)       importance=0.05195
 8) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.03770
 9) f3 (pattern: # to armour)                          importance=0.03637
10) f2 (pattern: # to accuracy rating)                 importance=0.03006
11) f28 (pattern: #% to lightning resistance)          importance=0.02903
12) f6 (pattern: # to intelligence)                    importance=0.02845
13) f26 (pattern: #% to cold resistance)               importance=0.02731
14) f23 (pattern: #% increased rarity of items found)  importance=0.02305
15) f27 (pattern: #% to fire resistance)               importance=0.02167
16) f21 (pattern: #% increased light radius)           importance=0.01524
17) f13 (pattern: # to strength)                       importance=0.01278
18) f17 (pattern: #% increased critical hit chance)    importance=0.01255
19) f24 (pattern: #% reduced attribute requirements)   importance=0.00983
20) f7 (pattern: # to level of all minion skills)      importance=0.00536
21) f12 (pattern: # to spirit)                         importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
