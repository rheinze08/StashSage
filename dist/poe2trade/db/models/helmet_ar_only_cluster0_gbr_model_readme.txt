=== helmet seg='ar_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0742
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
 1) f9 (pattern: # to maximum life)                    importance=0.24042
 2) f25 (pattern: #% to chaos resistance)              importance=0.13757
 3) f23 (pattern: #% increased rarity of items found)  importance=0.10369
 4) f14 (pattern: #% increased armour)                 importance=0.08037
 5) f27 (pattern: #% to fire resistance)               importance=0.07811
 6) f13 (pattern: # to strength)                       importance=0.06518
 7) f26 (pattern: #% to cold resistance)               importance=0.05139
 8) f6 (pattern: # to intelligence)                    importance=0.04864
 9) f2 (pattern: # to accuracy rating)                 importance=0.04733
10) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03933
11) f28 (pattern: #% to lightning resistance)          importance=0.03421
12) Quality (pattern: Quality)                         importance=0.02937
13) f10 (pattern: # to maximum mana)                   importance=0.02308
14) f17 (pattern: #% increased critical hit chance)    importance=0.00876
15) f1 (pattern: # life regeneration per second)       importance=0.00474
16) f3 (pattern: # to armour)                          importance=0.00240
17) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00179
18) f24 (pattern: #% reduced attribute requirements)   importance=0.00111
19) f11 (pattern: # to maximum power charges)          importance=0.00104
20) f21 (pattern: #% increased light radius)           importance=0.00102
21) f7 (pattern: # to level of all minion skills)      importance=0.00048
22) f12 (pattern: # to spirit)                         importance=0.00000
