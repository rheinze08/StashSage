=== gloves seg='es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: -0.0489
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f3 (pattern: # to dexterity)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to level of all melee skills)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f16 (pattern: #% increased energy shield)
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
  f31 (pattern: damage penetrates #% cold resistance)
  f32 (pattern: damage penetrates #% fire resistance)
  f33 (pattern: damage penetrates #% lightning resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f24 (pattern: #% to fire resistance)               importance=0.21148
 2) f7 (pattern: # to maximum energy shield)           importance=0.11369
 3) f28 (pattern: adds # to # lightning damage to attacks) importance=0.07993
 4) f5 (pattern: # to intelligence)                    importance=0.07596
 5) Quality (pattern: Quality)                         importance=0.06345
 6) f16 (pattern: #% increased energy shield)          importance=0.06073
 7) f22 (pattern: #% to chaos resistance)              importance=0.03532
 8) f29 (pattern: adds # to # physical damage to attacks) importance=0.03379
 9) f1 (pattern: # to accuracy rating)                 importance=0.03337
10) f8 (pattern: # to maximum life)                    importance=0.03218
11) f35 (pattern: gain # life per enemy killed)        importance=0.02980
12) f23 (pattern: #% to cold resistance)               importance=0.02961
13) f25 (pattern: #% to lightning resistance)          importance=0.02723
14) f19 (pattern: #% increased rarity of items found)  importance=0.02591
15) f34 (pattern: gain # life per enemy hit with attacks) importance=0.02152
16) f3 (pattern: # to dexterity)                       importance=0.02028
17) f26 (pattern: adds # to # cold damage to attacks)  importance=0.01617
18) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01554
19) f27 (pattern: adds # to # fire damage to attacks)  importance=0.01545
20) f37 (pattern: leech #% of physical attack damage as life) importance=0.01159
21) f6 (pattern: # to level of all melee skills)       importance=0.00914
22) f14 (pattern: #% increased attack speed)           importance=0.00876
23) f38 (pattern: leech #% of physical attack damage as mana) importance=0.00857
24) f36 (pattern: gain # mana per enemy killed)        importance=0.00617
25) f9 (pattern: # to maximum mana)                    importance=0.00540
26) f15 (pattern: #% increased critical damage bonus)  importance=0.00417
27) f21 (pattern: #% reduced attribute requirements)   importance=0.00362
28) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00116
29) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
30) f33 (pattern: damage penetrates #% lightning resistance) importance=0.00000
31) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
32) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
