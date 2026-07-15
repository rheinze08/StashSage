# Weapon Feature Algorithm

This README documents the feature-generation algorithm for weapon categories
that need derived weapon-stat features. The current set contains only `Bow`.

The goal of this branch is different from the existing armour, jewellery, and
simple branches:

- Keep ordinary item mods as model features: implicits, enchants, and explicits.
- Do not expose socket/rune mods as direct model features.
- Use socket/rune mods only to normalize displayed weapon base stats into
  stable DPS features.
- Train and score the category as one global model, with no armour-style
  AR/EV/ES segment split.

## Current Scope

| Weapon category | Branch name | Model topology | Derived base-stat features |
| --- | --- | --- | --- |
| `Bow` | Bow weapon DPS | Single global model | Total DPS, per-type DPS, crit chance |

Relevant implementation files:

- `poe2trade/utils/parse_utils.py`
  - category normalization
  - Bow socket baseline
  - trade-API property extraction
  - shared Bow DPS helper functions
- `poe2trade/utils/matrix_utils.py`
  - offline parsed-parquet to model/overlay feature matrices
- `poe2trade/utils/gui_utils.py`
  - runtime clipboard parsing and feature generation
- `poe2trade/utils/train_utils.py`
  - supervised/unsupervised single-model routing
- `poe2trade/utils/score_super_utils.py`
  - scored-matrix single-model routing

## Category and Socket Rules

Bow category names normalize to the internal token `bow`.

Known aliases:

- `Bow`
- `Bows`
- `bow`
- `bows`

Bows have two sockets by default. The model feature is therefore:

```text
extra_sockets = max(0, socket_count - 2)
```

Examples:

| Socket count | `extra_sockets` |
| --- | --- |
| 0 | 0 |
| 1 | 0 |
| 2 | 0 |
| 3 | 1 |
| 4 | 2 |

The trade API path computes this from `len(item["sockets"])`. The clipboard path
computes it from the copied `Sockets:` line.

## Raw Bow Properties

The parser extracts these raw weapon properties before matrix construction:

| Raw column | Meaning |
| --- | --- |
| `phys_damage_min` | displayed physical low roll |
| `phys_damage_max` | displayed physical high roll |
| `fire_damage_min` | displayed fire low roll |
| `fire_damage_max` | displayed fire high roll |
| `cold_damage_min` | displayed cold low roll |
| `cold_damage_max` | displayed cold high roll |
| `lightning_damage_min` | displayed lightning low roll |
| `lightning_damage_max` | displayed lightning high roll |
| `chaos_damage_min` | displayed chaos low roll |
| `chaos_damage_max` | displayed chaos high roll |
| `attack_speed` | displayed attacks per second |
| `crit_chance` | displayed critical hit chance percent |

The raw damage and attack-speed columns are intermediate inputs. They are dropped
from final model and overlay matrices after the derived DPS features are built.
`crit_chance` is retained as a model feature.

## Trade API Damage Extraction

Trade API properties are parsed by display name after tag cleanup.

Direct named properties map straight to one damage type:

| Property name after cleanup | Damage type |
| --- | --- |
| `Physical Damage` | physical |
| `Fire Damage` | fire |
| `Cold Damage` | cold |
| `Lightning Damage` | lightning |
| `Chaos Damage` | chaos |

The trade API may also provide grouped elemental values under:

```text
Elemental Damage
```

For grouped elemental values, the parser uses the value color/type code:

| Value code | Damage type |
| --- | --- |
| `4` | fire |
| `5` | cold |
| `6` | lightning |

Chaos and physical are also recognized by direct property names. The helper
allows code `7` for chaos and `9` for physical defensively, but grouped
elemental values should normally resolve only to fire/cold/lightning.

Damage ranges are parsed as:

```text
A-B -> (A, B)
A   -> (A, A)
```

Roll-range annotations such as `(augmented)` or copied advanced roll ranges are
ignored for this property parser.

## Clipboard Damage Extraction

Copied item text uses the same raw columns as trade API parsing. The Bow runtime
parser currently reads these metadata lines:

```text
Physical Damage: A-B
Elemental Damage: A-B (fire), C-D (cold), E-F (lightning)
Fire Damage: A-B
Cold Damage: A-B
Lightning Damage: A-B
Chaos Damage: A-B
Critical Hit Chance: N%
Attacks per Second: N
```

Those lines are metadata, not affixes. They also terminate item-name parsing, so
weapon property lines cannot accidentally become part of `Item Name`.

