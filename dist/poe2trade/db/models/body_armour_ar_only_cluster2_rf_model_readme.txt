=== body_armour seg='ar_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: -0.1480
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  extra_socket_mod (pattern: extra_socket_mod)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to # physical thorns damage)
  f3 (pattern: # to armour)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to spirit)
  f10 (pattern: # to strength)
  f11 (pattern: # to stun threshold)
  f12 (pattern: #% additional physical damage reduction)
  f14 (pattern: #% increased armour)
  f23 (pattern: #% increased stun threshold)
  f24 (pattern: #% increased thorns damage)
  f25 (pattern: #% of damage taken recouped as life)
  f26 (pattern: #% of damage taken recouped as mana)
  f27 (pattern: #% reduced attribute requirements)
  f28 (pattern: #% reduced bleeding duration on you)
  f29 (pattern: #% reduced ignite duration on you)
  f30 (pattern: #% reduced poison duration on you)
  f33 (pattern: #% to chaos resistance)
  f34 (pattern: #% to cold resistance)
  f35 (pattern: #% to fire resistance)
  f36 (pattern: #% to lightning resistance)
  f37 (pattern: allocates adverse growth)
  f38 (pattern: regenerate #% of maximum life per second)

Feature Importances:
 1) Quality (pattern: Quality)                         importance=0.13083
 2) f8 (pattern: # to maximum life)                    importance=0.11205
 3) f35 (pattern: #% to fire resistance)               importance=0.10132
 4) f3 (pattern: # to armour)                          importance=0.09772
 5) f36 (pattern: #% to lightning resistance)          importance=0.07395
 6) Deflated_Armour (pattern: Deflated_Armour)         importance=0.07392
 7) f14 (pattern: #% increased armour)                 importance=0.06761
 8) f9 (pattern: # to spirit)                          importance=0.06273
 9) f11 (pattern: # to stun threshold)                 importance=0.04511
10) f33 (pattern: #% to chaos resistance)              importance=0.04059
11) f34 (pattern: #% to cold resistance)               importance=0.03913
12) f1 (pattern: # life regeneration per second)       importance=0.02655
13) f27 (pattern: #% reduced attribute requirements)   importance=0.02346
14) f10 (pattern: # to strength)                       importance=0.02194
15) f38 (pattern: regenerate #% of maximum life per second) importance=0.02079
16) f2 (pattern: # to # physical thorns damage)        importance=0.01421
17) f28 (pattern: #% reduced bleeding duration on you) importance=0.01256
18) f23 (pattern: #% increased stun threshold)         importance=0.01086
19) f29 (pattern: #% reduced ignite duration on you)   importance=0.01081
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00964
21) f30 (pattern: #% reduced poison duration on you)   importance=0.00260
22) f12 (pattern: #% additional physical damage reduction) importance=0.00086
23) f37 (pattern: allocates adverse growth)            importance=0.00035
24) f26 (pattern: #% of damage taken recouped as mana) importance=0.00027
25) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00015
26) f24 (pattern: #% increased thorns damage)          importance=0.00000
27) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
