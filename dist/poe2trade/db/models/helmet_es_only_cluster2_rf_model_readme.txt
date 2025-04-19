=== helmet seg='es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.1572
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
 1) f28 (pattern: #% to lightning resistance)          importance=0.14580
 2) f26 (pattern: #% to cold resistance)               importance=0.12499
 3) f10 (pattern: # to maximum mana)                   importance=0.10280
 4) f25 (pattern: #% to chaos resistance)              importance=0.10167
 5) f27 (pattern: #% to fire resistance)               importance=0.08994
 6) f18 (pattern: #% increased energy shield)          importance=0.08624
 7) f9 (pattern: # to maximum life)                    importance=0.08427
 8) f23 (pattern: #% increased rarity of items found)  importance=0.06060
 9) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.05659
10) f2 (pattern: # to accuracy rating)                 importance=0.03820
11) f7 (pattern: # to level of all minion skills)      importance=0.02934
12) f6 (pattern: # to intelligence)                    importance=0.02229
13) f24 (pattern: #% reduced attribute requirements)   importance=0.01319
14) f8 (pattern: # to maximum energy shield)           importance=0.01241
15) Quality (pattern: Quality)                         importance=0.01241
16) f17 (pattern: #% increased critical hit chance)    importance=0.01160
17) f1 (pattern: # life regeneration per second)       importance=0.00489
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00222
19) f21 (pattern: #% increased light radius)           importance=0.00054
20) f12 (pattern: # to spirit)                         importance=0.00000
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
