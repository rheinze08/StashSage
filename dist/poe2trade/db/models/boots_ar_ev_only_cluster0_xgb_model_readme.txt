=== boots seg='ar_ev_only' cluster=0 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0623
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f9 (pattern: # to strength)
  f10 (pattern: # to stun threshold)
  f13 (pattern: #% increased armour and evasion)
  f17 (pattern: #% increased freeze threshold)
  f18 (pattern: #% increased movement speed)
  f19 (pattern: #% increased rarity of items found)
  f20 (pattern: #% increased stun threshold)
  f21 (pattern: #% reduced attribute requirements)
  f22 (pattern: #% reduced chill duration on you)
  f23 (pattern: #% reduced freeze duration on you)
  f24 (pattern: #% reduced shock duration on you)
  f25 (pattern: #% reduced slowing potency of debuffs on you)
  f26 (pattern: #% to chaos resistance)
  f27 (pattern: #% to cold resistance)
  f28 (pattern: #% to fire resistance)
  f29 (pattern: #% to lightning resistance)

Feature Importances:
 1) f19 (pattern: #% increased rarity of items found)  importance=0.08110
 2) f7 (pattern: # to maximum life)                    importance=0.06035
 3) f4 (pattern: # to evasion rating)                  importance=0.05745
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05113
 5) f1 (pattern: # life regeneration per second)       importance=0.04921
 6) Deflated_Armour (pattern: Deflated_Armour)         importance=0.04798
 7) f24 (pattern: #% reduced shock duration on you)    importance=0.04762
 8) f8 (pattern: # to maximum mana)                    importance=0.04750
 9) f18 (pattern: #% increased movement speed)         importance=0.04742
10) f29 (pattern: #% to lightning resistance)          importance=0.04538
11) f28 (pattern: #% to fire resistance)               importance=0.04484
12) f21 (pattern: #% reduced attribute requirements)   importance=0.04448
13) f26 (pattern: #% to chaos resistance)              importance=0.04233
14) f3 (pattern: # to dexterity)                       importance=0.04154
15) f10 (pattern: # to stun threshold)                 importance=0.04036
16) f9 (pattern: # to strength)                        importance=0.03889
17) Quality (pattern: Quality)                         importance=0.03503
18) f13 (pattern: #% increased armour and evasion)     importance=0.03361
19) f23 (pattern: #% reduced freeze duration on you)   importance=0.03360
20) f27 (pattern: #% to cold resistance)               importance=0.03162
21) f2 (pattern: # to armour)                          importance=0.02757
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.02568
23) f22 (pattern: #% reduced chill duration on you)    importance=0.02530
24) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
25) f20 (pattern: #% increased stun threshold)         importance=0.00000
26) f17 (pattern: #% increased freeze threshold)       importance=0.00000
