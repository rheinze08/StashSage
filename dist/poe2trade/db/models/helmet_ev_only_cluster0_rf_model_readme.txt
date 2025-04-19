=== helmet seg='ev_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: -0.0084
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
 1) f27 (pattern: #% to fire resistance)               importance=0.13311
 2) f20 (pattern: #% increased evasion rating)         importance=0.09924
 3) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.09046
 4) f28 (pattern: #% to lightning resistance)          importance=0.08770
 5) f23 (pattern: #% increased rarity of items found)  importance=0.07706
 6) f26 (pattern: #% to cold resistance)               importance=0.06819
 7) f4 (pattern: # to dexterity)                       importance=0.06074
 8) f9 (pattern: # to maximum life)                    importance=0.06006
 9) f17 (pattern: #% increased critical hit chance)    importance=0.05933
10) f2 (pattern: # to accuracy rating)                 importance=0.05475
11) f10 (pattern: # to maximum mana)                   importance=0.04780
12) f6 (pattern: # to intelligence)                    importance=0.03804
13) f5 (pattern: # to evasion rating)                  importance=0.03433
14) f25 (pattern: #% to chaos resistance)              importance=0.03421
15) Quality (pattern: Quality)                         importance=0.02390
16) f1 (pattern: # life regeneration per second)       importance=0.01699
17) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00725
18) f24 (pattern: #% reduced attribute requirements)   importance=0.00546
19) f21 (pattern: #% increased light radius)           importance=0.00140
20) f7 (pattern: # to level of all minion skills)      importance=0.00000
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) f12 (pattern: # to spirit)                         importance=0.00000
