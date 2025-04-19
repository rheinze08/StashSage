=== gloves seg='ar_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.0547
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
 1) f29 (pattern: adds # to # physical damage to attacks) importance=0.11198
 2) f26 (pattern: adds # to # cold damage to attacks)  importance=0.08035
 3) f8 (pattern: # to maximum life)                    importance=0.06510
 4) f27 (pattern: adds # to # fire damage to attacks)  importance=0.06485
 5) f1 (pattern: # to accuracy rating)                 importance=0.05963
 6) f24 (pattern: #% to fire resistance)               importance=0.05505
 7) f3 (pattern: # to dexterity)                       importance=0.05017
 8) f15 (pattern: #% increased critical damage bonus)  importance=0.04633
 9) Deflated_Armour (pattern: Deflated_Armour)         importance=0.04500
10) f25 (pattern: #% to lightning resistance)          importance=0.04457
11) f22 (pattern: #% to chaos resistance)              importance=0.04410
12) f9 (pattern: # to maximum mana)                    importance=0.04271
13) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03800
14) f6 (pattern: # to level of all melee skills)       importance=0.03660
15) f19 (pattern: #% increased rarity of items found)  importance=0.03418
16) f23 (pattern: #% to cold resistance)               importance=0.03296
17) f11 (pattern: #% increased armour)                 importance=0.03181
18) f10 (pattern: # to strength)                       importance=0.03030
19) f38 (pattern: leech #% of physical attack damage as mana) importance=0.02103
20) f35 (pattern: gain # life per enemy killed)        importance=0.01415
21) Quality (pattern: Quality)                         importance=0.00916
22) f14 (pattern: #% increased attack speed)           importance=0.00873
23) f30 (pattern: break #% increased armour)           importance=0.00782
24) f37 (pattern: leech #% of physical attack damage as life) importance=0.00660
25) f36 (pattern: gain # mana per enemy killed)        importance=0.00587
26) f2 (pattern: # to armour)                          importance=0.00478
27) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00433
28) f21 (pattern: #% reduced attribute requirements)   importance=0.00200
29) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00185
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
