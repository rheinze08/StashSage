=== helmet seg='es_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.0945
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f8 (pattern: # to maximum energy shield)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f17 (pattern: #% increased critical hit chance)
  f18 (pattern: #% increased energy shield)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f18 (pattern: #% increased energy shield)          importance=0.13516
 2) f25 (pattern: #% to chaos resistance)              importance=0.10733
 3) f26 (pattern: #% to cold resistance)               importance=0.10150
 4) f9 (pattern: # to maximum life)                    importance=0.09670
 5) f23 (pattern: #% increased rarity of items found)  importance=0.08633
 6) f6 (pattern: # to intelligence)                    importance=0.05722
 7) Quality (pattern: Quality)                         importance=0.05488
 8) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.05396
 9) f8 (pattern: # to maximum energy shield)           importance=0.05078
10) f10 (pattern: # to maximum mana)                   importance=0.04782
11) f28 (pattern: #% to lightning resistance)          importance=0.04248
12) f2 (pattern: # to accuracy rating)                 importance=0.04119
13) f27 (pattern: #% to fire resistance)               importance=0.03583
14) f1 (pattern: # life regeneration per second)       importance=0.02938
15) f7 (pattern: # to level of all minion skills)      importance=0.01795
16) f17 (pattern: #% increased critical hit chance)    importance=0.01412
17) f21 (pattern: #% increased light radius)           importance=0.00953
18) f24 (pattern: #% reduced attribute requirements)   importance=0.00924
19) f22 (pattern: #% increased mana regeneration rate) importance=0.00627
20) f12 (pattern: # to spirit)                         importance=0.00158
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00074
22) f11 (pattern: # to maximum power charges)          importance=0.00000
