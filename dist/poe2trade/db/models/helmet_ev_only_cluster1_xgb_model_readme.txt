=== helmet seg='ev_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0405
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
 1) f20 (pattern: #% increased evasion rating)         importance=0.07392
 2) f2 (pattern: # to accuracy rating)                 importance=0.06890
 3) Quality (pattern: Quality)                         importance=0.05749
 4) f23 (pattern: #% increased rarity of items found)  importance=0.05486
 5) f21 (pattern: #% increased light radius)           importance=0.05441
 6) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.05397
 7) f6 (pattern: # to intelligence)                    importance=0.05318
 8) f28 (pattern: #% to lightning resistance)          importance=0.05088
 9) f26 (pattern: #% to cold resistance)               importance=0.05060
10) f5 (pattern: # to evasion rating)                  importance=0.05036
11) f10 (pattern: # to maximum mana)                   importance=0.04698
12) f4 (pattern: # to dexterity)                       importance=0.04562
13) f17 (pattern: #% increased critical hit chance)    importance=0.04554
14) f9 (pattern: # to maximum life)                    importance=0.04485
15) f27 (pattern: #% to fire resistance)               importance=0.04444
16) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.04198
17) f24 (pattern: #% reduced attribute requirements)   importance=0.03948
18) f7 (pattern: # to level of all minion skills)      importance=0.03778
19) f25 (pattern: #% to chaos resistance)              importance=0.03233
20) f1 (pattern: # life regeneration per second)       importance=0.02991
21) f22 (pattern: #% increased mana regeneration rate) importance=0.02251
22) f12 (pattern: # to spirit)                         importance=0.00000
