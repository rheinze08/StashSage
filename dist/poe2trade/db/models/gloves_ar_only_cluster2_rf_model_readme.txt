=== gloves seg='ar_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: 0.0011
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
 1) f10 (pattern: # to strength)                       importance=0.15912
 2) f19 (pattern: #% increased rarity of items found)  importance=0.13643
 3) f11 (pattern: #% increased armour)                 importance=0.09787
 4) f8 (pattern: # to maximum life)                    importance=0.08410
 5) f25 (pattern: #% to lightning resistance)          importance=0.07835
 6) Deflated_Armour (pattern: Deflated_Armour)         importance=0.07807
 7) f2 (pattern: # to armour)                          importance=0.07322
 8) f9 (pattern: # to maximum mana)                    importance=0.04159
 9) f15 (pattern: #% increased critical damage bonus)  importance=0.03498
10) f37 (pattern: leech #% of physical attack damage as life) importance=0.02988
11) f23 (pattern: #% to cold resistance)               importance=0.02923
12) f24 (pattern: #% to fire resistance)               importance=0.02101
13) f35 (pattern: gain # life per enemy killed)        importance=0.02047
14) f6 (pattern: # to level of all melee skills)       importance=0.01889
15) f22 (pattern: #% to chaos resistance)              importance=0.01721
16) f29 (pattern: adds # to # physical damage to attacks) importance=0.01373
17) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01015
18) f28 (pattern: adds # to # lightning damage to attacks) importance=0.00962
19) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00927
20) f36 (pattern: gain # mana per enemy killed)        importance=0.00706
21) f14 (pattern: #% increased attack speed)           importance=0.00609
22) Quality (pattern: Quality)                         importance=0.00590
23) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00585
24) f1 (pattern: # to accuracy rating)                 importance=0.00416
25) f3 (pattern: # to dexterity)                       importance=0.00396
26) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00187
27) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00125
28) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00063
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f30 (pattern: break #% increased armour)           importance=0.00000
31) f21 (pattern: #% reduced attribute requirements)   importance=0.00000
