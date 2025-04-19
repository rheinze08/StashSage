=== helmet seg='ev_es_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0346
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
 1) f2 (pattern: # to accuracy rating)                 importance=0.21410
 2) f27 (pattern: #% to fire resistance)               importance=0.10538
 3) f25 (pattern: #% to chaos resistance)              importance=0.10465
 4) f19 (pattern: #% increased evasion and energy shield) importance=0.09897
 5) f26 (pattern: #% to cold resistance)               importance=0.07196
 6) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.07097
 7) f9 (pattern: # to maximum life)                    importance=0.06942
 8) f28 (pattern: #% to lightning resistance)          importance=0.05347
 9) f23 (pattern: #% increased rarity of items found)  importance=0.04858
10) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03557
11) f6 (pattern: # to intelligence)                    importance=0.03291
12) f8 (pattern: # to maximum energy shield)           importance=0.02078
13) f10 (pattern: # to maximum mana)                   importance=0.02074
14) Quality (pattern: Quality)                         importance=0.02015
15) f4 (pattern: # to dexterity)                       importance=0.00809
16) f5 (pattern: # to evasion rating)                  importance=0.00659
17) f1 (pattern: # life regeneration per second)       importance=0.00613
18) f24 (pattern: #% reduced attribute requirements)   importance=0.00497
19) f17 (pattern: #% increased critical hit chance)    importance=0.00349
20) f7 (pattern: # to level of all minion skills)      importance=0.00268
21) f21 (pattern: #% increased light radius)           importance=0.00038
22) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
23) f11 (pattern: # to maximum power charges)          importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
