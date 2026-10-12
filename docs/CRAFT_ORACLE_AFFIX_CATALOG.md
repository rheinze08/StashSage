# Craft Oracle intrinsic-affix catalog

## Status

- [x] Phase 1 — produce a deterministic, category-aware intrinsic-affix catalog during parsing.
- [x] Phase 2 — ship the catalog as a co-versioned runtime asset and make Craft Oracle require it.
- [x] Phase 3 — apply target-item amplification in simulation and distinguish intrinsic/effective rolls in the UI.
- [x] Phase 4 — enforce evidence thresholds, reporting, and affix eligibility rules.
- [x] Phase 5 — retain observed tier ladders and select the strongest target-eligible tier.
- [x] Phase 6 — reject exact observed affix-identity collisions from named target headers.
- [x] Phase 7 — expose selected-tier provenance in every Craft Oracle result view.

All seven phases are implemented without changing parsed item rows,
feature-matrix columns, KNN distances, or supervised model inputs. Phase 2
changed Craft Oracle candidate discovery to require the intrinsic catalog.
Phase 3 changes only the counterfactual increment and its presentation: the
catalog ceiling is transformed by effects found on the selected target item,
then normalized through the same typed-quality convention as ordinary runtime
inference. Phase 4 makes catalog evidence auditable and release-gated, then
uses the already-recorded affix side and required level to exclude impossible
top-tier counterfactuals when the target clipboard supplies trustworthy data.
Phase 5 makes that filtering constructive: when the catalog contains a lower
observed tier that fits the same target, Craft Oracle simulates the strongest
eligible tier instead of dropping the entire modifier pattern.
Phase 6 preserves the contributor names shared by structured listings and
advanced clipboard headers, allowing exact identity collisions to be rejected
without guessing hidden game group IDs.
Phase 7 makes the already-selected tier auditable in both resident and spawned
result views by showing its side, required item level, and evidence count next
to the intrinsic/effective roll.

## Problem

The original Craft Oracle implementation discovered candidate maximum rolls by scanning the
flattened `explicit_mod_*` values in each category's aggregated parquet. Those
values are effective item-display totals, not necessarily the roll of one
ordinary affix.

Runes of Aldur resistance transformations demonstrate the mismatch. Separate
Fire, Cold, and Lightning resistance suffixes can be transformed to the same
final resistance. The item payload then exposes one combined description for
that final stat while retaining several structured contributing modifiers. A
typed-quality multiplier and a crafted explicit-magnitude multiplier may also
be reflected in the combined description.

For example, a displayed `+224% to Fire Resistance` entry can contain three
ordinary S1 resistance contributors whose intrinsic magnitude ranges each end
at `45`. The pricing feature should represent the effective total, because the
complete item really has that much resistance. A hypothetical "append one new
explicit modifier" operation must use one contributor's intrinsic maximum,
not the combined display total.

The ordinary flattened parser loses that distinction in `_mod_entry_text`: it keeps the
parent description and discards the structured `mods[].magnitudes` contributors.
Changing the matrix aggregation from `sum` to `max` cannot repair the data,
because the combined `224` already occupies a single parsed explicit slot by
the time matrix construction starts.

## Design principle

The two consumers require two representations and should not share one lossy
number:

```text
Structured listing modifier
          |
          +-- existing item parser --> effective total features --> pricing models
          |
          +-- affix observer --------> intrinsic maxima catalog --> Craft Oracle
```

The existing pricing path remains authoritative for effective item totals.
The new catalog is a sidecar used only for counterfactual craft candidates.

## Phase 1: catalog production

### Extraction boundary

`parse_item_json` accepts an optional observer invoked with the structured item
mapping after the item has passed the existing listing filter. The observer is
isolated from parsed-row construction: an observer failure is reported but
cannot remove or mutate a training row.

The catalog collector examines `item.explicitMods` before the normal parser
reduces those entries to display strings. For each parent entry it:

1. Requires structured mapping data. Legacy string-only modifiers are counted
   as skipped and never used as unsafe maxima.
2. Accepts only an ordinary explicit domain, identified by `domain=explicit`
   or an `explicit` stat hash when older payloads omit `domain`.
