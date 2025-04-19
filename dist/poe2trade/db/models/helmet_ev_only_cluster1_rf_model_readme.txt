=== helmet seg='ev_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: -0.1553
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f4 (pattern: # to dexterity)
  f5 (pattern: # to evasion rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f12 (pattern: # to spirit)
  f17 (pattern: #% increased critical hit chance)
  f20 (pattern: #% increased evasion rating)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f20 (pattern: #% increased evasion rating)         importance=0.13453
 2) f5 (pattern: # to evasion rating)                  importance=0.13282
 3) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.10525
 4) f2 (pattern: # to accuracy rating)                 importance=0.08872
 5) f9 (pattern: # to maximum life)                    importance=0.06920
 6) f6 (pattern: # to intelligence)                    importance=0.06632
 7) f4 (pattern: # to dexterity)                       importance=0.04909
 8) f23 (pattern: #% increased rarity of items found)  importance=0.04776
 9) f10 (pattern: # to maximum mana)                   importance=0.04637
10) f26 (pattern: #% to cold resistance)               importance=0.04633
11) f28 (pattern: #% to lightning resistance)          importance=0.04266
12) f27 (pattern: #% to fire resistance)               importance=0.03833
13) Quality (pattern: Quality)                         importance=0.02811
14) f1 (pattern: # life regeneration per second)       importance=0.02662
15) f17 (pattern: #% increased critical hit chance)    importance=0.02451
16) f24 (pattern: #% reduced attribute requirements)   importance=0.01464
17) f25 (pattern: #% to chaos resistance)              importance=0.01456
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01277
19) f21 (pattern: #% increased light radius)           importance=0.00929
20) f7 (pattern: # to level of all minion skills)      importance=0.00166
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00037
22) f12 (pattern: # to spirit)                         importance=0.00011
