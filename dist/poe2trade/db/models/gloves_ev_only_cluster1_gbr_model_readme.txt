=== gloves seg='ev_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0047
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
 1) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.17405
 2) f8 (pattern: # to maximum life)                    importance=0.10271
 3) f4 (pattern: # to evasion rating)                  importance=0.09489
 4) f22 (pattern: #% to chaos resistance)              importance=0.09021
 5) f18 (pattern: #% increased evasion rating)         importance=0.07879
 6) f28 (pattern: adds # to # lightning damage to attacks) importance=0.07498
 7) f36 (pattern: gain # mana per enemy killed)        importance=0.07174
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.07152
 9) f19 (pattern: #% increased rarity of items found)  importance=0.06649
10) Quality (pattern: Quality)                         importance=0.04034
11) f23 (pattern: #% to cold resistance)               importance=0.03653
12) f24 (pattern: #% to fire resistance)               importance=0.01379
13) f9 (pattern: # to maximum mana)                    importance=0.01348
14) f15 (pattern: #% increased critical damage bonus)  importance=0.01023
15) f27 (pattern: adds # to # fire damage to attacks)  importance=0.00957
16) f3 (pattern: # to dexterity)                       importance=0.00950
17) f25 (pattern: #% to lightning resistance)          importance=0.00949
18) f35 (pattern: gain # life per enemy killed)        importance=0.00821
19) f1 (pattern: # to accuracy rating)                 importance=0.00574
20) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00436
21) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00428
22) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00271
23) f37 (pattern: leech #% of physical attack damage as life) importance=0.00253
24) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00180
25) f21 (pattern: #% reduced attribute requirements)   importance=0.00120
26) f6 (pattern: # to level of all melee skills)       importance=0.00053
27) f14 (pattern: #% increased attack speed)           importance=0.00034
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
