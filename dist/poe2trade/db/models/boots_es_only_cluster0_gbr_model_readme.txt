=== boots seg='es_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0635
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
 1) f18 (pattern: #% increased movement speed)         importance=0.28167
 2) f27 (pattern: #% to cold resistance)               importance=0.20282
 3) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.14660
 4) f29 (pattern: #% to lightning resistance)          importance=0.06896
 5) f28 (pattern: #% to fire resistance)               importance=0.04578
 6) f7 (pattern: # to maximum life)                    importance=0.04187
 7) f26 (pattern: #% to chaos resistance)              importance=0.04007
 8) f19 (pattern: #% increased rarity of items found)  importance=0.03823
 9) Quality (pattern: Quality)                         importance=0.02433
10) f22 (pattern: #% reduced chill duration on you)    importance=0.02270
11) f14 (pattern: #% increased energy shield)          importance=0.02210
12) f5 (pattern: # to intelligence)                    importance=0.01320
13) f10 (pattern: # to stun threshold)                 importance=0.01275
14) f6 (pattern: # to maximum energy shield)           importance=0.01241
15) f23 (pattern: #% reduced freeze duration on you)   importance=0.00976
16) f8 (pattern: # to maximum mana)                    importance=0.00952
17) f1 (pattern: # life regeneration per second)       importance=0.00491
18) f21 (pattern: #% reduced attribute requirements)   importance=0.00230
19) f24 (pattern: #% reduced shock duration on you)    importance=0.00000
20) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
