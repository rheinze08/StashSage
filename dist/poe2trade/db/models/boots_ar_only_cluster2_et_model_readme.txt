=== boots seg='ar_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: 0.0019
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
 1) f18 (pattern: #% increased movement speed)         importance=0.12881
 2) Deflated_Armour (pattern: Deflated_Armour)         importance=0.12065
 3) f28 (pattern: #% to fire resistance)               importance=0.10244
 4) f27 (pattern: #% to cold resistance)               importance=0.08002
 5) Quality (pattern: Quality)                         importance=0.07361
 6) f29 (pattern: #% to lightning resistance)          importance=0.07275
 7) f7 (pattern: # to maximum life)                    importance=0.06674
 8) f26 (pattern: #% to chaos resistance)              importance=0.06569
 9) f9 (pattern: # to strength)                        importance=0.05022
10) f10 (pattern: # to stun threshold)                 importance=0.04910
11) f11 (pattern: #% increased armour)                 importance=0.02810
12) f2 (pattern: # to armour)                          importance=0.02167
13) f24 (pattern: #% reduced shock duration on you)    importance=0.02142
14) f22 (pattern: #% reduced chill duration on you)    importance=0.02035
15) f23 (pattern: #% reduced freeze duration on you)   importance=0.01998
16) f8 (pattern: # to maximum mana)                    importance=0.01634
17) f19 (pattern: #% increased rarity of items found)  importance=0.01617
18) f1 (pattern: # life regeneration per second)       importance=0.01610
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01553
20) f21 (pattern: #% reduced attribute requirements)   importance=0.01431
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) f20 (pattern: #% increased stun threshold)         importance=0.00000
