=== gloves seg='ar_ev_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: -0.5351
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
 1) f25 (pattern: #% to lightning resistance)          importance=0.16642
 2) f27 (pattern: adds # to # fire damage to attacks)  importance=0.08317
 3) f21 (pattern: #% reduced attribute requirements)   importance=0.08188
 4) Deflated_Armour (pattern: Deflated_Armour)         importance=0.07387
 5) f19 (pattern: #% increased rarity of items found)  importance=0.06882
 6) f8 (pattern: # to maximum life)                    importance=0.06812
 7) f13 (pattern: #% increased armour and evasion)     importance=0.06121
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.05890
 9) f28 (pattern: adds # to # lightning damage to attacks) importance=0.05693
10) f23 (pattern: #% to cold resistance)               importance=0.05495
11) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.04413
12) f36 (pattern: gain # mana per enemy killed)        importance=0.04321
13) f14 (pattern: #% increased attack speed)           importance=0.04315
14) f3 (pattern: # to dexterity)                       importance=0.03878
15) f34 (pattern: gain # life per enemy hit with attacks) importance=0.03272
16) f15 (pattern: #% increased critical damage bonus)  importance=0.02374
17) f22 (pattern: #% to chaos resistance)              importance=0.00000
18) f24 (pattern: #% to fire resistance)               importance=0.00000
19) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00000
20) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00000
21) f35 (pattern: gain # life per enemy killed)        importance=0.00000
22) f37 (pattern: leech #% of physical attack damage as life) importance=0.00000
23) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
24) f30 (pattern: break #% increased armour)           importance=0.00000
25) f6 (pattern: # to level of all melee skills)       importance=0.00000
26) f9 (pattern: # to maximum mana)                    importance=0.00000
27) f10 (pattern: # to strength)                       importance=0.00000
28) f4 (pattern: # to evasion rating)                  importance=0.00000
29) f1 (pattern: # to accuracy rating)                 importance=0.00000
30) f2 (pattern: # to armour)                          importance=0.00000
31) Quality (pattern: Quality)                         importance=0.00000
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
