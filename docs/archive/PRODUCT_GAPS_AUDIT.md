# Product gaps audit — post Craft Oracle / DPS / UI work

> Archived 2026-09-03. Resolved findings remain here as evidence; unresolved
> decisions were consolidated into `docs/IMPLEMENTATION_NOTES.md`.

Date: 2026-08-08
Scope: the three recent workstreams and what they left open.

> **Status.** Items 2, 3, 4, 5, 6, 7, 8, 9, 11, and 12 are fixed; each is marked
> `[fixed]` below with what changed. Items 1 and 10 change the trained feature
> space and are deliberately **not** applied here — they need a retrain and a
> before/after comparison, and shipping either without one would leave inference
> reading a different feature space than the installed models were trained on.
> Item 1 is now recorded as a warning block in `docs/WEAPON_FEATURES.md` so it
> cannot be mistaken for correct. Items 13, 14, and 15 remain backlog/verify;
> 15 is now at least documented in `WEAPON_FEATURES.md`.

- **Craft Oracle** — `ffe5235` → `dcc4506` (intrinsic affix catalog, phases 1–7).
- **Damage calculations** — `8483cbe` "correct weapon DPS and compact result views".
- **UI/stash stream** — `f306768` (cp1252 repair), `fd03b22`/`ecffb9b` (unpriced
  stash items), `8b55ac3`/`ae84915`/`9836fc6`/`4f3121d` (stash scrape results),
  and the popup/overlay churn on `codex/unified-stashsage-ui`.

Method: read the diffs and the surrounding runtime paths, then reproduce the
suspected defects against the real code. Findings marked **reproduced** were
executed locally, not inferred.

---

## Priority list

| # | Severity | Area | Gap |
|---|---|---|---|
| 1 | P0 | Damage | **open (needs retrain)** — Weapon quality/rune deflation stacks multiplicatively; PoE local increases are additive. Model DPS is wrong and the error scales with the item's own phys%. |
| 2 | P0 | Craft Oracle | **fixed** — Composite affixes inflated the explicit-slot count, so legal items were rejected as "six explicit modifiers". |
| 3 | P1 | Craft Oracle | **fixed** — The same inflation silently disabled the Phase 4/5 prefix/suffix capacity filter on most real rares. |
| 4 | P1 | Craft Oracle | **fixed** — Corrupted items were accepted and given craft recommendations that cannot be executed in game. |
| 5 | P1 | Craft Oracle | **fixed** — Flat **physical** damage candidates ignored the target's own `#% increased physical damage`. |
| 6 | P1 | Process | **fixed** — No automatic CI. `tests.yml` was `workflow_dispatch` only; the whole Craft Oracle series ran no automated checks. |
| 7 | P1 | Damage | **fixed** — The `_model_dps_*` staging handshake had no test pinning the required call ordering. |
| 8 | P2 | Stash/UI | **fixed** — The "unpriced ≠ 0" fix covered only the scored path; pad/fallback/unscored rows still wrote `0.0`. |
| 9 | P2 | Craft Oracle | **partly fixed** — Delta precision no longer collapses to `+0e`; uncertainty, hit probability, and crafting cost remain absent. |
| 10 | P2 | Pricing | **open (needs retrain)** — Corrupted/fractured/sanctified are parsed but disabled as model features. |
| 11 | P2 | Damage | **fixed** — `#% to critical hit chance` was dropped from weapon features *and* had no Craft Oracle path. |
| 12 | P2 | Craft Oracle | **fixed** — `_intrinsic_value` averaged unrelated magnitudes on genuine hybrid affixes. |
| 13 | P3 | Craft Oracle | Catalog ceilings are observed maxima with no outlier guard, and a pattern ships on 2 observations. |
| 14 | P3 | Stash | Merchant mode now requests `sale_type: any` while still sorting `price: asc` — verify unpriced listings are reachable. |
| 15 | P3 | Damage | Wand/sceptre/staff have no base damage or attack speed features at all; `WEAPON_FEATURES.md` reads as if all weapons share the bow representation. |