For copied `Elemental Damage:` lines, each comma-separated segment must include
one of the type tags `fire`, `cold`, or `lightning`. The parser assigns that
segment's range to the matching damage type. Untyped elemental ranges are
ignored because they cannot be safely split into per-type DPS features.

## Mod Slot Policy

The weapon branch follows the same high-level mod policy as the other model
branches:

- `implicit_mod_*` becomes feature columns.
- `enchant_mod_*` becomes feature columns.
- `explicit_mod_*`, `fractured_mod_*`, and `desecrated_mod_*` become feature
  columns.
- `rune_mod_*` never becomes a direct feature column.

Rune mods are still parsed because direct socket/rune damage must be removed
from displayed weapon stats before DPS is calculated.

For Bow, explicit/fractured/desecrated mods that directly affect the displayed
weapon damage or attack speed are also not emitted as standalone feature
columns. They are already encoded in the displayed damage ranges and attack
speed used to build normalized DPS.

These DPS-encoded patterns are removed from the Bow explicit pool:

```text
#% increased physical damage
#% increased attack speed
adds # to # physical damage
adds # to # fire damage
adds # to # cold damage
adds # to # lightning damage
adds # to # chaos damage
```

The exact direct rune patterns used for Bow normalization are:

```text
#% increased physical damage
adds # to # physical damage
adds # to # fire damage
adds # to # cold damage
adds # to # lightning damage
adds # to # chaos damage
```

Only exact direct damage patterns are used. Conditional or indirect damage text
is intentionally ignored for DPS deflation, for example:

```text
Adds A to B Lightning Damage against Shocked Enemies
Gain N% of Damage as Extra Chaos Damage
Bow Attacks fire an additional Arrow
```

Those are either explicit model features or ignored rune effects depending on
which slot they occupy, but they do not alter the derived base DPS.

## DPS Feature Algorithm

The shared implementation is `compute_bow_dps_features`.

### Inputs

For one item, the helper reads:

```text
quality
phys_damage_min / phys_damage_max
fire_damage_min / fire_damage_max
cold_damage_min / cold_damage_max
lightning_damage_min / lightning_damage_max
chaos_damage_min / chaos_damage_max
attack_speed
crit_chance
rune_mod_1..6 text, pattern, value, and optional min/max range helpers
```

Missing numeric values are treated as zero.

### Step 1: Average Displayed Damage Ranges

For each damage type:

```text
avg_type = (damage_min + damage_max) / 2
```

So:

```text
avg_physical  = (phys_damage_min + phys_damage_max) / 2
avg_fire      = (fire_damage_min + fire_damage_max) / 2
avg_cold      = (cold_damage_min + cold_damage_max) / 2
avg_lightning = (lightning_damage_min + lightning_damage_max) / 2
avg_chaos     = (chaos_damage_min + chaos_damage_max) / 2
```

### Step 2: Collect Direct Rune Adjustments

For each `rune_mod_i`:

```text
if pattern == "#% increased physical damage":
    rune_phys_pct += rune_mod_i_value

if pattern == "adds # to # <type> damage":
    rune_flat_<type> += (low + high) / 2
```

When raw rune text is available, the low/high range is parsed from the text. At
runtime, `process_all_mods` stores optional `rune_mod_i_min` and
`rune_mod_i_max` helpers before the raw slots are dropped. If a range is not
available, the already-parsed average value is used as fallback.

Multiple matching runes stack by summing their effects.

### Step 3: Deflate Physical Damage

Physical damage is affected by weapon quality and by direct physical-percent
socket/rune modifiers. The physical denominator is:

```text
physical_denominator =
    (1 + quality / 100) *
    (1 + rune_phys_pct / 100)
```

The deflated physical average is:

```text
deflated_physical_avg =
    max(0, avg_physical / physical_denominator - rune_flat_physical)
```

This mirrors the armour branch approach: remove quality and socket/rune
augmentation from the displayed base stat before modeling.

### Step 4: Deflate Elemental and Chaos Damage

For fire, cold, lightning, and chaos, only direct flat socket/rune damage is
removed:

```text
deflated_fire_avg      = max(0, avg_fire      - rune_flat_fire)
deflated_cold_avg      = max(0, avg_cold      - rune_flat_cold)
deflated_lightning_avg = max(0, avg_lightning - rune_flat_lightning)
deflated_chaos_avg     = max(0, avg_chaos     - rune_flat_chaos)
```

No elemental-percent or chaos-percent rune deflation is currently applied
because the current Bow rune rules target direct physical percent and direct
flat damage additions.

### Step 5: Convert Flat Damage to DPS

