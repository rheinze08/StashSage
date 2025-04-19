=== gloves seg='ar_es_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0167
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
 1) f38 (pattern: leech #% of physical attack damage as mana) importance=0.05525
 2) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04871
 3) f8 (pattern: # to maximum life)                    importance=0.04519
 4) f29 (pattern: adds # to # physical damage to attacks) importance=0.04447
 5) f7 (pattern: # to maximum energy shield)           importance=0.04370
 6) f28 (pattern: adds # to # lightning damage to attacks) importance=0.04086
 7) f22 (pattern: #% to chaos resistance)              importance=0.04029
 8) f14 (pattern: #% increased attack speed)           importance=0.03884
 9) f3 (pattern: # to dexterity)                       importance=0.03805
10) f1 (pattern: # to accuracy rating)                 importance=0.03758
11) f15 (pattern: #% increased critical damage bonus)  importance=0.03626
12) f25 (pattern: #% to lightning resistance)          importance=0.03450
13) f23 (pattern: #% to cold resistance)               importance=0.03427
14) f26 (pattern: adds # to # cold damage to attacks)  importance=0.03291
15) f24 (pattern: #% to fire resistance)               importance=0.03273
16) f12 (pattern: #% increased armour and energy shield) importance=0.03254
17) f10 (pattern: # to strength)                       importance=0.03157
18) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03129
19) f5 (pattern: # to intelligence)                    importance=0.02989
20) f36 (pattern: gain # mana per enemy killed)        importance=0.02962
21) Quality (pattern: Quality)                         importance=0.02956
22) f9 (pattern: # to maximum mana)                    importance=0.02904
23) f19 (pattern: #% increased rarity of items found)  importance=0.02821
24) f21 (pattern: #% reduced attribute requirements)   importance=0.02662
25) f37 (pattern: leech #% of physical attack damage as life) importance=0.02618
26) f35 (pattern: gain # life per enemy killed)        importance=0.02533
27) f2 (pattern: # to armour)                          importance=0.02380
28) f34 (pattern: gain # life per enemy hit with attacks) importance=0.02153
29) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01252
30) f6 (pattern: # to level of all melee skills)       importance=0.01095
31) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00776
32) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
