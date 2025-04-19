=== boots seg='ev_es_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.0194
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
 1) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.20404
 2) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.20029
 3) f29 (pattern: #% to lightning resistance)          importance=0.15311
 4) f27 (pattern: #% to cold resistance)               importance=0.12541
 5) f28 (pattern: #% to fire resistance)               importance=0.06539
 6) f7 (pattern: # to maximum life)                    importance=0.05748
 7) f10 (pattern: # to stun threshold)                 importance=0.04937
 8) f3 (pattern: # to dexterity)                       importance=0.04385
 9) f21 (pattern: #% reduced attribute requirements)   importance=0.02787
10) f8 (pattern: # to maximum mana)                    importance=0.02338
11) f15 (pattern: #% increased evasion and energy shield) importance=0.02334
12) f18 (pattern: #% increased movement speed)         importance=0.01598
13) f23 (pattern: #% reduced freeze duration on you)   importance=0.00770
14) f24 (pattern: #% reduced shock duration on you)    importance=0.00172
15) f19 (pattern: #% increased rarity of items found)  importance=0.00039
16) f1 (pattern: # life regeneration per second)       importance=0.00034
17) f22 (pattern: #% reduced chill duration on you)    importance=0.00031
18) f6 (pattern: # to maximum energy shield)           importance=0.00002
19) f4 (pattern: # to evasion rating)                  importance=0.00001
20) f26 (pattern: #% to chaos resistance)              importance=0.00000
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) f5 (pattern: # to intelligence)                    importance=0.00000
23) Quality (pattern: Quality)                         importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