Each type-specific DPS feature is:

```text
dps_<type> = deflated_<type>_avg * attack_speed
```

So the generated feature columns are:

```text
dps_physical
dps_fire
dps_cold
dps_lightning
dps_chaos
```

Total DPS is:

```text
dps_total =
    dps_physical +
    dps_fire +
    dps_cold +
    dps_lightning +
    dps_chaos
```

Critical chance is retained as:

```text
crit_chance
```

## Final Bow Model Feature Surface

The Bow model matrix contains:

- `price`
- `extra_sockets`
- `dps_total`
- `dps_physical`
- `dps_fire`
- `dps_cold`
- `dps_lightning`
- `dps_chaos`
- `crit_chance`
- implicit feature columns not already encoded in DPS
- enchant feature columns not already encoded in DPS
- explicit/fractured/desecrated feature columns not already encoded in DPS

The Bow model matrix does not contain:

- raw damage min/max columns
- `attack_speed`
- raw `quality` / `quality_type`
- raw `rune_mod_*` columns
- rune pattern feature columns
- local flat physical/fire/cold/lightning/chaos damage mod columns
- local `% increased physical damage` mod columns
- local `% increased attack speed` mod columns
- raw `skill_pattern` / `skill_value`
- armour-only `ar_norm`, `ev_norm`, `es_norm`, or `block_norm`

The Bow overlay matrix mirrors the same Bow-specific features for GUI/KNN use,
with user-facing metadata retained according to the existing overlay rules.

## Worked Example

Input:

```text
Quality: 20
Physical Damage: 36-36
Fire Damage: 10-10
Lightning Damage: 30-30
Chaos Damage: 5-5
Attacks per Second: 2
Critical Hit Chance: 7.5

Rune 1: 20% increased Physical Damage
Rune 2: Adds 1 to 5 Lightning Damage
Rune 3: Adds 6 to 6 Physical Damage
```

Physical:

```text
avg_physical = 36
physical_denominator = (1 + 20/100) * (1 + 20/100) = 1.44
rune_flat_physical = 6
deflated_physical_avg = max(0, 36 / 1.44 - 6) = 19
dps_physical = 19 * 2 = 38
```

Fire:

```text
deflated_fire_avg = 10
dps_fire = 10 * 2 = 20
```

Lightning:

```text
rune_flat_lightning = (1 + 5) / 2 = 3
deflated_lightning_avg = 30 - 3 = 27
dps_lightning = 27 * 2 = 54
```

Chaos:

```text
deflated_chaos_avg = 5
dps_chaos = 5 * 2 = 10
```

Total:

```text
dps_total = 38 + 20 + 0 + 54 + 10 = 122
crit_chance = 7.5
```

## Offline and Runtime Parity

The offline pipeline and clipboard runtime intentionally share the same Bow DPS
helper.

Offline path:

```text
trade API JSON
-> parse_item_json
-> Bow raw columns
-> build_feature_matrix
-> compute_bow_dps_features
-> model/overlay parquet
```

Runtime path:

```text
copied item text
-> parse_copied_item_text
-> process_all_mods
-> deflator_and_normaliser
-> compute_bow_dps_features
-> build_feature_dataframe
```

This keeps app predictions aligned with the training matrices.

## Adding Another Weapon Type

When adding another weapon category to this branch, use this checklist:

1. Add category normalization aliases.
2. Define the default socket baseline for `extra_sockets`.
3. Parse raw weapon properties from trade API JSON.
4. Parse equivalent raw properties from copied item text.
5. Decide which socket/rune effects are direct base-stat effects and which are
   ordinary model features or ignored.
6. Add a shared DPS/stat helper, or generalize `compute_bow_dps_features` if the
   formula is identical.
7. Route the category through the matrix branch without armour segmentation.
8. Route train/score/ML lookup as a single global model unless the category
   needs its own segmentation.
9. Drop raw intermediate weapon-stat columns from final model and overlay
   matrices.
10. Add parser, matrix, and clipboard tests with hand-checkable DPS numbers.

Do not add socket/rune mods directly as feature columns unless the methodology
for that weapon explicitly changes.

## Focused Test Coverage

Current focused tests:

```powershell
python -m pytest tests/test_parse_cat.py tests/test_matrix_utils.py tests/test_gui_utils_parse.py -q
```

The Bow-specific tests verify:

- trade API property extraction
- Bow `extra_sockets`
- DPS deflation from direct physical-percent and flat damage runes
- rune patterns excluded as direct features
- clipboard Bow parsing
- single-model category detection
