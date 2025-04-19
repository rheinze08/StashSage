=== boots seg='ar_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: 0.1946
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
 1) f7 (pattern: # to maximum life)                    importance=0.16054
 2) f18 (pattern: #% increased movement speed)         importance=0.14095
 3) f28 (pattern: #% to fire resistance)               importance=0.10303
 4) Deflated_Armour (pattern: Deflated_Armour)         importance=0.08309
 5) f27 (pattern: #% to cold resistance)               importance=0.07756
 6) f29 (pattern: #% to lightning resistance)          importance=0.07306
 7) f26 (pattern: #% to chaos resistance)              importance=0.06393
 8) f9 (pattern: # to strength)                        importance=0.06216
 9) f8 (pattern: # to maximum mana)                    importance=0.04800
10) f11 (pattern: #% increased armour)                 importance=0.03536
11) f19 (pattern: #% increased rarity of items found)  importance=0.03272
12) f10 (pattern: # to stun threshold)                 importance=0.02927
13) f1 (pattern: # life regeneration per second)       importance=0.01801
14) f24 (pattern: #% reduced shock duration on you)    importance=0.01777
15) f21 (pattern: #% reduced attribute requirements)   importance=0.01349
16) f2 (pattern: # to armour)                          importance=0.01272
17) Quality (pattern: Quality)                         importance=0.01015
18) f22 (pattern: #% reduced chill duration on you)    importance=0.00908
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00559
20) f23 (pattern: #% reduced freeze duration on you)   importance=0.00352
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) f20 (pattern: #% increased stun threshold)         importance=0.00000
