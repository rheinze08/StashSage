=== helmet seg='ev_es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: 0.0180
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f4 (pattern: # to dexterity)
  f5 (pattern: # to evasion rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f8 (pattern: # to maximum energy shield)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f17 (pattern: #% increased critical hit chance)
  f19 (pattern: #% increased evasion and energy shield)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f27 (pattern: #% to fire resistance)               importance=0.13633
 2) f9 (pattern: # to maximum life)                    importance=0.12027
 3) f28 (pattern: #% to lightning resistance)          importance=0.09070
 4) f26 (pattern: #% to cold resistance)               importance=0.09033
 5) f25 (pattern: #% to chaos resistance)              importance=0.07860
 6) f6 (pattern: # to intelligence)                    importance=0.06712
 7) f8 (pattern: # to maximum energy shield)           importance=0.04948
 8) f23 (pattern: #% increased rarity of items found)  importance=0.04559
 9) f4 (pattern: # to dexterity)                       importance=0.04516
10) f5 (pattern: # to evasion rating)                  importance=0.04120
11) f1 (pattern: # life regeneration per second)       importance=0.03982
12) f19 (pattern: #% increased evasion and energy shield) importance=0.03563
13) f17 (pattern: #% increased critical hit chance)    importance=0.02899
14) Quality (pattern: Quality)                         importance=0.02104
15) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02056
16) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.01964
17) f24 (pattern: #% reduced attribute requirements)   importance=0.01735
18) f2 (pattern: # to accuracy rating)                 importance=0.01709
19) f10 (pattern: # to maximum mana)                   importance=0.01406
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01134
21) f7 (pattern: # to level of all minion skills)      importance=0.00689
22) f21 (pattern: #% increased light radius)           importance=0.00282
23) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
