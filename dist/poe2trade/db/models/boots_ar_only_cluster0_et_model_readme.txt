=== boots seg='ar_only' cluster=0 Model Readme ===

Model Type: ET
R^2 on test set: 0.1037
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to armour)
  f7 (pattern: # to maximum life)
  f8 (pattern: # to maximum mana)
  f9 (pattern: # to strength)
  f10 (pattern: # to stun threshold)
  f11 (pattern: #% increased armour)
  f17 (pattern: #% increased freeze threshold)
  f18 (pattern: #% increased movement speed)
  f19 (pattern: #% increased rarity of items found)
  f20 (pattern: #% increased stun threshold)
  f21 (pattern: #% reduced attribute requirements)
  f22 (pattern: #% reduced chill duration on you)
  f23 (pattern: #% reduced freeze duration on you)
  f24 (pattern: #% reduced shock duration on you)
  f26 (pattern: #% to chaos resistance)
  f27 (pattern: #% to cold resistance)
  f28 (pattern: #% to fire resistance)
  f29 (pattern: #% to lightning resistance)

Feature Importances:
 1) f18 (pattern: #% increased movement speed)         importance=0.17877
 2) f7 (pattern: # to maximum life)                    importance=0.11988
 3) f28 (pattern: #% to fire resistance)               importance=0.09089
 4) f26 (pattern: #% to chaos resistance)              importance=0.07198
 5) f27 (pattern: #% to cold resistance)               importance=0.07021
 6) f29 (pattern: #% to lightning resistance)          importance=0.06670
 7) f9 (pattern: # to strength)                        importance=0.06587
 8) Deflated_Armour (pattern: Deflated_Armour)         importance=0.06542
 9) f19 (pattern: #% increased rarity of items found)  importance=0.03856
10) f10 (pattern: # to stun threshold)                 importance=0.03549
11) f8 (pattern: # to maximum mana)                    importance=0.03267
12) f11 (pattern: #% increased armour)                 importance=0.02600
13) f24 (pattern: #% reduced shock duration on you)    importance=0.02367
14) f1 (pattern: # life regeneration per second)       importance=0.02322
15) f22 (pattern: #% reduced chill duration on you)    importance=0.02155
16) Quality (pattern: Quality)                         importance=0.01886
17) f2 (pattern: # to armour)                          importance=0.01841
18) f21 (pattern: #% reduced attribute requirements)   importance=0.01559
19) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00996
20) f23 (pattern: #% reduced freeze duration on you)   importance=0.00631
21) f17 (pattern: #% increased freeze threshold)       importance=0.00000
22) f20 (pattern: #% increased stun threshold)         importance=0.00000
