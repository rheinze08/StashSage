=== helmet seg='ar_ev_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0306
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
 1) f25 (pattern: #% to chaos resistance)              importance=0.06380
 2) f27 (pattern: #% to fire resistance)               importance=0.06267
 3) f23 (pattern: #% increased rarity of items found)  importance=0.05789
 4) f28 (pattern: #% to lightning resistance)          importance=0.05751
 5) f16 (pattern: #% increased armour and evasion)     importance=0.05642
 6) f2 (pattern: # to accuracy rating)                 importance=0.05471
 7) f9 (pattern: # to maximum life)                    importance=0.05212
 8) f13 (pattern: # to strength)                       importance=0.05161
 9) f10 (pattern: # to maximum mana)                   importance=0.05096
10) f26 (pattern: #% to cold resistance)               importance=0.04697
11) f6 (pattern: # to intelligence)                    importance=0.04576
12) f4 (pattern: # to dexterity)                       importance=0.04570
13) f17 (pattern: #% increased critical hit chance)    importance=0.04445
14) f24 (pattern: #% reduced attribute requirements)   importance=0.04012
15) f1 (pattern: # life regeneration per second)       importance=0.03897
16) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03825
17) Quality (pattern: Quality)                         importance=0.03580
18) f3 (pattern: # to armour)                          importance=0.03008
19) f7 (pattern: # to level of all minion skills)      importance=0.02993
20) f5 (pattern: # to evasion rating)                  importance=0.02885
21) Deflated_Armour (pattern: Deflated_Armour)         importance=0.02716
22) f21 (pattern: #% increased light radius)           importance=0.02639
23) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01389
24) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
25) f12 (pattern: # to spirit)                         importance=0.00000
26) f11 (pattern: # to maximum power charges)          importance=0.00000
