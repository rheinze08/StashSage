=== helmet seg='ev_es_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0080
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
 1) f9 (pattern: # to maximum life)                    importance=0.16684
 2) f28 (pattern: #% to lightning resistance)          importance=0.11656
 3) f26 (pattern: #% to cold resistance)               importance=0.10944
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.10100
 5) f27 (pattern: #% to fire resistance)               importance=0.09237
 6) f5 (pattern: # to evasion rating)                  importance=0.07721
 7) f23 (pattern: #% increased rarity of items found)  importance=0.05051
 8) f6 (pattern: # to intelligence)                    importance=0.04965
 9) f25 (pattern: #% to chaos resistance)              importance=0.04185
10) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03555
11) f19 (pattern: #% increased evasion and energy shield) importance=0.03215
12) f17 (pattern: #% increased critical hit chance)    importance=0.02847
13) f8 (pattern: # to maximum energy shield)           importance=0.02377
14) f2 (pattern: # to accuracy rating)                 importance=0.02095
15) f4 (pattern: # to dexterity)                       importance=0.02044
16) f10 (pattern: # to maximum mana)                   importance=0.01526
17) f24 (pattern: #% reduced attribute requirements)   importance=0.00668
18) f1 (pattern: # life regeneration per second)       importance=0.00591
19) Quality (pattern: Quality)                         importance=0.00539
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00001
21) f21 (pattern: #% increased light radius)           importance=0.00000
22) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
23) f7 (pattern: # to level of all minion skills)      importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
