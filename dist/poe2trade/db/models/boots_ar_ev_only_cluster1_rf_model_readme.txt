=== boots seg='ar_ev_only' cluster=1 Model Readme ===

Model Type: RF
R^2 on test set: 0.3737
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
 1) f26 (pattern: #% to chaos resistance)              importance=0.18670
 2) f27 (pattern: #% to cold resistance)               importance=0.13951
 3) f9 (pattern: # to strength)                        importance=0.13114
 4) f28 (pattern: #% to fire resistance)               importance=0.12330
 5) f18 (pattern: #% increased movement speed)         importance=0.09831
 6) f19 (pattern: #% increased rarity of items found)  importance=0.06211
 7) f29 (pattern: #% to lightning resistance)          importance=0.04760
 8) f4 (pattern: # to evasion rating)                  importance=0.04622
 9) Deflated_Armour (pattern: Deflated_Armour)         importance=0.03275
10) f8 (pattern: # to maximum mana)                    importance=0.02800
11) f22 (pattern: #% reduced chill duration on you)    importance=0.02315
12) f3 (pattern: # to dexterity)                       importance=0.01964
13) f13 (pattern: #% increased armour and evasion)     importance=0.01258
14) f7 (pattern: # to maximum life)                    importance=0.01231
15) f1 (pattern: # life regeneration per second)       importance=0.00906
16) f2 (pattern: # to armour)                          importance=0.00762
17) f23 (pattern: #% reduced freeze duration on you)   importance=0.00679
18) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.00541
19) f21 (pattern: #% reduced attribute requirements)   importance=0.00377
20) Quality (pattern: Quality)                         importance=0.00211
21) f10 (pattern: # to stun threshold)                 importance=0.00193
22) f24 (pattern: #% reduced shock duration on you)    importance=0.00000
23) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
24) f25 (pattern: #% reduced slowing potency of debuffs on you) importance=0.00000
25) f20 (pattern: #% increased stun threshold)         importance=0.00000
26) f17 (pattern: #% increased freeze threshold)       importance=0.00000
