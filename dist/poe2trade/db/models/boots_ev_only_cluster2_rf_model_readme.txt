=== boots seg='ev_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.0477
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f10 (pattern: # to stun threshold)
  f16 (pattern: #% increased evasion rating)
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
 1) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.10892
 2) f28 (pattern: #% to fire resistance)               importance=0.10128
 3) f18 (pattern: #% increased movement speed)         importance=0.09832
 4) f16 (pattern: #% increased evasion rating)         importance=0.09050
 5) f29 (pattern: #% to lightning resistance)          importance=0.07932
 6) Quality (pattern: Quality)                         importance=0.06230
 7) f7 (pattern: # to maximum life)                    importance=0.05682
 8) f27 (pattern: #% to cold resistance)               importance=0.05429
 9) f4 (pattern: # to evasion rating)                  importance=0.05318
10) f10 (pattern: # to stun threshold)                 importance=0.04653
11) f3 (pattern: # to dexterity)                       importance=0.04644
12) f26 (pattern: #% to chaos resistance)              importance=0.04035
13) f19 (pattern: #% increased rarity of items found)  importance=0.03791
14) f23 (pattern: #% reduced freeze duration on you)   importance=0.03609
15) f1 (pattern: # life regeneration per second)       importance=0.02514
16) f8 (pattern: # to maximum mana)                    importance=0.02301
17) f21 (pattern: #% reduced attribute requirements)   importance=0.01513
18) f22 (pattern: #% reduced chill duration on you)    importance=0.01436
19) f24 (pattern: #% reduced shock duration on you)    importance=0.00782
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00185
21) f17 (pattern: #% increased freeze threshold)       importance=0.00036
22) f20 (pattern: #% increased stun threshold)         importance=0.00007
23) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