3. Rejects crafted, desecrated, fractured, and otherwise flagged entries.
4. Expands composite attribute/resistance descriptions using the same parser
   semantics as training.
5. Explodes every structured `mods[]` contributor rather than treating the
   parent display total as one roll.
6. Accepts ordinary `P1+`/`S1+` tiers and rejects `P0`, `S0`, missing, or
   unclassified tiers.
7. Calculates the intrinsic candidate value from each contributor's
   `magnitudes[].max`. A two-ended range uses the average of its first and last
   maxima, matching the scalar convention used by `parse_rolled_mod`. That
   average is only meaningful when the magnitudes describe one stat, so a
   contributor supplying several magnitudes to several canonical patterns — a
   genuine hybrid affix — is rejected rather than reduced to a scalar belonging
   to neither pattern. A composite description with a single magnitude (`+# to
   X and Y`) still applies that one value to both expanded patterns, which is
   correct.
8. Keeps the maximum contributor value for each canonical pattern and category.
   Contributors are never summed.

The collector records audit statistics for structured observations and skipped
data. Missing structure therefore reduces catalog coverage visibly instead of
silently reintroducing combined display totals.

### Artifact

The parser writes a single deterministic JSON sidecar:

```text
poe2trade/db/super_models/craft_oracle_affix_catalog.json
```

It is generated data and remains ignored by Git like the model artifacts beside
it. The schema is versioned and category entries are independently replaceable,
allowing a partial category parse to update its selected categories without
destroying valid entries for categories that were not rebuilt.

Example shape:

```json
{
  "schema_version": 1,
  "categories": {
    "ring": {
      "patterns": {
        "#% to fire resistance": {
          "maximum_roll": 45.0,
          "affix_sides": ["suffix"],
          "winning_tier": "S1",
          "required_level": 82,
          "observations": 1842
        }
      },
      "statistics": {
        "accepted_contributors": 120000,
        "items_seen": 50000
      }
    }
  }
}
```

Writes use a temporary file followed by `os.replace`, so interruption cannot
leave a partially written catalog. Keys are sorted and volatile timestamps are
omitted, making identical inputs produce identical bytes.

### Category mapping

Catalog keys are derived from the resolved training folder through the same
folder/model conventions used by training:

```python
normalize_item_category(model_category_name(resolved_folder))
```

This yields stable runtime keys for ordinary aliases and split categories:

| Training folder | Catalog/runtime key |
| --- | --- |
| `rings` | `ring` |
| `body_armour` | `body_armour` |
| `Mace_One_Hand_Mace` | `mace_one_hand_mace` |
| `Mace_Two_Hand_Mace` | `mace_two_hand_mace` |
| `Shield` | `shield` |
| `Buckler` | `buckler` |
| `Sapphire` | `sapphire` |
| `Time-Lost_Ruby` | `time_lost_ruby` |
| `Tablet_Breach` | `tablet_breach` |
| `Waystone` | `waystone` |

Runtime looks up the catalog with
`normalize_item_category(prepared.model_category)`, not the broader clipboard
category. That is important for Jewel subtypes and Tablet families.

### Zero-impact contract

Phase 1 deliberately does not:

- add columns to `*_agg_parsed.parquet`;
- add `affix_max` or contributor-count features to model matrices;
- alter the existing summation of effective explicit/implicit/enchant values;
- change training configuration, model artifacts, scalers, or predictions;
- change Craft Oracle runtime behavior yet.

Tests compare parsing with and without the observer to ensure the returned
DataFrame is identical.

## Phase 2: runtime consumption and delivery

Phase 2 is complete:

1. The exact catalog filename is included in supervised-model asset selection in
   `tools/write_update_manifest.py` and `Update-Release.ps1`.
2. The supervised artifact release gate validates schema version, entry
   structure, positive intrinsic maxima, ordinary affix tiers, and coverage for
   every category advertised by `feature_importances_index.json`.
3. Runtime loads it through
   `asset_paths.resolve_asset_file("super_models", ...)` with an
   mtime-aware cache, allowing updater-delivered data to replace bundled data
   without a stale process cache.
