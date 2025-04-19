=== helmet seg='es_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: 0.1021
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
 1) f18 (pattern: #% increased energy shield)          importance=0.15847
 2) f26 (pattern: #% to cold resistance)               importance=0.12039
 3) f25 (pattern: #% to chaos resistance)              importance=0.10643
 4) f9 (pattern: # to maximum life)                    importance=0.10578
 5) f23 (pattern: #% increased rarity of items found)  importance=0.09167
 6) Quality (pattern: Quality)                         importance=0.05706
 7) f10 (pattern: # to maximum mana)                   importance=0.05168
 8) f8 (pattern: # to maximum energy shield)           importance=0.04630
 9) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.04192
10) f6 (pattern: # to intelligence)                    importance=0.03779
11) f28 (pattern: #% to lightning resistance)          importance=0.03609
12) f27 (pattern: #% to fire resistance)               importance=0.03572
13) f2 (pattern: # to accuracy rating)                 importance=0.03460
14) f1 (pattern: # life regeneration per second)       importance=0.02192
15) f17 (pattern: #% increased critical hit chance)    importance=0.01583
16) f7 (pattern: # to level of all minion skills)      importance=0.01534
17) f24 (pattern: #% reduced attribute requirements)   importance=0.01032
18) f21 (pattern: #% increased light radius)           importance=0.00756
19) f22 (pattern: #% increased mana regeneration rate) importance=0.00442
20) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00069
21) f12 (pattern: # to spirit)                         importance=0.00001
22) f11 (pattern: # to maximum power charges)          importance=0.00000
