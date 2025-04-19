=== helmet seg='ev_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: 0.0236
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
 1) f26 (pattern: #% to cold resistance)               importance=0.15334
 2) f2 (pattern: # to accuracy rating)                 importance=0.12636
 3) Quality (pattern: Quality)                         importance=0.09091
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.08258
 5) f9 (pattern: # to maximum life)                    importance=0.08207
 6) f17 (pattern: #% increased critical hit chance)    importance=0.06048
 7) f27 (pattern: #% to fire resistance)               importance=0.05937
 8) f20 (pattern: #% increased evasion rating)         importance=0.04777
 9) f28 (pattern: #% to lightning resistance)          importance=0.04741
10) f12 (pattern: # to spirit)                         importance=0.04627
11) f23 (pattern: #% increased rarity of items found)  importance=0.03638
12) f10 (pattern: # to maximum mana)                   importance=0.03496
13) f25 (pattern: #% to chaos resistance)              importance=0.03266
14) f6 (pattern: # to intelligence)                    importance=0.02657
15) f4 (pattern: # to dexterity)                       importance=0.02376
16) f1 (pattern: # life regeneration per second)       importance=0.02227
17) f5 (pattern: # to evasion rating)                  importance=0.01464
18) f7 (pattern: # to level of all minion skills)      importance=0.00552
19) f21 (pattern: #% increased light radius)           importance=0.00313
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00254
21) f24 (pattern: #% reduced attribute requirements)   importance=0.00100
22) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