---

## P0 findings

### 1. Weapon quality/rune deflation uses the wrong stacking rule

`compute_bow_dps_features` (`poe2trade/utils/parse_utils.py:306`) removes quality
and rune physical-percent by **dividing multiplicatively**:

```python
denom = (1.0 + quality / 100.0) * (1.0 + rune_phys_pct / 100.0)
avg = avg / denom - rune_flat[damage_type]
```

In PoE, weapon quality grants a *local increased physical damage* modifier, and
local increases are **additive** with each other and with explicit
`#% increased Physical Damage`. The displayed average is therefore

```text
displayed = base * (1 + (Q + explicit% + rune%) / 100)
```

Dividing by `(1 + Q/100)(1 + rune%/100)` does not recover
`base * (1 + explicit%/100)`, which is what `WEAPON_FEATURES.md` states the
feature is supposed to be. Reproduced against the real function:

| Quality | explicit phys% | displayed avg | `dps_physical` | intended | error |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 100.0 | 150.00 | 150.00 | 0.00% |
| 0 | 150 | 250.0 | 375.00 | 375.00 | 0.00% |
| 20 | 0 | 120.0 | 150.00 | 150.00 | 0.00% |
| 20 | 100 | 220.0 | 275.00 | 300.00 | **−8.33%** |
| 20 | 150 | 270.0 | 337.50 | 375.00 | **−10.00%** |

Two properties make this worse than a constant bias:

- The error is **zero at 0% quality and grows with explicit phys%** — i.e. it is
  correlated with the single biggest value driver on the item, so it is not
  absorbed as noise; it distorts the learned slope on `dps_physical`.
- It is **inconsistent between two items with identical real stats**, because a
  20%-quality copy and a 0%-quality copy of the same weapon land on different
  feature values.

A second, smaller order-of-operations bug sits in the same expression:
`rune_flat` is subtracted *after* the division, but local flat added damage is
scaled by local increases, so it should be removed from the deflated value in
the same space it was added.

This survived the recent DPS work because `8483cbe` only fixed the **display**
side (`compute_displayed_weapon_dps_features`, `parse_utils.py:336`). The commit
message and `WEAPON_FEATURES.md` now read as though weapon DPS is corrected,
which makes this the most likely gap to stay hidden.

Note the internal inconsistency: `craft_potential._simulate_derived_feature`
gets attack-speed stacking **right** (additive, `(1+(cur+v)/100)/(1+cur/100)`),
so the two halves of the codebase disagree about how PoE stacks local increases.

Fix sketch: deflate with a single additive denominator
`1 + (Q + rune_phys%) / 100` after removing rune flat in displayed space, and
retrain. Any change here invalidates existing model artifacts, so it needs to
land with a retrain and a pinned before/after comparison on a held-out set.

### 2. Craft Oracle rejects legal items with composite affixes

`validate_item` (`poe2trade/utils/craft_potential.py:111`) counts
`explicit_mod_\d+` slots and rejects at `>= 6`. But the clipboard parser expands
composite lines **before** slotting (`gui_utils.py:454` → `_expand_composite_line`),
so `+18 to Strength and Intelligence` becomes two slots and
`+25% to Fire and Lightning Resistances` becomes two more.

Reproduced — a glove with **four** affixes (1 prefix, 3 suffixes, two open
prefix slots):

```text
explicit_mod_1 => +45 to maximum Life
explicit_mod_2 => +18 to Strength
explicit_mod_3 => +18 to Intelligence
explicit_mod_4 => +25% to Fire Resistance
explicit_mod_5 => +25% to Lightning Resistance
explicit_mod_6 => 12% increased Attack Speed
explicit slot count: 6  | real affixes: 4

REJECTED: Craft Potential only supports rare items with fewer than six explicit modifiers.
```

Dual-attribute and dual-resistance affixes are among the most common rolls in the
game, so this is not an edge case — it turns the feature off for a large share of
craftable items, and the error message tells the user something factually untrue
about their item.

