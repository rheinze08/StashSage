=== gloves seg='ar_ev_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: -0.4159
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f6 (pattern: # to level of all melee skills)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f10 (pattern: # to strength)
  f13 (pattern: #% increased armour and evasion)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f19 (pattern: #% increased rarity of items found)
  f21 (pattern: #% reduced attribute requirements)
  f22 (pattern: #% to chaos resistance)
  f23 (pattern: #% to cold resistance)
  f24 (pattern: #% to fire resistance)
  f25 (pattern: #% to lightning resistance)
  f26 (pattern: adds # to # cold damage to attacks)
  f27 (pattern: adds # to # fire damage to attacks)
  f28 (pattern: adds # to # lightning damage to attacks)
  f29 (pattern: adds # to # physical damage to attacks)
  f30 (pattern: break #% increased armour)
  f31 (pattern: damage penetrates #% cold resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f8 (pattern: # to maximum life)                    importance=0.21363
 2) f23 (pattern: #% to cold resistance)               importance=0.07940
 3) f3 (pattern: # to dexterity)                       importance=0.07261
 4) f26 (pattern: adds # to # cold damage to attacks)  importance=0.06728
 5) f22 (pattern: #% to chaos resistance)              importance=0.05728
 6) f29 (pattern: adds # to # physical damage to attacks) importance=0.05013
 7) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04636
 8) f24 (pattern: #% to fire resistance)               importance=0.04323
 9) f9 (pattern: # to maximum mana)                    importance=0.04016
10) f10 (pattern: # to strength)                       importance=0.04016
11) f25 (pattern: #% to lightning resistance)          importance=0.03631
12) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03415
13) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03224
14) f19 (pattern: #% increased rarity of items found)  importance=0.02534
15) f36 (pattern: gain # mana per enemy killed)        importance=0.02421
16) f15 (pattern: #% increased critical damage bonus)  importance=0.01904
17) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01656
18) f13 (pattern: #% increased armour and evasion)     importance=0.01567
19) f35 (pattern: gain # life per enemy killed)        importance=0.01458
20) f1 (pattern: # to accuracy rating)                 importance=0.01431
21) f4 (pattern: # to evasion rating)                  importance=0.01266
22) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.01200
23) f2 (pattern: # to armour)                          importance=0.01185
24) f14 (pattern: #% increased attack speed)           importance=0.00999
25) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00590
26) f21 (pattern: #% reduced attribute requirements)   importance=0.00237
27) f37 (pattern: leech #% of physical attack damage as life) importance=0.00172
28) Quality (pattern: Quality)                         importance=0.00062
29) f6 (pattern: # to level of all melee skills)       importance=0.00024
30) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00001
31) f30 (pattern: break #% increased armour)           importance=0.00000
32) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
