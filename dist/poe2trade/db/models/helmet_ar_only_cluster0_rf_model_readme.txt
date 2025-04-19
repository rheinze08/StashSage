=== helmet seg='ar_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: 0.0877
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
 1) f9 (pattern: # to maximum life)                    importance=0.21383
 2) f25 (pattern: #% to chaos resistance)              importance=0.11447
 3) f23 (pattern: #% increased rarity of items found)  importance=0.08409
 4) f14 (pattern: #% increased armour)                 importance=0.08158
 5) f27 (pattern: #% to fire resistance)               importance=0.08090
 6) f13 (pattern: # to strength)                       importance=0.06565
 7) Deflated_Armour (pattern: Deflated_Armour)         importance=0.06099
 8) f26 (pattern: #% to cold resistance)               importance=0.04543
 9) f6 (pattern: # to intelligence)                    importance=0.04536
10) f2 (pattern: # to accuracy rating)                 importance=0.04149
11) f28 (pattern: #% to lightning resistance)          importance=0.03902
12) Quality (pattern: Quality)                         importance=0.03849
13) f10 (pattern: # to maximum mana)                   importance=0.03843
14) f17 (pattern: #% increased critical hit chance)    importance=0.02336
15) f1 (pattern: # life regeneration per second)       importance=0.00628
16) f3 (pattern: # to armour)                          importance=0.00424
17) f24 (pattern: #% reduced attribute requirements)   importance=0.00418
18) f21 (pattern: #% increased light radius)           importance=0.00415
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00282
20) f11 (pattern: # to maximum power charges)          importance=0.00262
21) f7 (pattern: # to level of all minion skills)      importance=0.00189
22) f12 (pattern: # to spirit)                         importance=0.00071