Fix sketch: count **affixes**, not feature slots. The advanced clipboard already
gives an exact count via recognized Prefix/Suffix headers; for basic copies,
count distinct pre-expansion mod lines rather than post-expansion slots.

---

## P1 findings

### 3. Side-capacity filtering silently disables on the same items

`_target_affix_eligibility` (`craft_potential.py:142`) sets
`sides_known = len(sides) == explicit_count` (`:171`) — recognized headers versus
post-expansion slots. Any composite affix makes those numbers disagree.

Reproduced on a 3-affix glove with one composite suffix:

```text
composite item: slots 4  headers p/s 1 2  sides_known False
  -> side-capacity filter DISABLED (fails open)
```

Failing open is the right *policy* — it is better to over-offer than to hide a
valid candidate. The gap is that the trigger is wrong: capacity is disabled by
an unrelated parser artifact rather than by genuinely missing metadata. Phases 4
and 5 (item-level + side joint tier selection) are advertised as complete, but
the side half is inert on any item carrying a dual-attribute or dual-resistance
roll. Fixing #2 fixes this too — they share one root cause.

### 4. Corrupted items receive craft recommendations

`validate_item` checks rarity and modifier count only. Reproduced:

```text
CORRUPTED item accepted by Craft Oracle: 2 slots; sides_known: True
  | Corrupted flag parsed: Yes
```

A corrupted rare cannot receive new explicit modifiers by any ordinary means, so
every row Craft Oracle returns for it is unactionable. The signal is already
parsed and sitting in the same dict (`gui_utils.py:281`, `"Corrupted": "Yes"`),
so this is a two-line guard with a clear user-facing message.

Worth confirming the same treatment for Mirrored items if that state is
reachable in the current league.

### 5. Flat physical damage candidates are understated

In `_simulate_derived_feature` (`craft_potential.py:340`):

```python
attack_speed = float(raw.get("attack_speed", 0) or 0)
increment = value * attack_speed
```

The target's `dps_physical` is in **deflated model space**, which still contains
the item's explicit `#% increased Physical Damage`. A newly added flat physical
affix is also scaled by that same local increase, so the correct increment is
`value * (1 + explicit_phys% / 100) * attack_speed`.

This is correct as written for fire/cold/lightning/chaos — flat elemental is not
scaled by increased *physical* damage — so the fix is physical-only. The practical
effect is that Craft Oracle systematically under-ranks flat-phys crafts on
exactly the high-phys% weapons where they are most valuable, and the
`#% increased physical damage` branch immediately above it will out-rank them.

### 6. No automatic CI on this repository

- `.github/workflows/tests.yml` triggers on `workflow_dispatch` **only**. Its own
  header calls it "Manual fallback CI only".
- `.github/workflows/gui-overlay.yml` runs on PR/push but is restricted to four
  paths (`prediction_presenter.py`, `prediction_popup.py`, its test, and a
  fixture) and to `branches: [main, "codex/**"]`.

Consequence: the entire Craft Oracle series — new modules
`craft_affix_catalog.py`, `craft_display.py`, plus changes to `craft_potential.py`,
`parse_cat.py`, and the release validator — landed on `agent/craft-oracle-…` with
**no automated test run at all**. The gate is `python -m poe2trade.db test`, which
does run the full suite (`poe2trade/db/__main__.py:40`), but only when a developer
runs it locally before a release.

Given the change volume in this window, this is the highest-leverage process fix:
add `pull_request` and `push` triggers to the pytest job, and widen the branch
filter to include `agent/**` and `claude/**`.

### 7. The DPS model/display handoff is untested anywhere

`8483cbe` routes model DPS through `_model_`-prefixed keys stashed in
`deflator_and_normaliser` (`gui_utils.py:550`) and unpacked in
`cleanup_unused_features` (`gui_utils.py:668`). The comment explains why:

```text
The API builds its target-item payload before cleanup, when dps_* contains
actual displayed DPS. Inference happens after cleanup and must retain the
historical quality/rune-deflated model features.
```

