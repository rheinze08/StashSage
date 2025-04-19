=== boots seg='ev_es_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.0237
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
 1) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.39591
 2) f29 (pattern: #% to lightning resistance)          importance=0.17260
 3) f28 (pattern: #% to fire resistance)               importance=0.15085
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.11898
 5) f27 (pattern: #% to cold resistance)               importance=0.08724
 6) f10 (pattern: # to stun threshold)                 importance=0.02833
 7) f21 (pattern: #% reduced attribute requirements)   importance=0.02292
 8) f8 (pattern: # to maximum mana)                    importance=0.00716
 9) f15 (pattern: #% increased evasion and energy shield) importance=0.00353
10) f24 (pattern: #% reduced shock duration on you)    importance=0.00331
11) f18 (pattern: #% increased movement speed)         importance=0.00324
12) f7 (pattern: # to maximum life)                    importance=0.00283
13) f3 (pattern: # to dexterity)                       importance=0.00091
14) f22 (pattern: #% reduced chill duration on you)    importance=0.00091
15) f19 (pattern: #% increased rarity of items found)  importance=0.00087
16) f23 (pattern: #% reduced freeze duration on you)   importance=0.00038
17) f1 (pattern: # life regeneration per second)       importance=0.00003
18) f6 (pattern: # to maximum energy shield)           importance=0.00001
19) f4 (pattern: # to evasion rating)                  importance=0.00001
20) f26 (pattern: #% to chaos resistance)              importance=0.00000
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) f5 (pattern: # to intelligence)                    importance=0.00000
23) Quality (pattern: Quality)                         importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
