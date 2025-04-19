=== gloves seg='ar_es_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: -0.0181
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
 1) f8 (pattern: # to maximum life)                    importance=0.15692
 2) f1 (pattern: # to accuracy rating)                 importance=0.13881
 3) f27 (pattern: adds # to # fire damage to attacks)  importance=0.09366
 4) f22 (pattern: #% to chaos resistance)              importance=0.05384
 5) f3 (pattern: # to dexterity)                       importance=0.05368
 6) f25 (pattern: #% to lightning resistance)          importance=0.04650
 7) f24 (pattern: #% to fire resistance)               importance=0.04539
 8) f38 (pattern: leech #% of physical attack damage as mana) importance=0.04270
 9) f29 (pattern: adds # to # physical damage to attacks) importance=0.04225
10) f10 (pattern: # to strength)                       importance=0.03271
11) f23 (pattern: #% to cold resistance)               importance=0.03171
12) f9 (pattern: # to maximum mana)                    importance=0.03076
13) f14 (pattern: #% increased attack speed)           importance=0.02932
14) f5 (pattern: # to intelligence)                    importance=0.02667
15) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02631
16) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02540
17) f19 (pattern: #% increased rarity of items found)  importance=0.01714
18) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01441
19) f15 (pattern: #% increased critical damage bonus)  importance=0.01366
20) f36 (pattern: gain # mana per enemy killed)        importance=0.01320
21) f35 (pattern: gain # life per enemy killed)        importance=0.01259
22) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01056
23) f2 (pattern: # to armour)                          importance=0.00983
24) f7 (pattern: # to maximum energy shield)           importance=0.00978
25) Quality (pattern: Quality)                         importance=0.00677
26) Deflated_Armour (pattern: Deflated_Armour)         importance=0.00470
27) f12 (pattern: #% increased armour and energy shield) importance=0.00333
28) f37 (pattern: leech #% of physical attack damage as life) importance=0.00320
29) f21 (pattern: #% reduced attribute requirements)   importance=0.00257
30) f6 (pattern: # to level of all melee skills)       importance=0.00159
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00005
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