That is a contract with `StashSage_Serve`, expressed as a key-naming convention
and an implicit call ordering.

Correction to an earlier draft of this audit: the *split itself* was already
covered in-repo, by
`test_talisman_keeps_actual_display_dps_separate_from_model_dps`, which asserts
both `prepared.features` and `prepared.display_features`. What had no coverage
was the **ordering** — nothing failed if a caller ran
`deflator_and_normaliser` without `cleanup_unused_features`, which is the actual
failure mode, and there is exactly one caller of the pair in this repo to
demonstrate it. The end-to-end serve behaviour is also unverified here: the test
that would cover it, `tests/test_serve_api_contract.py`, begins with:

```python
SERVE_ROOT = Path(__file__).resolve().parents[2] / "StashSage_Serve"
if not SERVE_ROOT.is_dir():
    pytest.skip("StashSage_Serve checkout is not available", allow_module_level=True)
```

**Fixed**, partially. `test_model_dps_staging_contract_between_normaliser_and_cleanup`
now pins the handshake directly: every `BOW_DPS_COLUMNS` entry must be staged
under `_model_*` after `deflator_and_normaliser`, the staged model value must
differ from the displayed one, and `cleanup_unused_features` must promote each
one back and remove the staging key. A refactor that drops either half now
fails loudly.

Replacing the mutation protocol with an explicit return value would be better
still, but it would break `StashSage_Serve`, which is not visible from this
repo. That belongs in a coordinated change across both repositories, and the
end-to-end serve assertion stays skipped until a checkout is present.

---

## P2 findings

### 8. The unpriced-item fix is only half applied

`fd03b22` changed the scored path to leave unpriced listings blank
(`scrape_stash_utils.py:1333`) with the rationale "zero would look like a real
asking price". The other price-producing paths in the same file were not changed
and still emit `0.0`:

- `:1019` unscored aggregate rows — `fill_value=0.0`
- `:1257` blank frame construction — `[0.0 for _ in range(n)]`
- `:1278` default tuple — `("price", 0.0)`
- `:1291` short-chunk padding — `[0.0]*(n-len(chunk))`

So the misleading `0` still appears, and it now appears specifically on rows that
failed scoring — the ones a user is least equipped to sanity-check. Worse, `price`
is now mixed-semantics across rows in a single result table.

### 9. Craft Oracle deltas are presented with false precision

`prediction_presenter.py:1311`/`:1319` render each row as `{delta:+.0f}e`. Three
problems:

- **No uncertainty.** The delta is a difference of two XGBoost point estimates.
  Nothing in the row indicates whether `+3e` exceeds the model's own error on
  either prediction. Rows are sorted strictly by `-delta`
  (`craft_potential.py:483`), so noise-level differences determine the ranking.
- **No probability or cost.** Every row assumes the affix lands at its selected
  tier ceiling. There is no spawn weight, no attempt count, no currency cost. The
  docs are explicit that this is out of scope, but the UI presents a ranked list
  of gains, which reads as advice.
- **Rounding.** `+.0f` collapses every sub-1-exalt delta to `+0e`, so on cheap
  items the entire ranked list displays as zeros while still being ordered.

The name "Craft Oracle" sets an expectation of expected value; the feature
delivers a sensitivity analysis. Either narrow the label/subtitle, or add the
missing terms. At minimum: show one decimal below 10e, and suppress or grey rows
whose delta is inside the model's reported error band.

### 10. Corrupted/fractured/sanctified are parsed but not modelled

`ITEM_STATUS_FEATURES` exists (`parse_utils.py:38`) and both the JSON and
clipboard parsers populate it, but it is gated behind
`item_status_feature_flag`, which defaults to `False` (`poe2trade/__init__.py:82`).
The pricing model therefore cannot distinguish an item that can still be crafted
on from one that cannot — a real and sometimes large price difference on
otherwise-identical rares. This is also the feature that would let #4 be handled
by the model rather than by a hard guard.