4. Craft Oracle maxima lookup uses
   `normalize_item_category(prepared.model_category)`.
5. A missing, corrupt, unsupported, or category-incomplete catalog produces a
   clear user-facing failure. The source-parquet and compact-matrix fallbacks
   have been removed.
6. The catalog remains in the updater's `super_models` consistency bucket so model
   and catalog updates roll back together if a download is incomplete.

Release builds also assert that both Windows and Linux portable archives
contain the catalog at the expected bundled asset path. This closes the gap
between selecting the release asset and actually making it available offline
inside a fresh installation.

The catalog remains a generated, Git-ignored training artifact. No empty
placeholder is synthesized for a build: the category parse stage must have
produced current coverage before release, and the release gate fails explicitly
if the file, schema, active category, or required pattern metadata is missing.

Older application builds will ignore the additional JSON asset. New builds will
bundle it and can therefore require it without depending on a successful first
online update.

## Phase 3: target-aware simulation

Phase 3 is complete. Catalog values remain intrinsic and target-independent;
simulation now applies only local effects parsed from the selected clipboard
item.

### Roll spaces

Each candidate has three deliberately separate values:

- `intrinsic_roll`: the ordinary-affix ceiling read from the catalog;
- `effective_roll`: the magnitude the affix would display on this target;
- `feature_roll`: the increment inserted into the prepared model feature row.

Let `I` be the intrinsic roll, `M` the sum of matching `increased Explicit X
Modifier magnitudes` effects on the target, and `Q` its matching typed jewellery
quality. Display space is:

```text
effective_roll = I * (1 + (M + Q) / 100)
```

The normal ring/amulet/belt pipeline deflates a matching typed-quality modifier
by `1 + Q / 100` before inference. Craft Oracle performs the same normalization:

```text
feature_roll = effective_roll / (1 + Q / 100)
```

For targets without matching typed quality, `Q` is zero and the effective and
feature rolls are identical.

Examples:

| Target state | Intrinsic | Effective display | Model increment |
| --- | ---: | ---: | ---: |
| No local amplification | 45 | 45 | 45 |
| 30% explicit Resistance magnitude | 45 | 58.5 | 58.5 |
| The same 30% effect plus 20% matching quality | 45 | 67.5 | 56.25 |

The final row demonstrates why quality cannot simply be multiplied into the
prepared feature: the ordinary runtime feature builder would divide that
quality back out. The 30% target effect remains represented, while the 20%
typed-quality display effect is not counted twice.

### Scope mapping

The copied-item format exposes the magnitude-effect description but not a
standalone affix-tag database. Mapping is therefore deterministic and
conservative:

- exact patterns from `ring_amulet_quality_lookup.json` are reused for matching
  typed quality and corresponding named scopes;
- canonical pattern words map the observed Chaos, Cold, Critical, Elemental
  Damage, Fire, Lightning, Mana, Physical, Resistance, and Speed scopes;
- Elemental Damage requires both a damage pattern and an elemental/fire/cold/
  lightning term, so elemental resistance is not accidentally amplified;
- an unknown scope applies no amplification instead of guessing.

This registry covers every explicit-magnitude scope observed in the current
training listings and is exercised as a fixed contract in unit tests. Multiple
matching target effects add together, matching the displayed structured-listing
examples used to verify the rule.

### Feature transforms and UI

Direct features receive `feature_roll`. Derived armour and weapon-DPS candidates
receive the same value before continuing through their existing normalized
AR/EV/ES and component-DPS transformations. Plain armour/weapon quality remains
outside this calculation because it changes base item stats, not the magnitude
of the appended explicit affix.

Every Craft Oracle presentation route now shows both values when they differ:

```text
#% to fire resistance: intrinsic 45; effective 58.5
```

Rows with no target amplification retain the compact single-value display. The
resident presenter payload carries numeric intrinsic and effective values, so
formatting cannot silently replace the value used for prediction.

Amplification found on any training/source item is absent from the catalog and
can never carry over. Only the selected target's parsed modifiers and typed
quality participate in this phase.

## Phase 4: hardening and eligibility

