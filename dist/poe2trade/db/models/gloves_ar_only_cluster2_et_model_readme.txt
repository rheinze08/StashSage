=== gloves seg='ar_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: 0.0540
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f6 (pattern: # to level of all melee skills)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f10 (pattern: # to strength)
  f11 (pattern: #% increased armour)
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
  f30 (pattern: break #% increased armour)
  f32 (pattern: damage penetrates #% fire resistance)
  f33 (pattern: damage penetrates #% lightning resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f19 (pattern: #% increased rarity of items found)  importance=0.16878
 2) f10 (pattern: # to strength)                       importance=0.10287
 3) f8 (pattern: # to maximum life)                    importance=0.09121
 4) f11 (pattern: #% increased armour)                 importance=0.07487
 5) f24 (pattern: #% to fire resistance)               importance=0.06486
 6) f22 (pattern: #% to chaos resistance)              importance=0.06062
 7) f2 (pattern: # to armour)                          importance=0.05158
 8) f25 (pattern: #% to lightning resistance)          importance=0.04503
 9) f6 (pattern: # to level of all melee skills)       importance=0.03839
10) f15 (pattern: #% increased critical damage bonus)  importance=0.03741
11) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03533
12) f23 (pattern: #% to cold resistance)               importance=0.02794
13) Quality (pattern: Quality)                         importance=0.02616
14) f38 (pattern: leech #% of physical attack damage as mana) importance=0.02528
15) f14 (pattern: #% increased attack speed)           importance=0.02516
16) f9 (pattern: # to maximum mana)                    importance=0.02300
17) f29 (pattern: adds # to # physical damage to attacks) importance=0.02169
18) f36 (pattern: gain # mana per enemy killed)        importance=0.01726
19) f1 (pattern: # to accuracy rating)                 importance=0.01691
20) f37 (pattern: leech #% of physical attack damage as life) importance=0.01619
21) f28 (pattern: adds # to # lightning damage to attacks) importance=0.01223
22) f27 (pattern: adds # to # fire damage to attacks)  importance=0.00462
23) f3 (pattern: # to dexterity)                       importance=0.00365
24) f35 (pattern: gain # life per enemy killed)        importance=0.00320
25) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00228
26) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00157
27) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00148
28) f21 (pattern: #% reduced attribute requirements)   importance=0.00045
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
31) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
