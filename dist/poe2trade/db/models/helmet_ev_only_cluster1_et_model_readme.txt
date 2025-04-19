=== helmet seg='ev_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.1692
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
 1) f2 (pattern: # to accuracy rating)                 importance=0.12336
 2) f5 (pattern: # to evasion rating)                  importance=0.10696
 3) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.10270
 4) Quality (pattern: Quality)                         importance=0.10214
 5) f20 (pattern: #% increased evasion rating)         importance=0.10054
 6) f6 (pattern: # to intelligence)                    importance=0.07181
 7) f4 (pattern: # to dexterity)                       importance=0.05562
 8) f9 (pattern: # to maximum life)                    importance=0.04576
 9) f24 (pattern: #% reduced attribute requirements)   importance=0.04557
10) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.03786
11) f23 (pattern: #% increased rarity of items found)  importance=0.03670
12) f27 (pattern: #% to fire resistance)               importance=0.03219
13) f1 (pattern: # life regeneration per second)       importance=0.03138
14) f28 (pattern: #% to lightning resistance)          importance=0.02877
15) f26 (pattern: #% to cold resistance)               importance=0.02744
16) f10 (pattern: # to maximum mana)                   importance=0.02012
17) f25 (pattern: #% to chaos resistance)              importance=0.01459
18) f21 (pattern: #% increased light radius)           importance=0.00755
19) f17 (pattern: #% increased critical hit chance)    importance=0.00613
20) f7 (pattern: # to level of all minion skills)      importance=0.00223
21) f12 (pattern: # to spirit)                         importance=0.00037
22) f22 (pattern: #% increased mana regeneration rate) importance=0.00021
