=== gloves seg='es_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: -0.0347
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
 1) f28 (pattern: adds # to # lightning damage to attacks) importance=0.15641
 2) f8 (pattern: # to maximum life)                    importance=0.10335
 3) f16 (pattern: #% increased energy shield)          importance=0.08954
 4) Quality (pattern: Quality)                         importance=0.06062
 5) f27 (pattern: adds # to # fire damage to attacks)  importance=0.04804
 6) f23 (pattern: #% to cold resistance)               importance=0.04245
 7) f26 (pattern: adds # to # cold damage to attacks)  importance=0.04233
 8) f38 (pattern: leech #% of physical attack damage as mana) importance=0.03983
 9) f25 (pattern: #% to lightning resistance)          importance=0.03912
10) f24 (pattern: #% to fire resistance)               importance=0.03758
11) f7 (pattern: # to maximum energy shield)           importance=0.03236
12) f9 (pattern: # to maximum mana)                    importance=0.03182
13) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03047
14) f35 (pattern: gain # life per enemy killed)        importance=0.02950
15) f29 (pattern: adds # to # physical damage to attacks) importance=0.02144
16) f3 (pattern: # to dexterity)                       importance=0.02125
17) f14 (pattern: #% increased attack speed)           importance=0.02104
18) f5 (pattern: # to intelligence)                    importance=0.02088
19) f22 (pattern: #% to chaos resistance)              importance=0.01737
20) f36 (pattern: gain # mana per enemy killed)        importance=0.01700
21) f37 (pattern: leech #% of physical attack damage as life) importance=0.01684
22) f19 (pattern: #% increased rarity of items found)  importance=0.01627
23) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01480
24) f1 (pattern: # to accuracy rating)                 importance=0.01366
25) f6 (pattern: # to level of all melee skills)       importance=0.01162
26) f21 (pattern: #% reduced attribute requirements)   importance=0.00996
27) f15 (pattern: #% increased critical damage bonus)  importance=0.00907
28) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00478
29) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00056
30) f32 (pattern: damage penetrates #% fire resistance) importance=0.00003
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
