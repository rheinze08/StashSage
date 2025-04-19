=== gloves seg='ev_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: -0.0283
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
 1) f4 (pattern: # to evasion rating)                  importance=0.10574
 2) f28 (pattern: adds # to # lightning damage to attacks) importance=0.08959
 3) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.08255
 4) f36 (pattern: gain # mana per enemy killed)        importance=0.08007
 5) f22 (pattern: #% to chaos resistance)              importance=0.07252
 6) Quality (pattern: Quality)                         importance=0.07170
 7) f19 (pattern: #% increased rarity of items found)  importance=0.07091
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.07088
 9) f8 (pattern: # to maximum life)                    importance=0.05939
10) f18 (pattern: #% increased evasion rating)         importance=0.04974
11) f9 (pattern: # to maximum mana)                    importance=0.04469
12) f24 (pattern: #% to fire resistance)               importance=0.04372
13) f23 (pattern: #% to cold resistance)               importance=0.02111
14) f25 (pattern: #% to lightning resistance)          importance=0.01856
15) f3 (pattern: # to dexterity)                       importance=0.01781
16) f21 (pattern: #% reduced attribute requirements)   importance=0.01760
17) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01649
18) f1 (pattern: # to accuracy rating)                 importance=0.01336
19) f15 (pattern: #% increased critical damage bonus)  importance=0.01305
20) f37 (pattern: leech #% of physical attack damage as life) importance=0.01081
21) f27 (pattern: adds # to # fire damage to attacks)  importance=0.00804
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00569
23) f35 (pattern: gain # life per enemy killed)        importance=0.00568
24) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00407
25) f26 (pattern: adds # to # cold damage to attacks)  importance=0.00388
26) f6 (pattern: # to level of all melee skills)       importance=0.00137
27) f14 (pattern: #% increased attack speed)           importance=0.00099
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f30 (pattern: break #% increased armour)           importance=0.00000
30) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
