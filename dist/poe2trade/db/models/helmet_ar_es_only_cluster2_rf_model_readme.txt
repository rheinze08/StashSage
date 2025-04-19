=== helmet seg='ar_es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.1507
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
 1) f15 (pattern: #% increased armour and energy shield) importance=0.10689
 2) Deflated_Armour (pattern: Deflated_Armour)         importance=0.09019
 3) f26 (pattern: #% to cold resistance)               importance=0.08941
 4) f9 (pattern: # to maximum life)                    importance=0.08765
 5) f23 (pattern: #% increased rarity of items found)  importance=0.08634
 6) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.07068
 7) f27 (pattern: #% to fire resistance)               importance=0.06069
 8) f6 (pattern: # to intelligence)                    importance=0.05597
 9) Quality (pattern: Quality)                         importance=0.05572
10) f25 (pattern: #% to chaos resistance)              importance=0.05110
11) f10 (pattern: # to maximum mana)                   importance=0.05107
12) f2 (pattern: # to accuracy rating)                 importance=0.04604
13) f13 (pattern: # to strength)                       importance=0.04284
14) f28 (pattern: #% to lightning resistance)          importance=0.02747
15) f1 (pattern: # life regeneration per second)       importance=0.02354
16) f24 (pattern: #% reduced attribute requirements)   importance=0.02099
17) f17 (pattern: #% increased critical hit chance)    importance=0.01603
18) f7 (pattern: # to level of all minion skills)      importance=0.01343
19) f8 (pattern: # to maximum energy shield)           importance=0.00182
20) f3 (pattern: # to armour)                          importance=0.00112
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00067
22) f21 (pattern: #% increased light radius)           importance=0.00034
23) f12 (pattern: # to spirit)                         importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
