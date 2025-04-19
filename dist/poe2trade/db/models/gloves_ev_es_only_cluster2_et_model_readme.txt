=== gloves seg='ev_es_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: -0.0583
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
 1) Quality (pattern: Quality)                         importance=0.11639
 2) f28 (pattern: adds # to # lightning damage to attacks) importance=0.11146
 3) f29 (pattern: adds # to # physical damage to attacks) importance=0.10741
 4) f1 (pattern: # to accuracy rating)                 importance=0.09330
 5) f27 (pattern: adds # to # fire damage to attacks)  importance=0.06687
 6) f23 (pattern: #% to cold resistance)               importance=0.04478
 7) f5 (pattern: # to intelligence)                    importance=0.04359
 8) f25 (pattern: #% to lightning resistance)          importance=0.04134
 9) f19 (pattern: #% increased rarity of items found)  importance=0.03902
10) f24 (pattern: #% to fire resistance)               importance=0.03851
11) f3 (pattern: # to dexterity)                       importance=0.02837
12) f22 (pattern: #% to chaos resistance)              importance=0.02468
13) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02450
14) f35 (pattern: gain # life per enemy killed)        importance=0.02094
15) f9 (pattern: # to maximum mana)                    importance=0.02026
16) f14 (pattern: #% increased attack speed)           importance=0.02011
17) f21 (pattern: #% reduced attribute requirements)   importance=0.01848
18) f37 (pattern: leech #% of physical attack damage as life) importance=0.01826
19) f8 (pattern: # to maximum life)                    importance=0.01679
20) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01593
21) f15 (pattern: #% increased critical damage bonus)  importance=0.01470
22) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.01351
23) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01317
24) f4 (pattern: # to evasion rating)                  importance=0.01201
25) f6 (pattern: # to level of all melee skills)       importance=0.01110
26) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00764
27) f36 (pattern: gain # mana per enemy killed)        importance=0.00532
28) f7 (pattern: # to maximum energy shield)           importance=0.00480
29) f17 (pattern: #% increased evasion and energy shield) importance=0.00456
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00220
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
