=== helmet seg='es_only' cluster=0 Model Readme ===

Model Type: XGB
R^2 on test set: -0.2075
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
 1) Quality (pattern: Quality)                         importance=0.12656
 2) f9 (pattern: # to maximum life)                    importance=0.08334
 3) f26 (pattern: #% to cold resistance)               importance=0.07467
 4) f28 (pattern: #% to lightning resistance)          importance=0.06939
 5) f23 (pattern: #% increased rarity of items found)  importance=0.06725
 6) f27 (pattern: #% to fire resistance)               importance=0.06191
 7) f8 (pattern: # to maximum energy shield)           importance=0.06042
 8) f10 (pattern: # to maximum mana)                   importance=0.05317
 9) f18 (pattern: #% increased energy shield)          importance=0.05302
10) f1 (pattern: # life regeneration per second)       importance=0.05298
11) f24 (pattern: #% reduced attribute requirements)   importance=0.04855
12) f17 (pattern: #% increased critical hit chance)    importance=0.04391
13) f6 (pattern: # to intelligence)                    importance=0.04132
14) f7 (pattern: # to level of all minion skills)      importance=0.03925
15) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03423
16) f2 (pattern: # to accuracy rating)                 importance=0.03299
17) f25 (pattern: #% to chaos resistance)              importance=0.02479
18) f21 (pattern: #% increased light radius)           importance=0.02229
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00995
20) f12 (pattern: # to spirit)                         importance=0.00000
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
