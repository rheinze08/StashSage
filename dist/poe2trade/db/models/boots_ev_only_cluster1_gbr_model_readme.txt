=== boots seg='ev_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0408
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
 1) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.18980
 2) f18 (pattern: #% increased movement speed)         importance=0.09832
 3) f29 (pattern: #% to lightning resistance)          importance=0.09363
 4) f28 (pattern: #% to fire resistance)               importance=0.08425
 5) f4 (pattern: # to evasion rating)                  importance=0.07666
 6) f10 (pattern: # to stun threshold)                 importance=0.06378
 7) f7 (pattern: # to maximum life)                    importance=0.05948
 8) f16 (pattern: #% increased evasion rating)         importance=0.05891
 9) f27 (pattern: #% to cold resistance)               importance=0.05268
10) f3 (pattern: # to dexterity)                       importance=0.04938
11) f26 (pattern: #% to chaos resistance)              importance=0.03491
12) f8 (pattern: # to maximum mana)                    importance=0.03210
13) f24 (pattern: #% reduced shock duration on you)    importance=0.02477
14) f1 (pattern: # life regeneration per second)       importance=0.02176
15) f21 (pattern: #% reduced attribute requirements)   importance=0.02127
16) f19 (pattern: #% increased rarity of items found)  importance=0.01916
17) Quality (pattern: Quality)                         importance=0.01041
18) f23 (pattern: #% reduced freeze duration on you)   importance=0.00495
19) f22 (pattern: #% reduced chill duration on you)    importance=0.00328
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00049
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
23) f20 (pattern: #% increased stun threshold)         importance=0.00000
