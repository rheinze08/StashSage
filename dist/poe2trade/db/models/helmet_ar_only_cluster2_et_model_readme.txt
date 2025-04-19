=== helmet seg='ar_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: 0.0317
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
 1) Quality (pattern: Quality)                         importance=0.29579
 2) f27 (pattern: #% to fire resistance)               importance=0.11411
 3) f25 (pattern: #% to chaos resistance)              importance=0.10953
 4) f23 (pattern: #% increased rarity of items found)  importance=0.08057
 5) f14 (pattern: #% increased armour)                 importance=0.06893
 6) f9 (pattern: # to maximum life)                    importance=0.05779
 7) f3 (pattern: # to armour)                          importance=0.04590
 8) f7 (pattern: # to level of all minion skills)      importance=0.04498
 9) f2 (pattern: # to accuracy rating)                 importance=0.04298
10) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03419
11) f28 (pattern: #% to lightning resistance)          importance=0.02950
12) f26 (pattern: #% to cold resistance)               importance=0.02607
13) f1 (pattern: # life regeneration per second)       importance=0.02072
14) f13 (pattern: # to strength)                       importance=0.00773
15) f6 (pattern: # to intelligence)                    importance=0.00772
16) f10 (pattern: # to maximum mana)                   importance=0.00694
17) f17 (pattern: #% increased critical hit chance)    importance=0.00271
18) f21 (pattern: #% increased light radius)           importance=0.00219
19) f24 (pattern: #% reduced attribute requirements)   importance=0.00165
20) f11 (pattern: # to maximum power charges)          importance=0.00000
21) f12 (pattern: # to spirit)                         importance=0.00000
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
