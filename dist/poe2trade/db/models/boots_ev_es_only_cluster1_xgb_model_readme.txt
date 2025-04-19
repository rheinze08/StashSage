=== boots seg='ev_es_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0898
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
 1) f7 (pattern: # to maximum life)                    importance=0.11658
 2) f8 (pattern: # to maximum mana)                    importance=0.09929
 3) f29 (pattern: #% to lightning resistance)          importance=0.09759
 4) f27 (pattern: #% to cold resistance)               importance=0.07879
 5) f18 (pattern: #% increased movement speed)         importance=0.07871
 6) f1 (pattern: # life regeneration per second)       importance=0.07503
 7) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.07150
 8) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.06836
 9) f28 (pattern: #% to fire resistance)               importance=0.06604
10) f5 (pattern: # to intelligence)                    importance=0.06596
11) f15 (pattern: #% increased evasion and energy shield) importance=0.06066
12) f3 (pattern: # to dexterity)                       importance=0.05384
13) f10 (pattern: # to stun threshold)                 importance=0.04676
14) f23 (pattern: #% reduced freeze duration on you)   importance=0.01231
15) f21 (pattern: #% reduced attribute requirements)   importance=0.00658
16) f22 (pattern: #% reduced chill duration on you)    importance=0.00091
17) f19 (pattern: #% increased rarity of items found)  importance=0.00075
18) f24 (pattern: #% reduced shock duration on you)    importance=0.00034
19) f4 (pattern: # to evasion rating)                  importance=0.00000
20) f6 (pattern: # to maximum energy shield)           importance=0.00000
21) f26 (pattern: #% to chaos resistance)              importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
23) Quality (pattern: Quality)                         importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
