=== boots seg='es_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0969
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
 1) f18 (pattern: #% increased movement speed)         importance=0.09601
 2) Quality (pattern: Quality)                         importance=0.07379
 3) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.06723
 4) f29 (pattern: #% to lightning resistance)          importance=0.06502
 5) f27 (pattern: #% to cold resistance)               importance=0.05594
 6) f5 (pattern: # to intelligence)                    importance=0.05492
 7) f7 (pattern: # to maximum life)                    importance=0.05486
 8) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.05346
 9) f14 (pattern: #% increased energy shield)          importance=0.05300
10) f6 (pattern: # to maximum energy shield)           importance=0.05097
11) f26 (pattern: #% to chaos resistance)              importance=0.04620
12) f8 (pattern: # to maximum mana)                    importance=0.04556
13) f23 (pattern: #% reduced freeze duration on you)   importance=0.04387
14) f28 (pattern: #% to fire resistance)               importance=0.04287
15) f1 (pattern: # life regeneration per second)       importance=0.04188
16) f10 (pattern: # to stun threshold)                 importance=0.03783
17) f24 (pattern: #% reduced shock duration on you)    importance=0.03577
18) f21 (pattern: #% reduced attribute requirements)   importance=0.03459
19) f19 (pattern: #% increased rarity of items found)  importance=0.03243
20) f22 (pattern: #% reduced chill duration on you)    importance=0.01381
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
