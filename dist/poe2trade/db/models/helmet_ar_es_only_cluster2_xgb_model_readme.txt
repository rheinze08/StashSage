=== helmet seg='ar_es_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: -0.2095
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f3 (pattern: # to armour)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f8 (pattern: # to maximum energy shield)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f13 (pattern: # to strength)
  f15 (pattern: #% increased armour and energy shield)
  f17 (pattern: #% increased critical hit chance)
  f21 (pattern: #% increased light radius)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f24 (pattern: #% reduced attribute requirements)   importance=0.07971
 2) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.06262
 3) f26 (pattern: #% to cold resistance)               importance=0.05740
 4) Quality (pattern: Quality)                         importance=0.05543
 5) f17 (pattern: #% increased critical hit chance)    importance=0.05360
 6) f23 (pattern: #% increased rarity of items found)  importance=0.05340
 7) f13 (pattern: # to strength)                       importance=0.05310
 8) f25 (pattern: #% to chaos resistance)              importance=0.05064
 9) f15 (pattern: #% increased armour and energy shield) importance=0.04928
10) f27 (pattern: #% to fire resistance)               importance=0.04792
11) f6 (pattern: # to intelligence)                    importance=0.04761
12) f2 (pattern: # to accuracy rating)                 importance=0.04655
13) f9 (pattern: # to maximum life)                    importance=0.04494
14) f10 (pattern: # to maximum mana)                   importance=0.04093
15) f8 (pattern: # to maximum energy shield)           importance=0.03854
16) f7 (pattern: # to level of all minion skills)      importance=0.03499
17) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03420
18) f28 (pattern: #% to lightning resistance)          importance=0.03356
19) f3 (pattern: # to armour)                          importance=0.03145
20) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03080
21) f1 (pattern: # life regeneration per second)       importance=0.02932
22) f21 (pattern: #% increased light radius)           importance=0.02399
23) f12 (pattern: # to spirit)                         importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
