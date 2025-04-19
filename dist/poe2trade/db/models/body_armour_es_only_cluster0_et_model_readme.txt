=== body_armour seg='es_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: 0.0142
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
 1) Quality (pattern: Quality)                         importance=0.14907
 2) f36 (pattern: #% to lightning resistance)          importance=0.10471
 3) f9 (pattern: # to spirit)                          importance=0.10333
 4) f34 (pattern: #% to cold resistance)               importance=0.07680
 5) f18 (pattern: #% increased energy shield)          importance=0.07358
 6) f35 (pattern: #% to fire resistance)               importance=0.06953
 7) f33 (pattern: #% to chaos resistance)              importance=0.05561
 8) f8 (pattern: # to maximum life)                    importance=0.05437
 9) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.05018
10) f13 (pattern: #% faster start of energy shield recharge) importance=0.04342
11) f11 (pattern: # to stun threshold)                 importance=0.04337
12) f7 (pattern: # to maximum energy shield)           importance=0.04024
13) f1 (pattern: # life regeneration per second)       importance=0.03612
14) f6 (pattern: # to intelligence)                    importance=0.03399
15) f29 (pattern: #% reduced ignite duration on you)   importance=0.01887
16) f2 (pattern: # to # physical thorns damage)        importance=0.01374
17) f27 (pattern: #% reduced attribute requirements)   importance=0.01090
18) f28 (pattern: #% reduced bleeding duration on you) importance=0.01083
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00870
20) f30 (pattern: #% reduced poison duration on you)   importance=0.00253
21) f26 (pattern: #% of damage taken recouped as mana) importance=0.00011
22) f12 (pattern: #% additional physical damage reduction) importance=0.00000
23) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
24) f24 (pattern: #% increased thorns damage)          importance=0.00000
25) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00000
