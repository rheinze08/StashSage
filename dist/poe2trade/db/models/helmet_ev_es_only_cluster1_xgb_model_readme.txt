=== helmet seg='ev_es_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0044
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f4 (pattern: # to dexterity)
  f5 (pattern: # to evasion rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f8 (pattern: # to maximum energy shield)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f17 (pattern: #% increased critical hit chance)
  f19 (pattern: #% increased evasion and energy shield)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) Quality (pattern: Quality)                         importance=0.08430
 2) f26 (pattern: #% to cold resistance)               importance=0.07406
 3) f2 (pattern: # to accuracy rating)                 importance=0.06642
 4) f27 (pattern: #% to fire resistance)               importance=0.05998
 5) f28 (pattern: #% to lightning resistance)          importance=0.05801
 6) f9 (pattern: # to maximum life)                    importance=0.05606
 7) f25 (pattern: #% to chaos resistance)              importance=0.05320
 8) f19 (pattern: #% increased evasion and energy shield) importance=0.05267
 9) f23 (pattern: #% increased rarity of items found)  importance=0.05059
10) f7 (pattern: # to level of all minion skills)      importance=0.04878
11) f10 (pattern: # to maximum mana)                   importance=0.04849
12) f21 (pattern: #% increased light radius)           importance=0.04822
13) f6 (pattern: # to intelligence)                    importance=0.04540
14) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.04407
15) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04369
16) f1 (pattern: # life regeneration per second)       importance=0.03996
17) f4 (pattern: # to dexterity)                       importance=0.03721
18) f17 (pattern: #% increased critical hit chance)    importance=0.03612
19) f5 (pattern: # to evasion rating)                  importance=0.02751
20) f24 (pattern: #% reduced attribute requirements)   importance=0.02527
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
23) f8 (pattern: # to maximum energy shield)           importance=0.00000
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
