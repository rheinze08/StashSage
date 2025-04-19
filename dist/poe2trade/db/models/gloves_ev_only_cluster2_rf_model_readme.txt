=== gloves seg='ev_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.0051
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.15563
 2) f23 (pattern: #% to cold resistance)               importance=0.11281
 3) f8 (pattern: # to maximum life)                    importance=0.08638
 4) f28 (pattern: adds # to # lightning damage to attacks) importance=0.08392
 5) f27 (pattern: adds # to # fire damage to attacks)  importance=0.06004
 6) f24 (pattern: #% to fire resistance)               importance=0.05678
 7) f29 (pattern: adds # to # physical damage to attacks) importance=0.05247
 8) f35 (pattern: gain # life per enemy killed)        importance=0.04803
 9) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.04774
10) f14 (pattern: #% increased attack speed)           importance=0.03550
11) f25 (pattern: #% to lightning resistance)          importance=0.03432
12) f3 (pattern: # to dexterity)                       importance=0.03031
13) f9 (pattern: # to maximum mana)                    importance=0.02388
14) f19 (pattern: #% increased rarity of items found)  importance=0.02173
15) Quality (pattern: Quality)                         importance=0.01957
16) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01817
17) f4 (pattern: # to evasion rating)                  importance=0.01771
18) f15 (pattern: #% increased critical damage bonus)  importance=0.01744
19) f21 (pattern: #% reduced attribute requirements)   importance=0.01434
20) f18 (pattern: #% increased evasion rating)         importance=0.01221
21) f26 (pattern: adds # to # cold damage to attacks)  importance=0.01005
22) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00753
23) f22 (pattern: #% to chaos resistance)              importance=0.00729
24) f20 (pattern: #% increased weapon swap speed)      importance=0.00728
25) f36 (pattern: gain # mana per enemy killed)        importance=0.00632
26) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00444
27) f6 (pattern: # to level of all melee skills)       importance=0.00438
28) f37 (pattern: leech #% of physical attack damage as life) importance=0.00372
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
