=== helmet seg='ar_es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: 0.0009
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
 1) f2 (pattern: # to accuracy rating)                 importance=0.13657
 2) f12 (pattern: # to spirit)                         importance=0.13474
 3) f9 (pattern: # to maximum life)                    importance=0.11025
 4) f17 (pattern: #% increased critical hit chance)    importance=0.09623
 5) f26 (pattern: #% to cold resistance)               importance=0.09482
 6) f15 (pattern: #% increased armour and energy shield) importance=0.05090
 7) f13 (pattern: # to strength)                       importance=0.04648
 8) f27 (pattern: #% to fire resistance)               importance=0.04086
 9) f10 (pattern: # to maximum mana)                   importance=0.03784
10) f6 (pattern: # to intelligence)                    importance=0.03748
11) f25 (pattern: #% to chaos resistance)              importance=0.03640
12) f1 (pattern: # life regeneration per second)       importance=0.03503
13) f23 (pattern: #% increased rarity of items found)  importance=0.03394
14) f24 (pattern: #% reduced attribute requirements)   importance=0.02100
15) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01984
16) f7 (pattern: # to level of all minion skills)      importance=0.01927
17) f28 (pattern: #% to lightning resistance)          importance=0.01911
18) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01667
19) Quality (pattern: Quality)                         importance=0.00907
20) f21 (pattern: #% increased light radius)           importance=0.00261
21) f3 (pattern: # to armour)                          importance=0.00037
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00029
23) f8 (pattern: # to maximum energy shield)           importance=0.00022
24) f11 (pattern: # to maximum power charges)          importance=0.00000
