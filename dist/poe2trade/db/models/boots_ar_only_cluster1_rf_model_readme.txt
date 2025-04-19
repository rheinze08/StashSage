=== boots seg='ar_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.0965
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to armour)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f9 (pattern: # to strength)
  f10 (pattern: # to stun threshold)
  f11 (pattern: #% increased armour)
  f17 (pattern: #% increased freeze threshold)
  f18 (pattern: #% increased movement speed)
  f19 (pattern: #% increased rarity of items found)
  f20 (pattern: #% increased stun threshold)
  f21 (pattern: #% reduced attribute requirements)
  f22 (pattern: #% reduced chill duration on you)
  f23 (pattern: #% reduced freeze duration on you)
  f24 (pattern: #% reduced shock duration on you)
  f26 (pattern: #% to chaos resistance)
  f27 (pattern: #% to cold resistance)
  f28 (pattern: #% to fire resistance)
  f29 (pattern: #% to lightning resistance)

Feature Importances:
 1) f28 (pattern: #% to fire resistance)               importance=0.14498
 2) Deflated_Armour (pattern: Deflated_Armour)         importance=0.13786
 3) f11 (pattern: #% increased armour)                 importance=0.10679
 4) f26 (pattern: #% to chaos resistance)              importance=0.09739
 5) f2 (pattern: # to armour)                          importance=0.09075
 6) f27 (pattern: #% to cold resistance)               importance=0.07966
 7) f29 (pattern: #% to lightning resistance)          importance=0.06728
 8) f18 (pattern: #% increased movement speed)         importance=0.05138
 9) f19 (pattern: #% increased rarity of items found)  importance=0.04341
10) f7 (pattern: # to maximum life)                    importance=0.03861
11) f9 (pattern: # to strength)                        importance=0.02741
12) f8 (pattern: # to maximum mana)                    importance=0.02383
13) f21 (pattern: #% reduced attribute requirements)   importance=0.02111
14) f23 (pattern: #% reduced freeze duration on you)   importance=0.01907
15) f10 (pattern: # to stun threshold)                 importance=0.01581
16) f1 (pattern: # life regeneration per second)       importance=0.01410
17) Quality (pattern: Quality)                         importance=0.00973
18) f24 (pattern: #% reduced shock duration on you)    importance=0.00906
19) f22 (pattern: #% reduced chill duration on you)    importance=0.00149
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00027
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) f20 (pattern: #% increased stun threshold)         importance=0.00000
