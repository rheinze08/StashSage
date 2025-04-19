=== gloves seg='ar_es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: -0.0718
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.17586
 2) Quality (pattern: Quality)                         importance=0.16292
 3) f8 (pattern: # to maximum life)                    importance=0.12369
 4) f15 (pattern: #% increased critical damage bonus)  importance=0.08200
 5) f19 (pattern: #% increased rarity of items found)  importance=0.04298
 6) f24 (pattern: #% to fire resistance)               importance=0.04207
 7) f25 (pattern: #% to lightning resistance)          importance=0.04100
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.03125
 9) f7 (pattern: # to maximum energy shield)           importance=0.02994
10) f14 (pattern: #% increased attack speed)           importance=0.02927
11) f2 (pattern: # to armour)                          importance=0.02674
12) f23 (pattern: #% to cold resistance)               importance=0.02554
13) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02220
14) f9 (pattern: # to maximum mana)                    importance=0.01840
15) f3 (pattern: # to dexterity)                       importance=0.01827
16) f36 (pattern: gain # mana per enemy killed)        importance=0.01765
17) f10 (pattern: # to strength)                       importance=0.01343
18) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01255
19) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01186
20) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01181
21) f28 (pattern: adds # to # lightning damage to attacks) importance=0.01074
22) f12 (pattern: #% increased armour and energy shield) importance=0.00875
23) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00869
24) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00824
25) f22 (pattern: #% to chaos resistance)              importance=0.00624
26) f37 (pattern: leech #% of physical attack damage as life) importance=0.00530
27) f21 (pattern: #% reduced attribute requirements)   importance=0.00437
28) f5 (pattern: # to intelligence)                    importance=0.00342
29) f35 (pattern: gain # life per enemy killed)        importance=0.00259
30) f6 (pattern: # to level of all melee skills)       importance=0.00148
31) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00074
32) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
