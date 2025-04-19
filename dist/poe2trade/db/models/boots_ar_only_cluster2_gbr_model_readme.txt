=== boots seg='ar_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0493
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
 1) Deflated_Armour (pattern: Deflated_Armour)         importance=0.13326
 2) f28 (pattern: #% to fire resistance)               importance=0.11246
 3) f18 (pattern: #% increased movement speed)         importance=0.10788
 4) f7 (pattern: # to maximum life)                    importance=0.08727
 5) f27 (pattern: #% to cold resistance)               importance=0.07561
 6) f11 (pattern: #% increased armour)                 importance=0.06716
 7) f29 (pattern: #% to lightning resistance)          importance=0.06161
 8) Quality (pattern: Quality)                         importance=0.05984
 9) f10 (pattern: # to stun threshold)                 importance=0.05819
10) f9 (pattern: # to strength)                        importance=0.04644
11) f26 (pattern: #% to chaos resistance)              importance=0.04626
12) f24 (pattern: #% reduced shock duration on you)    importance=0.02914
13) f1 (pattern: # life regeneration per second)       importance=0.02612
14) f22 (pattern: #% reduced chill duration on you)    importance=0.01714
15) f2 (pattern: # to armour)                          importance=0.01671
16) f8 (pattern: # to maximum mana)                    importance=0.01611
17) f23 (pattern: #% reduced freeze duration on you)   importance=0.01194
18) f19 (pattern: #% increased rarity of items found)  importance=0.01126
19) f21 (pattern: #% reduced attribute requirements)   importance=0.00860
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00701
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) f20 (pattern: #% increased stun threshold)         importance=0.00000
