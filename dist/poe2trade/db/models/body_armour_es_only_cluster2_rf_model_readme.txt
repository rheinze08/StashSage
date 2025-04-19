=== body_armour seg='es_only' cluster=2 Model Readme ===

Model Type: RF
R^2 on test set: 0.0171
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
 1) f9 (pattern: # to spirit)                          importance=0.16749
 2) f7 (pattern: # to maximum energy shield)           importance=0.09270
 3) f36 (pattern: #% to lightning resistance)          importance=0.09174
 4) f34 (pattern: #% to cold resistance)               importance=0.08331
 5) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.08238
 6) f18 (pattern: #% increased energy shield)          importance=0.08027
 7) Quality (pattern: Quality)                         importance=0.06441
 8) f35 (pattern: #% to fire resistance)               importance=0.05670
 9) f1 (pattern: # life regeneration per second)       importance=0.04562
10) f13 (pattern: #% faster start of energy shield recharge) importance=0.04033
11) f8 (pattern: # to maximum life)                    importance=0.03996
12) f6 (pattern: # to intelligence)                    importance=0.03078
13) f33 (pattern: #% to chaos resistance)              importance=0.02555
14) f29 (pattern: #% reduced ignite duration on you)   importance=0.02245
15) f11 (pattern: # to stun threshold)                 importance=0.02035
16) f27 (pattern: #% reduced attribute requirements)   importance=0.01412
17) f2 (pattern: # to # physical thorns damage)        importance=0.01067
18) f30 (pattern: #% reduced poison duration on you)   importance=0.00833
19) f28 (pattern: #% reduced bleeding duration on you) importance=0.00743
20) f24 (pattern: #% increased thorns damage)          importance=0.00467
21) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00423
22) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00390
23) f26 (pattern: #% of damage taken recouped as mana) importance=0.00262
24) f12 (pattern: #% additional physical damage reduction) importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
