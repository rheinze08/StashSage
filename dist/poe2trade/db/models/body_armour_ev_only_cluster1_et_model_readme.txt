=== body_armour seg='ev_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: 0.1199
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
 1) Quality (pattern: Quality)                         importance=0.26233
 2) f9 (pattern: # to spirit)                          importance=0.13118
 3) f35 (pattern: #% to fire resistance)               importance=0.10301
 4) f34 (pattern: #% to cold resistance)               importance=0.08268
 5) f20 (pattern: #% increased evasion rating)         importance=0.07852
 6) f36 (pattern: #% to lightning resistance)          importance=0.05503
 7) f33 (pattern: #% to chaos resistance)              importance=0.04926
 8) f5 (pattern: # to evasion rating)                  importance=0.02760
 9) f2 (pattern: # to # physical thorns damage)        importance=0.02497
10) f8 (pattern: # to maximum life)                    importance=0.02317
11) extra_socket_mod (pattern: extra_socket_mod)       importance=0.02276
12) f11 (pattern: # to stun threshold)                 importance=0.02246
13) f4 (pattern: # to dexterity)                       importance=0.02205
14) f28 (pattern: #% reduced bleeding duration on you) importance=0.01794
15) f1 (pattern: # life regeneration per second)       importance=0.01512
16) f31 (pattern: #% reduced slowing potency of debuffs on you) importance=0.01425
17) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.01189
18) f17 (pattern: #% increased elemental ailment threshold) importance=0.01036
19) f27 (pattern: #% reduced attribute requirements)   importance=0.00841
20) f30 (pattern: #% reduced poison duration on you)   importance=0.00711
21) f29 (pattern: #% reduced ignite duration on you)   importance=0.00533
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00365
23) f24 (pattern: #% increased thorns damage)          importance=0.00095
24) f32 (pattern: #% to all maximum elemental resistances) importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
26) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
27) f12 (pattern: #% additional physical damage reduction) importance=0.00000
28) f22 (pattern: #% increased rarity of items found)  importance=0.00000
