=== boots seg='ev_es_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: 0.3179
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to maximum energy shield)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f10 (pattern: # to stun threshold)
  f15 (pattern: #% increased evasion and energy shield)
  f17 (pattern: #% increased freeze threshold)
  f18 (pattern: #% increased movement speed)
  f19 (pattern: #% increased rarity of items found)
  f21 (pattern: #% reduced attribute requirements)
  f22 (pattern: #% reduced chill duration on you)
  f23 (pattern: #% reduced freeze duration on you)
  f24 (pattern: #% reduced shock duration on you)
  f26 (pattern: #% to chaos resistance)
  f27 (pattern: #% to cold resistance)
  f28 (pattern: #% to fire resistance)
  f29 (pattern: #% to lightning resistance)

Feature Importances:
 1) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.21516
 2) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.20352
 3) f27 (pattern: #% to cold resistance)               importance=0.12965
 4) f29 (pattern: #% to lightning resistance)          importance=0.11366
 5) f28 (pattern: #% to fire resistance)               importance=0.09439
 6) f18 (pattern: #% increased movement speed)         importance=0.07898
 7) f7 (pattern: # to maximum life)                    importance=0.04380
 8) f10 (pattern: # to stun threshold)                 importance=0.02977
 9) f8 (pattern: # to maximum mana)                    importance=0.02714
10) f21 (pattern: #% reduced attribute requirements)   importance=0.01937
11) f5 (pattern: # to intelligence)                    importance=0.01216
12) f19 (pattern: #% increased rarity of items found)  importance=0.00696
13) f15 (pattern: #% increased evasion and energy shield) importance=0.00671
14) f3 (pattern: # to dexterity)                       importance=0.00518
15) f23 (pattern: #% reduced freeze duration on you)   importance=0.00431
16) f22 (pattern: #% reduced chill duration on you)    importance=0.00331
17) f1 (pattern: # life regeneration per second)       importance=0.00232
18) Quality (pattern: Quality)                         importance=0.00199
19) f26 (pattern: #% to chaos resistance)              importance=0.00151
20) f24 (pattern: #% reduced shock duration on you)    importance=0.00010
21) f4 (pattern: # to evasion rating)                  importance=0.00000
22) f6 (pattern: # to maximum energy shield)           importance=0.00000
23) f17 (pattern: #% increased freeze threshold)       importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
