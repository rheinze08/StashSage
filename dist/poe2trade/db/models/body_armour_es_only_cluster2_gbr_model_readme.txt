=== body_armour seg='es_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0102
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
 1) f9 (pattern: # to spirit)                          importance=0.22480
 2) f36 (pattern: #% to lightning resistance)          importance=0.10402
 3) f7 (pattern: # to maximum energy shield)           importance=0.10154
 4) f34 (pattern: #% to cold resistance)               importance=0.09877
 5) Quality (pattern: Quality)                         importance=0.09031
 6) f18 (pattern: #% increased energy shield)          importance=0.07168
 7) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.06194
 8) f35 (pattern: #% to fire resistance)               importance=0.05556
 9) f13 (pattern: #% faster start of energy shield recharge) importance=0.03906
10) f33 (pattern: #% to chaos resistance)              importance=0.02776
11) f1 (pattern: # life regeneration per second)       importance=0.02177
12) f29 (pattern: #% reduced ignite duration on you)   importance=0.01966
13) f8 (pattern: # to maximum life)                    importance=0.01891
14) f2 (pattern: # to # physical thorns damage)        importance=0.01806
15) f6 (pattern: # to intelligence)                    importance=0.01678
16) f11 (pattern: # to stun threshold)                 importance=0.00628
17) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00622
18) f24 (pattern: #% increased thorns damage)          importance=0.00548
19) f27 (pattern: #% reduced attribute requirements)   importance=0.00441
20) f30 (pattern: #% reduced poison duration on you)   importance=0.00438
21) f26 (pattern: #% of damage taken recouped as mana) importance=0.00119
22) f28 (pattern: #% reduced bleeding duration on you) importance=0.00092
23) extra_socket_mod (pattern: extra_socket_mod)       importance=0.00050
24) f12 (pattern: #% additional physical damage reduction) importance=0.00000
25) f25 (pattern: #% of damage taken recouped as life) importance=0.00000
