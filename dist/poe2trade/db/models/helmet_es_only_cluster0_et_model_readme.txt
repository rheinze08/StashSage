=== helmet seg='es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: -0.2403
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
 1) Quality (pattern: Quality)                         importance=0.13062
 2) f23 (pattern: #% increased rarity of items found)  importance=0.10575
 3) f9 (pattern: # to maximum life)                    importance=0.10038
 4) f26 (pattern: #% to cold resistance)               importance=0.09204
 5) f18 (pattern: #% increased energy shield)          importance=0.07155
 6) f8 (pattern: # to maximum energy shield)           importance=0.06369
 7) f27 (pattern: #% to fire resistance)               importance=0.06089
 8) f28 (pattern: #% to lightning resistance)          importance=0.05632
 9) f1 (pattern: # life regeneration per second)       importance=0.04503
10) f17 (pattern: #% increased critical hit chance)    importance=0.04418
11) f10 (pattern: # to maximum mana)                   importance=0.03513
12) f6 (pattern: # to intelligence)                    importance=0.03391
13) f2 (pattern: # to accuracy rating)                 importance=0.03039
14) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02830
15) f25 (pattern: #% to chaos resistance)              importance=0.02698
16) f21 (pattern: #% increased light radius)           importance=0.02543
17) f7 (pattern: # to level of all minion skills)      importance=0.02389
18) f24 (pattern: #% reduced attribute requirements)   importance=0.02371
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00180
20) f12 (pattern: # to spirit)                         importance=0.00000
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
