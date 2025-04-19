=== gloves seg='ev_es_only' cluster=0 Model Readme ===

Model Type: XGB
R^2 on test set: -0.1001
use_scaler: True

Target => Price_in_Exalts

Features =>
  Deflated_Evasion (pattern: Deflated_Evasion)
  Deflated_EnergyShield (pattern: Deflated_EnergyShield)
  Quality (pattern: Quality)
  Corrupted_Flag (pattern: Corrupted_Flag)
  f1 (pattern: # to accuracy rating)
  f3 (pattern: # to dexterity)
  f4 (pattern: # to evasion rating)
  f5 (pattern: # to intelligence)
  f6 (pattern: # to level of all melee skills)
  f7 (pattern: # to maximum energy shield)
  f8 (pattern: # to maximum life)
  f9 (pattern: # to maximum mana)
  f14 (pattern: #% increased attack speed)
  f15 (pattern: #% increased critical damage bonus)
  f17 (pattern: #% increased evasion and energy shield)
  f19 (pattern: #% increased rarity of items found)
  f20 (pattern: #% increased weapon swap speed)
  f21 (pattern: #% reduced attribute requirements)
  f22 (pattern: #% to chaos resistance)
  f23 (pattern: #% to cold resistance)
  f24 (pattern: #% to fire resistance)
  f25 (pattern: #% to lightning resistance)
  f26 (pattern: adds # to # cold damage to attacks)
  f27 (pattern: adds # to # fire damage to attacks)
  f28 (pattern: adds # to # lightning damage to attacks)
  f29 (pattern: adds # to # physical damage to attacks)
  f30 (pattern: break #% increased armour)
  f31 (pattern: damage penetrates #% cold resistance)
  f32 (pattern: damage penetrates #% fire resistance)
  f34 (pattern: gain # life per enemy hit with attacks)
  f35 (pattern: gain # life per enemy killed)
  f36 (pattern: gain # mana per enemy killed)
  f37 (pattern: leech #% of physical attack damage as life)
  f38 (pattern: leech #% of physical attack damage as mana)

Feature Importances:
 1) f25 (pattern: #% to lightning resistance)          importance=0.04927
 2) f8 (pattern: # to maximum life)                    importance=0.04877
 3) f4 (pattern: # to evasion rating)                  importance=0.04840
 4) f24 (pattern: #% to fire resistance)               importance=0.04740
 5) f17 (pattern: #% increased evasion and energy shield) importance=0.04694
 6) f23 (pattern: #% to cold resistance)               importance=0.04671
 7) f3 (pattern: # to dexterity)                       importance=0.04619
 8) f1 (pattern: # to accuracy rating)                 importance=0.04229
 9) f7 (pattern: # to maximum energy shield)           importance=0.03851
10) f36 (pattern: gain # mana per enemy killed)        importance=0.03824
11) f22 (pattern: #% to chaos resistance)              importance=0.03761
12) f5 (pattern: # to intelligence)                    importance=0.03750
13) Deflated_EnergyShield (pattern: Deflated_EnergyShield) importance=0.03745
14) f28 (pattern: adds # to # lightning damage to attacks) importance=0.03460
15) f6 (pattern: # to level of all melee skills)       importance=0.03380
16) f19 (pattern: #% increased rarity of items found)  importance=0.03228
17) f26 (pattern: adds # to # cold damage to attacks)  importance=0.03213
18) f27 (pattern: adds # to # fire damage to attacks)  importance=0.03185
19) f9 (pattern: # to maximum mana)                    importance=0.03174
20) f35 (pattern: gain # life per enemy killed)        importance=0.03169
21) f29 (pattern: adds # to # physical damage to attacks) importance=0.03013
22) f37 (pattern: leech #% of physical attack damage as life) importance=0.02904
23) f15 (pattern: #% increased critical damage bonus)  importance=0.02778
24) f14 (pattern: #% increased attack speed)           importance=0.02690
25) f21 (pattern: #% reduced attribute requirements)   importance=0.02375
26) Quality (pattern: Quality)                         importance=0.02334
27) Deflated_Evasion (pattern: Deflated_Evasion)       importance=0.02188
28) f34 (pattern: gain # life per enemy hit with attacks) importance=0.01230
29) f38 (pattern: leech #% of physical attack damage as mana) importance=0.01152
30) f31 (pattern: damage penetrates #% cold resistance) importance=0.00000
31) f20 (pattern: #% increased weapon swap speed)      importance=0.00000
32) f32 (pattern: damage penetrates #% fire resistance) importance=0.00000
33) f30 (pattern: break #% increased armour)           importance=0.00000
34) Corrupted_Flag (pattern: Corrupted_Flag)           importance=0.00000
