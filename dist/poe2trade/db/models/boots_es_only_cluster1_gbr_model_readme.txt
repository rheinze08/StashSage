=== boots seg='es_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: 0.1087
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
 1) f18 (pattern: #% increased movement speed)         importance=0.19834
 2) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.18977
 3) f28 (pattern: #% to fire resistance)               importance=0.11647
 4) f6 (pattern: # to maximum energy shield)           importance=0.11011
 5) Quality (pattern: Quality)                         importance=0.10883
 6) f29 (pattern: #% to lightning resistance)          importance=0.04788
 7) f27 (pattern: #% to cold resistance)               importance=0.04166
 8) f14 (pattern: #% increased energy shield)          importance=0.04127
 9) f24 (pattern: #% reduced shock duration on you)    importance=0.03923
10) f10 (pattern: # to stun threshold)                 importance=0.02356
11) f8 (pattern: # to maximum mana)                    importance=0.01697
12) f1 (pattern: # life regeneration per second)       importance=0.01386
13) f7 (pattern: # to maximum life)                    importance=0.01378
14) f23 (pattern: #% reduced freeze duration on you)   importance=0.01271
15) f5 (pattern: # to intelligence)                    importance=0.00883
16) f26 (pattern: #% to chaos resistance)              importance=0.00728
17) f19 (pattern: #% increased rarity of items found)  importance=0.00479
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00193
19) f21 (pattern: #% reduced attribute requirements)   importance=0.00161
20) f22 (pattern: #% reduced chill duration on you)    importance=0.00112
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
