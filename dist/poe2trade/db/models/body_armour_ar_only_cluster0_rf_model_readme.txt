=== body_armour seg='ar_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: -0.0601
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
 1) Deflated_Armour (pattern: Deflated_Armour)         importance=0.22902
 2) f14 (pattern: #% increased armour)                 importance=0.12943
 3) f35 (pattern: #% to fire resistance)               importance=0.09506
 4) f3 (pattern: # to armour)                          importance=0.08224
 5) f8 (pattern: # to maximum life)                    importance=0.05821
 6) f33 (pattern: #% to chaos resistance)              importance=0.05350
 7) f1 (pattern: # life regeneration per second)       importance=0.05253
 8) f10 (pattern: # to strength)                       importance=0.05181
 9) f34 (pattern: #% to cold resistance)               importance=0.04431
10) f36 (pattern: #% to lightning resistance)          importance=0.03474
11) f9 (pattern: # to spirit)                          importance=0.02638
12) Quality (pattern: Quality)                         importance=0.02551
13) f27 (pattern: #% reduced attribute requirements)   importance=0.02348
14) f11 (pattern: # to stun threshold)                 importance=0.01943
15) f28 (pattern: #% reduced bleeding duration on you) importance=0.01802
16) f23 (pattern: #% increased stun threshold)         importance=0.01720
17) f2 (pattern: # to # physical thorns damage)        importance=0.01031
18) f38 (pattern: regenerate #% of maximum life per second) importance=0.00967
19) f29 (pattern: #% reduced ignite duration on you)   importance=0.00746
20) f30 (pattern: #% reduced poison duration on you)   importance=0.00654
21) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00304
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00211
23) f37 (pattern: allocates adverse growth)            importance=0.00000
24) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
25) f12 (pattern: #% additional physical damage reduction) importance=0.00000
26) f24 (pattern: #% increased thorns damage)          importance=0.00000
27) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
