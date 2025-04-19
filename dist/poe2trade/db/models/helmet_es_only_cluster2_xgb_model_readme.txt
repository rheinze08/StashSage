=== helmet seg='es_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0232
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
 1) f26 (pattern: #% to cold resistance)               importance=0.08162
 2) f27 (pattern: #% to fire resistance)               importance=0.07949
 3) f25 (pattern: #% to chaos resistance)              importance=0.07850
 4) f28 (pattern: #% to lightning resistance)          importance=0.07186
 5) f10 (pattern: # to maximum mana)                   importance=0.07113
 6) Quality (pattern: Quality)                         importance=0.06655
 7) f1 (pattern: # life regeneration per second)       importance=0.06453
 8) f2 (pattern: # to accuracy rating)                 importance=0.05933
 9) f23 (pattern: #% increased rarity of items found)  importance=0.05862
10) f7 (pattern: # to level of all minion skills)      importance=0.05433
11) f9 (pattern: # to maximum life)                    importance=0.05343
12) f24 (pattern: #% reduced attribute requirements)   importance=0.05176
13) f18 (pattern: #% increased energy shield)          importance=0.04944
14) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04922
15) f17 (pattern: #% increased critical hit chance)    importance=0.04705
16) f6 (pattern: # to intelligence)                    importance=0.04123
17) f8 (pattern: # to maximum energy shield)           importance=0.02189
18) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
19) f12 (pattern: # to spirit)                         importance=0.00000
20) f11 (pattern: # to maximum power charges)          importance=0.00000
21) f21 (pattern: #% increased light radius)           importance=0.00000
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
