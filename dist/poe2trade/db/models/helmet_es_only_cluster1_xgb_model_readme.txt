=== helmet seg='es_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0954
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
 1) f26 (pattern: #% to cold resistance)               importance=0.08446
 2) Quality (pattern: Quality)                         importance=0.07893
 3) f25 (pattern: #% to chaos resistance)              importance=0.07594
 4) f18 (pattern: #% increased energy shield)          importance=0.06999
 5) f23 (pattern: #% increased rarity of items found)  importance=0.06158
 6) f9 (pattern: # to maximum life)                    importance=0.06095
 7) f2 (pattern: # to accuracy rating)                 importance=0.05567
 8) f24 (pattern: #% reduced attribute requirements)   importance=0.05465
 9) f1 (pattern: # life regeneration per second)       importance=0.05261
10) f8 (pattern: # to maximum energy shield)           importance=0.04910
11) f17 (pattern: #% increased critical hit chance)    importance=0.04770
12) f6 (pattern: # to intelligence)                    importance=0.04712
13) f21 (pattern: #% increased light radius)           importance=0.04681
14) f27 (pattern: #% to fire resistance)               importance=0.04654
15) f10 (pattern: # to maximum mana)                   importance=0.04583
16) f7 (pattern: # to level of all minion skills)      importance=0.04565
17) f28 (pattern: #% to lightning resistance)          importance=0.04535
18) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03113
19) f12 (pattern: # to spirit)                         importance=0.00000
20) f11 (pattern: # to maximum power charges)          importance=0.00000
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
