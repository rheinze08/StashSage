=== helmet seg='ar_es_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: -0.0141
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
 1) f9 (pattern: # to maximum life)                    importance=0.12039
 2) f26 (pattern: #% to cold resistance)               importance=0.09025
 3) Deflated_Armour (pattern: Deflated_Armour)         importance=0.08363
 4) f2 (pattern: # to accuracy rating)                 importance=0.08170
 5) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.06641
 6) f27 (pattern: #% to fire resistance)               importance=0.05957
 7) f15 (pattern: #% increased armour and energy shield) importance=0.05904
 8) f23 (pattern: #% increased rarity of items found)  importance=0.05867
 9) f28 (pattern: #% to lightning resistance)          importance=0.05843
10) f10 (pattern: # to maximum mana)                   importance=0.05621
11) f25 (pattern: #% to chaos resistance)              importance=0.05331
12) f17 (pattern: #% increased critical hit chance)    importance=0.05163
13) f6 (pattern: # to intelligence)                    importance=0.03423
14) f12 (pattern: # to spirit)                         importance=0.03245
15) f13 (pattern: # to strength)                       importance=0.02727
16) f1 (pattern: # life regeneration per second)       importance=0.02116
17) f24 (pattern: #% reduced attribute requirements)   importance=0.01642
18) f21 (pattern: #% increased light radius)           importance=0.00758
19) f3 (pattern: # to armour)                          importance=0.00755
20) f7 (pattern: # to level of all minion skills)      importance=0.00460
21) f8 (pattern: # to maximum energy shield)           importance=0.00395
22) Quality (pattern: Quality)                         importance=0.00370
23) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00184
24) f11 (pattern: # to maximum power charges)          importance=0.00000