Phase 4 is complete.

### Evidence and coverage thresholds

Structural JSON validity is not sufficient evidence that an observed maximum is
safe to ship. Every active model category now has the following shared release
and runtime requirements:

| Requirement | Minimum |
| --- | ---: |
| Accepted target items (`items_seen`) | 10 |
| Accepted ordinary contributors | 10 |
| Observations for every candidate pattern | 2 |
| Usable structured evidence | 50% |

Usable structured evidence is calculated as:

```text
accepted contributors
------------------------------------------------------------
accepted + legacy + missing contributors + missing magnitudes
```

Special domains and nonordinary P0/S0 tiers are intentionally excluded from
this denominator. They are valid observations of data that Craft Oracle must
reject, not failures to decode an otherwise eligible contributor.

The release validator applies these thresholds only to categories advertised by
the active `feature_importances_index.json`. A missing audit field, low category
volume, low pattern evidence, or insufficient usable coverage blocks release.
Runtime validates the same readiness contract and fails closed if an incomplete
catalog is installed outside the normal release path.

Catalog production excludes candidate patterns below the pattern evidence
minimum. Their observations still contribute to the category audit statistics,
but they are not serialized as Craft Oracle candidates. The validator retains
the minimum check so malformed, hand-edited, or older artifacts containing a
singleton pattern still fail closed.

The constants live with catalog production/runtime validation so the producer,
consumer, and release-gate tests share one definition rather than maintaining
independent policy values.

### Training audit report

Every parse run prints a deterministic Craft Oracle audit section after its
category work. The normal database pipeline already tees parse output into its
per-run `parse.txt`, so the audit becomes part of the persistent training report
without creating another runtime asset.

For each selected category the report includes:

- ready/not-ready status, accepted items, pattern count, retained tier count,
  accepted contributors, and usable-evidence percentage;
- skipped legacy entries, missing contributor structures, missing magnitudes,
  nonordinary tiers, and special/crafted/fractured/desecrated domains;
- each concrete readiness failure with its actual and required value;
- explicit notice when an empty category removes a stale catalog entry.

Partial developer parses are allowed to finish and write their atomic sidecar,
but their report says `NOT READY`. This preserves iterative training workflows
while ensuring release/runtime gates cannot silently treat the partial result as
production evidence.

### Item-level eligibility

The structured catalog already records the required level of the contributor
that supplied each maximum. Craft Oracle now parses the target clipboard's
`Item Level` and excludes a candidate when its catalog maximum requires a higher
level. At the end of Phase 4 it did not substitute a lower tier because the
catalog stored only the observed intrinsic ceiling; inventing a lower-tier roll
would have reintroduced an unsupported data source. Phase 5 resolves this by
retaining lower tiers from the same structured evidence stream.

### Prefix/suffix capacity

The catalog's `affix_sides` metadata is now carried into runtime candidate
entries. The target's advanced-description Prefix/Suffix headers are counted
against the ordinary three-prefix/three-suffix capacity:

- a prefix-only candidate is excluded when three prefixes are present;
- a suffix-only candidate is excluded when three suffixes are present;
- a pattern observed on both sides remains eligible if either side has room.

Side filtering is deliberately conservative, and it is driven by the parser's
affix-level metadata rather than by counting feature slots. The clipboard parser
groups explicit lines back to the header that produced them, so a composite line
expanded into two slots and a hybrid affix printed across two lines both count
as one affix with one side. Filtering runs when every explicit affix declared a
Prefix/Suffix side; basic clipboard copies and side-less
fractured/desecrated/corruption headers leave capacity unknown and fail open.
Item-level filtering remains safe and active independently.

An earlier version compared recognized headers against the parser's
*expanded slot* count. Those two numbers can never agree on an item carrying a
dual-attribute or dual-resistance roll, so side filtering silently switched
itself off for a large share of real rares.

Each result row retains `affix_sides`, `required_level`, and `observations`, and
the resident presenter payload carries that metadata for Phase 7 presentation.

### Remaining simulator boundaries

