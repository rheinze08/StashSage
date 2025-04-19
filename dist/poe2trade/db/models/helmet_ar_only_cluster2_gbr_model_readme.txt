=== helmet seg='ar_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0824
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
 1) Quality (pattern: Quality)                         importance=0.14839
 2) f27 (pattern: #% to fire resistance)               importance=0.12716
 3) Deflated_Armour (pattern: Deflated_Armour)         importance=0.11425
 4) f3 (pattern: # to armour)                          importance=0.10083
 5) f9 (pattern: # to maximum life)                    importance=0.08820
 6) f2 (pattern: # to accuracy rating)                 importance=0.06383
 7) f14 (pattern: #% increased armour)                 importance=0.06366
 8) f23 (pattern: #% increased rarity of items found)  importance=0.05803
 9) f28 (pattern: #% to lightning resistance)          importance=0.05381
10) f26 (pattern: #% to cold resistance)               importance=0.04472
11) f1 (pattern: # life regeneration per second)       importance=0.03016
12) f6 (pattern: # to intelligence)                    importance=0.02351
13) f25 (pattern: #% to chaos resistance)              importance=0.02160
14) f7 (pattern: # to level of all minion skills)      importance=0.01965
15) f10 (pattern: # to maximum mana)                   importance=0.01459
16) f13 (pattern: # to strength)                       importance=0.01035
17) f17 (pattern: #% increased critical hit chance)    importance=0.00882
18) f24 (pattern: #% reduced attribute requirements)   importance=0.00573
19) f21 (pattern: #% increased light radius)           importance=0.00255
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00015
21) f12 (pattern: # to spirit)                         importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
