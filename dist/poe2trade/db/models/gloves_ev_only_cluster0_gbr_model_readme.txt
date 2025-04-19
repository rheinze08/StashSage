=== gloves seg='ev_only' cluster=0 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0665
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
 1) Quality (pattern: Quality)                         importance=0.12932
 2) f18 (pattern: #% increased evasion rating)         importance=0.12062
 3) f29 (pattern: adds # to # physical damage to attacks) importance=0.11072
 4) f21 (pattern: #% reduced attribute requirements)   importance=0.09507
 5) f15 (pattern: #% increased critical damage bonus)  importance=0.06034
 6) f25 (pattern: #% to lightning resistance)          importance=0.05724
 7) f4 (pattern: # to evasion rating)                  importance=0.05376
 8) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05367
 9) f1 (pattern: # to accuracy rating)                 importance=0.05363
10) f8 (pattern: # to maximum life)                    importance=0.05283
11) f24 (pattern: #% to fire resistance)               importance=0.03392
12) f37 (pattern: leech #% of physical attack damage as life) importance=0.03169
13) f9 (pattern: # to maximum mana)                    importance=0.02607
14) f28 (pattern: adds # to # lightning damage to attacks) importance=0.02425
15) f19 (pattern: #% increased rarity of items found)  importance=0.02244
16) f3 (pattern: # to dexterity)                       importance=0.02095
17) f26 (pattern: adds # to # cold damage to attacks)  importance=0.01785
18) f35 (pattern: gain # life per enemy killed)        importance=0.01590
19) f23 (pattern: #% to cold resistance)               importance=0.00818
20) f22 (pattern: #% to chaos resistance)              importance=0.00471
21) f27 (pattern: adds # to # fire damage to attacks)  importance=0.00406
22) f34 (pattern: gain # life per enemy hit with attacks) importance=0.00122
23) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00120
24) f6 (pattern: # to level of all melee skills)       importance=0.00036
25) f14 (pattern: #% increased attack speed)           importance=0.00003
26) f36 (pattern: gain # mana per enemy killed)        importance=0.00000
27) f30 (pattern: break #% increased armour)           importance=0.00000
28) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
29) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
30) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
