=== gloves seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: -0.0977
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f6 (pattern: # to level of all melee skills)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f10 (pattern: # to strength)
  f13 (pattern: #% increased armour and evasion)
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
  f31 (pattern: damage penetrates #% cold resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f22 (pattern: #% to chaos resistance)              importance=0.12278
 2) f14 (pattern: #% increased attack speed)           importance=0.09608
 3) Quality (pattern: Quality)                         importance=0.09059
 4) f25 (pattern: #% to lightning resistance)          importance=0.07820
 5) f8 (pattern: # to maximum life)                    importance=0.07817
 6) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.07306
 7) f3 (pattern: # to dexterity)                       importance=0.07141
 8) f21 (pattern: #% reduced attribute requirements)   importance=0.05072
 9) f6 (pattern: # to level of all melee skills)       importance=0.05003
10) f29 (pattern: adds # to # physical damage to attacks) importance=0.03548
11) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02484
12) f38 (pattern: leech #% of physical attack damage as mana) importance=0.02389
13) f26 (pattern: adds # to # cold damage to attacks)  importance=0.02323
14) f10 (pattern: # to strength)                       importance=0.01933
15) f1 (pattern: # to accuracy rating)                 importance=0.01654
16) f36 (pattern: gain # mana per enemy killed)        importance=0.01462
17) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01456
18) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01398
19) f23 (pattern: #% to cold resistance)               importance=0.01310
20) f9 (pattern: # to maximum mana)                    importance=0.01226
21) f24 (pattern: #% to fire resistance)               importance=0.01213
22) f35 (pattern: gain # life per enemy killed)        importance=0.01104
23) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01056
24) f4 (pattern: # to evasion rating)                  importance=0.00878
25) f15 (pattern: #% increased critical damage bonus)  importance=0.00843
26) f37 (pattern: leech #% of physical attack damage as life) importance=0.00664
27) f13 (pattern: #% increased armour and evasion)     importance=0.00633
28) f2 (pattern: # to armour)                          importance=0.00616
29) f19 (pattern: #% increased rarity of items found)  importance=0.00524
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00182
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f30 (pattern: break #% increased armour)           importance=0.00000
