=== gloves seg='ar_es_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.0192
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.14819
 2) f8 (pattern: # to maximum life)                    importance=0.11762
 3) f27 (pattern: adds # to # fire damage to attacks)  importance=0.07676
 4) f14 (pattern: #% increased attack speed)           importance=0.05303
 5) f3 (pattern: # to dexterity)                       importance=0.05025
 6) f22 (pattern: #% to chaos resistance)              importance=0.04894
 7) f26 (pattern: adds # to # cold damage to attacks)  importance=0.04574
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.03966
 9) f9 (pattern: # to maximum mana)                    importance=0.03804
10) f5 (pattern: # to intelligence)                    importance=0.03734
11) f24 (pattern: #% to fire resistance)               importance=0.03438
12) f10 (pattern: # to strength)                       importance=0.03203
13) f25 (pattern: #% to lightning resistance)          importance=0.03173
14) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02940
15) f34 (pattern: gain # life per enemy hit with attacks) importance=0.02712
16) f23 (pattern: #% to cold resistance)               importance=0.02415
17) f19 (pattern: #% increased rarity of items found)  importance=0.02211
18) f38 (pattern: leech #% of physical attack damage as mana) importance=0.02120
19) f12 (pattern: #% increased armour and energy shield) importance=0.01912
20) f2 (pattern: # to armour)                          importance=0.01825
21) Quality (pattern: Quality)                         importance=0.01678
22) f7 (pattern: # to maximum energy shield)           importance=0.01629
23) f35 (pattern: gain # life per enemy killed)        importance=0.01264
24) f36 (pattern: gain # mana per enemy killed)        importance=0.01066
25) f15 (pattern: #% increased critical damage bonus)  importance=0.00831
26) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.00677
27) f37 (pattern: leech #% of physical attack damage as life) importance=0.00550
28) Deflated_Armour (pattern: Deflated_Armour)         importance=0.00449
29) f6 (pattern: # to level of all melee skills)       importance=0.00238
30) f21 (pattern: #% reduced attribute requirements)   importance=0.00096
31) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00014
32) f31 (pattern: damage penetrates #% cold resistance) importance=0.00003
