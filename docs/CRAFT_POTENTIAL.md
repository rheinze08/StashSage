# Craft Potential: counterfactual feature simulation

## Purpose

Craft Potential estimates the supervised price-prediction change if a selected
rare item gained one additional explicit modifier at that modifier's highest
target-eligible intrinsic roll represented in the category's Craft Oracle
affix catalog.

It is a counterfactual model analysis, not a crafting simulator.  It answers
"what would the current pricing model predict if this feature were added?" It
does not answer an affix's crafting weight, affix-group compatibility, or full
game-domain legality. It does conservatively require an observed tier whose
item level and, when advanced clipboard headers are complete, prefix/suffix
side fit the target. When advanced headers name an existing affix, it also
rejects exact contributor-identity collisions observed in the catalog.

## Eligibility and candidate discovery

The mode accepts clipboard items only when all of the following are true:

- The text declares `Rarity: Rare`.
- The item is not `Corrupted`. A corrupted rare cannot gain a modifier, so every
  row would be unactionable.
- The parser finds fewer than six *affixes*.
- The item category and its supervised model are available.
- The installed catalog category passes its evidence/readiness thresholds.
- The target item level can roll at least one observed catalog tier.
- No named target affix exactly matches an observed contributor identity for
  the candidate pattern.
- When complete advanced Prefix/Suffix headers are available, at least one of
  the candidate's observed affix sides has capacity.

Candidate maximum rolls are read from the versioned
`super_models/craft_oracle_affix_catalog.json` runtime asset. The catalog is
built from structured ordinary `explicitMods[].mods[]` contributors before the
listing description is flattened. Each value comes from the contributor's
intrinsic `magnitudes[].max`; contributors are never summed. Crafted,
fractured, desecrated, implicit, enchant, P0, and S0 modifiers are excluded
during catalog production.

Runtime lookup uses the prepared supervised `model_category`, including Jewel
subtypes and Tablet families. Updater-delivered assets take precedence over the
bundled offline copy, and an mtime-aware cache reloads an atomically replaced
catalog. A missing, corrupt, or category-incomplete catalog is a user-facing
error. There is no fallback to flattened feature matrices or aggregated source
parquets because those can contain transformed effective totals such as 224%
resistance that are not legal rolls for one new affix.

Existing explicit patterns on the selected item are excluded. Only candidates
that affect a feature used by the installed supervised model are retained.
Item-level eligibility always uses the copied `Item Level`. Craft Potential
selects the strongest observed tier that fits it rather than dropping a pattern
when only its global ceiling is too high. Side capacity uses the
three-prefix/three-suffix limit only when every explicit affix declared a
Prefix/Suffix side; incomplete side metadata does not hide candidates. Quoted
affix names are trustworthy independently: an exact normalized name match
excludes the observed identity even if another header is unnamed. Basic copies
and legacy catalogs have no identity metadata and fail open.

### Affixes are counted, not feature slots

An affix and a parsed `explicit_mod_*` slot are not the same thing:

- a composite line (`+# to Strength and Intelligence`,
  `+#% to Fire and Lightning Resistances`) is **one** affix that the parser
  expands into **two** feature slots;
- a hybrid affix prints **two** lines under **one** advanced header.

`parse_copied_item_text` therefore groups explicit lines back to the header that
produced them and publishes `explicit_affix_count`, `explicit_prefix_count`,
`explicit_suffix_count`, `explicit_affix_sides_known`, and
`explicit_affix_names`. Craft Potential reads that metadata instead of counting
slots. Counting slots rejected four-affix items as "six explicit modifiers" and
also disabled side-capacity filtering on any item carrying a composite roll,
because the header count and the slot count could never agree.

The metadata is stripped in `cleanup_unused_features`, so it is eligibility data
only and never reaches a model feature row.

Before simulation, each intrinsic candidate is mapped through local effects on
the selected item. Matching `increased Explicit X Modifier magnitudes` effects
and typed jewellery quality determine its effective displayed roll. Unknown
magnitude scopes are ignored rather than applied heuristically to unrelated
features.

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

## Intrinsic, effective, and model-feature rolls

Craft Potential retains three values for each candidate:

- the catalog `maximum_roll`, which is always intrinsic;
- `effective_roll`, which includes matching local target magnitude effects and
  typed quality;
- the internal feature increment used for prediction.

For intrinsic roll `I`, matching local magnitude total `M`, and matching typed
quality `Q`, the effective roll is `I * (1 + (M + Q) / 100)`. Jewellery runtime
preprocessing divides matching typed quality back out, so its model increment
is `effective_roll / (1 + Q / 100)`. This is the same normalization a real
copied item receives and prevents quality from being counted twice.

The UI shows `intrinsic X; effective Y` whenever the values differ, followed by
the selected tier provenance. For example:

```text
#% to fire resistance: intrinsic 45; effective 58.5 [S2 suffix · ilvl 60 · 6 obs]
```

The suffix identifies the selected tier and side, its required item level, and
its tier-specific structured-evidence count. Compatibility payloads that have
only a total pattern count label it as `pattern obs`. The model increment
intentionally remains an implementation detail because it represents normalized
feature space rather than an in-game displayed roll. Resident and isolated
popup views use one shared formatter so their value semantics remain identical.

## Direct features

For normal direct model features (for example life, resistance, attributes,
rarity, and comparable category-specific modifiers), the simulated feature is:

`current feature value + target-normalized candidate feature roll`

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

## Derived weapon DPS features

