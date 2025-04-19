=== boots seg='es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: -0.0134
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
 1) f18 (pattern: #% increased movement speed)         importance=0.28053
 2) f27 (pattern: #% to cold resistance)               importance=0.16067
 3) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.07607
 4) f29 (pattern: #% to lightning resistance)          importance=0.07241
 5) f19 (pattern: #% increased rarity of items found)  importance=0.05526
 6) f26 (pattern: #% to chaos resistance)              importance=0.05232
 7) f7 (pattern: # to maximum life)                    importance=0.03986
 8) Quality (pattern: Quality)                         importance=0.03287
 9) f8 (pattern: # to maximum mana)                    importance=0.03171
10) f28 (pattern: #% to fire resistance)               importance=0.03061
11) f5 (pattern: # to intelligence)                    importance=0.02655
12) f6 (pattern: # to maximum energy shield)           importance=0.02421
13) f1 (pattern: # life regeneration per second)       importance=0.02247
14) f14 (pattern: #% increased energy shield)          importance=0.02054
15) f23 (pattern: #% reduced freeze duration on you)   importance=0.01649
16) f10 (pattern: # to stun threshold)                 importance=0.01547
17) f21 (pattern: #% reduced attribute requirements)   importance=0.01360
18) f22 (pattern: #% reduced chill duration on you)    importance=0.01323
19) f24 (pattern: #% reduced shock duration on you)    importance=0.00997
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00516
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
