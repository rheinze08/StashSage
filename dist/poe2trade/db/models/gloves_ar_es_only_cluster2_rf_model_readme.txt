=== gloves seg='ar_es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.1884
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
 1) Deflated_Armour (pattern: Deflated_Armour)         importance=0.14447
 2) f15 (pattern: #% increased critical damage bonus)  importance=0.12350
 3) f10 (pattern: # to strength)                       importance=0.10595
 4) f5 (pattern: # to intelligence)                    importance=0.06601
 5) f8 (pattern: # to maximum life)                    importance=0.06192
 6) f28 (pattern: adds # to # lightning damage to attacks) importance=0.06133
 7) f29 (pattern: adds # to # physical damage to attacks) importance=0.05245
 8) f23 (pattern: #% to cold resistance)               importance=0.05157
 9) f24 (pattern: #% to fire resistance)               importance=0.04918
10) f12 (pattern: #% increased armour and energy shield) importance=0.04235
11) f14 (pattern: #% increased attack speed)           importance=0.03538
12) f22 (pattern: #% to chaos resistance)              importance=0.03220
13) Quality (pattern: Quality)                         importance=0.02866
14) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02748
15) f3 (pattern: # to dexterity)                       importance=0.02704
16) f9 (pattern: # to maximum mana)                    importance=0.02565
17) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02080
18) f1 (pattern: # to accuracy rating)                 importance=0.01757
19) f36 (pattern: gain # mana per enemy killed)        importance=0.00444
20) f6 (pattern: # to level of all melee skills)       importance=0.00435
21) f25 (pattern: #% to lightning resistance)          importance=0.00424
22) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00412
23) f19 (pattern: #% increased rarity of items found)  importance=0.00298
24) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00274
25) f35 (pattern: gain # life per enemy killed)        importance=0.00224
26) f37 (pattern: leech #% of physical attack damage as life) importance=0.00072
27) f2 (pattern: # to armour)                          importance=0.00063
28) f7 (pattern: # to maximum energy shield)           importance=0.00000
29) f21 (pattern: #% reduced attribute requirements)   importance=0.00000
30) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
