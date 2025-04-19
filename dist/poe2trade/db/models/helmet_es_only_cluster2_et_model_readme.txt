=== helmet seg='es_only' cluster=2 Model Readme ===

Model Type: ET
R^2 on test set: -0.0893
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f8 (pattern: # to maximum energy shield)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f17 (pattern: #% increased critical hit chance)
  f18 (pattern: #% increased energy shield)
  f21 (pattern: #% increased light radius)
  f22 (pattern: #% increased mana regeneration rate)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f26 (pattern: #% to cold resistance)               importance=0.12837
 2) f28 (pattern: #% to lightning resistance)          importance=0.11475
 3) f25 (pattern: #% to chaos resistance)              importance=0.11363
 4) f27 (pattern: #% to fire resistance)               importance=0.10294
 5) f7 (pattern: # to level of all minion skills)      importance=0.06561
 6) f23 (pattern: #% increased rarity of items found)  importance=0.06356
 7) f10 (pattern: # to maximum mana)                   importance=0.06078
 8) f9 (pattern: # to maximum life)                    importance=0.05813
 9) f18 (pattern: #% increased energy shield)          importance=0.05602
10) f6 (pattern: # to intelligence)                    importance=0.04144
11) Quality (pattern: Quality)                         importance=0.03426
12) f2 (pattern: # to accuracy rating)                 importance=0.03365
13) f1 (pattern: # life regeneration per second)       importance=0.02695
14) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.02572
15) f8 (pattern: # to maximum energy shield)           importance=0.02104
16) f17 (pattern: #% increased critical hit chance)    importance=0.02017
17) f24 (pattern: #% reduced attribute requirements)   importance=0.01796
18) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.01246
19) f21 (pattern: #% increased light radius)           importance=0.00258
20) f12 (pattern: # to spirit)                         importance=0.00000
21) f22 (pattern: #% increased mana regeneration rate) importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