Phase 4 does not claim full game-engine legality. Affix groups, tag-based group
conflicts, spawn weights, influence/domain restrictions beyond catalog
production, and crafting-method rules remain outside Craft Oracle's
counterfactual model analysis. Unknown side metadata never hides a candidate.

## Phase 5: observed tier-ladder fallback

Phase 5 is complete. It addresses the first remaining simulator limitation
without importing a game-data affix database or changing the pricing pipeline.

### Additive catalog representation

Every newly collected pattern retains one deterministic record for each
observed ordinary `P1+`/`S1+` tier. A tier record contains:

- the tier label, whose `P` or `S` prefix is the authoritative affix side;
- that tier's highest intrinsic structured `magnitudes[].max` scalar;
- the required level attached to the observation that supplied that maximum;
- the total number of accepted observations for the tier.

The existing pattern-level fields remain as a summary of the strongest tier:

```json
{
  "maximum_roll": 45.0,
  "affix_sides": ["suffix"],
  "winning_tier": "S1",
  "required_level": 82,
  "observations": 150,
  "tiers": [
    {
      "maximum_roll": 45.0,
      "tier": "S1",
      "required_level": 82,
      "observations": 40
    },
    {
      "maximum_roll": 35.0,
      "tier": "S2",
      "required_level": 60,
      "observations": 110
    }
  ]
}
```

Contributors are still never summed. Observations of the same tier increase
that tier's evidence count and may replace only its maximum. Different tiers
remain distinct even when they canonicalize to the same model-feature pattern.

Schema version 1 is intentionally retained because `tiers` is additive. Older
application builds continue reading the unchanged summary fields. New builds
also accept a pre-Phase-5 catalog by treating its summary as a one-tier ladder;
the next category parse refreshes it with all observed tiers. This avoids a
forced asset migration or a partial-parse reset of unrelated categories.

### Deterministic integrity contract

Runtime loading and the release gate share the same ladder validation. For a
new ladder to be accepted:

- it must be a non-empty list of unique ordinary tier labels;
- every maximum must be finite and positive;
- every observation count must be a positive integer;
- required levels must be absent or non-negative integers;
- tier observation counts must sum to the pattern summary's observations;
- tier-derived prefix/suffix sides must exactly match `affix_sides`;
- the strongest tier, using the producer's deterministic tie-break, must match
  `maximum_roll`, `winning_tier`, and `required_level` in the summary.

The pattern-level evidence threshold remains authoritative. Tier records do not
introduce a second release threshold: they partition evidence that Phase 4
already accepted, and even the former single maximum could be supplied by one
observation inside a multi-observation pattern. The tier-specific count is
retained in result metadata so a later policy can tighten this independently.

### Joint item-level and side selection

Craft Oracle evaluates all tier records for a pattern against the selected
target before simulation:

1. If item level is known, discard tiers whose known required level is higher.
2. If complete advanced Prefix/Suffix headers are known, discard tiers whose
   side has no remaining slot.
3. Select the remaining tier with the greatest intrinsic maximum.
4. Resolve equal maxima deterministically by tier label and then required level.
5. Apply the Phase 3 target-amplification and feature-normalization rules to
   that selected intrinsic roll.

Item level and side capacity are evaluated together. For example, if an `S1`
ceiling is above the target's item level, `S2` is used when observed and legal.
If all suffixes are full but the same canonical pattern also has an observed
prefix tier, the strongest eligible prefix tier is used instead. This avoids
incorrectly applying a suffix maximum merely because the pattern appeared on
both sides somewhere in training.

Missing item level and incomplete side headers retain the established fail-open
policy. They select from all observed tiers rather than guessing that a tier is
illegal. A legacy one-tier catalog retains exactly the Phase 4 behavior.

### Result metadata and zero-impact boundary

Craft Potential rows now report the selected tier, selected required level,
selected side, tier observation count, and total pattern observation count.
The resident presenter transport carries those fields for Phase 7 to render.

Phase 5 changes only sidecar collection, validation, Craft Oracle candidate
selection, and diagnostic result metadata. Parsed DataFrames, aggregate
parquets, model feature columns and values, KNN distances, supervised training,
and baseline price predictions remain byte-for-byte on their existing paths.
Tags, weights, affix groups, influence restrictions, and crafting-method rules
remain outside this phase.

