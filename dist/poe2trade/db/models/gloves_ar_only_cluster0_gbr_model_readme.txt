=== gloves seg='ar_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.2469
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
 1) f8 (pattern: # to maximum life)                    importance=0.21144
 2) f10 (pattern: # to strength)                       importance=0.19572
 3) f25 (pattern: #% to lightning resistance)          importance=0.10265
 4) f27 (pattern: adds # to # fire damage to attacks)  importance=0.07650
 5) f1 (pattern: # to accuracy rating)                 importance=0.06168
 6) f26 (pattern: adds # to # cold damage to attacks)  importance=0.04978
 7) f6 (pattern: # to level of all melee skills)       importance=0.03580
 8) f24 (pattern: #% to fire resistance)               importance=0.03554
 9) f11 (pattern: #% increased armour)                 importance=0.03041
10) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03026
11) Quality (pattern: Quality)                         importance=0.03005
12) f37 (pattern: leech #% of physical attack damage as life) importance=0.02573
13) f14 (pattern: #% increased attack speed)           importance=0.02344
14) f22 (pattern: #% to chaos resistance)              importance=0.02106
15) f19 (pattern: #% increased rarity of items found)  importance=0.01988
16) f23 (pattern: #% to cold resistance)               importance=0.01463
17) f29 (pattern: adds # to # physical damage to attacks) importance=0.01367
18) f21 (pattern: #% reduced attribute requirements)   importance=0.00557
19) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00509
20) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00375
21) f28 (pattern: adds # to # lightning damage to attacks) importance=0.00349
22) f3 (pattern: # to dexterity)                       importance=0.00225
23) f2 (pattern: # to armour)                          importance=0.00070
24) f15 (pattern: #% increased critical damage bonus)  importance=0.00029
25) f36 (pattern: gain # mana per enemy killed)        importance=0.00024
26) f9 (pattern: # to maximum mana)                    importance=0.00023
27) f35 (pattern: gain # life per enemy killed)        importance=0.00014
28) f30 (pattern: break #% increased armour)           importance=0.00000
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
