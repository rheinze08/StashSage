=== gloves seg='ar_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0328
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
 1) f29 (pattern: adds # to # physical damage to attacks) importance=0.05205
 2) f28 (pattern: adds # to # lightning damage to attacks) importance=0.05156
 3) f26 (pattern: adds # to # cold damage to attacks)  importance=0.05136
 4) f25 (pattern: #% to lightning resistance)          importance=0.04991
 5) f15 (pattern: #% increased critical damage bonus)  importance=0.04839
 6) f22 (pattern: #% to chaos resistance)              importance=0.04494
 7) f6 (pattern: # to level of all melee skills)       importance=0.04419
 8) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04380
 9) f8 (pattern: # to maximum life)                    importance=0.04286
10) f3 (pattern: # to dexterity)                       importance=0.04272
11) f11 (pattern: #% increased armour)                 importance=0.04250
12) f19 (pattern: #% increased rarity of items found)  importance=0.04239
13) f23 (pattern: #% to cold resistance)               importance=0.04204
14) f9 (pattern: # to maximum mana)                    importance=0.04192
15) f24 (pattern: #% to fire resistance)               importance=0.04088
16) f37 (pattern: leech #% of physical attack damage as life) importance=0.04050
17) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03958
18) f1 (pattern: # to accuracy rating)                 importance=0.03947
19) Quality (pattern: Quality)                         importance=0.03829
20) f38 (pattern: leech #% of physical attack damage as mana) importance=0.03580
21) f35 (pattern: gain # life per enemy killed)        importance=0.03299
22) f36 (pattern: gain # mana per enemy killed)        importance=0.03251
23) f14 (pattern: #% increased attack speed)           importance=0.02655
24) f2 (pattern: # to armour)                          importance=0.01660
25) f10 (pattern: # to strength)                       importance=0.01620
26) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
27) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
28) f30 (pattern: break #% increased armour)           importance=0.00000
29) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
30) f21 (pattern: #% reduced attribute requirements)   importance=0.00000
31) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
