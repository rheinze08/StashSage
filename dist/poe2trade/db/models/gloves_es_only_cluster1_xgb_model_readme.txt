=== gloves seg='es_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0452
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
 1) f16 (pattern: #% increased energy shield)          importance=0.06577
 2) f36 (pattern: gain # mana per enemy killed)        importance=0.05348
 3) f25 (pattern: #% to lightning resistance)          importance=0.04524
 4) f19 (pattern: #% increased rarity of items found)  importance=0.04370
 5) f22 (pattern: #% to chaos resistance)              importance=0.04310
 6) f1 (pattern: # to accuracy rating)                 importance=0.04296
 7) f23 (pattern: #% to cold resistance)               importance=0.04294
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.04235
 9) f26 (pattern: adds # to # cold damage to attacks)  importance=0.04209
10) f7 (pattern: # to maximum energy shield)           importance=0.04137
11) f3 (pattern: # to dexterity)                       importance=0.04136
12) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03896
13) f27 (pattern: adds # to # fire damage to attacks)  importance=0.03768
14) f24 (pattern: #% to fire resistance)               importance=0.03692
15) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.03662
16) f34 (pattern: gain # life per enemy hit with attacks) importance=0.03309
17) f38 (pattern: leech #% of physical attack damage as mana) importance=0.03259
18) f5 (pattern: # to intelligence)                    importance=0.03190
19) f8 (pattern: # to maximum life)                    importance=0.03177
20) f21 (pattern: #% reduced attribute requirements)   importance=0.03022
21) f6 (pattern: # to level of all melee skills)       importance=0.02829
22) f9 (pattern: # to maximum mana)                    importance=0.02763
23) f35 (pattern: gain # life per enemy killed)        importance=0.02710
24) f14 (pattern: #% increased attack speed)           importance=0.02501
25) f15 (pattern: #% increased critical damage bonus)  importance=0.02334
26) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02210
27) f37 (pattern: leech #% of physical attack damage as life) importance=0.01843
28) Quality (pattern: Quality)                         importance=0.01398
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
