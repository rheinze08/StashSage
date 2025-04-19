=== helmet seg='ar_es_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: -0.7474
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
 1) f23 (pattern: #% increased rarity of items found)  importance=0.08572
 2) f26 (pattern: #% to cold resistance)               importance=0.07790
 3) Deflated_Armour (pattern: Deflated_Armour)         importance=0.07635
 4) f9 (pattern: # to maximum life)                    importance=0.07571
 5) f15 (pattern: #% increased armour and energy shield) importance=0.07411
 6) f2 (pattern: # to accuracy rating)                 importance=0.06004
 7) f6 (pattern: # to intelligence)                    importance=0.05855
 8) f27 (pattern: #% to fire resistance)               importance=0.05339
 9) f13 (pattern: # to strength)                       importance=0.05104
10) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04841
11) f10 (pattern: # to maximum mana)                   importance=0.04562
12) f28 (pattern: #% to lightning resistance)          importance=0.04550
13) f24 (pattern: #% reduced attribute requirements)   importance=0.04216
14) f25 (pattern: #% to chaos resistance)              importance=0.04177
15) Quality (pattern: Quality)                         importance=0.03888
16) f17 (pattern: #% increased critical hit chance)    importance=0.03811
17) f1 (pattern: # life regeneration per second)       importance=0.02575
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.02247
19) f7 (pattern: # to level of all minion skills)      importance=0.02143
20) f3 (pattern: # to armour)                          importance=0.00691
21) f8 (pattern: # to maximum energy shield)           importance=0.00629
22) f21 (pattern: #% increased light radius)           importance=0.00391
23) f12 (pattern: # to spirit)                         importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
