=== gloves seg='es_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0985
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f3 (pattern: # to dexterity)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to level of all melee skills)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f16 (pattern: #% increased energy shield)
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
  f31 (pattern: damage penetrates #% cold resistance)
  f32 (pattern: damage penetrates #% fire resistance)
  f33 (pattern: damage penetrates #% lightning resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f1 (pattern: # to accuracy rating)                 importance=0.12645
 2) f7 (pattern: # to maximum energy shield)           importance=0.08569
 3) f36 (pattern: gain # mana per enemy killed)        importance=0.08515
 4) f25 (pattern: #% to lightning resistance)          importance=0.07025
 5) f19 (pattern: #% increased rarity of items found)  importance=0.06178
 6) f23 (pattern: #% to cold resistance)               importance=0.05788
 7) f3 (pattern: # to dexterity)                       importance=0.05113
 8) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04331
 9) f16 (pattern: #% increased energy shield)          importance=0.04135
10) f29 (pattern: adds # to # physical damage to attacks) importance=0.04133
11) f5 (pattern: # to intelligence)                    importance=0.04024
12) f8 (pattern: # to maximum life)                    importance=0.03972
13) f22 (pattern: #% to chaos resistance)              importance=0.03546
14) f26 (pattern: adds # to # cold damage to attacks)  importance=0.03524
15) f15 (pattern: #% increased critical damage bonus)  importance=0.03020
16) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02998
17) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02512
18) f24 (pattern: #% to fire resistance)               importance=0.01630
19) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01483
20) f35 (pattern: gain # life per enemy killed)        importance=0.01404
21) f9 (pattern: # to maximum mana)                    importance=0.01367
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00956
23) f14 (pattern: #% increased attack speed)           importance=0.00898
24) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00628
25) f21 (pattern: #% reduced attribute requirements)   importance=0.00561
26) f37 (pattern: leech #% of physical attack damage as life) importance=0.00424
27) Quality (pattern: Quality)                         importance=0.00361
28) f6 (pattern: # to level of all melee skills)       importance=0.00214
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00049
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