Turning the flag on requires a reparse and retrain, so treat it as a scheduled
experiment with a before/after metric, not a config flip.

### 11. Critical hit chance is invisible to both the model and Craft Oracle

`DPS_WEAPON_OMITTED_MOD_PATTERNS` (`parse_utils.py:190`) adds
`#% to critical hit chance` to the skip set, on the grounds that the displayed
critical property already encodes it. That holds for the pricing model, which
carries `crit_chance` as a feature.

But Craft Oracle's candidate filter keeps a pattern only if it is a model feature
or in `BOW_DPS_ENCODED_PATTERNS` (`craft_potential.py:427`), and
`#% to critical hit chance` is in neither set. So a crit-chance craft — a
significant weapon value driver — is silently dropped from the candidate list
with no explanation to the user. It needs a derived branch in
`_simulate_derived_feature` alongside the DPS ones.

### 12. `_intrinsic_value` averaging is unsafe for hybrid affixes

`craft_affix_catalog.py:115`:

```python
value = (maxima[0] + maxima[-1]) / 2.0
```

For `Adds # to # X Damage` this is right — the two magnitudes are the ends of one
range and the average matches `parse_rolled_mod`'s convention. For a genuine
hybrid affix with two *unrelated* magnitudes (flat + percent, or two different
stats), the average is a meaningless scalar. That scalar is then written to
**every** expanded pattern from the parent description (`:302`), so both halves of
the hybrid inherit it.

Suggested guard: when the parent expands to more than one canonical pattern *and*
the contributor carries more than one magnitude, either match magnitudes to
patterns positionally or skip the contributor and count it in
`skipped_missing_magnitudes`. Silently averaging is the one option that produces
confident bad data.

---

## P3 / verify

### 13. Catalog ceilings have no outlier guard

`MIN_PATTERN_OBSERVATIONS = 2` (`craft_affix_catalog.py:36`). A pattern ships once
two structured contributors are seen, and the retained value is the **maximum**
observed. A single mis-parsed or anomalous magnitude therefore sets that pattern's
ceiling permanently for the category, with no trimmed statistic and no sanity
bound. Because the ceiling propagates into every counterfactual, one bad
observation shifts an entire pattern's ranking.

Consider recording the top-2 maxima per tier and rejecting a maximum that exceeds
the runner-up by more than a set factor, or requiring ≥2 observations *at the
winning tier* rather than at the pattern.

Related and already documented: the catalog ceiling is the highest value seen in
**listings**, not the game's true maximum. Worth stating in the UI, since users
will read "intrinsic 45" as authoritative.

### 14. Merchant search sale type vs. price sort

`ecffb9b` changed merchant mode to `("securable", "any")` so unpriced records are
not excluded (`scrape_stash_utils.py:65`), but the query still sorts
`{"price": "asc"}` (`:595`). Verify that unpriced listings actually appear within
the result cap under a price-ascending sort rather than being pushed past it —
otherwise the fix widens the filter without widening what is returned.

### 15. Weapon feature representation is not uniform, and the doc says it is

`DPS_WEAPON_CATEGORIES` (`parse_utils.py:194`) covers bow, crossbow, both mace
splits, quarterstaff, spear, talisman. Wands, sceptres, and staves are trained
categories (`db/categories.py:17`) but are **not** in that set, while
`BOW_RAW_STAT_COLUMNS` is dropped unconditionally in both the runtime path
(`gui_utils.py:668`) and the matrix path (`matrix_utils.py:323`).

Net effect for wand/sceptre/staff: no `dps_*` features, and no base damage or
attack speed either — the weapon's damage does not reach the model in any form,
while their `Adds # to # X Damage` explicits survive as ordinary direct features
(the skip set is gated on `DPS_WEAPON_CATEGORIES`). That is defensible for caster
weapons whose value sits in skill levels and spell damage, but it is undocumented:
`docs/WEAPON_FEATURES.md` reads as though every weapon shares the bow
representation. Craft Oracle inherits the divergence — a flat-damage candidate on
a wand takes the direct-feature path, on a spear the derived-DPS path.

