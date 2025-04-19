=== helmet seg='ar_ev_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: -0.0316
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
 1) f9 (pattern: # to maximum life)                    importance=0.10154
 2) f2 (pattern: # to accuracy rating)                 importance=0.08766
 3) f27 (pattern: #% to fire resistance)               importance=0.07429
 4) f10 (pattern: # to maximum mana)                   importance=0.06986
 5) f23 (pattern: #% increased rarity of items found)  importance=0.06700
 6) f28 (pattern: #% to lightning resistance)          importance=0.06031
 7) f17 (pattern: #% increased critical hit chance)    importance=0.05500
 8) f16 (pattern: #% increased armour and evasion)     importance=0.05285
 9) f4 (pattern: # to dexterity)                       importance=0.05171
10) f25 (pattern: #% to chaos resistance)              importance=0.05028
11) f26 (pattern: #% to cold resistance)               importance=0.04955
12) Quality (pattern: Quality)                         importance=0.04828
13) f6 (pattern: # to intelligence)                    importance=0.04779
14) f13 (pattern: # to strength)                       importance=0.03821
15) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03359
16) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03026
17) f1 (pattern: # life regeneration per second)       importance=0.02445
18) f24 (pattern: #% reduced attribute requirements)   importance=0.02341
19) f7 (pattern: # to level of all minion skills)      importance=0.01343
20) f5 (pattern: # to evasion rating)                  importance=0.00998
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00372
22) f3 (pattern: # to armour)                          importance=0.00361
23) f21 (pattern: #% increased light radius)           importance=0.00321
24) f11 (pattern: # to maximum power charges)          importance=0.00001
25) f12 (pattern: # to spirit)                         importance=0.00001
26) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
