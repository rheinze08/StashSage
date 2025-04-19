=== body_armour seg='es_only' cluster=0 Model Readme ===

Model Type: RF
R^2 on test set: 0.0204
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  extra_socket_mod (pattern: extra_socket_mod)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to # physical thorns damage)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to spirit)
  f11 (pattern: # to stun threshold)
  f12 (pattern: #% additional physical damage reduction)
  f13 (pattern: #% faster start of energy shield recharge)
  f18 (pattern: #% increased energy shield)
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

Feature Importances:
 1) f9 (pattern: # to spirit)                          importance=0.11010
 2) f18 (pattern: #% increased energy shield)          importance=0.10197
 3) f34 (pattern: #% to cold resistance)               importance=0.09201
 4) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.09164
 5) f8 (pattern: # to maximum life)                    importance=0.08921
 6) f36 (pattern: #% to lightning resistance)          importance=0.08579
 7) f35 (pattern: #% to fire resistance)               importance=0.07735
 8) Quality (pattern: Quality)                         importance=0.07442
 9) f7 (pattern: # to maximum energy shield)           importance=0.05983
10) f13 (pattern: #% faster start of energy shield recharge) importance=0.04921
11) f33 (pattern: #% to chaos resistance)              importance=0.04393
12) f1 (pattern: # life regeneration per second)       importance=0.03972
13) f6 (pattern: # to intelligence)                    importance=0.02261
14) f29 (pattern: #% reduced ignite duration on you)   importance=0.01603
15) f11 (pattern: # to stun threshold)                 importance=0.01383
16) f2 (pattern: # to # physical thorns damage)        importance=0.01216
17) f27 (pattern: #% reduced attribute requirements)   importance=0.00711
18) f28 (pattern: #% reduced bleeding duration on you) importance=0.00581
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00379
20) f30 (pattern: #% reduced poison duration on you)   importance=0.00302
21) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00030
22) f26 (pattern: #% of damage taken recouped as mana) importance=0.00015
23) f12 (pattern: #% additional physical damage reduction) importance=0.00000
24) f24 (pattern: #% increased thorns damage)          importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
