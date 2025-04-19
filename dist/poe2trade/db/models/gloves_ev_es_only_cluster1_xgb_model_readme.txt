=== gloves seg='ev_es_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0116
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
 1) f22 (pattern: #% to chaos resistance)              importance=0.05964
 2) f24 (pattern: #% to fire resistance)               importance=0.05761
 3) f29 (pattern: adds # to # physical damage to attacks) importance=0.05364
 4) f4 (pattern: # to evasion rating)                  importance=0.04865
 5) f14 (pattern: #% increased attack speed)           importance=0.04256
 6) f7 (pattern: # to maximum energy shield)           importance=0.04007
 7) f36 (pattern: gain # mana per enemy killed)        importance=0.03824
 8) f15 (pattern: #% increased critical damage bonus)  importance=0.03675
 9) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03544
10) f3 (pattern: # to dexterity)                       importance=0.03520
11) f25 (pattern: #% to lightning resistance)          importance=0.03507
12) f37 (pattern: leech #% of physical attack damage as life) importance=0.03441
13) f23 (pattern: #% to cold resistance)               importance=0.03307
14) f9 (pattern: # to maximum mana)                    importance=0.03207
15) f26 (pattern: adds # to # cold damage to attacks)  importance=0.03152
16) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03124
17) f17 (pattern: #% increased evasion and energy shield) importance=0.03037
18) f8 (pattern: # to maximum life)                    importance=0.02975
19) f19 (pattern: #% increased rarity of items found)  importance=0.02927
20) f35 (pattern: gain # life per enemy killed)        importance=0.02870
21) f5 (pattern: # to intelligence)                    importance=0.02799
22) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02747
23) f38 (pattern: leech #% of physical attack damage as mana) importance=0.02726
24) f21 (pattern: #% reduced attribute requirements)   importance=0.02660
25) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.02335
26) Quality (pattern: Quality)                         importance=0.02326
27) f1 (pattern: # to accuracy rating)                 importance=0.02322
28) f6 (pattern: # to level of all melee skills)       importance=0.02282
29) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01833
30) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01645
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
