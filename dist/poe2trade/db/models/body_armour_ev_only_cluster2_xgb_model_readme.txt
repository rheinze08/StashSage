=== body_armour seg='ev_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: 0.0960
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
 1) Quality (pattern: Quality)                         importance=0.10638
 2) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.07327
 3) f36 (pattern: #% to lightning resistance)          importance=0.06634
 4) f34 (pattern: #% to cold resistance)               importance=0.05964
 5) f33 (pattern: #% to chaos resistance)              importance=0.05487
 6) f35 (pattern: #% to fire resistance)               importance=0.05431
 7) f1 (pattern: # life regeneration per second)       importance=0.05118
 8) f20 (pattern: #% increased evasion rating)         importance=0.04680
 9) f2 (pattern: # to # physical thorns damage)        importance=0.04528
10) f9 (pattern: # to spirit)                          importance=0.04450
11) f5 (pattern: # to evasion rating)                  importance=0.04253
12) f28 (pattern: #% reduced bleeding duration on you) importance=0.03872
13) f8 (pattern: # to maximum life)                    importance=0.03712
14) f31 (pattern: #% reduced slowing potency of debuffs on you) importance=0.03637
15) f27 (pattern: #% reduced attribute requirements)   importance=0.03560
16) f29 (pattern: #% reduced ignite duration on you)   importance=0.03407
17) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.03313
18) f11 (pattern: # to stun threshold)                 importance=0.03048
19) f4 (pattern: # to dexterity)                       importance=0.02930
20) f17 (pattern: #% increased elemental ailment threshold) importance=0.02919
21) extra_socket_mod (pattern: extra_socket_mod)       importance=0.02634
22) f30 (pattern: #% reduced poison duration on you)   importance=0.02457
23) f32 (pattern: #% to all maximum elemental resistances) importance=0.00000
24) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
26) f12 (pattern: #% additional physical damage reduction) importance=0.00000
27) f22 (pattern: #% increased rarity of items found)  importance=0.00000
28) f24 (pattern: #% increased thorns damage)          importance=0.00000
