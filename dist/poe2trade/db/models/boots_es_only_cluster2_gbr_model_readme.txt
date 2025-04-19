=== boots seg='es_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0931
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
 1) f18 (pattern: #% increased movement speed)         importance=0.19983
 2) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.16843
 3) f29 (pattern: #% to lightning resistance)          importance=0.09479
 4) f27 (pattern: #% to cold resistance)               importance=0.09272
 5) f6 (pattern: # to maximum energy shield)           importance=0.07579
 6) f7 (pattern: # to maximum life)                    importance=0.06423
 7) Quality (pattern: Quality)                         importance=0.05994
 8) f8 (pattern: # to maximum mana)                    importance=0.03968
 9) f5 (pattern: # to intelligence)                    importance=0.03719
10) f14 (pattern: #% increased energy shield)          importance=0.03284
11) f1 (pattern: # life regeneration per second)       importance=0.03173
12) f28 (pattern: #% to fire resistance)               importance=0.01926
13) f23 (pattern: #% reduced freeze duration on you)   importance=0.01888
14) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01853
15) f10 (pattern: # to stun threshold)                 importance=0.01701
16) f26 (pattern: #% to chaos resistance)              importance=0.01271
17) f24 (pattern: #% reduced shock duration on you)    importance=0.00654
18) f19 (pattern: #% increased rarity of items found)  importance=0.00491
19) f22 (pattern: #% reduced chill duration on you)    importance=0.00460
20) f21 (pattern: #% reduced attribute requirements)   importance=0.00040
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
