=== gloves seg='ar_es_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: -0.2043
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
 1) f28 (pattern: adds # to # lightning damage to attacks) importance=0.18836
 2) f24 (pattern: #% to fire resistance)               importance=0.13693
 3) f10 (pattern: # to strength)                       importance=0.10772
 4) f1 (pattern: # to accuracy rating)                 importance=0.08466
 5) f15 (pattern: #% increased critical damage bonus)  importance=0.07110
 6) f5 (pattern: # to intelligence)                    importance=0.04837
 7) f8 (pattern: # to maximum life)                    importance=0.03762
 8) f23 (pattern: #% to cold resistance)               importance=0.03724
 9) f12 (pattern: #% increased armour and energy shield) importance=0.03532
10) f22 (pattern: #% to chaos resistance)              importance=0.03387
11) f3 (pattern: # to dexterity)                       importance=0.02551
12) Deflated_Armour (pattern: Deflated_Armour)         importance=0.02406
13) f29 (pattern: adds # to # physical damage to attacks) importance=0.02381
14) f6 (pattern: # to level of all melee skills)       importance=0.02106
15) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01800
16) Quality (pattern: Quality)                         importance=0.01774
17) f14 (pattern: #% increased attack speed)           importance=0.01487
18) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01324
19) f9 (pattern: # to maximum mana)                    importance=0.01236
20) f19 (pattern: #% increased rarity of items found)  importance=0.01141
21) f25 (pattern: #% to lightning resistance)          importance=0.00870
22) f35 (pattern: gain # life per enemy killed)        importance=0.00854
23) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00596
24) f37 (pattern: leech #% of physical attack damage as life) importance=0.00575
25) f2 (pattern: # to armour)                          importance=0.00234
26) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00221
27) f21 (pattern: #% reduced attribute requirements)   importance=0.00115
28) f7 (pattern: # to maximum energy shield)           importance=0.00112
29) f36 (pattern: gain # mana per enemy killed)        importance=0.00097
30) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00001
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
