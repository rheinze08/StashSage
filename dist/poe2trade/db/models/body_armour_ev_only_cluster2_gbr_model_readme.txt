=== body_armour seg='ev_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0617
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  extra_socket_mod (pattern: extra_socket_mod)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to # physical thorns damage)
  f4 (pattern: # to dexterity)
  f5 (pattern: # to evasion rating)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to spirit)
  f11 (pattern: # to stun threshold)
  f12 (pattern: #% additional physical damage reduction)
  f17 (pattern: #% increased elemental ailment threshold)
  f20 (pattern: #% increased evasion rating)
  f22 (pattern: #% increased rarity of items found)
  f24 (pattern: #% increased thorns damage)
  f25 (pattern: #% of damage taken recouped as life)
  f26 (pattern: #% of damage taken recouped as mana)
  f27 (pattern: #% reduced attribute requirements)
  f28 (pattern: #% reduced bleeding duration on you)
  f29 (pattern: #% reduced ignite duration on you)
  f30 (pattern: #% reduced poison duration on you)
  f31 (pattern: #% reduced slowing potency of debuffs on you)
  f32 (pattern: #% to all maximum elemental resistances)
  f33 (pattern: #% to chaos resistance)
  f34 (pattern: #% to cold resistance)
  f35 (pattern: #% to fire resistance)
  f36 (pattern: #% to lightning resistance)

Feature Importances:
 1) f36 (pattern: #% to lightning resistance)          importance=0.12417
 2) f20 (pattern: #% increased evasion rating)         importance=0.10851
 3) f34 (pattern: #% to cold resistance)               importance=0.10594
 4) Quality (pattern: Quality)                         importance=0.10430
 5) f35 (pattern: #% to fire resistance)               importance=0.08515
 6) f33 (pattern: #% to chaos resistance)              importance=0.08364
 7) f5 (pattern: # to evasion rating)                  importance=0.08193
 8) f9 (pattern: # to spirit)                          importance=0.06296
 9) f8 (pattern: # to maximum life)                    importance=0.06243
10) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03854
11) f31 (pattern: #% reduced slowing potency of debuffs on you) importance=0.02620
12) f28 (pattern: #% reduced bleeding duration on you) importance=0.02232
13) f1 (pattern: # life regeneration per second)       importance=0.02151
14) f2 (pattern: # to # physical thorns damage)        importance=0.02086
15) f4 (pattern: # to dexterity)                       importance=0.01217
16) f11 (pattern: # to stun threshold)                 importance=0.00969
17) f30 (pattern: #% reduced poison duration on you)   importance=0.00947
18) f17 (pattern: #% increased elemental ailment threshold) importance=0.00615
19) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00506
20) f29 (pattern: #% reduced ignite duration on you)   importance=0.00426
21) f27 (pattern: #% reduced attribute requirements)   importance=0.00276
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00197
23) f32 (pattern: #% to all maximum elemental resistances) importance=0.00000
24) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
26) f12 (pattern: #% additional physical damage reduction) importance=0.00000
27) f22 (pattern: #% increased rarity of items found)  importance=0.00000
28) f24 (pattern: #% increased thorns damage)          importance=0.00000
