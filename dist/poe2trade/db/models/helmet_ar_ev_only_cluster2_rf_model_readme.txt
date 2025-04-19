=== helmet seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.1428
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
 1) f27 (pattern: #% to fire resistance)               importance=0.14729
 2) f16 (pattern: #% increased armour and evasion)     importance=0.11222
 3) f17 (pattern: #% increased critical hit chance)    importance=0.10983
 4) f5 (pattern: # to evasion rating)                  importance=0.07384
 5) f3 (pattern: # to armour)                          importance=0.06923
 6) Deflated_Armour (pattern: Deflated_Armour)         importance=0.06409
 7) f23 (pattern: #% increased rarity of items found)  importance=0.06177
 8) f26 (pattern: #% to cold resistance)               importance=0.05553
 9) f9 (pattern: # to maximum life)                    importance=0.05453
10) f10 (pattern: # to maximum mana)                   importance=0.04165
11) f2 (pattern: # to accuracy rating)                 importance=0.03852
12) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03601
13) f28 (pattern: #% to lightning resistance)          importance=0.03428
14) f6 (pattern: # to intelligence)                    importance=0.03378
15) f13 (pattern: # to strength)                       importance=0.02403
16) f4 (pattern: # to dexterity)                       importance=0.01149
17) f21 (pattern: #% increased light radius)           importance=0.01038
18) Quality (pattern: Quality)                         importance=0.00656
19) f25 (pattern: #% to chaos resistance)              importance=0.00385
20) f1 (pattern: # life regeneration per second)       importance=0.00341
21) f24 (pattern: #% reduced attribute requirements)   importance=0.00311
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00235
23) f7 (pattern: # to level of all minion skills)      importance=0.00224
24) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
25) f12 (pattern: # to spirit)                         importance=0.00000
26) f11 (pattern: # to maximum power charges)          importance=0.00000
