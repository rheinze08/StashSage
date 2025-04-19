=== helmet seg='ar_ev_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.0449
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f3 (pattern: # to armour)
  f4 (pattern: # to dexterity)
  f5 (pattern: # to evasion rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f13 (pattern: # to strength)
  f16 (pattern: #% increased armour and evasion)
  f17 (pattern: #% increased critical hit chance)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f9 (pattern: # to maximum life)                    importance=0.10802
 2) f23 (pattern: #% increased rarity of items found)  importance=0.10583
 3) f2 (pattern: # to accuracy rating)                 importance=0.09923
 4) f25 (pattern: #% to chaos resistance)              importance=0.09551
 5) f26 (pattern: #% to cold resistance)               importance=0.07614
 6) f28 (pattern: #% to lightning resistance)          importance=0.07160
 7) f27 (pattern: #% to fire resistance)               importance=0.05332
 8) f16 (pattern: #% increased armour and evasion)     importance=0.04993
 9) f1 (pattern: # life regeneration per second)       importance=0.04364
10) f4 (pattern: # to dexterity)                       importance=0.04224
11) f10 (pattern: # to maximum mana)                   importance=0.03996
12) f24 (pattern: #% reduced attribute requirements)   importance=0.03675
13) f6 (pattern: # to intelligence)                    importance=0.03207
14) f17 (pattern: #% increased critical hit chance)    importance=0.03011
15) f13 (pattern: # to strength)                       importance=0.02970
16) Quality (pattern: Quality)                         importance=0.02612
17) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01286
18) f3 (pattern: # to armour)                          importance=0.01142
19) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.01051
20) f7 (pattern: # to level of all minion skills)      importance=0.00986
21) f5 (pattern: # to evasion rating)                  importance=0.00910
22) f21 (pattern: #% increased light radius)           importance=0.00360
23) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00250
24) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
25) f12 (pattern: # to spirit)                         importance=0.00000
26) f11 (pattern: # to maximum power charges)          importance=0.00000
