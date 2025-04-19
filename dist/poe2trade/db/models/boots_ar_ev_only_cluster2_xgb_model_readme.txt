=== boots seg='ar_ev_only' cluster=2 Model Readme ===

Model Type: XGB
R^2 on test set: -0.3002
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
 1) f26 (pattern: #% to chaos resistance)              importance=0.09474
 2) f23 (pattern: #% reduced freeze duration on you)   importance=0.09290
 3) f18 (pattern: #% increased movement speed)         importance=0.08325
 4) f27 (pattern: #% to cold resistance)               importance=0.07285
 5) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.05847
 6) f8 (pattern: # to maximum mana)                    importance=0.05783
 7) f3 (pattern: # to dexterity)                       importance=0.05633
 8) Deflated_Armour (pattern: Deflated_Armour)         importance=0.05337
 9) f19 (pattern: #% increased rarity of items found)  importance=0.04660
10) f29 (pattern: #% to lightning resistance)          importance=0.04386
11) f22 (pattern: #% reduced chill duration on you)    importance=0.04297
12) f28 (pattern: #% to fire resistance)               importance=0.04241
13) Quality (pattern: Quality)                         importance=0.04092
14) f10 (pattern: # to stun threshold)                 importance=0.03445
15) f2 (pattern: # to armour)                          importance=0.03393
16) f7 (pattern: # to maximum life)                    importance=0.03369
17) f1 (pattern: # life regeneration per second)       importance=0.03353
18) f13 (pattern: #% increased armour and evasion)     importance=0.03286
19) f9 (pattern: # to strength)                        importance=0.01680
20) f21 (pattern: #% reduced attribute requirements)   importance=0.01529
21) f24 (pattern: #% reduced shock duration on you)    importance=0.01295
22) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
23) f20 (pattern: #% increased stun threshold)         importance=0.00000
24) f17 (pattern: #% increased freeze threshold)       importance=0.00000
25) f4 (pattern: # to evasion rating)                  importance=0.00000
26) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
