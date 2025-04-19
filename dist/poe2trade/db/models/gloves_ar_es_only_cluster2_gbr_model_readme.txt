=== gloves seg='ar_es_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: -0.0783
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
 1) Deflated_Armour (pattern: Deflated_Armour)         importance=0.16904
 2) f12 (pattern: #% increased armour and energy shield) importance=0.15003
 3) f10 (pattern: # to strength)                       importance=0.14771
 4) f5 (pattern: # to intelligence)                    importance=0.13098
 5) f15 (pattern: #% increased critical damage bonus)  importance=0.11127
 6) f28 (pattern: adds # to # lightning damage to attacks) importance=0.10369
 7) f23 (pattern: #% to cold resistance)               importance=0.07428
 8) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02509
 9) f9 (pattern: # to maximum mana)                    importance=0.02393
10) f8 (pattern: # to maximum life)                    importance=0.02320
11) f24 (pattern: #% to fire resistance)               importance=0.01957
12) f3 (pattern: # to dexterity)                       importance=0.00601
13) f27 (pattern: adds # to # fire damage to attacks)  importance=0.00457
14) f1 (pattern: # to accuracy rating)                 importance=0.00373
15) f19 (pattern: #% increased rarity of items found)  importance=0.00311
16) f14 (pattern: #% increased attack speed)           importance=0.00295
17) f29 (pattern: adds # to # physical damage to attacks) importance=0.00083
18) f35 (pattern: gain # life per enemy killed)        importance=0.00002
19) f25 (pattern: #% to lightning resistance)          importance=0.00000
20) Quality (pattern: Quality)                         importance=0.00000
21) f36 (pattern: gain # mana per enemy killed)        importance=0.00000
22) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00000
23) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00000
24) f37 (pattern: leech #% of physical attack damage as life) importance=0.00000
25) f21 (pattern: #% reduced attribute requirements)   importance=0.00000
26) f22 (pattern: #% to chaos resistance)              importance=0.00000
27) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
28) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
29) f6 (pattern: # to level of all melee skills)       importance=0.00000
30) f7 (pattern: # to maximum energy shield)           importance=0.00000
31) f2 (pattern: # to armour)                          importance=0.00000
32) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
