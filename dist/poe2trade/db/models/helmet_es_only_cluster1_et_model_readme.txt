=== helmet seg='es_only' cluster=1 Model Readme ===

Model Type: ET
R^2 on test set: 0.0812
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
 1) f25 (pattern: #% to chaos resistance)              importance=0.12913
 2) f18 (pattern: #% increased energy shield)          importance=0.11898
 3) f26 (pattern: #% to cold resistance)               importance=0.10693
 4) Quality (pattern: Quality)                         importance=0.10209
 5) f9 (pattern: # to maximum life)                    importance=0.09883
 6) f23 (pattern: #% increased rarity of items found)  importance=0.07762
 7) f7 (pattern: # to level of all minion skills)      importance=0.05905
 8) f6 (pattern: # to intelligence)                    importance=0.03667
 9) f8 (pattern: # to maximum energy shield)           importance=0.03302
10) f28 (pattern: #% to lightning resistance)          importance=0.03271
11) f1 (pattern: # life regeneration per second)       importance=0.02540
12) f24 (pattern: #% reduced attribute requirements)   importance=0.02384
13) f2 (pattern: # to accuracy rating)                 importance=0.02341
14) f10 (pattern: # to maximum mana)                   importance=0.02326
15) f17 (pattern: #% increased critical hit chance)    importance=0.02083
16) f27 (pattern: #% to fire resistance)               importance=0.02059
17) f21 (pattern: #% increased light radius)           importance=0.02011
18) f22 (pattern: #% increased mana regeneration rate) importance=0.02005
19) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.01751
20) f12 (pattern: # to spirit)                         importance=0.00676
21) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00320
22) f11 (pattern: # to maximum power charges)          importance=0.00000
