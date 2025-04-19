=== gloves seg='es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.0513
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
 1) f8 (pattern: # to maximum life)                    importance=0.12716
 2) f28 (pattern: adds # to # lightning damage to attacks) importance=0.12142
 3) f16 (pattern: #% increased energy shield)          importance=0.11821
 4) f23 (pattern: #% to cold resistance)               importance=0.07767
 5) f38 (pattern: leech #% of physical attack damage as mana) importance=0.06828
 6) f26 (pattern: adds # to # cold damage to attacks)  importance=0.05473
 7) f24 (pattern: #% to fire resistance)               importance=0.04695
 8) Quality (pattern: Quality)                         importance=0.04595
 9) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04474
10) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03909
11) f25 (pattern: #% to lightning resistance)          importance=0.03461
12) f1 (pattern: # to accuracy rating)                 importance=0.02538
13) f14 (pattern: #% increased attack speed)           importance=0.02250
14) f22 (pattern: #% to chaos resistance)              importance=0.02235
15) f9 (pattern: # to maximum mana)                    importance=0.02102
16) f5 (pattern: # to intelligence)                    importance=0.01942
17) f7 (pattern: # to maximum energy shield)           importance=0.01942
18) f35 (pattern: gain # life per enemy killed)        importance=0.01935
19) f3 (pattern: # to dexterity)                       importance=0.01611
20) f29 (pattern: adds # to # physical damage to attacks) importance=0.01504
21) f37 (pattern: leech #% of physical attack damage as life) importance=0.01345
22) f15 (pattern: #% increased critical damage bonus)  importance=0.00566
23) f19 (pattern: #% increased rarity of items found)  importance=0.00542
24) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00485
25) f36 (pattern: gain # mana per enemy killed)        importance=0.00480
26) f6 (pattern: # to level of all melee skills)       importance=0.00456
27) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00185
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f21 (pattern: #% reduced attribute requirements)   importance=0.00000
