=== boots seg='ev_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: 0.0291
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
 1) f18 (pattern: #% increased movement speed)         importance=0.16673
 2) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.14836
 3) f28 (pattern: #% to fire resistance)               importance=0.10459
 4) f29 (pattern: #% to lightning resistance)          importance=0.09595
 5) f26 (pattern: #% to chaos resistance)              importance=0.06866
 6) f27 (pattern: #% to cold resistance)               importance=0.06390
 7) f16 (pattern: #% increased evasion rating)         importance=0.05827
 8) f7 (pattern: # to maximum life)                    importance=0.04676
 9) f4 (pattern: # to evasion rating)                  importance=0.04567
10) f10 (pattern: # to stun threshold)                 importance=0.03055
11) f24 (pattern: #% reduced shock duration on you)    importance=0.02678
12) f8 (pattern: # to maximum mana)                    importance=0.02613
13) f3 (pattern: # to dexterity)                       importance=0.02582
14) f19 (pattern: #% increased rarity of items found)  importance=0.02353
15) f1 (pattern: # life regeneration per second)       importance=0.02087
16) f21 (pattern: #% reduced attribute requirements)   importance=0.02008
17) Quality (pattern: Quality)                         importance=0.01501
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00506
19) f22 (pattern: #% reduced chill duration on you)    importance=0.00461
20) f23 (pattern: #% reduced freeze duration on you)   importance=0.00265
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
23) f20 (pattern: #% increased stun threshold)         importance=0.00000
