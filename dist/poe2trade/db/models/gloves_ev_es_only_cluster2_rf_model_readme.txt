=== gloves seg='ev_es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.0682
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.11668
 2) f29 (pattern: adds # to # physical damage to attacks) importance=0.10378
 3) f28 (pattern: adds # to # lightning damage to attacks) importance=0.07864
 4) f23 (pattern: #% to cold resistance)               importance=0.07703
 5) Quality (pattern: Quality)                         importance=0.07088
 6) f27 (pattern: adds # to # fire damage to attacks)  importance=0.06775
 7) f24 (pattern: #% to fire resistance)               importance=0.05497
 8) f25 (pattern: #% to lightning resistance)          importance=0.04968
 9) f3 (pattern: # to dexterity)                       importance=0.04620
10) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03681
11) f14 (pattern: #% increased attack speed)           importance=0.03490
12) f8 (pattern: # to maximum life)                    importance=0.03070
13) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02906
14) f19 (pattern: #% increased rarity of items found)  importance=0.02718
15) f35 (pattern: gain # life per enemy killed)        importance=0.02689
16) f5 (pattern: # to intelligence)                    importance=0.02324
17) f15 (pattern: #% increased critical damage bonus)  importance=0.01774
18) f4 (pattern: # to evasion rating)                  importance=0.01521
19) f9 (pattern: # to maximum mana)                    importance=0.01387
20) f21 (pattern: #% reduced attribute requirements)   importance=0.01284
21) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01274
22) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01059
23) f6 (pattern: # to level of all melee skills)       importance=0.01007
24) f22 (pattern: #% to chaos resistance)              importance=0.00887
25) f36 (pattern: gain # mana per enemy killed)        importance=0.00857
26) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00700
27) f7 (pattern: # to maximum energy shield)           importance=0.00276
28) f17 (pattern: #% increased evasion and energy shield) importance=0.00252
29) f37 (pattern: leech #% of physical attack damage as life) importance=0.00232
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00053
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
