=== boots seg='es_only' cluster=1 Model Readme ===

Model Type: XGB
R^2 on test set: 0.1173
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to maximum energy shield)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f10 (pattern: # to stun threshold)
  f14 (pattern: #% increased energy shield)
  f17 (pattern: #% increased freeze threshold)
  f18 (pattern: #% increased movement speed)
  f19 (pattern: #% increased rarity of items found)
  f21 (pattern: #% reduced attribute requirements)
  f22 (pattern: #% reduced chill duration on you)
  f23 (pattern: #% reduced freeze duration on you)
  f24 (pattern: #% reduced shock duration on you)
  f25 (pattern: #% reduced slowing potency of debuffs on you)
  f26 (pattern: #% to chaos resistance)
  f27 (pattern: #% to cold resistance)
  f28 (pattern: #% to fire resistance)
  f29 (pattern: #% to lightning resistance)

Feature Importances:
 1) Quality (pattern: Quality)                         importance=0.09852
 2) f28 (pattern: #% to fire resistance)               importance=0.08437
 3) f18 (pattern: #% increased movement speed)         importance=0.08399
 4) f6 (pattern: # to maximum energy shield)           importance=0.06562
 5) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.06259
 6) f29 (pattern: #% to lightning resistance)          importance=0.05242
 7) f8 (pattern: # to maximum mana)                    importance=0.04869
 8) f14 (pattern: #% increased energy shield)          importance=0.04736
 9) f24 (pattern: #% reduced shock duration on you)    importance=0.04734
10) f23 (pattern: #% reduced freeze duration on you)   importance=0.04573
11) f10 (pattern: # to stun threshold)                 importance=0.04417
12) f27 (pattern: #% to cold resistance)               importance=0.04222
13) f7 (pattern: # to maximum life)                    importance=0.04013
14) f5 (pattern: # to intelligence)                    importance=0.03921
15) f22 (pattern: #% reduced chill duration on you)    importance=0.03889
16) f26 (pattern: #% to chaos resistance)              importance=0.03635
17) f19 (pattern: #% increased rarity of items found)  importance=0.03489
18) f1 (pattern: # life regeneration per second)       importance=0.03461
19) f21 (pattern: #% reduced attribute requirements)   importance=0.03163
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.02127
21) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
22) f17 (pattern: #% increased freeze threshold)       importance=0.00000
