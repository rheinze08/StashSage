=== gloves seg='ev_es_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: 0.1528
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to level of all melee skills)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f17 (pattern: #% increased evasion and energy shield)
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
  f32 (pattern: damage penetrates #% fire resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f29 (pattern: adds # to # physical damage to attacks) importance=0.12789
 2) f24 (pattern: #% to fire resistance)               importance=0.11970
 3) f22 (pattern: #% to chaos resistance)              importance=0.10474
 4) f4 (pattern: # to evasion rating)                  importance=0.09337
 5) f14 (pattern: #% increased attack speed)           importance=0.05828
 6) f15 (pattern: #% increased critical damage bonus)  importance=0.05641
 7) f28 (pattern: adds # to # lightning damage to attacks) importance=0.05561
 8) f36 (pattern: gain # mana per enemy killed)        importance=0.04561
 9) f9 (pattern: # to maximum mana)                    importance=0.03799
10) f17 (pattern: #% increased evasion and energy shield) importance=0.03238
11) f27 (pattern: adds # to # fire damage to attacks)  importance=0.03023
12) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02758
13) f19 (pattern: #% increased rarity of items found)  importance=0.02695
14) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02534
15) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.02159
16) f25 (pattern: #% to lightning resistance)          importance=0.02020
17) f8 (pattern: # to maximum life)                    importance=0.01687
18) f23 (pattern: #% to cold resistance)               importance=0.01626
19) f6 (pattern: # to level of all melee skills)       importance=0.01597
20) f3 (pattern: # to dexterity)                       importance=0.01344
21) f7 (pattern: # to maximum energy shield)           importance=0.00922
22) f35 (pattern: gain # life per enemy killed)        importance=0.00890
23) f1 (pattern: # to accuracy rating)                 importance=0.00803
24) f5 (pattern: # to intelligence)                    importance=0.00600
25) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00494
26) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00481
27) f37 (pattern: leech #% of physical attack damage as life) importance=0.00419
28) f21 (pattern: #% reduced attribute requirements)   importance=0.00381
29) Quality (pattern: Quality)                         importance=0.00339
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00031
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
