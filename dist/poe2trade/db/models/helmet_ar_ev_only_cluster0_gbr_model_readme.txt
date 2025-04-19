=== helmet seg='ar_ev_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0186
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f3 (pattern: # to armour)
  f4 (pattern: # to dexterity)
  f5 (pattern: # to evasion rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f13 (pattern: # to strength)
  f16 (pattern: #% increased armour and evasion)
  f17 (pattern: #% increased critical hit chance)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f9 (pattern: # to maximum life)                    importance=0.14879
 2) f2 (pattern: # to accuracy rating)                 importance=0.10534
 3) f10 (pattern: # to maximum mana)                   importance=0.08000
 4) f27 (pattern: #% to fire resistance)               importance=0.07332
 5) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.06993
 6) Deflated_Armour (pattern: Deflated_Armour)         importance=0.05805
 7) f23 (pattern: #% increased rarity of items found)  importance=0.05264
 8) f28 (pattern: #% to lightning resistance)          importance=0.04959
 9) f16 (pattern: #% increased armour and evasion)     importance=0.04790
10) f26 (pattern: #% to cold resistance)               importance=0.04615
11) f17 (pattern: #% increased critical hit chance)    importance=0.04206
12) f6 (pattern: # to intelligence)                    importance=0.04092
13) f25 (pattern: #% to chaos resistance)              importance=0.03939
14) Quality (pattern: Quality)                         importance=0.03613
15) f4 (pattern: # to dexterity)                       importance=0.03294
16) f1 (pattern: # life regeneration per second)       importance=0.02904
17) f13 (pattern: # to strength)                       importance=0.01911
18) f5 (pattern: # to evasion rating)                  importance=0.01627
19) f21 (pattern: #% increased light radius)           importance=0.00587
20) f24 (pattern: #% reduced attribute requirements)   importance=0.00306
21) f3 (pattern: # to armour)                          importance=0.00264
22) f7 (pattern: # to level of all minion skills)      importance=0.00087
23) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
24) f11 (pattern: # to maximum power charges)          importance=0.00000
25) f12 (pattern: # to spirit)                         importance=0.00000
26) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
