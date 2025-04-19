=== gloves seg='ev_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: 0.0656
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
 1) Quality (pattern: Quality)                         importance=0.11410
 2) f29 (pattern: adds # to # physical damage to attacks) importance=0.07840
 3) f8 (pattern: # to maximum life)                    importance=0.07204
 4) f18 (pattern: #% increased evasion rating)         importance=0.07016
 5) f21 (pattern: #% reduced attribute requirements)   importance=0.06224
 6) f1 (pattern: # to accuracy rating)                 importance=0.05979
 7) f26 (pattern: adds # to # cold damage to attacks)  importance=0.04542
 8) f15 (pattern: #% increased critical damage bonus)  importance=0.04338
 9) f25 (pattern: #% to lightning resistance)          importance=0.04191
10) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03972
11) f9 (pattern: # to maximum mana)                    importance=0.03898
12) f24 (pattern: #% to fire resistance)               importance=0.03771
13) f37 (pattern: leech #% of physical attack damage as life) importance=0.03664
14) f35 (pattern: gain # life per enemy killed)        importance=0.03546
15) f23 (pattern: #% to cold resistance)               importance=0.03157
16) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02948
17) f19 (pattern: #% increased rarity of items found)  importance=0.02873
18) f4 (pattern: # to evasion rating)                  importance=0.02611
19) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01465
20) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01440
21) f3 (pattern: # to dexterity)                       importance=0.01376
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01338
23) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01192
24) f36 (pattern: gain # mana per enemy killed)        importance=0.01171
25) f22 (pattern: #% to chaos resistance)              importance=0.01081
26) f14 (pattern: #% increased attack speed)           importance=0.00978
27) f6 (pattern: # to level of all melee skills)       importance=0.00775
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
