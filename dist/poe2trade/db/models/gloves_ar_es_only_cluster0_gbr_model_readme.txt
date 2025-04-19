=== gloves seg='ar_es_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0511
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to level of all melee skills)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f10 (pattern: # to strength)
  f12 (pattern: #% increased armour and energy shield)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f19 (pattern: #% increased rarity of items found)
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
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f1 (pattern: # to accuracy rating)                 importance=0.21166
 2) f8 (pattern: # to maximum life)                    importance=0.16338
 3) Quality (pattern: Quality)                         importance=0.13251
 4) f15 (pattern: #% increased critical damage bonus)  importance=0.08577
 5) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04723
 6) Deflated_Armour (pattern: Deflated_Armour)         importance=0.04610
 7) f23 (pattern: #% to cold resistance)               importance=0.04489
 8) f24 (pattern: #% to fire resistance)               importance=0.04303
 9) f25 (pattern: #% to lightning resistance)          importance=0.03837
10) f12 (pattern: #% increased armour and energy shield) importance=0.03825
11) f38 (pattern: leech #% of physical attack damage as mana) importance=0.03565
12) f19 (pattern: #% increased rarity of items found)  importance=0.02452
13) f3 (pattern: # to dexterity)                       importance=0.01263
14) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01141
15) f2 (pattern: # to armour)                          importance=0.00963
16) f5 (pattern: # to intelligence)                    importance=0.00926
17) f9 (pattern: # to maximum mana)                    importance=0.00881
18) f29 (pattern: adds # to # physical damage to attacks) importance=0.00713
19) f14 (pattern: #% increased attack speed)           importance=0.00606
20) f7 (pattern: # to maximum energy shield)           importance=0.00603
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00591
22) f10 (pattern: # to strength)                       importance=0.00456
23) f37 (pattern: leech #% of physical attack damage as life) importance=0.00321
24) f36 (pattern: gain # mana per enemy killed)        importance=0.00145
25) f28 (pattern: adds # to # lightning damage to attacks) importance=0.00111
26) f22 (pattern: #% to chaos resistance)              importance=0.00086
27) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00052
28) f6 (pattern: # to level of all melee skills)       importance=0.00005
29) f35 (pattern: gain # life per enemy killed)        importance=0.00000
30) f21 (pattern: #% reduced attribute requirements)   importance=0.00000
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
