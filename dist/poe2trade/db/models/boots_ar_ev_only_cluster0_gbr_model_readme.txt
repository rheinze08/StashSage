=== boots seg='ar_ev_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0730
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
 1) f7 (pattern: # to maximum life)                    importance=0.13696
 2) f19 (pattern: #% increased rarity of items found)  importance=0.12279
 3) f29 (pattern: #% to lightning resistance)          importance=0.08681
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.08124
 5) f18 (pattern: #% increased movement speed)         importance=0.07619
 6) Deflated_Armour (pattern: Deflated_Armour)         importance=0.06852
 7) f4 (pattern: # to evasion rating)                  importance=0.06669
 8) f8 (pattern: # to maximum mana)                    importance=0.06520
 9) f26 (pattern: #% to chaos resistance)              importance=0.04894
10) f21 (pattern: #% reduced attribute requirements)   importance=0.04044
11) f1 (pattern: # life regeneration per second)       importance=0.03864
12) f10 (pattern: # to stun threshold)                 importance=0.02553
13) f27 (pattern: #% to cold resistance)               importance=0.02076
14) f3 (pattern: # to dexterity)                       importance=0.01947
15) Quality (pattern: Quality)                         importance=0.01906
16) f23 (pattern: #% reduced freeze duration on you)   importance=0.01808
17) f22 (pattern: #% reduced chill duration on you)    importance=0.01554
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01162
19) f28 (pattern: #% to fire resistance)               importance=0.01086
20) f13 (pattern: #% increased armour and evasion)     importance=0.01062
21) f9 (pattern: # to strength)                        importance=0.00744
22) f2 (pattern: # to armour)                          importance=0.00572
23) f24 (pattern: #% reduced shock duration on you)    importance=0.00247
24) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00041
25) f20 (pattern: #% increased stun threshold)         importance=0.00000
26) f17 (pattern: #% increased freeze threshold)       importance=0.00000
