=== gloves seg='ev_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0610
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f6 (pattern: # to level of all melee skills)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f18 (pattern: #% increased evasion rating)
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
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f26 (pattern: adds # to # cold damage to attacks)  importance=0.10817
 2) f4 (pattern: # to evasion rating)                  importance=0.06182
 3) f22 (pattern: #% to chaos resistance)              importance=0.05565
 4) Quality (pattern: Quality)                         importance=0.05545
 5) f28 (pattern: adds # to # lightning damage to attacks) importance=0.05395
 6) f19 (pattern: #% increased rarity of items found)  importance=0.05268
 7) f36 (pattern: gain # mana per enemy killed)        importance=0.05250
 8) f37 (pattern: leech #% of physical attack damage as life) importance=0.04959
 9) f8 (pattern: # to maximum life)                    importance=0.04752
10) f29 (pattern: adds # to # physical damage to attacks) importance=0.04653
11) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.04548
12) f18 (pattern: #% increased evasion rating)         importance=0.03661
13) f23 (pattern: #% to cold resistance)               importance=0.03501
14) f25 (pattern: #% to lightning resistance)          importance=0.03276
15) f24 (pattern: #% to fire resistance)               importance=0.03247
16) f1 (pattern: # to accuracy rating)                 importance=0.02722
17) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02686
18) f9 (pattern: # to maximum mana)                    importance=0.02583
19) f3 (pattern: # to dexterity)                       importance=0.02550
20) f15 (pattern: #% increased critical damage bonus)  importance=0.02545
21) f35 (pattern: gain # life per enemy killed)        importance=0.02425
22) f38 (pattern: leech #% of physical attack damage as mana) importance=0.02383
23) f6 (pattern: # to level of all melee skills)       importance=0.01999
24) f21 (pattern: #% reduced attribute requirements)   importance=0.01789
25) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01042
26) f14 (pattern: #% increased attack speed)           importance=0.00654
27) f30 (pattern: break #% increased armour)           importance=0.00000
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00000
30) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
