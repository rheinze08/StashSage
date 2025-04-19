=== gloves seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0064
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
 1) Quality (pattern: Quality)                         importance=0.05549
 2) f8 (pattern: # to maximum life)                    importance=0.05171
 3) f22 (pattern: #% to chaos resistance)              importance=0.05060
 4) f21 (pattern: #% reduced attribute requirements)   importance=0.04765
 5) f25 (pattern: #% to lightning resistance)          importance=0.04531
 6) f14 (pattern: #% increased attack speed)           importance=0.04353
 7) f3 (pattern: # to dexterity)                       importance=0.04254
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.03954
 9) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03907
10) f13 (pattern: #% increased armour and evasion)     importance=0.03790
11) f4 (pattern: # to evasion rating)                  importance=0.03599
12) f37 (pattern: leech #% of physical attack damage as life) importance=0.03561
13) f6 (pattern: # to level of all melee skills)       importance=0.03473
14) f9 (pattern: # to maximum mana)                    importance=0.03306
15) f36 (pattern: gain # mana per enemy killed)        importance=0.03289
16) f34 (pattern: gain # life per enemy hit with attacks) importance=0.03169
17) f26 (pattern: adds # to # cold damage to attacks)  importance=0.03055
18) f23 (pattern: #% to cold resistance)               importance=0.03050
19) f35 (pattern: gain # life per enemy killed)        importance=0.03033
20) f24 (pattern: #% to fire resistance)               importance=0.02924
21) f15 (pattern: #% increased critical damage bonus)  importance=0.02781
22) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02746
23) f10 (pattern: # to strength)                       importance=0.02663
24) f27 (pattern: adds # to # fire damage to attacks)  importance=0.02581
25) f2 (pattern: # to armour)                          importance=0.02441
26) f1 (pattern: # to accuracy rating)                 importance=0.02245
27) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01909
28) Deflated_Armour (pattern: Deflated_Armour)         importance=0.01834
29) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01673
30) f19 (pattern: #% increased rarity of items found)  importance=0.01334
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f30 (pattern: break #% increased armour)           importance=0.00000
