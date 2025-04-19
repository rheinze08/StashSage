=== body_armour seg='es_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.0632
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
 1) Quality (pattern: Quality)                         importance=0.16898
 2) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.11196
 3) f18 (pattern: #% increased energy shield)          importance=0.11102
 4) f9 (pattern: # to spirit)                          importance=0.07601
 5) f34 (pattern: #% to cold resistance)               importance=0.07437
 6) f7 (pattern: # to maximum energy shield)           importance=0.07209
 7) f35 (pattern: #% to fire resistance)               importance=0.06976
 8) f36 (pattern: #% to lightning resistance)          importance=0.05503
 9) f33 (pattern: #% to chaos resistance)              importance=0.04915
10) f6 (pattern: # to intelligence)                    importance=0.04472
11) f1 (pattern: # life regeneration per second)       importance=0.03214
12) f8 (pattern: # to maximum life)                    importance=0.03011
13) f11 (pattern: # to stun threshold)                 importance=0.02497
14) f13 (pattern: #% faster start of energy shield recharge) importance=0.01770
15) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01283
16) f28 (pattern: #% reduced bleeding duration on you) importance=0.01277
17) f30 (pattern: #% reduced poison duration on you)   importance=0.01043
18) f2 (pattern: # to # physical thorns damage)        importance=0.00862
19) f29 (pattern: #% reduced ignite duration on you)   importance=0.00796
20) f27 (pattern: #% reduced attribute requirements)   importance=0.00604
21) f12 (pattern: #% additional physical damage reduction) importance=0.00132
22) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00096
23) f24 (pattern: #% increased thorns damage)          importance=0.00086
24) f26 (pattern: #% of damage taken recouped as mana) importance=0.00012
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00007