DPS weapon models use derived component DPS fields (`dps_physical`, elemental
DPS fields, `dps_total`, and `crit_chance`) rather than direct flat-damage,
physical-percent, attack-speed, and critical-chance affix columns.

Craft Potential does **not** hand-derive an increment into normalized DPS space.
It edits the item's *displayed* stats and re-runs `compute_bow_dps_features`,
then applies the resulting difference. One place therefore encodes the game's
stacking rule, and the counterfactual cannot drift away from whatever deflation
the feature builder performs.

PoE stacks local weapon increases **additively**: weapon quality, rune
increased-physical, and explicit increased-physical all add before scaling the
base range, and local flat damage is added before those increases apply. The
displayed-space edits are:

| Candidate | Displayed-space edit |
| --- | --- |
| `adds # to # physical damage` | add `roll * (1 + (quality + local physical%) / 100)` to both ends of the physical range |
| `adds # to # <element> damage` | add `roll` to both ends of that element's range — flat elemental is not scaled by increased *physical* damage |
| `#% increased physical damage` | scale the physical range by `(1 + (L + roll)/100) / (1 + L/100)`, where `L` is quality plus every local physical-percent source |
| `#% increased attack speed` | scale displayed attacks per second by `(1 + (A + roll)/100) / (1 + A/100)`, where `A` is every local attack-speed source |
| `#% to critical hit chance` | add `roll` to the displayed critical property, matching the canonical pattern's "`to`" wording |

Adding a flat physical roll straight into the normalized feature understated it
on every weapon carrying increased physical damage — which is most weapons worth
crafting on. Critical hit chance is omitted from the weapon explicit pool
because the displayed property already encodes it; it still needs a derived
branch here, or it disappears from the candidate list entirely.

The stored roll value is an average, matching the DPS feature's average-damage
basis.  This is a model-feature calculation, not a replacement for constructing
full in-game minimum/maximum displayed ranges.

## Current limitations and revisit checklist

- Required item level and trustworthy prefix/suffix capacity are evaluated
  jointly across observed tier candidates. Exact observed contributor-name
  collisions are evaluated, but different names in the same hidden game affix
  group, tags, and weights are not.
- The catalog maximum is the highest intrinsic tier ceiling present in the
  structured training observations, not necessarily the game database's
  theoretical global maximum.
- Percentage armour simulation follows the existing normalizer's `max`
  treatment of defence percentages.  A future more exact game-stat model should
  be implemented in both the feature matrix and Craft Potential together.
- Weapon calculations use the item's displayed damage ranges and attacks per
  second, and average damage. They inherit whatever normalization
  `compute_bow_dps_features` applies, including its **known-incorrect
  multiplicative** removal of quality and rune physical-percent: PoE stacks
  those additively with explicit increased-physical, so the model's
  `dps_physical` is understated on quality-bearing weapons by an amount that
  grows with the item's own physical percent (about −8% at 20% quality and 100%
  explicit). Correcting it changes the trained feature space, so it must land
  together with a retrain and a before/after comparison. Craft Potential needs
  no change when it does, because it derives its delta by re-running that same
  function.
- Craft Potential ranks rows by the difference between two model point
  estimates. It reports no confidence interval, no probability that an affix
  lands at the selected tier, and no crafting cost. A small delta is not
  distinguishable from model error.
- Jewellery keeps defence affixes as direct model features, so it follows the
  direct-feature path rather than the armour normalization path.
- Copied item text does not contain a complete affix-tag database. Target
  magnitude scope matching is conservative and covers the ten scope names
  observed in current structured listings; an unknown future scope has no
  effect until it is explicitly mapped.

## Relevant implementation and tests

- `poe2trade/utils/craft_affix_catalog.py` owns catalog production, validation,
  category mapping, and updater/bundle-aware runtime loading.
- `poe2trade/utils/craft_potential.py` owns item validation, catalog-backed
  candidate selection, feature simulation, and ranking.
- `poe2trade/utils/craft_display.py` owns the shared intrinsic/effective and
  selected-tier provenance text, plus the shared delta format. Precision scales
  with magnitude (two decimals below 10e, one below 100e, whole exalts above),
  so a cheap item's ranked list is not rendered as a column of `+0e`. All three
  result routes call it.
- `poe2trade/utils/ml_super_utils.py` exposes the active model feature columns
  so ignored modifiers are not displayed as candidates.
- `poe2trade/app/gui_tk.py` is limited to Ctrl+4 binding, warning/progress UI,
  and results rendering.
- `tests/test_craft_affix_catalog.py` covers structured extraction, per-tier
  aggregation, contributor identities, runtime override resolution, mtime
  cache invalidation, backward-compatible summary loading, and fail-closed
  category data.
- `tests/test_craft_potential.py` covers model-category routing, no-fallback
  behavior, eligibility, all observed target-magnitude scopes, typed-quality
  normalization, item-level tier fallback, joint prefix/suffix capacity, exact
  named-identity collisions, incomplete-header fail-open behavior, direct
  ranking, glove armour normalization, and Bow flat-damage/attack-speed
  transformations.
- `tests/test_craft_display.py` verifies resident object formatting, legacy
  evidence labeling, and malformed optional metadata handling.
- `tests/test_prediction_presenter_overlay.py` verifies provenance-aware
  intrinsic/effective result text and the native Craft Oracle presentation
  lifecycle.
- Release/manifest/updater tests prove the catalog is validated, packaged,
  published, and rolled back with its supervised-model consistency bucket.
