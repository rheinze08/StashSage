=== gloves seg='es_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0188
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
 1) f28 (pattern: adds # to # lightning damage to attacks) importance=0.06134
 2) Quality (pattern: Quality)                         importance=0.05318
 3) f16 (pattern: #% increased energy shield)          importance=0.05148
 4) f26 (pattern: adds # to # cold damage to attacks)  importance=0.05078
 5) f38 (pattern: leech #% of physical attack damage as mana) importance=0.04934
 6) f8 (pattern: # to maximum life)                    importance=0.04713
 7) f25 (pattern: #% to lightning resistance)          importance=0.04428
 8) f23 (pattern: #% to cold resistance)               importance=0.04246
 9) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04226
10) f24 (pattern: #% to fire resistance)               importance=0.04103
11) f22 (pattern: #% to chaos resistance)              importance=0.03825
12) f6 (pattern: # to level of all melee skills)       importance=0.03473
13) f36 (pattern: gain # mana per enemy killed)        importance=0.03336
14) f14 (pattern: #% increased attack speed)           importance=0.03292
15) f5 (pattern: # to intelligence)                    importance=0.03228
16) f21 (pattern: #% reduced attribute requirements)   importance=0.03216
17) f9 (pattern: # to maximum mana)                    importance=0.03187
18) f37 (pattern: leech #% of physical attack damage as life) importance=0.03171
19) f7 (pattern: # to maximum energy shield)           importance=0.02918
20) f34 (pattern: gain # life per enemy hit with attacks) importance=0.02803
21) f35 (pattern: gain # life per enemy killed)        importance=0.02794
22) f29 (pattern: adds # to # physical damage to attacks) importance=0.02763
23) f1 (pattern: # to accuracy rating)                 importance=0.02626
24) f19 (pattern: #% increased rarity of items found)  importance=0.02532
25) f3 (pattern: # to dexterity)                       importance=0.02356
26) f15 (pattern: #% increased critical damage bonus)  importance=0.02191
27) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02009
28) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01953
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
