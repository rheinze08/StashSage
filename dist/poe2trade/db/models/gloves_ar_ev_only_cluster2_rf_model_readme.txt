=== gloves seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.0449
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
 1) f8 (pattern: # to maximum life)                    importance=0.13525
 2) f22 (pattern: #% to chaos resistance)              importance=0.10086
 3) f25 (pattern: #% to lightning resistance)          importance=0.08226
 4) Quality (pattern: Quality)                         importance=0.06090
 5) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05986
 6) f3 (pattern: # to dexterity)                       importance=0.05313
 7) f21 (pattern: #% reduced attribute requirements)   importance=0.05112
 8) f24 (pattern: #% to fire resistance)               importance=0.05088
 9) f14 (pattern: #% increased attack speed)           importance=0.04397
10) f9 (pattern: # to maximum mana)                    importance=0.04244
11) f29 (pattern: adds # to # physical damage to attacks) importance=0.04032
12) f6 (pattern: # to level of all melee skills)       importance=0.03617
13) f23 (pattern: #% to cold resistance)               importance=0.03174
14) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02533
15) Deflated_Armour (pattern: Deflated_Armour)         importance=0.02186
16) f1 (pattern: # to accuracy rating)                 importance=0.02014
17) f35 (pattern: gain # life per enemy killed)        importance=0.02006
18) f36 (pattern: gain # mana per enemy killed)        importance=0.01994
19) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01788
20) f26 (pattern: adds # to # cold damage to attacks)  importance=0.01746
21) f15 (pattern: #% increased critical damage bonus)  importance=0.01566
22) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01440
23) f10 (pattern: # to strength)                       importance=0.00986
24) f13 (pattern: #% increased armour and evasion)     importance=0.00805
25) f19 (pattern: #% increased rarity of items found)  importance=0.00755
26) f37 (pattern: leech #% of physical attack damage as life) importance=0.00442
27) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00387
28) f4 (pattern: # to evasion rating)                  importance=0.00335
29) f2 (pattern: # to armour)                          importance=0.00117
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00008
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f30 (pattern: break #% increased armour)           importance=0.00000
