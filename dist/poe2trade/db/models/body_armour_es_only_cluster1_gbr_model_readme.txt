=== body_armour seg='es_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0797
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
 1) f18 (pattern: #% increased energy shield)          importance=0.14046
 2) Quality (pattern: Quality)                         importance=0.13586
 3) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.09410
 4) f9 (pattern: # to spirit)                          importance=0.09181
 5) f34 (pattern: #% to cold resistance)               importance=0.08240
 6) f35 (pattern: #% to fire resistance)               importance=0.07435
 7) f7 (pattern: # to maximum energy shield)           importance=0.06558
 8) f36 (pattern: #% to lightning resistance)          importance=0.06223
 9) f33 (pattern: #% to chaos resistance)              importance=0.05192
10) f6 (pattern: # to intelligence)                    importance=0.04439
11) f8 (pattern: # to maximum life)                    importance=0.03786
12) f1 (pattern: # life regeneration per second)       importance=0.03153
13) f30 (pattern: #% reduced poison duration on you)   importance=0.01840
14) f11 (pattern: # to stun threshold)                 importance=0.01826
15) f13 (pattern: #% faster start of energy shield recharge) importance=0.01489
16) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01386
17) f28 (pattern: #% reduced bleeding duration on you) importance=0.00871
18) f2 (pattern: # to # physical thorns damage)        importance=0.00602
19) f29 (pattern: #% reduced ignite duration on you)   importance=0.00373
20) f12 (pattern: #% additional physical damage reduction) importance=0.00149
21) f27 (pattern: #% reduced attribute requirements)   importance=0.00135
22) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00079
23) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
24) f24 (pattern: #% increased thorns damage)          importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
