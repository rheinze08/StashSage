=== helmet seg='ar_es_only' cluster=0 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0361
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
 1) f9 (pattern: # to maximum life)                    importance=0.06215
 2) f26 (pattern: #% to cold resistance)               importance=0.06121
 3) f23 (pattern: #% increased rarity of items found)  importance=0.06070
 4) f17 (pattern: #% increased critical hit chance)    importance=0.06037
 5) f21 (pattern: #% increased light radius)           importance=0.05864
 6) f2 (pattern: # to accuracy rating)                 importance=0.05791
 7) f13 (pattern: # to strength)                       importance=0.05503
 8) f12 (pattern: # to spirit)                         importance=0.05376
 9) f27 (pattern: #% to fire resistance)               importance=0.05227
10) f15 (pattern: #% increased armour and energy shield) importance=0.04989
11) f28 (pattern: #% to lightning resistance)          importance=0.04984
12) f25 (pattern: #% to chaos resistance)              importance=0.04919
13) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04795
14) Deflated_Armour (pattern: Deflated_Armour)         importance=0.04568
15) f10 (pattern: # to maximum mana)                   importance=0.04432
16) f24 (pattern: #% reduced attribute requirements)   importance=0.03942
17) f6 (pattern: # to intelligence)                    importance=0.03682
18) f7 (pattern: # to level of all minion skills)      importance=0.02924
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.02577
20) f8 (pattern: # to maximum energy shield)           importance=0.01876
21) f1 (pattern: # life regeneration per second)       importance=0.01436
22) f3 (pattern: # to armour)                          importance=0.01417
23) Quality (pattern: Quality)                         importance=0.01254
24) f11 (pattern: # to maximum power charges)          importance=0.00000