## Phase 6: observed affix-identity collision guard

Phase 6 is complete. It is the first affix-conflict phase and deliberately uses
only an identity exposed on both sides of the workflow.

### Available identity evidence

Each structured ordinary contributor carries a display name such as
`Glimmering`, `Rotund`, or `of the Volcano`. PoE's advanced clipboard format
places that same name in quotes in the corresponding header:

```text
{ Suffix Modifier "of the Volcano" (Tier: 3) — Elemental, Fire, Resistance }
```

Neither representation exposes the underlying game affix-group ID. Tags shown
after the dash are descriptive spawn tags, not a sufficient group identity.
Phase 6 therefore treats an exact contributor-name match as evidence and does
not infer conflicts between different names, even when they look related.

Names are canonicalized by collapsing whitespace, trimming, and Unicode-aware
case folding. Punctuation and apostrophes remain significant. This maps header
capitalization differences safely while avoiding fuzzy name matching.

Identity association is accepted only from a structured parent with exactly
one contributor. Multi-contributor transformed parents prove each intrinsic
roll but do not prove which native contributor name belongs to the flattened
final pattern. Across the category, that name must also map consistently to one
canonical pattern signature. A name observed under multiple signatures is
withheld everywhere instead of selecting one mapping heuristically.

### Additive catalog metadata

Newly parsed pattern summaries and tier records include sorted `affix_names`
lists. The pattern list is the union of every accepted ordinary contributor
name that produced the canonical pattern; each tier list contains only names
observed for that tier.

The field is additive under schema version 1. A pre-Phase-6 catalog has no name
metadata and loads as an empty identity set, retaining its prior eligibility
behavior until parsing refreshes the category. Missing contributor names do
not discard otherwise valid intrinsic-roll evidence.

Shared runtime/release validation requires name metadata, when present, to be
a list of non-empty identities with no duplicates after normalization. The
union of tier identities must exactly equal the pattern summary identities.
This prevents a corrupt summary from excluding candidates under names that its
tier evidence never supplied.

The parse audit reports the number of unique retained identities alongside
items, patterns, tiers, contributors, and usable evidence. Identity count is
diagnostic rather than a release threshold because older listing payloads and
older installed catalogs can legitimately omit names.

### Target extraction and conflict rule

Craft Oracle reads quoted names only from headers that are independently
recognized as Prefix/Suffix modifier headers. Crafted, fractured, and
desecrated Prefix/Suffix headers are included because those existing modifiers
can still occupy an identity that an ordinary append must not duplicate.

Name trust is independent of the Phase 4 side-capacity completeness rule. One
recognized quoted header provides an exact identity even when other explicit
headers are missing names. Incomplete side coverage still disables only side
capacity filtering.

Before item-level and side-specific tier selection, a candidate pattern is
excluded when:

```text
target named affixes ∩ catalog pattern affix_names != empty
```

Checking the pattern-level union is intentional. It prevents a lower or higher
tier of a contributor already present on the target from being treated as a
new candidate. It also protects transformed or multi-stat descriptions where
the target's flattened canonical patterns no longer provide a reliable exact
feature-pattern match, but the advanced affix identity survives.

### Fail-open and zero-impact boundaries

Basic clipboard copies, unnamed advanced headers, unknown contributor names,
and legacy catalogs provide no identity evidence and therefore do not remove a
candidate. There is no fuzzy string matching, tag-based inference, or learned
co-occurrence grouping.

Phase 6 changes only sidecar identity metadata, its audit/validation, and Craft
Oracle candidate eligibility/result diagnostics. It does not change parsed
training rows, feature matrices, KNN distances, model artifacts, supervised
inputs, baseline predictions, or the Phase 3 roll transforms.

Different names belonging to the same hidden game affix group remain outside
this phase. A future implementation requires an authoritative group database
or an equally explicit join key; spawn weights, influence restrictions, and
crafting-method rules also remain unresolved.

## Phase 7: selected-tier provenance presentation

