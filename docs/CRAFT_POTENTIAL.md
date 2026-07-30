# Craft Potential: counterfactual feature simulation

## Purpose

Craft Potential estimates the supervised price-prediction change if a selected
rare item gained one additional explicit modifier at that modifier's highest
observed roll in the category source data.

It is a counterfactual model analysis, not a crafting simulator.  It answers
"what would the current pricing model predict if this feature were added?" It
does not answer whether an affix can legally roll, its crafting weight, its
prefix/suffix availability, or affix-group compatibility.

## Eligibility and candidate discovery

The mode accepts clipboard items only when all of the following are true:

- The text declares `Rarity: Rare`.
- The parser finds fewer than six explicit modifier slots.
- The item category and its supervised model are available.

Candidate maximum rolls are read from the category's
`*_agg_parsed.parquet` source file. The scan uses only ordinary `explicit`
modifier slots, canonicalizes patterns through `parse_rolled_mod`, and retains
the highest positive stored value for each pattern. Fractured, desecrated,
implicit, and enchant slots are deliberately excluded.

This deliberately does not use the flattened feature matrix to find maxima:
that matrix combines explicit, implicit, and enchant sources, which would make
an explicit-modifier recommendation unreliable.

Existing explicit patterns on the selected item are excluded.  Only candidates
that affect a feature used by the installed supervised model are retained.

## Prediction convention

The baseline and every simulated item use the normal supervised prediction
path.  The displayed XGBoost prediction is used when available; otherwise the
aggregate median is used.  Each row reports the absolute and percentage change
from that baseline and is ranked from greatest to smallest increase.

## Why the simulation works in feature space

Craft Potential does not generate fake clipboard text with altered displayed
Armour, Evasion, Energy Shield, damage ranges, or attack speed.  Instead, it
starts from the selected item's prepared model-feature row and applies the same
derived-feature semantics used by the runtime/matrix pipeline.

If a synthetic displayed item were constructed perfectly and then passed back
through the normal deflation/normalization process, the intended model-feature
result would be equivalent.  Feature-space simulation avoids guessing at text
formatting and keeps the counterfactual aligned with what the model actually
receives.

## Direct features

For normal direct model features (for example life, resistance, attributes,
rarity, and comparable category-specific modifiers), the simulated feature is:

`current feature value + candidate maximum roll`

The row is then aligned to the saved model feature columns by the normal
supervised scorer.

## Derived armour features

Armour-like categories are `boots`, `gloves`, `helmet`, `body_armour`,
`shield`, `buckler`, and `focus`.  Their flat and percentage defence affixes are
not direct model columns; the model uses normalized fields such as `ar_norm`,
`ev_norm`, and `es_norm`.

### Flat defences

For `# to armour`, `# to evasion rating`, or `# to maximum energy shield`, Craft
Potential increases the corresponding normalized feature by:

`candidate flat value * (1 + current maximum defence percent / 100)`

The current maximum defence percentage is determined from the item's parsed
explicit, implicit, and enchant defence modifiers.  This mirrors the current
runtime normalizer's representation.

### Percentage defences

For a percentage defence candidate, Craft Potential applies the current
normalizer's maximum-percent rule:

`new normalized value = old normalized value * (1 + new percent / 100) / (1 + old percent / 100)`

where `new percent` is the larger of the existing maximum defence percentage
and the candidate's percentage roll.  The same multiplier is applied to the
model-supported normalized AR/EV/ES fields.

This is intentionally faithful to the current model pipeline.  It is not a
complete game-engine calculation of every individual defence modifier's
stacking scope.  If the core normalizer changes, update this calculation and
its tests at the same time.

## Derived Bow DPS features

Bow models use derived component DPS fields (`dps_physical`, elemental DPS
fields, and `dps_total`) rather than direct flat-damage, physical-percent, and
attack-speed affix columns.

- Flat `adds # to # <type> damage` adds `candidate average damage * current
  attack speed` to the matching component and total DPS.
- `% increased physical damage` rescales physical DPS based on the current
  parsed physical-percent total, then applies the difference to total DPS.
- `% increased attack speed` rescales every model-supported DPS component and
  total DPS by the ratio of new effective attack speed to current effective
  attack speed.

The stored roll value is an average, matching the DPS feature's average-damage
basis.  This is a model-feature calculation, not a replacement for constructing
full in-game minimum/maximum displayed ranges.

## Current limitations and revisit checklist

- Affix legality, prefix/suffix slots, required item level, tags, weights, and
  affix-group conflicts are not evaluated.
- The source maximum is an observed dataset maximum, not necessarily the game
  database's theoretical tier maximum.
- Percentage armour simulation follows the existing normalizer's `max`
  treatment of defence percentages.  A future more exact game-stat model should
  be implemented in both the feature matrix and Craft Potential together.
- Bow calculations assume the parsed current attack speed and use average
  damage.  If Bow feature generation changes, update Craft Potential's Bow
  transform and tests.
- Jewellery keeps defence affixes as direct model features, so it follows the
  direct-feature path rather than the armour normalization path.

## Relevant implementation and tests

- `poe2trade/utils/craft_potential.py` owns validation, source-data maxima,
  feature simulation, and ranking.
- `poe2trade/utils/ml_super_utils.py` exposes the active model feature columns
  so ignored modifiers are not displayed as candidates.
- `poe2trade/app/gui_tk.py` is limited to Ctrl+4 binding, warning/progress UI,
  and results rendering.
- `tests/test_craft_potential.py` covers eligibility, direct ranking, glove
  armour normalization, and Bow flat-damage/attack-speed transformations.
