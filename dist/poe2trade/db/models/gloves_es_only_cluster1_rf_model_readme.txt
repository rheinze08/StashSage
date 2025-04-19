=== gloves seg='es_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: -0.0853
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.11367
 2) f36 (pattern: gain # mana per enemy killed)        importance=0.09085
 3) f7 (pattern: # to maximum energy shield)           importance=0.07805
 4) f25 (pattern: #% to lightning resistance)          importance=0.07221
 5) f23 (pattern: #% to cold resistance)               importance=0.07024
 6) f19 (pattern: #% increased rarity of items found)  importance=0.05867
 7) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.05144
 8) f3 (pattern: # to dexterity)                       importance=0.04848
 9) f26 (pattern: adds # to # cold damage to attacks)  importance=0.04593
10) f22 (pattern: #% to chaos resistance)              importance=0.04294
11) f8 (pattern: # to maximum life)                    importance=0.04282
12) f27 (pattern: adds # to # fire damage to attacks)  importance=0.03755
13) f5 (pattern: # to intelligence)                    importance=0.03631
14) f29 (pattern: adds # to # physical damage to attacks) importance=0.03595
15) f16 (pattern: #% increased energy shield)          importance=0.03566
16) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02596
17) f15 (pattern: #% increased critical damage bonus)  importance=0.02087
18) f35 (pattern: gain # life per enemy killed)        importance=0.01910
19) f24 (pattern: #% to fire resistance)               importance=0.01622
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01052
21) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00997
22) f14 (pattern: #% increased attack speed)           importance=0.00936
23) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00586
24) f9 (pattern: # to maximum mana)                    importance=0.00557
25) f21 (pattern: #% reduced attribute requirements)   importance=0.00504
26) f6 (pattern: # to level of all melee skills)       importance=0.00381
27) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00269
28) Quality (pattern: Quality)                         importance=0.00258
29) f37 (pattern: leech #% of physical attack damage as life) importance=0.00168
30) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
