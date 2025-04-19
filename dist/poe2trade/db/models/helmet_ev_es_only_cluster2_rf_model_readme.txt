=== helmet seg='ev_es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: 0.0108
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
 1) f2 (pattern: # to accuracy rating)                 importance=0.19986
 2) f25 (pattern: #% to chaos resistance)              importance=0.11029
 3) f27 (pattern: #% to fire resistance)               importance=0.10189
 4) f19 (pattern: #% increased evasion and energy shield) importance=0.09538
 5) f9 (pattern: # to maximum life)                    importance=0.08235
 6) f23 (pattern: #% increased rarity of items found)  importance=0.06059
 7) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.05746
 8) f26 (pattern: #% to cold resistance)               importance=0.05205
 9) f28 (pattern: #% to lightning resistance)          importance=0.05174
10) f10 (pattern: # to maximum mana)                   importance=0.03833
11) f6 (pattern: # to intelligence)                    importance=0.03554
12) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.02862
13) Quality (pattern: Quality)                         importance=0.02441
14) f8 (pattern: # to maximum energy shield)           importance=0.01712
15) f24 (pattern: #% reduced attribute requirements)   importance=0.01253
16) f17 (pattern: #% increased critical hit chance)    importance=0.00926
17) f4 (pattern: # to dexterity)                       importance=0.00748
18) f5 (pattern: # to evasion rating)                  importance=0.00719
19) f1 (pattern: # life regeneration per second)       importance=0.00410
20) f7 (pattern: # to level of all minion skills)      importance=0.00290
21) f21 (pattern: #% increased light radius)           importance=0.00090
22) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
23) f11 (pattern: # to maximum power charges)          importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
