=== boots seg='ar_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0820
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
 1) f26 (pattern: #% to chaos resistance)              importance=0.08203
 2) f28 (pattern: #% to fire resistance)               importance=0.07701
 3) Deflated_Armour (pattern: Deflated_Armour)         importance=0.07322
 4) f29 (pattern: #% to lightning resistance)          importance=0.07222
 5) f27 (pattern: #% to cold resistance)               importance=0.06812
 6) f18 (pattern: #% increased movement speed)         importance=0.06435
 7) f11 (pattern: #% increased armour)                 importance=0.06169
 8) f2 (pattern: # to armour)                          importance=0.05890
 9) f7 (pattern: # to maximum life)                    importance=0.05831
10) f21 (pattern: #% reduced attribute requirements)   importance=0.05563
11) f19 (pattern: #% increased rarity of items found)  importance=0.05306
12) Quality (pattern: Quality)                         importance=0.04748
13) f23 (pattern: #% reduced freeze duration on you)   importance=0.04564
14) f9 (pattern: # to strength)                        importance=0.04538
15) f10 (pattern: # to stun threshold)                 importance=0.04251
16) f8 (pattern: # to maximum mana)                    importance=0.03471
17) f24 (pattern: #% reduced shock duration on you)    importance=0.03008
18) f1 (pattern: # life regeneration per second)       importance=0.02965
19) f17 (pattern: #% increased freeze threshold)       importance=0.00000
20) f20 (pattern: #% increased stun threshold)         importance=0.00000
21) f22 (pattern: #% reduced chill duration on you)    importance=0.00000
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
