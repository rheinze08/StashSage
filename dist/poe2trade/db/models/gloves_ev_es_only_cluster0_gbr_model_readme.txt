=== gloves seg='ev_es_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0162
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
 1) f8 (pattern: # to maximum life)                    importance=0.16661
 2) f17 (pattern: #% increased evasion and energy shield) importance=0.13232
 3) f1 (pattern: # to accuracy rating)                 importance=0.09760
 4) f25 (pattern: #% to lightning resistance)          importance=0.08257
 5) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.08051
 6) f24 (pattern: #% to fire resistance)               importance=0.07305
 7) f22 (pattern: #% to chaos resistance)              importance=0.05819
 8) f3 (pattern: # to dexterity)                       importance=0.05548
 9) f4 (pattern: # to evasion rating)                  importance=0.04028
10) f15 (pattern: #% increased critical damage bonus)  importance=0.03518
11) f23 (pattern: #% to cold resistance)               importance=0.03342
12) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.02366
13) f7 (pattern: # to maximum energy shield)           importance=0.02267
14) f28 (pattern: adds # to # lightning damage to attacks) importance=0.01600
15) f5 (pattern: # to intelligence)                    importance=0.01520
16) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01276
17) f29 (pattern: adds # to # physical damage to attacks) importance=0.01188
18) f9 (pattern: # to maximum mana)                    importance=0.00890
19) f36 (pattern: gain # mana per enemy killed)        importance=0.00878
20) f35 (pattern: gain # life per enemy killed)        importance=0.00724
21) f19 (pattern: #% increased rarity of items found)  importance=0.00518
22) f37 (pattern: leech #% of physical attack damage as life) importance=0.00445
23) f21 (pattern: #% reduced attribute requirements)   importance=0.00204
24) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00176
25) f6 (pattern: # to level of all melee skills)       importance=0.00126
26) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00118
27) Quality (pattern: Quality)                         importance=0.00107
28) f14 (pattern: #% increased attack speed)           importance=0.00074
29) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
30) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
31) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
32) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
