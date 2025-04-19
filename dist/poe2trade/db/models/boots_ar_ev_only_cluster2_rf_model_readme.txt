=== boots seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.6630
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
 1) f26 (pattern: #% to chaos resistance)              importance=0.17810
 2) f23 (pattern: #% reduced freeze duration on you)   importance=0.14652
 3) f27 (pattern: #% to cold resistance)               importance=0.11960
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.07613
 5) Deflated_Armour (pattern: Deflated_Armour)         importance=0.07517
 6) f18 (pattern: #% increased movement speed)         importance=0.07142
 7) f8 (pattern: # to maximum mana)                    importance=0.05223
 8) f29 (pattern: #% to lightning resistance)          importance=0.04932
 9) f13 (pattern: #% increased armour and evasion)     importance=0.04815
10) f3 (pattern: # to dexterity)                       importance=0.03893
11) f28 (pattern: #% to fire resistance)               importance=0.03656
12) f7 (pattern: # to maximum life)                    importance=0.03238
13) f19 (pattern: #% increased rarity of items found)  importance=0.03151
14) f9 (pattern: # to strength)                        importance=0.01311
15) f2 (pattern: # to armour)                          importance=0.01068
16) f10 (pattern: # to stun threshold)                 importance=0.00896
17) f24 (pattern: #% reduced shock duration on you)    importance=0.00555
18) f21 (pattern: #% reduced attribute requirements)   importance=0.00159
19) Quality (pattern: Quality)                         importance=0.00136
20) f4 (pattern: # to evasion rating)                  importance=0.00119
21) f1 (pattern: # life regeneration per second)       importance=0.00081
22) f22 (pattern: #% reduced chill duration on you)    importance=0.00072
23) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
24) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
25) f20 (pattern: #% increased stun threshold)         importance=0.00000
26) f17 (pattern: #% increased freeze threshold)       importance=0.00000
