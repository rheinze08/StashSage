=== helmet seg='es_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0987
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
 1) Quality (pattern: Quality)                         importance=0.15563
 2) f9 (pattern: # to maximum life)                    importance=0.13553
 3) f23 (pattern: #% increased rarity of items found)  importance=0.12550
 4) f26 (pattern: #% to cold resistance)               importance=0.11111
 5) f8 (pattern: # to maximum energy shield)           importance=0.10028
 6) f28 (pattern: #% to lightning resistance)          importance=0.08569
 7) f18 (pattern: #% increased energy shield)          importance=0.06993
 8) f1 (pattern: # life regeneration per second)       importance=0.04625
 9) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03577
10) f2 (pattern: # to accuracy rating)                 importance=0.03284
11) f6 (pattern: # to intelligence)                    importance=0.02925
12) f10 (pattern: # to maximum mana)                   importance=0.02344
13) f27 (pattern: #% to fire resistance)               importance=0.02156
14) f17 (pattern: #% increased critical hit chance)    importance=0.01593
15) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00471
16) f21 (pattern: #% increased light radius)           importance=0.00332
17) f25 (pattern: #% to chaos resistance)              importance=0.00183
18) f7 (pattern: # to level of all minion skills)      importance=0.00114
19) f24 (pattern: #% reduced attribute requirements)   importance=0.00029
20) f12 (pattern: # to spirit)                         importance=0.00000
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
