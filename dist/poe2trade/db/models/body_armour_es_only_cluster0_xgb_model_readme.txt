=== body_armour seg='es_only' cluster=0 Model Readme ===

Model Type: XGB
R^2 on test set: -0.0128
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
 1) Quality (pattern: Quality)                         importance=0.10634
 2) f18 (pattern: #% increased energy shield)          importance=0.06732
 3) f9 (pattern: # to spirit)                          importance=0.06639
 4) f35 (pattern: #% to fire resistance)               importance=0.06359
 5) f36 (pattern: #% to lightning resistance)          importance=0.06279
 6) f13 (pattern: #% faster start of energy shield recharge) importance=0.05842
 7) f33 (pattern: #% to chaos resistance)              importance=0.05314
 8) f34 (pattern: #% to cold resistance)               importance=0.05301
 9) f8 (pattern: # to maximum life)                    importance=0.05249
10) f27 (pattern: #% reduced attribute requirements)   importance=0.04781
11) f7 (pattern: # to maximum energy shield)           importance=0.04385
12) f29 (pattern: #% reduced ignite duration on you)   importance=0.04267
13) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.03967
14) f1 (pattern: # life regeneration per second)       importance=0.03880
15) f6 (pattern: # to intelligence)                    importance=0.03661
16) f11 (pattern: # to stun threshold)                 importance=0.03643
17) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03422
18) f2 (pattern: # to # physical thorns damage)        importance=0.03381
19) extra_socket_mod (pattern: extra_socket_mod)       importance=0.02733
20) f30 (pattern: #% reduced poison duration on you)   importance=0.01893
21) f28 (pattern: #% reduced bleeding duration on you) importance=0.01637
22) f26 (pattern: #% of damage taken recouped as mana) importance=0.00000
23) f12 (pattern: #% additional physical damage reduction) importance=0.00000
24) f24 (pattern: #% increased thorns damage)          importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
