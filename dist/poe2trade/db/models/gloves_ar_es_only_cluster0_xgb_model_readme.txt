=== gloves seg='ar_es_only' cluster=0 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0529
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
 1) f1 (pattern: # to accuracy rating)                 importance=0.06150
 2) Quality (pattern: Quality)                         importance=0.06005
 3) f8 (pattern: # to maximum life)                    importance=0.05863
 4) f15 (pattern: #% increased critical damage bonus)  importance=0.04933
 5) f24 (pattern: #% to fire resistance)               importance=0.04816
 6) f14 (pattern: #% increased attack speed)           importance=0.04790
 7) f23 (pattern: #% to cold resistance)               importance=0.04712
 8) f2 (pattern: # to armour)                          importance=0.04560
 9) f25 (pattern: #% to lightning resistance)          importance=0.04214
10) f28 (pattern: adds # to # lightning damage to attacks) importance=0.04204
11) f19 (pattern: #% increased rarity of items found)  importance=0.04091
12) f36 (pattern: gain # mana per enemy killed)        importance=0.04017
13) f38 (pattern: leech #% of physical attack damage as mana) importance=0.03906
14) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03679
15) f3 (pattern: # to dexterity)                       importance=0.03618
16) f12 (pattern: #% increased armour and energy shield) importance=0.03401
17) f10 (pattern: # to strength)                       importance=0.03317
18) f35 (pattern: gain # life per enemy killed)        importance=0.03218
19) f29 (pattern: adds # to # physical damage to attacks) importance=0.03211
20) f5 (pattern: # to intelligence)                    importance=0.03192
21) f9 (pattern: # to maximum mana)                    importance=0.03076
22) Deflated_Armour (pattern: Deflated_Armour)         importance=0.02742
23) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02617
24) f37 (pattern: leech #% of physical attack damage as life) importance=0.02409
25) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02233
26) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01026
27) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
28) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
29) f21 (pattern: #% reduced attribute requirements)   importance=0.00000
30) f22 (pattern: #% to chaos resistance)              importance=0.00000
31) f6 (pattern: # to level of all melee skills)       importance=0.00000
32) f7 (pattern: # to maximum energy shield)           importance=0.00000
