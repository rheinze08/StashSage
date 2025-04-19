=== boots seg='ev_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0056
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
 1) f18 (pattern: #% increased movement speed)         importance=0.09026
 2) f29 (pattern: #% to lightning resistance)          importance=0.07297
 3) f28 (pattern: #% to fire resistance)               importance=0.07038
 4) f21 (pattern: #% reduced attribute requirements)   importance=0.06151
 5) f10 (pattern: # to stun threshold)                 importance=0.06018
 6) f27 (pattern: #% to cold resistance)               importance=0.05897
 7) f24 (pattern: #% reduced shock duration on you)    importance=0.05845
 8) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05532
 9) f16 (pattern: #% increased evasion rating)         importance=0.05467
10) f8 (pattern: # to maximum mana)                    importance=0.05082
11) f26 (pattern: #% to chaos resistance)              importance=0.04891
12) f7 (pattern: # to maximum life)                    importance=0.04540
13) f4 (pattern: # to evasion rating)                  importance=0.04450
14) f22 (pattern: #% reduced chill duration on you)    importance=0.03999
15) f19 (pattern: #% increased rarity of items found)  importance=0.03767
16) Quality (pattern: Quality)                         importance=0.03401
17) f3 (pattern: # to dexterity)                       importance=0.03399
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.03070
19) f1 (pattern: # life regeneration per second)       importance=0.02570
20) f23 (pattern: #% reduced freeze duration on you)   importance=0.02559
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
23) f20 (pattern: #% increased stun threshold)         importance=0.00000
