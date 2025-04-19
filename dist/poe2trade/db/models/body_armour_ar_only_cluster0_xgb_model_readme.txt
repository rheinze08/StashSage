=== body_armour seg='ar_only' cluster=0 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0410
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
 1) Deflated_Armour (pattern: Deflated_Armour)         importance=0.07681
 2) f29 (pattern: #% reduced ignite duration on you)   importance=0.06543
 3) Quality (pattern: Quality)                         importance=0.05614
 4) f9 (pattern: # to spirit)                          importance=0.05518
 5) f30 (pattern: #% reduced poison duration on you)   importance=0.05062
 6) f33 (pattern: #% to chaos resistance)              importance=0.05004
 7) f1 (pattern: # life regeneration per second)       importance=0.04947
 8) f35 (pattern: #% to fire resistance)               importance=0.04880
 9) f14 (pattern: #% increased armour)                 importance=0.04716
10) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.04626
11) f28 (pattern: #% reduced bleeding duration on you) importance=0.04442
12) f8 (pattern: # to maximum life)                    importance=0.04027
13) f23 (pattern: #% increased stun threshold)         importance=0.04027
14) extra_socket_mod (pattern: extra_socket_mod)       importance=0.03979
15) f36 (pattern: #% to lightning resistance)          importance=0.03918
16) f27 (pattern: #% reduced attribute requirements)   importance=0.03844
17) f2 (pattern: # to # physical thorns damage)        importance=0.03727
18) f3 (pattern: # to armour)                          importance=0.03641
19) f38 (pattern: regenerate #% of maximum life per second) importance=0.03589
20) f10 (pattern: # to strength)                       importance=0.03580
21) f34 (pattern: #% to cold resistance)               importance=0.03526
22) f11 (pattern: # to stun threshold)                 importance=0.03109
23) f37 (pattern: allocates adverse growth)            importance=0.00000
24) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
25) f12 (pattern: #% additional physical damage reduction) importance=0.00000
26) f24 (pattern: #% increased thorns damage)          importance=0.00000
27) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
