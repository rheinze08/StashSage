=== boots seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: GBR
R^2 on test set: -0.4178
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Deflated_Evasion (pattern: Deflated_Evasion)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to armour)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f9 (pattern: # to strength)
  f10 (pattern: # to stun threshold)
  f13 (pattern: #% increased armour and evasion)
  f17 (pattern: #% increased freeze threshold)
  f18 (pattern: #% increased movement speed)
  f19 (pattern: #% increased rarity of items found)
  f20 (pattern: #% increased stun threshold)
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
 1) f26 (pattern: #% to chaos resistance)              importance=0.18928
 2) f23 (pattern: #% reduced freeze duration on you)   importance=0.14194
 3) f27 (pattern: #% to cold resistance)               importance=0.12676
 4) Deflated_Armour (pattern: Deflated_Armour)         importance=0.10682
 5) f18 (pattern: #% increased movement speed)         importance=0.09375
 6) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.08883
 7) f8 (pattern: # to maximum mana)                    importance=0.04956
 8) f13 (pattern: #% increased armour and evasion)     importance=0.03280
 9) f29 (pattern: #% to lightning resistance)          importance=0.03131
10) f3 (pattern: # to dexterity)                       importance=0.03043
11) f7 (pattern: # to maximum life)                    importance=0.02555
12) f19 (pattern: #% increased rarity of items found)  importance=0.02232
13) f28 (pattern: #% to fire resistance)               importance=0.01901
14) f10 (pattern: # to stun threshold)                 importance=0.01513
15) f2 (pattern: # to armour)                          importance=0.01119
16) Quality (pattern: Quality)                         importance=0.00583
17) f9 (pattern: # to strength)                        importance=0.00301
18) f1 (pattern: # life regeneration per second)       importance=0.00208
19) f24 (pattern: #% reduced shock duration on you)    importance=0.00161
20) f22 (pattern: #% reduced chill duration on you)    importance=0.00127
21) f4 (pattern: # to evasion rating)                  importance=0.00089
22) f21 (pattern: #% reduced attribute requirements)   importance=0.00063
23) f20 (pattern: #% increased stun threshold)         importance=0.00000
24) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
25) f17 (pattern: #% increased freeze threshold)       importance=0.00000
26) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
