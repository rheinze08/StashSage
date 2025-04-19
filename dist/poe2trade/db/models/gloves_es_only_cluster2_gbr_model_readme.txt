=== gloves seg='es_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0257
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
 1) f8 (pattern: # to maximum life)                    importance=0.15263
 2) f28 (pattern: adds # to # lightning damage to attacks) importance=0.12013
 3) f16 (pattern: #% increased energy shield)          importance=0.11173
 4) f24 (pattern: #% to fire resistance)               importance=0.06359
 5) f38 (pattern: leech #% of physical attack damage as mana) importance=0.06318
 6) f26 (pattern: adds # to # cold damage to attacks)  importance=0.06254
 7) Quality (pattern: Quality)                         importance=0.05949
 8) f23 (pattern: #% to cold resistance)               importance=0.05922
 9) f25 (pattern: #% to lightning resistance)          importance=0.05532
10) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04770
11) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03039
12) f35 (pattern: gain # life per enemy killed)        importance=0.02318
13) f22 (pattern: #% to chaos resistance)              importance=0.02186
14) f7 (pattern: # to maximum energy shield)           importance=0.02146
15) f5 (pattern: # to intelligence)                    importance=0.01918
16) f1 (pattern: # to accuracy rating)                 importance=0.01808
17) f9 (pattern: # to maximum mana)                    importance=0.01419
18) f3 (pattern: # to dexterity)                       importance=0.01332
19) f29 (pattern: adds # to # physical damage to attacks) importance=0.01143
20) f14 (pattern: #% increased attack speed)           importance=0.00982
21) f19 (pattern: #% increased rarity of items found)  importance=0.00761
22) f37 (pattern: leech #% of physical attack damage as life) importance=0.00444
23) f15 (pattern: #% increased critical damage bonus)  importance=0.00343
24) f21 (pattern: #% reduced attribute requirements)   importance=0.00270
25) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00204
26) f6 (pattern: # to level of all melee skills)       importance=0.00068
27) f36 (pattern: gain # mana per enemy killed)        importance=0.00065
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
