=== boots seg='es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: 0.0367
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
 1) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.22467
 2) f18 (pattern: #% increased movement speed)         importance=0.19236
 3) f6 (pattern: # to maximum energy shield)           importance=0.07405
 4) f29 (pattern: #% to lightning resistance)          importance=0.07392
 5) f7 (pattern: # to maximum life)                    importance=0.06719
 6) f27 (pattern: #% to cold resistance)               importance=0.06334
 7) Quality (pattern: Quality)                         importance=0.05722
 8) f5 (pattern: # to intelligence)                    importance=0.04751
 9) f1 (pattern: # life regeneration per second)       importance=0.03969
10) f8 (pattern: # to maximum mana)                    importance=0.03214
11) f23 (pattern: #% reduced freeze duration on you)   importance=0.02711
12) f28 (pattern: #% to fire resistance)               importance=0.02499
13) f14 (pattern: #% increased energy shield)          importance=0.01822
14) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01599
15) f26 (pattern: #% to chaos resistance)              importance=0.01186
16) f19 (pattern: #% increased rarity of items found)  importance=0.01054
17) f10 (pattern: # to stun threshold)                 importance=0.01010
18) f24 (pattern: #% reduced shock duration on you)    importance=0.00664
19) f21 (pattern: #% reduced attribute requirements)   importance=0.00169
20) f22 (pattern: #% reduced chill duration on you)    importance=0.00074
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
