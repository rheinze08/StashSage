=== gloves seg='ar_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: 0.0596
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
 1) f29 (pattern: adds # to # physical damage to attacks) importance=0.10337
 2) f26 (pattern: adds # to # cold damage to attacks)  importance=0.08625
 3) f6 (pattern: # to level of all melee skills)       importance=0.07346
 4) f15 (pattern: #% increased critical damage bonus)  importance=0.06884
 5) f27 (pattern: adds # to # fire damage to attacks)  importance=0.06097
 6) f28 (pattern: adds # to # lightning damage to attacks) importance=0.05779
 7) f19 (pattern: #% increased rarity of items found)  importance=0.05023
 8) f22 (pattern: #% to chaos resistance)              importance=0.04911
 9) f8 (pattern: # to maximum life)                    importance=0.04863
10) f24 (pattern: #% to fire resistance)               importance=0.04753
11) f3 (pattern: # to dexterity)                       importance=0.04592
12) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03743
13) f1 (pattern: # to accuracy rating)                 importance=0.03411
14) f25 (pattern: #% to lightning resistance)          importance=0.03362
15) f9 (pattern: # to maximum mana)                    importance=0.02906
16) f11 (pattern: #% increased armour)                 importance=0.02231
17) f23 (pattern: #% to cold resistance)               importance=0.02108
18) f30 (pattern: break #% increased armour)           importance=0.01955
19) f10 (pattern: # to strength)                       importance=0.01670
20) Quality (pattern: Quality)                         importance=0.01535
21) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01315
22) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01106
23) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01046
24) f14 (pattern: #% increased attack speed)           importance=0.01035
25) f35 (pattern: gain # life per enemy killed)        importance=0.01030
26) f36 (pattern: gain # mana per enemy killed)        importance=0.00867
27) f2 (pattern: # to armour)                          importance=0.00652
28) f37 (pattern: leech #% of physical attack damage as life) importance=0.00621
29) f21 (pattern: #% reduced attribute requirements)   importance=0.00195
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
