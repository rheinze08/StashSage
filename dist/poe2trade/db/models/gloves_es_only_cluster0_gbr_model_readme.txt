=== gloves seg='es_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0299
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
 1) f24 (pattern: #% to fire resistance)               importance=0.25073
 2) f7 (pattern: # to maximum energy shield)           importance=0.17740
 3) f16 (pattern: #% increased energy shield)          importance=0.11075
 4) f5 (pattern: # to intelligence)                    importance=0.07822
 5) f1 (pattern: # to accuracy rating)                 importance=0.05604
 6) f25 (pattern: #% to lightning resistance)          importance=0.03920
 7) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03906
 8) Quality (pattern: Quality)                         importance=0.03347
 9) f29 (pattern: adds # to # physical damage to attacks) importance=0.03092
10) f3 (pattern: # to dexterity)                       importance=0.02912
11) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02412
12) f22 (pattern: #% to chaos resistance)              importance=0.02294
13) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01817
14) f8 (pattern: # to maximum life)                    importance=0.01672
15) f37 (pattern: leech #% of physical attack damage as life) importance=0.01455
16) f23 (pattern: #% to cold resistance)               importance=0.01185
17) f19 (pattern: #% increased rarity of items found)  importance=0.01088
18) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01026
19) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00744
20) f9 (pattern: # to maximum mana)                    importance=0.00427
21) f36 (pattern: gain # mana per enemy killed)        importance=0.00413
22) f21 (pattern: #% reduced attribute requirements)   importance=0.00278
23) f35 (pattern: gain # life per enemy killed)        importance=0.00275
24) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00187
25) f14 (pattern: #% increased attack speed)           importance=0.00140
26) f15 (pattern: #% increased critical damage bonus)  importance=0.00096
27) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
28) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
31) f6 (pattern: # to level of all melee skills)       importance=0.00000
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
