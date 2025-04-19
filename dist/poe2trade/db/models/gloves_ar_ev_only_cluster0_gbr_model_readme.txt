=== gloves seg='ar_ev_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.3615
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
 1) f8 (pattern: # to maximum life)                    importance=0.21637
 2) f23 (pattern: #% to cold resistance)               importance=0.08948
 3) f3 (pattern: # to dexterity)                       importance=0.07907
 4) f26 (pattern: adds # to # cold damage to attacks)  importance=0.07637
 5) f9 (pattern: # to maximum mana)                    importance=0.06020
 6) f22 (pattern: #% to chaos resistance)              importance=0.05149
 7) f29 (pattern: adds # to # physical damage to attacks) importance=0.04387
 8) f24 (pattern: #% to fire resistance)               importance=0.04007
 9) f27 (pattern: adds # to # fire damage to attacks)  importance=0.03909
10) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03287
11) f25 (pattern: #% to lightning resistance)          importance=0.03182
12) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03055
13) f10 (pattern: # to strength)                       importance=0.02680
14) f19 (pattern: #% increased rarity of items found)  importance=0.02272
15) f36 (pattern: gain # mana per enemy killed)        importance=0.02259
16) f1 (pattern: # to accuracy rating)                 importance=0.01884
17) f4 (pattern: # to evasion rating)                  importance=0.01882
18) f15 (pattern: #% increased critical damage bonus)  importance=0.01796
19) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01717
20) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.01357
21) f13 (pattern: #% increased armour and evasion)     importance=0.01304
22) f35 (pattern: gain # life per enemy killed)        importance=0.01163
23) f14 (pattern: #% increased attack speed)           importance=0.01029
24) f2 (pattern: # to armour)                          importance=0.00687
25) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00390
26) f21 (pattern: #% reduced attribute requirements)   importance=0.00238
27) f37 (pattern: leech #% of physical attack damage as life) importance=0.00163
28) f6 (pattern: # to level of all melee skills)       importance=0.00049
29) Quality (pattern: Quality)                         importance=0.00006
30) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00001
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f30 (pattern: break #% increased armour)           importance=0.00000
