=== helmet seg='ev_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0120
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
 1) Quality (pattern: Quality)                         importance=0.08085
 2) f20 (pattern: #% increased evasion rating)         importance=0.06770
 3) f26 (pattern: #% to cold resistance)               importance=0.06380
 4) f2 (pattern: # to accuracy rating)                 importance=0.06307
 5) f28 (pattern: #% to lightning resistance)          importance=0.05907
 6) f12 (pattern: # to spirit)                         importance=0.05528
 7) f9 (pattern: # to maximum life)                    importance=0.05520
 8) f6 (pattern: # to intelligence)                    importance=0.05103
 9) f7 (pattern: # to level of all minion skills)      importance=0.05016
10) f25 (pattern: #% to chaos resistance)              importance=0.04864
11) f27 (pattern: #% to fire resistance)               importance=0.04859
12) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.04544
13) f23 (pattern: #% increased rarity of items found)  importance=0.04198
14) f17 (pattern: #% increased critical hit chance)    importance=0.04113
15) f10 (pattern: # to maximum mana)                   importance=0.04018
16) f24 (pattern: #% reduced attribute requirements)   importance=0.04014
17) f1 (pattern: # life regeneration per second)       importance=0.03914
18) f5 (pattern: # to evasion rating)                  importance=0.03882
19) f4 (pattern: # to dexterity)                       importance=0.03520
20) f21 (pattern: #% increased light radius)           importance=0.03460
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
