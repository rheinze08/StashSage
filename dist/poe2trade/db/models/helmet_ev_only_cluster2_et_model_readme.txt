=== helmet seg='ev_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: -0.0382
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
 1) Quality (pattern: Quality)                         importance=0.17635
 2) f26 (pattern: #% to cold resistance)               importance=0.16172
 3) f12 (pattern: # to spirit)                         importance=0.11183
 4) f2 (pattern: # to accuracy rating)                 importance=0.10852
 5) f28 (pattern: #% to lightning resistance)          importance=0.06223
 6) f20 (pattern: #% increased evasion rating)         importance=0.04907
 7) f9 (pattern: # to maximum life)                    importance=0.04659
 8) f17 (pattern: #% increased critical hit chance)    importance=0.03635
 9) f10 (pattern: # to maximum mana)                   importance=0.03412
10) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.02916
11) f27 (pattern: #% to fire resistance)               importance=0.02868
12) f21 (pattern: #% increased light radius)           importance=0.02547
13) f1 (pattern: # life regeneration per second)       importance=0.02430
14) f4 (pattern: # to dexterity)                       importance=0.02168
15) f5 (pattern: # to evasion rating)                  importance=0.01761
16) f25 (pattern: #% to chaos resistance)              importance=0.01651
17) f6 (pattern: # to intelligence)                    importance=0.01590
18) f23 (pattern: #% increased rarity of items found)  importance=0.01573
19) f24 (pattern: #% reduced attribute requirements)   importance=0.01028
20) f7 (pattern: # to level of all minion skills)      importance=0.00696
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00095
22) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
