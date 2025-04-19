=== gloves seg='ev_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0017
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.20625
 2) f23 (pattern: #% to cold resistance)               importance=0.12332
 3) f28 (pattern: adds # to # lightning damage to attacks) importance=0.11922
 4) f8 (pattern: # to maximum life)                    importance=0.09596
 5) f27 (pattern: adds # to # fire damage to attacks)  importance=0.07611
 6) f29 (pattern: adds # to # physical damage to attacks) importance=0.06329
 7) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05116
 8) f14 (pattern: #% increased attack speed)           importance=0.04093
 9) f35 (pattern: gain # life per enemy killed)        importance=0.04018
10) f24 (pattern: #% to fire resistance)               importance=0.02754
11) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.02550
12) Quality (pattern: Quality)                         importance=0.02252
13) f19 (pattern: #% increased rarity of items found)  importance=0.01973
14) f25 (pattern: #% to lightning resistance)          importance=0.01679
15) f9 (pattern: # to maximum mana)                    importance=0.01497
16) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00957
17) f18 (pattern: #% increased evasion rating)         importance=0.00808
18) f4 (pattern: # to evasion rating)                  importance=0.00782
19) f3 (pattern: # to dexterity)                       importance=0.00746
20) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00634
21) f15 (pattern: #% increased critical damage bonus)  importance=0.00625
22) f21 (pattern: #% reduced attribute requirements)   importance=0.00281
23) f20 (pattern: #% increased weapon swap speed)      importance=0.00205
24) f36 (pattern: gain # mana per enemy killed)        importance=0.00204
25) f22 (pattern: #% to chaos resistance)              importance=0.00166
26) f6 (pattern: # to level of all melee skills)       importance=0.00142
27) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00102
28) f37 (pattern: leech #% of physical attack damage as life) importance=0.00002
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
