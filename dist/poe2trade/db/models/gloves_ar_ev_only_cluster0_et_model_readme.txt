=== gloves seg='ar_ev_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: -0.4810
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
 1) f8 (pattern: # to maximum life)                    importance=0.13994
 2) f26 (pattern: adds # to # cold damage to attacks)  importance=0.09514
 3) f22 (pattern: #% to chaos resistance)              importance=0.06854
 4) f3 (pattern: # to dexterity)                       importance=0.06095
 5) f29 (pattern: adds # to # physical damage to attacks) importance=0.05612
 6) f23 (pattern: #% to cold resistance)               importance=0.05525
 7) f24 (pattern: #% to fire resistance)               importance=0.04921
 8) f28 (pattern: adds # to # lightning damage to attacks) importance=0.04682
 9) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04419
10) f10 (pattern: # to strength)                       importance=0.04324
11) f1 (pattern: # to accuracy rating)                 importance=0.04000
12) f19 (pattern: #% increased rarity of items found)  importance=0.03921
13) f25 (pattern: #% to lightning resistance)          importance=0.03633
14) f9 (pattern: # to maximum mana)                    importance=0.03460
15) Deflated_Armour (pattern: Deflated_Armour)         importance=0.02158
16) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.02006
17) f36 (pattern: gain # mana per enemy killed)        importance=0.01818
18) f35 (pattern: gain # life per enemy killed)        importance=0.01810
19) f15 (pattern: #% increased critical damage bonus)  importance=0.01683
20) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01655
21) f13 (pattern: #% increased armour and evasion)     importance=0.01625
22) f4 (pattern: # to evasion rating)                  importance=0.01359
23) f14 (pattern: #% increased attack speed)           importance=0.01341
24) f2 (pattern: # to armour)                          importance=0.01242
25) f37 (pattern: leech #% of physical attack damage as life) importance=0.00845
26) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00800
27) f21 (pattern: #% reduced attribute requirements)   importance=0.00345
28) Quality (pattern: Quality)                         importance=0.00261
29) f6 (pattern: # to level of all melee skills)       importance=0.00070
30) f30 (pattern: break #% increased armour)           importance=0.00028
31) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00002
32) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