Also worth a coverage check against the current league's item classes: the raw
folder list has no swords, axes, daggers, claws, or flails. If those exist and are
traded, they are unpriced by the product entirely.

---

## Bad assumptions register

Assumptions currently baked into the code that are worth re-stating explicitly:

1. **Local increases stack multiplicatively.** They don't. (#1) The codebase
   contradicts itself on this point — craft simulation uses additive stacking,
   feature generation uses multiplicative.
2. **One parsed explicit slot equals one affix.** False for every composite
   attribute/resistance roll. (#2, #3)
3. **Any rare with open slots can be crafted.** False for corrupted items. (#4)
4. **A new flat affix enters model space unscaled.** False for physical damage on
   a weapon with increased phys%. (#5)
5. **The mutation ordering between `deflator_and_normaliser` and
   `cleanup_unused_features` will be preserved by all future callers, including
   in another repository.** Enforced by comment only. (#7)
6. **Blank means unpriced.** True in one code path out of five. (#8)
7. **A model point-estimate difference is a decision-grade number.** Presented as
   one, with no error band, probability, or cost. (#9)
8. **Corrupted state does not affect price.** Encoded by leaving the feature flag
   off. (#10)
9. **Two observations are enough evidence to ship a pattern ceiling, and the max
   is the right statistic.** No outlier protection. (#13)
10. **The catalog maximum is the game maximum.** Documented internally as false;
    the UI does not say so.

## Sequencing and status

1. ~~**Now, cheap, no retrain:** #2 + #3 (one root cause), #4, #5, #8, #6.~~ Done.
2. **Next, needs a retrain and a before/after comparison:** #1, then #10 as a
   measured experiment. **Still open** — see below.
3. ~~**Then:** #7, #11, #12, #9.~~ Done, except the parts of #9 that need a
   product decision (uncertainty, hit probability, crafting cost).
4. **Backlog / verify:** #13, #14, #15.

Items 1–5 were all in the two workstreams that had just been declared complete,
which is the main takeaway: the Craft Oracle phase docs and `WEAPON_FEATURES.md`
both read as finished, and that framing is what would have kept these hidden.

### Why #1 and #10 were not applied

Both change what a model feature *means*, not just how it is computed. The
matrices and the runtime share one function, so a code-only change is consistent
only after the next full parse/train/score cycle. Landing either without a
retrain would leave installed model artifacts scoring inputs from a feature
space they were not fitted on — strictly worse than the current known bias.

The intended sequence for #1:

1. apply the additive denominator in `compute_bow_dps_features`, removing
   `rune_flat` in displayed space before deflating;
2. rerun `parse matrix train_super score_super` for every category in
   `DPS_WEAPON_CATEGORIES`;
3. compare held-out error against the current artifacts before publishing.

Craft Potential needs no change in that sequence: since this pass, its weapon
deltas are produced by re-running `compute_bow_dps_features`, so it follows the
corrected definition automatically.

### Notes on this pass

- Turning on PR CI (#6) meant the lint and typecheck gates started blocking, and
  both were already failing on pre-existing issues. Those were fixed here rather
  than left to make every future PR red. Two were real defects that the manual
  workflow had hidden: `prediction_popup.py` referenced an `except ... as exc`
  name inside a deferred Tk callback, where it is already unbound (a `NameError`
  instead of the Craft Oracle error message), and
  `tests/test_prediction_presenter_overlay.py` raised `tk.TclError` without
  importing `tk`, so that test was not exercising the path it claimed.
- `tests/test_pipeline_e2e.py::test_train_score_validate_roundtrip` fails in a
  sandbox without the supervised model artifacts. It fails identically before
  and after this pass; it is an environment gap, not a regression.
- `test_github_actions_are_manual_only` asserted the opposite of #6 and was
  replaced by `test_github_actions_run_on_pull_requests_and_feature_branches`.
  If CI minutes are the reason the workflow was manual, revert that pair of
  changes — the rest of this pass does not depend on them.
