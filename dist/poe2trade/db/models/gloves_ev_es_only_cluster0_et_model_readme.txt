=== gloves seg='ev_es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: -0.2635
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.09213
 2) f8 (pattern: # to maximum life)                    importance=0.09009
 3) f3 (pattern: # to dexterity)                       importance=0.08296
 4) f22 (pattern: #% to chaos resistance)              importance=0.07004
 5) f17 (pattern: #% increased evasion and energy shield) importance=0.06300
 6) f25 (pattern: #% to lightning resistance)          importance=0.06037
 7) f24 (pattern: #% to fire resistance)               importance=0.05947
 8) f36 (pattern: gain # mana per enemy killed)        importance=0.04672
 9) f4 (pattern: # to evasion rating)                  importance=0.04387
10) f23 (pattern: #% to cold resistance)               importance=0.04333
11) f28 (pattern: adds # to # lightning damage to attacks) importance=0.04171
12) f7 (pattern: # to maximum energy shield)           importance=0.02669
13) f35 (pattern: gain # life per enemy killed)        importance=0.02579
14) f5 (pattern: # to intelligence)                    importance=0.02440
15) f6 (pattern: # to level of all melee skills)       importance=0.02395
16) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02266
17) f29 (pattern: adds # to # physical damage to attacks) importance=0.02158
18) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02087
19) f37 (pattern: leech #% of physical attack damage as life) importance=0.01912
20) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01882
21) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01759
22) f15 (pattern: #% increased critical damage bonus)  importance=0.01714
23) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01522
24) f9 (pattern: # to maximum mana)                    importance=0.01132
25) f19 (pattern: #% increased rarity of items found)  importance=0.01098
26) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.01041
27) f14 (pattern: #% increased attack speed)           importance=0.00967
28) f21 (pattern: #% reduced attribute requirements)   importance=0.00664
29) Quality (pattern: Quality)                         importance=0.00344
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