Phase 7 is complete. It closes a presentation gap left by Phase 5: the runtime
selected a concrete target-eligible tier and retained its evidence, but the UI
showed only the resulting intrinsic/effective number. A legitimate fallback
from an observed S1 roll to an item-level-eligible S2 roll could therefore look
like an unexplained reduction or an aggregated stat.

### Display contract

Every Craft Oracle roll label now appends a compact provenance suffix:

```text
#% to fire resistance: intrinsic 45; effective 58.5 [S2 suffix · ilvl 60 · 6 obs]
```

The fields mean:

- `S2 suffix` is the exact tier and side selected for this target;
- `ilvl 60` is that observed tier's required item level;
- `6 obs` is the number of accepted structured contributors for that tier.

When intrinsic and effective values are equal, the concise value form remains,
followed by the same provenance. The total pattern observation count is not
substituted for tier evidence. A compatibility payload that has only the older
pattern count labels it explicitly as `pattern obs`, preventing it from being
misread as evidence for the selected tier.

### One formatter for both presentation routes

The resident Craft Oracle view receives `CraftPotentialRow` objects. The
isolated popup receives ordinary mapping payloads from the worker process.
Both now call the dependency-free `poe2trade.utils.craft_display` formatter,
which accepts either shape. This preserves the popup's lightweight import
boundary while preventing the two result views from acquiring different value
or provenance conventions.

Optional metadata is rendered only when it is structurally valid. Missing
fields preserve the prior roll text, which keeps older worker payloads readable.
Invalid tier labels, negative levels, non-positive counts, booleans, and
non-finite values are omitted rather than displayed as apparent evidence.

### Zero-impact boundary

Phase 7 does not alter catalog extraction, tier selection, target amplification,
feature construction, ranking, or prediction. It formats metadata already
present in every newly produced result row. Parsed training rows, feature
matrices, KNN distances, supervised artifacts, and baseline predictions are
unchanged.

## Validation and acceptance criteria

The complete rollout is accepted when:

- a three-contributor displayed `224%` resistance produces a catalog maximum of
  `45%`;
- a four-contributor displayed `304%` resistance also produces `45%`;
- implicit, crafted, desecrated, fractured, P0, and S0 entries cannot influence
  the catalog;
- partial category rebuilds are atomic and do not delete unrelated categories;
- every active model category maps to exactly one canonical catalog key;
- existing parsed DataFrames and feature matrices remain schema/value identical;
- baseline KNN and supervised predictions remain unchanged;
- Craft Oracle has no aggregated-data fallback after Phase 2;
- updater and package tests prove the catalog is co-versioned with the models;
- a target with 30% explicit Resistance magnitude maps intrinsic `45` to
  effective/model `58.5` without changing the catalog;
- matching typed quality appears in the effective UI roll but is divided back
  out of the prepared model increment exactly once;
- derived weapon/armour candidates still use their established feature-space
  transforms after target amplification;
- release and runtime reject low-volume, low-coverage, or single-observation
  catalog data;
- parse-stage training reports expose accepted and skipped catalog evidence;
- item level and trustworthy prefix/suffix capacity exclude impossible catalog
  ceilings without guessing when side metadata is incomplete.
- per-tier maxima remain separate and their evidence sums back to the unchanged
  pattern summary;
- a target below the global ceiling's required level receives the strongest
  observed lower tier instead of losing the whole pattern;
- item-level and side-capacity constraints select one jointly eligible tier,
  while missing target metadata continues to fail open to the global ceiling.
- contributor identities are normalized and retained without affecting roll
  aggregation, and tier identities union exactly to the pattern summary;
- multi-contributor parents and names with conflicting pattern signatures do
  not create identity exclusions;
- an exact named advanced-header collision excludes the corresponding observed
  pattern before tier simulation, including transformed/hybrid descriptions;
- unnamed headers, legacy catalogs, and different affix names fail open rather
  than inferring unavailable game group relationships;
- resident and isolated result routes show the same selected tier, side,
  required item level, and tier-specific evidence count;
- older payloads without provenance metadata retain their prior readable roll
  text, and pattern-level fallback evidence is labeled unambiguously.
