=== boots seg='ev_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: 0.1624
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
 1) f7 (pattern: # to maximum life)                    importance=0.13034
 2) f18 (pattern: #% increased movement speed)         importance=0.12854
 3) f29 (pattern: #% to lightning resistance)          importance=0.09756
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.08612
 5) f27 (pattern: #% to cold resistance)               importance=0.08501
 6) f28 (pattern: #% to fire resistance)               importance=0.07926
 7) f26 (pattern: #% to chaos resistance)              importance=0.07761
 8) f16 (pattern: #% increased evasion rating)         importance=0.06928
 9) f10 (pattern: # to stun threshold)                 importance=0.04429
10) f8 (pattern: # to maximum mana)                    importance=0.03638
11) f19 (pattern: #% increased rarity of items found)  importance=0.03300
12) f1 (pattern: # life regeneration per second)       importance=0.02842
13) f3 (pattern: # to dexterity)                       importance=0.02757
14) f22 (pattern: #% reduced chill duration on you)    importance=0.01653
15) f4 (pattern: # to evasion rating)                  importance=0.01495
16) Quality (pattern: Quality)                         importance=0.01334
17) f21 (pattern: #% reduced attribute requirements)   importance=0.01025
18) f23 (pattern: #% reduced freeze duration on you)   importance=0.00941
19) f24 (pattern: #% reduced shock duration on you)    importance=0.00787
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00382
21) f17 (pattern: #% increased freeze threshold)       importance=0.00046
22) f20 (pattern: #% increased stun threshold)         importance=0.00000
23) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
