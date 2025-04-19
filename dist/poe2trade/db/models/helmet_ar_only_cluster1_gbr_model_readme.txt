=== helmet seg='ar_only' cluster=1 Model Readme ===

Model Type: GBR
R^2 on test set: 0.0438
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Armour (pattern: Deflated_Armour)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # life regeneration per second)
  f2 (pattern: # to accuracy rating)
  f3 (pattern: # to armour)
  f6 (pattern: # to intelligence)
  f7 (pattern: # to level of all minion skills)
  f9 (pattern: # to maximum life)
  f10 (pattern: # to maximum mana)
  f11 (pattern: # to maximum power charges)
  f12 (pattern: # to spirit)
  f13 (pattern: # to strength)
  f14 (pattern: #% increased armour)
  f17 (pattern: #% increased critical hit chance)
  f21 (pattern: #% increased light radius)
  f23 (pattern: #% increased rarity of items found)
  f24 (pattern: #% reduced attribute requirements)
  f25 (pattern: #% to chaos resistance)
  f26 (pattern: #% to cold resistance)
  f27 (pattern: #% to fire resistance)
  f28 (pattern: #% to lightning resistance)

Feature Importances:
 1) f14 (pattern: #% increased armour)                 importance=0.18088
 2) Quality (pattern: Quality)                         importance=0.10130
 3) Deflated_Armour (pattern: Deflated_Armour)         importance=0.08998
 4) f6 (pattern: # to intelligence)                    importance=0.08708
 5) f3 (pattern: # to armour)                          importance=0.08453
 6) f10 (pattern: # to maximum mana)                   importance=0.07568
 7) f25 (pattern: #% to chaos resistance)              importance=0.06985
 8) f1 (pattern: # life regeneration per second)       importance=0.06882
 9) f9 (pattern: # to maximum life)                    importance=0.06861
10) f27 (pattern: #% to fire resistance)               importance=0.04399
11) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.03920
12) f26 (pattern: #% to cold resistance)               importance=0.03098
13) f28 (pattern: #% to lightning resistance)          importance=0.02155
14) f23 (pattern: #% increased rarity of items found)  importance=0.01200
15) f2 (pattern: # to accuracy rating)                 importance=0.00960
16) f7 (pattern: # to level of all minion skills)      importance=0.00666
17) f24 (pattern: #% reduced attribute requirements)   importance=0.00443
18) f13 (pattern: # to strength)                       importance=0.00299
19) f21 (pattern: #% increased light radius)           importance=0.00112
20) f17 (pattern: #% increased critical hit chance)    importance=0.00076
21) f12 (pattern: # to spirit)                         importance=0.00000
22) f11 (pattern: # to maximum power charges)          importance=0.00000
