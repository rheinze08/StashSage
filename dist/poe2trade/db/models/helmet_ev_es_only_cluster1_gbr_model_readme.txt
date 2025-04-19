=== helmet seg='ev_es_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0362
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
 1) f2 (pattern: # to accuracy rating)                 importance=0.11384
 2) f26 (pattern: #% to cold resistance)               importance=0.09417
 3) f9 (pattern: # to maximum life)                    importance=0.08899
 4) f19 (pattern: #% increased evasion and energy shield) importance=0.08264
 5) f28 (pattern: #% to lightning resistance)          importance=0.07761
 6) f27 (pattern: #% to fire resistance)               importance=0.07475
 7) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.07281
 8) f10 (pattern: # to maximum mana)                   importance=0.06463
 9) f6 (pattern: # to intelligence)                    importance=0.06202
10) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05464
11) Quality (pattern: Quality)                         importance=0.05057
12) f23 (pattern: #% increased rarity of items found)  importance=0.04628
13) f25 (pattern: #% to chaos resistance)              importance=0.02467
14) f4 (pattern: # to dexterity)                       importance=0.02254
15) f1 (pattern: # life regeneration per second)       importance=0.01569
16) f21 (pattern: #% increased light radius)           importance=0.01545
17) f17 (pattern: #% increased critical hit chance)    importance=0.01529
18) f7 (pattern: # to level of all minion skills)      importance=0.00991
19) f24 (pattern: #% reduced attribute requirements)   importance=0.00739
20) f8 (pattern: # to maximum energy shield)           importance=0.00243
21) f5 (pattern: # to evasion rating)                  importance=0.00184
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00183
23) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
