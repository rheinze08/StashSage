=== gloves seg='ar_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: 0.0062
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f6 (pattern: # to level of all melee skills)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f10 (pattern: # to strength)
  f11 (pattern: #% increased armour)
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
  f32 (pattern: damage penetrates #% fire resistance)
  f33 (pattern: damage penetrates #% lightning resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f10 (pattern: # to strength)                       importance=0.17450
 2) f8 (pattern: # to maximum life)                    importance=0.14178
 3) f24 (pattern: #% to fire resistance)               importance=0.09775
 4) f6 (pattern: # to level of all melee skills)       importance=0.08840
 5) f28 (pattern: adds # to # lightning damage to attacks) importance=0.07943
 6) f27 (pattern: adds # to # fire damage to attacks)  importance=0.07083
 7) Quality (pattern: Quality)                         importance=0.04510
 8) f26 (pattern: adds # to # cold damage to attacks)  importance=0.04490
 9) f25 (pattern: #% to lightning resistance)          importance=0.04370
10) f22 (pattern: #% to chaos resistance)              importance=0.03654
11) f19 (pattern: #% increased rarity of items found)  importance=0.03382
12) f14 (pattern: #% increased attack speed)           importance=0.02920
13) f37 (pattern: leech #% of physical attack damage as life) importance=0.02539
14) f29 (pattern: adds # to # physical damage to attacks) importance=0.01756
15) f1 (pattern: # to accuracy rating)                 importance=0.01004
16) f15 (pattern: #% increased critical damage bonus)  importance=0.00987
17) f3 (pattern: # to dexterity)                       importance=0.00909
18) f9 (pattern: # to maximum mana)                    importance=0.00831
19) f21 (pattern: #% reduced attribute requirements)   importance=0.00619
20) f23 (pattern: #% to cold resistance)               importance=0.00618
21) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00518
22) f35 (pattern: gain # life per enemy killed)        importance=0.00488
23) Deflated_Armour (pattern: Deflated_Armour)         importance=0.00396
24) f11 (pattern: #% increased armour)                 importance=0.00339
25) f36 (pattern: gain # mana per enemy killed)        importance=0.00231
26) f2 (pattern: # to armour)                          importance=0.00130
27) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00039
28) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
