=== gloves seg='ev_es_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0483
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to level of all melee skills)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f17 (pattern: #% increased evasion and energy shield)
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
  f30 (pattern: break #% increased armour)
  f31 (pattern: damage penetrates #% cold resistance)
  f32 (pattern: damage penetrates #% fire resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f1 (pattern: # to accuracy rating)                 importance=0.13041
 2) f29 (pattern: adds # to # physical damage to attacks) importance=0.10760
 3) f28 (pattern: adds # to # lightning damage to attacks) importance=0.09354
 4) f27 (pattern: adds # to # fire damage to attacks)  importance=0.08317
 5) Quality (pattern: Quality)                         importance=0.07817
 6) f23 (pattern: #% to cold resistance)               importance=0.07706
 7) f25 (pattern: #% to lightning resistance)          importance=0.05561
 8) f24 (pattern: #% to fire resistance)               importance=0.05513
 9) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03773
10) f3 (pattern: # to dexterity)                       importance=0.03711
11) f14 (pattern: #% increased attack speed)           importance=0.03528
12) f5 (pattern: # to intelligence)                    importance=0.02923
13) f4 (pattern: # to evasion rating)                  importance=0.02237
14) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02237
15) f8 (pattern: # to maximum life)                    importance=0.02183
16) f35 (pattern: gain # life per enemy killed)        importance=0.02069
17) f19 (pattern: #% increased rarity of items found)  importance=0.02038
18) f9 (pattern: # to maximum mana)                    importance=0.01380
19) f37 (pattern: leech #% of physical attack damage as life) importance=0.01019
20) f21 (pattern: #% reduced attribute requirements)   importance=0.00837
21) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.00771
22) f36 (pattern: gain # mana per enemy killed)        importance=0.00752
23) f22 (pattern: #% to chaos resistance)              importance=0.00668
24) f15 (pattern: #% increased critical damage bonus)  importance=0.00624
25) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00580
26) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00227
27) f7 (pattern: # to maximum energy shield)           importance=0.00212
28) f6 (pattern: # to level of all melee skills)       importance=0.00147
29) f17 (pattern: #% increased evasion and energy shield) importance=0.00013
30) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
