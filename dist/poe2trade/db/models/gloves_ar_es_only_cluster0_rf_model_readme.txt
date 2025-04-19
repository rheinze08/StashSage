=== gloves seg='ar_es_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: -0.2939
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to level of all melee skills)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f10 (pattern: # to strength)
  f12 (pattern: #% increased armour and energy shield)
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
  f31 (pattern: damage penetrates #% cold resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f1 (pattern: # to accuracy rating)                 importance=0.14369
 2) f8 (pattern: # to maximum life)                    importance=0.13554
 3) Quality (pattern: Quality)                         importance=0.08283
 4) f15 (pattern: #% increased critical damage bonus)  importance=0.07324
 5) f25 (pattern: #% to lightning resistance)          importance=0.05918
 6) f24 (pattern: #% to fire resistance)               importance=0.05768
 7) f12 (pattern: #% increased armour and energy shield) importance=0.05403
 8) f23 (pattern: #% to cold resistance)               importance=0.05336
 9) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03941
10) f38 (pattern: leech #% of physical attack damage as mana) importance=0.03717
11) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03405
12) f27 (pattern: adds # to # fire damage to attacks)  importance=0.03062
13) f2 (pattern: # to armour)                          importance=0.02591
14) f29 (pattern: adds # to # physical damage to attacks) importance=0.01947
15) f10 (pattern: # to strength)                       importance=0.01933
16) f9 (pattern: # to maximum mana)                    importance=0.01636
17) f3 (pattern: # to dexterity)                       importance=0.01630
18) f19 (pattern: #% increased rarity of items found)  importance=0.01460
19) f22 (pattern: #% to chaos resistance)              importance=0.01453
20) f28 (pattern: adds # to # lightning damage to attacks) importance=0.01438
21) f14 (pattern: #% increased attack speed)           importance=0.01085
22) f5 (pattern: # to intelligence)                    importance=0.00943
23) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00877
24) f7 (pattern: # to maximum energy shield)           importance=0.00717
25) f35 (pattern: gain # life per enemy killed)        importance=0.00669
26) f36 (pattern: gain # mana per enemy killed)        importance=0.00505
27) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00384
28) f37 (pattern: leech #% of physical attack damage as life) importance=0.00254
29) f6 (pattern: # to level of all melee skills)       importance=0.00246
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00092
31) f21 (pattern: #% reduced attribute requirements)   importance=0.00056
32) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
