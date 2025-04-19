=== gloves seg='es_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.0120
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
 1) f36 (pattern: gain # mana per enemy killed)        importance=0.08213
 2) f25 (pattern: #% to lightning resistance)          importance=0.07544
 3) f7 (pattern: # to maximum energy shield)           importance=0.06162
 4) f28 (pattern: adds # to # lightning damage to attacks) importance=0.05965
 5) f26 (pattern: adds # to # cold damage to attacks)  importance=0.05669
 6) f23 (pattern: #% to cold resistance)               importance=0.05655
 7) f16 (pattern: #% increased energy shield)          importance=0.05152
 8) f1 (pattern: # to accuracy rating)                 importance=0.04820
 9) f3 (pattern: # to dexterity)                       importance=0.04582
10) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04196
11) f29 (pattern: adds # to # physical damage to attacks) importance=0.04181
12) f22 (pattern: #% to chaos resistance)              importance=0.04061
13) f19 (pattern: #% increased rarity of items found)  importance=0.03815
14) f21 (pattern: #% reduced attribute requirements)   importance=0.03328
15) f5 (pattern: # to intelligence)                    importance=0.03278
16) f15 (pattern: #% increased critical damage bonus)  importance=0.02945
17) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.02768
18) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02579
19) f6 (pattern: # to level of all melee skills)       importance=0.02439
20) f35 (pattern: gain # life per enemy killed)        importance=0.02086
21) f8 (pattern: # to maximum life)                    importance=0.02022
22) f9 (pattern: # to maximum mana)                    importance=0.01738
23) f24 (pattern: #% to fire resistance)               importance=0.01482
24) Quality (pattern: Quality)                         importance=0.01419
25) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01345
26) f14 (pattern: #% increased attack speed)           importance=0.00883
27) f37 (pattern: leech #% of physical attack damage as life) importance=0.00677
28) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00519
29) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00427
30) f32 (pattern: damage penetrates #% fire resistance) importance=0.00049
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00003
32) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
