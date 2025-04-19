=== body_armour seg='ev_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: 0.1794
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
 1) f20 (pattern: #% increased evasion rating)         importance=0.14725
 2) f9 (pattern: # to spirit)                          importance=0.14292
 3) Quality (pattern: Quality)                         importance=0.12567
 4) f35 (pattern: #% to fire resistance)               importance=0.10301
 5) f34 (pattern: #% to cold resistance)               importance=0.07502
 6) f8 (pattern: # to maximum life)                    importance=0.06937
 7) f36 (pattern: #% to lightning resistance)          importance=0.06066
 8) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.04918
 9) f33 (pattern: #% to chaos resistance)              importance=0.03922
10) f5 (pattern: # to evasion rating)                  importance=0.03286
11) f1 (pattern: # life regeneration per second)       importance=0.02404
12) f2 (pattern: # to # physical thorns damage)        importance=0.02387
13) f11 (pattern: # to stun threshold)                 importance=0.01987
14) f4 (pattern: # to dexterity)                       importance=0.01501
15) f17 (pattern: #% increased elemental ailment threshold) importance=0.01454
16) f30 (pattern: #% reduced poison duration on you)   importance=0.01346
17) f28 (pattern: #% reduced bleeding duration on you) importance=0.01156
18) extra_socket_mod (pattern: extra_socket_mod)       importance=0.01147
19) f27 (pattern: #% reduced attribute requirements)   importance=0.00754
20) f29 (pattern: #% reduced ignite duration on you)   importance=0.00715
21) f31 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00506
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00092
23) f24 (pattern: #% increased thorns damage)          importance=0.00035
24) f32 (pattern: #% to all maximum elemental resistances) importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
26) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
27) f12 (pattern: #% additional physical damage reduction) importance=0.00000
28) f22 (pattern: #% increased rarity of items found)  importance=0.00000
