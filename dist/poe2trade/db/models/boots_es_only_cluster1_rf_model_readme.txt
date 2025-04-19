=== boots seg='es_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.1042
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
 1) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.19017
 2) f18 (pattern: #% increased movement speed)         importance=0.11930
 3) f6 (pattern: # to maximum energy shield)           importance=0.10225
 4) f28 (pattern: #% to fire resistance)               importance=0.09603
 5) f14 (pattern: #% increased energy shield)          importance=0.08012
 6) Quality (pattern: Quality)                         importance=0.07580
 7) f29 (pattern: #% to lightning resistance)          importance=0.05615
 8) f27 (pattern: #% to cold resistance)               importance=0.05254
 9) f10 (pattern: # to stun threshold)                 importance=0.03682
10) f19 (pattern: #% increased rarity of items found)  importance=0.03124
11) f8 (pattern: # to maximum mana)                    importance=0.02903
12) f24 (pattern: #% reduced shock duration on you)    importance=0.02806
13) f7 (pattern: # to maximum life)                    importance=0.02567
14) f1 (pattern: # life regeneration per second)       importance=0.02092
15) f5 (pattern: # to intelligence)                    importance=0.01981
16) f23 (pattern: #% reduced freeze duration on you)   importance=0.01169
17) f26 (pattern: #% to chaos resistance)              importance=0.01163
18) f21 (pattern: #% reduced attribute requirements)   importance=0.00569
19) f22 (pattern: #% reduced chill duration on you)    importance=0.00396
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00294
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00018
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
