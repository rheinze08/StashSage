=== body_armour seg='ar_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.0717
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
 1) Deflated_Armour (pattern: Deflated_Armour)         importance=0.11239
 2) f8 (pattern: # to maximum life)                    importance=0.09385
 3) f14 (pattern: #% increased armour)                 importance=0.08984
 4) f35 (pattern: #% to fire resistance)               importance=0.08454
 5) f3 (pattern: # to armour)                          importance=0.07945
 6) f9 (pattern: # to spirit)                          importance=0.06932
 7) f34 (pattern: #% to cold resistance)               importance=0.06755
 8) Quality (pattern: Quality)                         importance=0.06481
 9) f36 (pattern: #% to lightning resistance)          importance=0.05712
10) f11 (pattern: # to stun threshold)                 importance=0.04038
11) f1 (pattern: # life regeneration per second)       importance=0.04020
12) f2 (pattern: # to # physical thorns damage)        importance=0.03062
13) f33 (pattern: #% to chaos resistance)              importance=0.03059
14) f10 (pattern: # to strength)                       importance=0.02879
15) f23 (pattern: #% increased stun threshold)         importance=0.02541
16) f38 (pattern: regenerate #% of maximum life per second) importance=0.02194
17) f30 (pattern: #% reduced poison duration on you)   importance=0.02055
18) f29 (pattern: #% reduced ignite duration on you)   importance=0.01973
19) f27 (pattern: #% reduced attribute requirements)   importance=0.01090
20) f28 (pattern: #% reduced bleeding duration on you) importance=0.00946
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00254
22) f26 (pattern: #% of damage taken recouped as mana) importance=0.00003
23) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
24) f37 (pattern: allocates adverse growth)            importance=0.00000
25) f24 (pattern: #% increased thorns damage)          importance=0.00000
26) f12 (pattern: #% additional physical damage reduction) importance=0.00000
27) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00000
