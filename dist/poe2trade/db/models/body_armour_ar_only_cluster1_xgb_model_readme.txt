=== body_armour seg='ar_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0627
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
 1) Quality (pattern: Quality)                         importance=0.09339
 2) f26 (pattern: #% of damage taken recouped as mana) importance=0.05823
 3) f35 (pattern: #% to fire resistance)               importance=0.05540
 4) f9 (pattern: # to spirit)                          importance=0.05410
 5) f11 (pattern: # to stun threshold)                 importance=0.05153
 6) f30 (pattern: #% reduced poison duration on you)   importance=0.04905
 7) f29 (pattern: #% reduced ignite duration on you)   importance=0.04806
 8) f36 (pattern: #% to lightning resistance)          importance=0.04789
 9) f34 (pattern: #% to cold resistance)               importance=0.04617
10) f14 (pattern: #% increased armour)                 importance=0.04558
11) f3 (pattern: # to armour)                          importance=0.04490
12) f8 (pattern: # to maximum life)                    importance=0.04362
13) f33 (pattern: #% to chaos resistance)              importance=0.04287
14) f23 (pattern: #% increased stun threshold)         importance=0.04024
15) f2 (pattern: # to # physical thorns damage)        importance=0.03844
16) f1 (pattern: # life regeneration per second)       importance=0.03790
17) f28 (pattern: #% reduced bleeding duration on you) importance=0.03776
18) f27 (pattern: #% reduced attribute requirements)   importance=0.03677
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.03511
20) f10 (pattern: # to strength)                       importance=0.03248
21) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03190
22) f38 (pattern: regenerate #% of maximum life per second) importance=0.02860
23) f37 (pattern: allocates adverse growth)            importance=0.00000
24) f12 (pattern: #% additional physical damage reduction) importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
26) f24 (pattern: #% increased thorns damage)          importance=0.00000
27) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00000
