=== boots seg='es_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: 0.0488
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to maximum energy shield)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f10 (pattern: # to stun threshold)
  f14 (pattern: #% increased energy shield)
  f17 (pattern: #% increased freeze threshold)
  f18 (pattern: #% increased movement speed)
  f19 (pattern: #% increased rarity of items found)
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
 1) f18 (pattern: #% increased movement speed)         importance=0.18220
 2) f6 (pattern: # to maximum energy shield)           importance=0.14530
 3) Quality (pattern: Quality)                         importance=0.13669
 4) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.12322
 5) f28 (pattern: #% to fire resistance)               importance=0.10419
 6) f27 (pattern: #% to cold resistance)               importance=0.04239
 7) f24 (pattern: #% reduced shock duration on you)    importance=0.04063
 8) f14 (pattern: #% increased energy shield)          importance=0.03841
 9) f8 (pattern: # to maximum mana)                    importance=0.03297
10) f29 (pattern: #% to lightning resistance)          importance=0.02674
11) f10 (pattern: # to stun threshold)                 importance=0.01967
12) f21 (pattern: #% reduced attribute requirements)   importance=0.01872
13) f26 (pattern: #% to chaos resistance)              importance=0.01859
14) f7 (pattern: # to maximum life)                    importance=0.01566
15) f23 (pattern: #% reduced freeze duration on you)   importance=0.01457
16) f19 (pattern: #% increased rarity of items found)  importance=0.01347
17) f5 (pattern: # to intelligence)                    importance=0.01085
18) f1 (pattern: # life regeneration per second)       importance=0.00968
19) f22 (pattern: #% reduced chill duration on you)    importance=0.00403
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00156
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00046
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
