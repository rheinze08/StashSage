=== gloves seg='ev_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: 0.0951
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f6 (pattern: # to level of all melee skills)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f18 (pattern: #% increased evasion rating)
  f19 (pattern: #% increased rarity of items found)
  f20 (pattern: #% increased weapon swap speed)
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
 1) f18 (pattern: #% increased evasion rating)         importance=0.11234
 2) Quality (pattern: Quality)                         importance=0.09195
 3) f29 (pattern: adds # to # physical damage to attacks) importance=0.09180
 4) f4 (pattern: # to evasion rating)                  importance=0.07975
 5) f25 (pattern: #% to lightning resistance)          importance=0.07051
 6) f21 (pattern: #% reduced attribute requirements)   importance=0.06901
 7) f8 (pattern: # to maximum life)                    importance=0.06654
 8) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05450
 9) f1 (pattern: # to accuracy rating)                 importance=0.05359
10) f15 (pattern: #% increased critical damage bonus)  importance=0.05228
11) f24 (pattern: #% to fire resistance)               importance=0.03733
12) f3 (pattern: # to dexterity)                       importance=0.03226
13) f37 (pattern: leech #% of physical attack damage as life) importance=0.03202
14) f35 (pattern: gain # life per enemy killed)        importance=0.02974
15) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02677
16) f23 (pattern: #% to cold resistance)               importance=0.02374
17) f26 (pattern: adds # to # cold damage to attacks)  importance=0.01951
18) f9 (pattern: # to maximum mana)                    importance=0.01371
19) f22 (pattern: #% to chaos resistance)              importance=0.01041
20) f19 (pattern: #% increased rarity of items found)  importance=0.01023
21) f27 (pattern: adds # to # fire damage to attacks)  importance=0.00792
22) f14 (pattern: #% increased attack speed)           importance=0.00285
23) f36 (pattern: gain # mana per enemy killed)        importance=0.00274
24) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00263
25) f6 (pattern: # to level of all melee skills)       importance=0.00237
26) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00207
27) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00144
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
