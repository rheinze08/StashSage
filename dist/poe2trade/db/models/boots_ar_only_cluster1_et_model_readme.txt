=== boots seg='ar_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: 0.1205
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
 1) Deflated_Armour (pattern: Deflated_Armour)         importance=0.17381
 2) f26 (pattern: #% to chaos resistance)              importance=0.09617
 3) f11 (pattern: #% increased armour)                 importance=0.09411
 4) f28 (pattern: #% to fire resistance)               importance=0.09369
 5) f18 (pattern: #% increased movement speed)         importance=0.07564
 6) f27 (pattern: #% to cold resistance)               importance=0.07224
 7) f29 (pattern: #% to lightning resistance)          importance=0.06144
 8) f19 (pattern: #% increased rarity of items found)  importance=0.05585
 9) f2 (pattern: # to armour)                          importance=0.04722
10) f7 (pattern: # to maximum life)                    importance=0.04094
11) f9 (pattern: # to strength)                        importance=0.04085
12) f21 (pattern: #% reduced attribute requirements)   importance=0.02339
13) f8 (pattern: # to maximum mana)                    importance=0.02283
14) Quality (pattern: Quality)                         importance=0.02165
15) f23 (pattern: #% reduced freeze duration on you)   importance=0.02099
16) f1 (pattern: # life regeneration per second)       importance=0.01992
17) f24 (pattern: #% reduced shock duration on you)    importance=0.01733
18) f10 (pattern: # to stun threshold)                 importance=0.01186
19) f22 (pattern: #% reduced chill duration on you)    importance=0.01007
20) f20 (pattern: #% increased stun threshold)         importance=0.00000
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
