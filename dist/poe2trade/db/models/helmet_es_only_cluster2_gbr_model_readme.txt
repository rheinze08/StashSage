=== helmet seg='es_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0377
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
 1) f28 (pattern: #% to lightning resistance)          importance=0.14538
 2) f26 (pattern: #% to cold resistance)               importance=0.13178
 3) f25 (pattern: #% to chaos resistance)              importance=0.11412
 4) f10 (pattern: # to maximum mana)                   importance=0.11210
 5) f18 (pattern: #% increased energy shield)          importance=0.10260
 6) f27 (pattern: #% to fire resistance)               importance=0.09591
 7) f9 (pattern: # to maximum life)                    importance=0.07368
 8) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.06579
 9) f23 (pattern: #% increased rarity of items found)  importance=0.04273
10) f1 (pattern: # life regeneration per second)       importance=0.02894
11) f2 (pattern: # to accuracy rating)                 importance=0.02749
12) f7 (pattern: # to level of all minion skills)      importance=0.01726
13) f6 (pattern: # to intelligence)                    importance=0.01403
14) Quality (pattern: Quality)                         importance=0.01233
15) f24 (pattern: #% reduced attribute requirements)   importance=0.00705
16) f8 (pattern: # to maximum energy shield)           importance=0.00674
17) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00203
18) f17 (pattern: #% increased critical hit chance)    importance=0.00003
19) f12 (pattern: # to spirit)                         importance=0.00000
20) f11 (pattern: # to maximum power charges)          importance=0.00000
21) f21 (pattern: #% increased light radius)           importance=0.00000
22) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
