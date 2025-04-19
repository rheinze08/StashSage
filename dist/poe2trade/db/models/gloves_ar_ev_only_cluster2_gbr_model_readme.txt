=== gloves seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0283
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
 1) f8 (pattern: # to maximum life)                    importance=0.16299
 2) f22 (pattern: #% to chaos resistance)              importance=0.12698
 3) f25 (pattern: #% to lightning resistance)          importance=0.09029
 4) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.08061
 5) Quality (pattern: Quality)                         importance=0.06094
 6) f14 (pattern: #% increased attack speed)           importance=0.05378
 7) f21 (pattern: #% reduced attribute requirements)   importance=0.05151
 8) f3 (pattern: # to dexterity)                       importance=0.05129
 9) f29 (pattern: adds # to # physical damage to attacks) importance=0.04630
10) f24 (pattern: #% to fire resistance)               importance=0.04013
11) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03167
12) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02726
13) f6 (pattern: # to level of all melee skills)       importance=0.02544
14) f37 (pattern: leech #% of physical attack damage as life) importance=0.02211
15) f35 (pattern: gain # life per enemy killed)        importance=0.01691
16) f10 (pattern: # to strength)                       importance=0.01373
17) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01222
18) f23 (pattern: #% to cold resistance)               importance=0.01220
19) f36 (pattern: gain # mana per enemy killed)        importance=0.01093
20) f9 (pattern: # to maximum mana)                    importance=0.00954
21) f1 (pattern: # to accuracy rating)                 importance=0.00815
22) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00814
23) f27 (pattern: adds # to # fire damage to attacks)  importance=0.00791
24) f2 (pattern: # to armour)                          importance=0.00699
25) f19 (pattern: #% increased rarity of items found)  importance=0.00647
26) f15 (pattern: #% increased critical damage bonus)  importance=0.00552
27) f13 (pattern: #% increased armour and evasion)     importance=0.00502
28) f4 (pattern: # to evasion rating)                  importance=0.00496
29) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
30) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00000
31) f30 (pattern: break #% increased armour)           importance=0.00000
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
