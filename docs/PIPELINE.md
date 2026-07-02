# poe2trade Pipeline Reference — Parse → Matrix → Train → Score

This document describes, in full detail, the offline machine-learning pipeline in
`poe2trade.db`: how raw item JSON becomes feature matrices, trained models, and
the scored statistics the app consumes. It is reference-grade and is meant to be
diffed against the source. Every formula, constant, filename, and routing rule
below is traceable to a specific function in the modules cited per section.

For the quick "how do I run it" version, see [`README.md`](../README.md) and
[`poe2trade/db/readme`](../poe2trade/db/readme). This document is the deep dive.

---

## 0. Orientation — the one idea that organizes everything

The pipeline has six stages:

```
scrape_selenium → parse → matrix → train_super → score_super → train_unsuper → validate
```

Only the **`parse`** stage treats every category identically. From **`matrix`**
onward, each category is routed into exactly one of **three branches**, and the
branch fully determines feature engineering, model topology (segmented vs.
single global), output filenames, and the keys used to look stats back up at
inference time.

| Branch | Categories | Model topology |
| --- | --- | --- |
| **Armour (segmented)** | `Body_Armour`, `Boots`, `Helmet`, `Gloves`, `Focus`, `Shield`, `Buckler` | 7 defence-segment models per category |
| **Jewellery (single)** | `Belt`, `Ring`, `Amulet` | 1 global model per category |
| **Simple (single)** | `Jewel` subtypes, `Sceptre`, `Staff`, `Wand`, `Quiver` | 1 global model per category |

Routing is decided independently inside each module by path-substring detectors
(`_is_jewelry_branch`, `_is_belt_branch`, `_is_simple_branch`, etc.). The
detectors agree on the *end behavior* but differ in *grouping*, and there is one
subtlety worth memorizing:

> **Belt-grouping subtlety.** In `matrix_utils._is_jewelry_branch`, belt is
> grouped *with* ring/amulet (the detector matches `belt`, `ring`, `amulet`).
> In `train_utils` and `score_super_utils`, belt is split out by
> `_is_belt_branch` (`"belt" in p and not (ring or amulet)`). Both paths still
> produce a single global model, but they reach it through different code. If you
> edit one detector, check all four (matrix / train / score / unsuper).

The rest of this document follows the spine above: one section that is shared
(`parse`), then a branch-by-branch treatment of each downstream stage.

---

## 1. The CLI surface and execution order

Entry point: `poe2trade/db/__main__.py`, invoked as

```powershell
python -m poe2trade.db <actions...> <categories...>
```

**Valid actions:** `clean`, `combine`, `scrape_selenium`, `parse`, `matrix`,
`train_super`, `score_super`, `train_unsuper`, `validate`, `test`.

**Token parsing.** Positional arguments are classified one at a time: an argument
matching a known action becomes an action; anything else is treated as a
category name. The literal token `all` expands to the 15-category preset
(`ALL_CATEGORY_PRESET`) plus the full action sequence.

**Fixed execution order.** Regardless of the order you type actions on the
command line, the CLI runs them in its built-in order. `clean` runs first (even
before the disk-space preflight, so freeing space can let heavy stages proceed),
then `combine`/`scrape_selenium`; then the `ALL_ACTION_SEQUENCE`:

```
parse → matrix → train_super → score_super → train_unsuper
```

and `validate` runs last. (See the sequence of `if "<action>" in actions_found`
blocks in `main()`.)

**`clean`.** Deletes generated pipeline artifacts (feature matrices, trained
super/unsuper models, scoring/report output under `generated/super_models/`, and
old `logs/db_pipeline_runs/` transcripts) so the next stages rebuild from
scratch. The exact patterns live in `poe2trade/db/artifacts.py` and mirror the
`.gitignore` rules (`tests/test_db_artifacts.py` guards against drift). By
default `clean` leaves **raw** scraped item JSON and the `file_sets_to_combine/`
staging dirs alone — those are pipeline input and expensive to reacquire. Pass
`--clean-raw` to remove those too. Because `clean` runs first, a full rebuild is
a single command: `python -m poe2trade.db clean combine all`.

Pass `--tests` with `validate` to run the merge/regression pytest scope after
the inference sanity check. Use `--tests all` to run the full test directory.
Use `test` as the local release-readiness gate; it runs validation plus the
full pytest suite, supervised artifact validation, and base-image/icon freshness
checks without retraining or regenerating pipeline artifacts.

**`Jewel` expansion.** Two things happen when `Jewel` appears:

1. `_migrate_jewel_jsons()` rebuilds `db/files/<Subtype>/` folders by deleting
   any existing destination first, then moving `db/files/Jewel/<Subtype>.json`
   into it. The clean-rebuild avoids OS auto-renames such as `Ruby (1)`.
2. `_expand_categories()` replaces `Jewel` with the 8 subtypes from
   `poe2trade.__init__.jewel_list`:
   `Sapphire, Emerald, Ruby, Diamond, Time-Lost_Sapphire, Time-Lost_Emerald,
   Time-Lost_Ruby, Time-Lost_Diamond`.

**Per-stage logging.** Each stage tees stdout/stderr to
`logs/db_pipeline_runs/<timestamp>/<stage>.txt` via `_TeeStream` / `_tee_output`,
so warnings and tracebacks survive after the run.

**Global configuration flags** (`poe2trade/__init__.py`) that govern the
pipeline, with current defaults:

| Flag | Value | Effect |
| --- | --- | --- |
| `train_super_xgb` | `True` | XGBoost is the only active supervised model type |
| `train_super_rf` / `train_super_gbr` | `False` | RandomForest / GradientBoosting disabled |
| `shap_flag` | `False` | SHAP explanations and SHAP-weighted KNN off |
| `score_with_z` | `False` | Buckets use percentile cutoffs, not z-score |
| `quantile_splitters` | `[50, 80]` | Percentile cutoffs for Low/Medium/High |
| `hyperparameter_flag` | `True` | Hyperparameter search enabled |
| `use_previous_model_settings` | `False` | Re-search params instead of reusing |
| `use_cuda` | `False` | XGB runs on CPU |
| `buyout_only` | `False` | Do not filter to `~b/o` listings at parse time |
| `divine_exalt` / `chaos_exalt` / `annul_exalt` | `197` / `19` / `107` | Currency → exalt ratios |

---

## 2. Stage 1 — PARSE (identical for all categories)

Source: `poe2trade/db/parse_cat.py` and `poe2trade/utils/parse_utils.py`.

This is the only stage with no branching, so it is documented once, in full.

**Input / output.** Reads every `db/files/<Category>/*.json` (raw trade-API
dumps) and writes the aggregated `<Category>_agg_parsed.xlsx` and
`<Category>_agg_parsed.parquet`.

### 2.1 Per-item flattening (`parse_item_json`)

- **API-shape detection:** the file must look like a trade-API dump (a dict with
  `result`, or a list of dicts containing `item`/`listing`). Local template JSON
  files are skipped (empty DataFrame).
- **`buyout_only` filter:** when enabled, only listings whose price `type` starts
  with `~b/o` are kept. (Disabled by default.)
- **Top-level fields:** `price`, `currency` (from `listing.price`), `name`,
  `base` (`baseType` or `base`), and stash coordinates (`stash_name/x/y`).

### 2.2 Mod slotting (`_slot_mods`)

Each mod stream is flattened into a fixed number of slots; per slot the parser
emits three columns: `<pfx>_mod_<i>`, `<pfx>_mod_<i>_pattern`,
`<pfx>_mod_<i>_value`.

| Stream | Prefix | Slots |
| --- | --- | --- |
| `enchantMods` | `enchant` | 3 |
| `implicitMods` | `implicit` | 3 |
| `explicitMods` | `explicit` | 10 |
| `fracturedMods` (capped at 3) | `fractured` | 3 |
| `desecratedMods` (capped at 3) | `desecrated` | 3 |
| `runeMods` | `rune` | 6 |

`fractured` and `desecrated` are parsed into their *own* slots and are **not**
merged into the `explicit` stream at parse time. Presence-only mods (a pattern
with no numeric roll) get value `1.0` for `implicit`/`explicit`/`fractured`/
`desecrated`.

### 2.3 Roll parsing (`parse_rolled_mod`)

Given one mod string, returns `(pattern, avg, max, bucket, is_armour,
is_evasion, is_es)`:

- Strips a leading `+`, lowercases, trims.
- **Removes advanced-text roll ranges** like `88(85-109)%` (these describe
  possible rolls, not the actual value).
- **Masks metre tokens** (`6m`, `10-20m`) before extracting numbers so they do
  not pollute the value, then restores them in the pattern.
- Numbers → `#` to form the `pattern`; `avg = (first + last) / 2`.
- **Defence reference flags:** set when the text mentions `armour` / `evasion` /
  `energy shield` *and* does not contain `recharge` / `break` / `penetrate`.

### 2.4 Text normalization

- **`clean_mod_text`** expands wiki-style tags. The `_TAG_REPLACEMENTS` LUT
  handles specific cases (resistances, charges, ailments, leech, etc.); the
  generic rule is `[a|b] → b` (prefer the display side), and single-bracket
  `[x]` tags are stripped.
- **`_expand_composite_mods`** removes the literal `(descrated)` marker and
  splits combined lines into two so each can be matched and summed downstream:
  - `"+# to X and Y"` where X/Y ∈ {Strength, Dexterity, Intelligence}
  - `"+#% to X and Y Resistances"` where X/Y ∈ {Cold, Fire, Lightning, Chaos}

### 2.5 Properties and skills

- **Quality:** plain `Quality` → `quality`; typed `Quality (X modifiers)` →
  `quality_type = x` plus the numeric `quality`.
- **Defences** (`DEFENCE_KEYS`): `armour/armor → ar`, `evasion[ rating] → ev`,
  `energy shield → es`, `block[ chance] → block` (block numeric-extracted).
- **Granted skills:** `grantedSkills[0]` → `skill_pattern` (numbers → `#`, with a
  leading `grants skill[s]:` stripped) and `skill_value` (the level).

### 2.6 Row filtering and aggregation

- Rows whose `explicit`/`enchant` slots contain `allocates`, `bears`
  (abyssal-lord), or `on corruption` are dropped — these are passive/conditional
  statuses, not item stats.
- `parse_cat.main` concatenates all per-file frames with `_concat_safely`
  (drops all-NA frames/columns, re-adds canonical columns), casts canonical
  dtypes (`_cast_canonical_dtypes`), and orders columns
  (`_reorder_columns`: price/currency/base/name/quality/defences, then ordered
  mod columns, then the rest).

---

## 3. Stage 2 — MATRIX (branch-specific) — the core of the pipeline

Source: `poe2trade/db/matrix_cat.py` and
`poe2trade/utils/matrix_utils.build_feature_matrix`.

Reads `<cat>_agg_parsed.parquet`; writes four files:

- `<cat>_agg_parsed_feature_matrix_model.{parquet,xlsx}` — model training input
- `<cat>_agg_parsed_feature_matrix_overlay.{parquet,xlsx}` — human/GUI/KNN view

### 3.0 Shared steps (all branches)

1. Lowercase all columns; build `item = name + " " + base`.
2. Split quality into helpers: `_plain_quality` (untyped), `_qtype`,
   `_qtype_pct` (typed percentage).
3. Drop legacy `property_*` columns.
4. **Feature-set construction.** Harvest every `*_mod_*_pattern` column
   **except** `rune_*`, re-normalize each through `parse_rolled_mod`, and take
   the sorted unique set as the feature columns (all initialized to `0.0`).
5. **Value summation.** For each mod slot of `explicit`, `fractured`,
   `desecrated`, `implicit`, `enchant`, sum its `_value` into the column named by
   its normalized pattern. Thus **`fractured_*` and `desecrated_*` are treated
   exactly like `explicit_*`**. **Rune patterns never become feature columns** —
   they only feed defence normalization (3.1).
6. **Price → exalts** (`_to_exalt`): the model target. `exalt`-like currencies
   pass through; `chaos × chaos_exalt`, `divine × divine_exalt`,
   `annul × annul_exalt`; unknown currency → `0.0`.
7. **Overlay vs. model split** (see each branch for the exact drop lists). The
   overlay keeps human-facing `ar/ev/es` and `*_norm`; the model file drops raw
   defences and intermediate helpers.

### 3.1 Armour branch — `Body_Armour, Boots, Helmet, Gloves, Focus, Shield, Buckler`

Condition: `not jewelry_branch and not simple_branch`.

Defence normalization produces the `*_norm` columns that define segments
everywhere downstream. With:

- `Q`  = `_plain_quality`
- `EM` = `explicit_mod_%` = max over the seven `#% increased <defence>` columns
  (and legacy `+`-prefixed variants)
- `RM` = `rune_mod_%` = the `rune_mod_*` value matching
  `#% increased armour, evasion and energy shield`
- `A/E/S` = raw `ar/ev/es`; `fA/fE/fS` = flat `# to armour` /
  `# to evasion rating` / `# to maximum energy shield`

the math is:

```
denom   = (1 + Q/100) · (1 + (EM + RM)/100)        # zeros replaced by 1
ar_base = A/denom − fA       ev_base = E/denom − fE       es_base = S/denom − fS
ar_norm = (ar_base + fA)·(1 + EM/100)
ev_norm = (ev_base + fE)·(1 + EM/100)
es_norm = (es_base + fS)·(1 + EM/100)
```

`*_norm` strips quality and rune contributions so items are comparable across
rolls; these three columns drive segment masks in train/score/unsuper.

- **Shield / Buckler sub-case** (`category_token in {shield, buckler}`): parses
  `block`, computes `block_base`/`block_norm` from `#% increased block chance`,
  and keeps `block_norm` as a model feature (the raw `#% increased block chance`
  is dropped from the model to avoid double-encoding).
- **Focus sub-case** (`category_token == "focus"`): armour-like and segmented;
  raw skill columns are dropped (like shield-like items).

**Model drops** for armour: `item`, the raw flat/percent defence inputs
(`# to armour`, `#% increased armour`, …, plus `+`-variants), and
`ar/ev/es/block/explicit_mod_%/rune_mod_%/*_base`. **Overlay drops** the `%`
helpers and `*_base` but keeps `ar/ev/es` and `*_norm`.

### 3.2 Jewellery branch — `Belt, Ring, Amulet`

Condition: `_is_jewelry_branch` (path contains `belt`/`ring`/`amulet`).

- **Belt sub-case:** charm-slot columns (`has # charm slot`, `has # charm slots`)
  are collapsed into a single `has # charm slots` (max of variants, clipped to
  ≥ 1); leftover charm variants dropped.
- **Ring / Amulet sub-case:** typed-quality **deflation**. Load
  `db/files/ring_amulet_quality_lookup.xlsx`, normalize its headers and pattern
  columns through `parse_rolled_mod`, and for each row with `(_qtype, _qtype_pct)`
  divide the matching pattern columns by `1 + _qtype_pct/100`. This removes the
  quality bonus so base rolls are comparable.

Both drop raw `ar/ev/es` from overlay and model.

### 3.3 Simple branch — `Jewel` subtypes, `Sceptre`, `Staff`, `Wand`, `Quiver`

Condition: `_is_simple_branch` (path contains `jewel`/a jewel subtype/`sceptre`/
`scepter`/`staff`/`staves`/`wand`/`quiver`).

- No defence math, no typed-quality deflation.
- **Weapon-caster sub-case** (`weapon_skill_branch` = `sceptre`/`staff`/`wand`):
  `skill_pattern`/`skill_value` is materialized as a feature column. **Quiver and
  jewels do not get the skill feature.** Raw skill columns are then dropped for
  weapon casters.
- Overlay and model both drop raw `ar/ev/es`.

### 3.4 Category → branch resolution table

| Category | Branch | Segmented? | Special feature engineering |
| --- | --- | --- | --- |
| Body_Armour, Boots, Helmet, Gloves | Armour | Yes (7) | `ar/ev/es_norm` defence normalization |
| Focus | Armour | Yes (7) | Defence normalization; skill cols dropped |
| Shield, Buckler | Armour | Yes (7) | Defence normalization + `block_norm` |
| Belt | Jewellery | No | `has # charm slots` collapse |
| Ring, Amulet | Jewellery | No | Typed-quality deflation via lookup xlsx |
| Sceptre, Staff, Wand | Simple | No | `skill_pattern`/`skill_value` feature |
| Quiver | Simple | No | None (no skill feature) |
| Jewel subtypes (×8) | Simple | No | None |

---

## 4. Stage 3 — TRAIN_SUPER (branch-specific topology)

Source: `poe2trade/db/train_super_cat.py` and
`poe2trade/utils/train_utils.train_super_model_from_matrix`.
Output directory: `db/super_models/`.

**Currency confirmation prompt.** `_prompt_for_currency_check` prints the
current `divine_exalt/chaos_exalt/annul_exalt` and blocks on Enter so you can
confirm the ratios baked into the price→exalt target are still accurate. When
running via `python -m poe2trade.db`, this fires **once at the very start of the
pipeline** (before any stage, regardless of which stages were requested), and
train_super's own per-stage prompt is suppressed to avoid prompting twice.
Calling `train_super_cat.main` directly still prompts on its own.
`POE2TRADE_QUIET=1` is set to suppress per-iteration logs.

**Input.** `<cat>_agg_parsed_feature_matrix_model.parquet`. Drops `item`,
lowercases columns, coerces `price` to numeric, drops priceless rows.

### 4.1 Model topology by branch

- **Armour (segment-wise).** The seven segments in `_SEGMENTS`:

  | Segment | Predicate (over `ar_norm`, `ev_norm`, `es_norm`) |
  | --- | --- |
  | `ar_only` | `ar>0 & ev==0 & es==0` |
  | `ev_only` | `ev>0 & ar==0 & es==0` |
  | `es_only` | `es>0 & ar==0 & ev==0` |
  | `ar_ev_only` | `ar>0 & ev>0 & es==0` |
  | `ar_es_only` | `ar>0 & es>0 & ev==0` |
  | `ev_es_only` | `ev>0 & es>0 & ar==0` |
  | `all_three` | `ar>0 & ev>0 & es>0` |

  One model **per segment per active model type**. Segments are trained in
  parallel (`ThreadPoolExecutor`, `parallel_segments=True`, so inner
  `n_jobs=1`). Segments with `< 5` rows are skipped. Per segment, constant /
  zero-variance columns (including degenerate `*_norm`) are dropped.

- **Jewellery + Simple (belt / ring / amulet / simple).** A single global model
  per active type. `ar_norm/ev_norm/es_norm` are dropped; constant columns
  dropped.

### 4.2 The estimator stack

- **Active types** come from the flags via `_get_active_model_types`
  (`xgb` only, by default).
- **`_build_pipeline`** assembles `StandardScaler` (optional) →
  `ClippedRegressor(<estimator>)`, tuned by `RandomizedSearchCV`
  (`n_iter=20`, `cv=3`, `scoring="r2"`, `refit=True`). Each model type carries its
  own `param_distributions`:
  - **XGB:** `n_estimators ∈ {300,600,900}`, `max_depth ∈ {3,5,7}`,
    `learning_rate = logspace(-2,-0.5,5)`, `subsample/colsample_bytree ∈
    {0.6,0.8,1.0}`, `reg_lambda ∈ {0.1,1,3,10}`, `reg_alpha ∈ {0,0.1,0.5}`,
    `min_child_weight ∈ {1,3,5}`, `gamma ∈ {0,0.1,0.5}`; `tree_method="hist"`,
    device CPU/CUDA from `use_cuda`.
  - **RF:** `n_estimators ∈ {300,600}`, `max_depth ∈ {3,5,None}`,
    `max_features ∈ {sqrt,log2}`, `min_samples_leaf ∈ {1,2,5}`.
  - **GBR:** `n_estimators ∈ {300,600,900}`, `max_depth ∈ {2,3,5}`,
    `learning_rate = logspace(-2,-0.5,5)`, `subsample ∈ {0.6,0.8,1.0}`.
  - All: `clip_q ∈ {0.0, 0.01}`, `margin = 0.05`.
- **`ClippedRegressor`** (robust wrapper for outlier-heavy prices):
  - *Fit:* winsorize labels to `[clip_q, 1−clip_q]` quantiles (or min/max if
    `clip_q==0`), and store prediction bounds
    `[lo − margin·span, hi + margin·span]`. Records `_non_negative_target_`.
  - *Predict:* clip to the stored bounds; if the target was non-negative, also
    clamp predictions at `0`.
- **`use_previous_model_settings`** fast-path: if a prior `*_model.pkl` exists,
  reuse its `best_params` and fit directly (no search).

### 4.3 Per-model artifacts

With `<base>` = `<cat_norm>` (single) or `<cat_norm>_<seg>` (armour), each
`(base, model_type)` writes into `db/super_models/`:

- `<base>_<mtype>_model.pkl` — dict with `model_pipeline`, `feature_cols`,
  `base_features` (`[ar_norm, ev_norm, es_norm]` for armour, `[]` otherwise),
  `use_scaler`, `model_type`, `best_params`, `segment_name`.
- `<base>_<mtype>_model_readme.txt` — R², hyperparameters, rank-sorted feature
  importances.
- `<base>_<mtype>_shap.pkl` — only when `shap_flag` is on.
- An appended entry in `feature_importances_index.json`.

R² is reported on a `train_test_split(test_size=0.2, random_state=42)` holdout.

---

## 5. Stage 4 — SCORE_SUPER (branch-specific, mirrors training)

Source: `poe2trade/db/score_super_cat.py` and
`poe2trade/utils/score_super_utils.score_matrix`.
Output directory: `poe2trade/generated/super_models/`.

Loads `<cat>_agg_parsed_feature_matrix_model.parquet`, aligns features to each
model (`_align_features_to_model`: add missing cols as `0.0`, drop extras,
reindex), runs every active model, and takes the **median ensemble**
(`pred_median = median over model types`). `Jewel` self-expands to its subtypes
and scores each independently.

### 5.1 Bucketization

Single strategy chosen by `score_with_z` (`_compute_pred_cutoffs`,
`_assign_buckets_from_cutoffs`), always computed on `pred_median`:

- **`use_z = True`:** `t_low = mean + 1σ`, `t_high = mean + 2σ`;
  `value ≤ t_low → Low`, `value > t_high → High`, else `Medium`.
- **`use_z = False` (default):** percentile cutoffs at `quantile_splitters`
  (currently `[50, 80]`); `value ≤ p[0] → Low`, `value > p[1] → High`, else
  `Medium`.

### 5.2 Stats keying (the contract with inference)

`category_segment_stats.json` is keyed by:

- **Jewellery / simple:** `<cat_norm>` (e.g. `belt`, `ring`, `wand`, `ruby`).
- **Armour:** `<cat_norm>_<seg>` (e.g. `body_armour_all_three`).

This keying must match `ml_super_utils.call_ml`'s `base_name` exactly, or
inference cannot find the bucket stats. Each entry stores `method`, `mean`,
`std`, `t_low`, `t_high`, `percentile_splitters`, `percentile_values`,
`bucket_intervals` (10–90% of **actual** prices per bucket),
`prediction_bucket_intervals`, and a compact `distribution_profile` histogram.

### 5.3 Sidecars

Per branch/segment: `<...>_scoring.xlsx`, `<...>_scoring.json`, and a
`<...>_price_dists.png` overlay plot. A final
`generate_score_super_report(...)` summarizes the run.

---

## 6. Stage 5 — TRAIN_UNSUPER (KNN reference bundles)

Source: `poe2trade/db/train_unsuper_cat.py` and
`poe2trade/utils/train_utils.train_unsuper_model_from_matrix`.
Output directory: `db/unsuper_models/`.

Same branch split as supervised training:

- **Armour:** one KNN bundle **per defence segment**. Segments with `< k+1` rows
  are skipped.
- **Belt / Ring / Amulet / Simple:** one global KNN bundle.

`k = knn_filtered_k` from config (default 10). Each bundle pairs the model matrix
with the matching `_feature_matrix_overlay.parquet` slice so the GUI can display
real neighbor items. A bundle contains:

- `scaler` (`StandardScaler`) + `scaler_data` (`mean`, `scale`)
- `feature_cols`, `feature_weights` (SHAP-derived when `shap_flag` is on, else
  uniform) + `feature_weights_source`
- `segment`, `row_indices`, `X_all` (float32), `model_price` (float32),
  `overlay_df`, `n_neighbors = k`, `algorithm = "brute"`

Files: `<base>_knn_model.pkl` and `<base>_knn_model_readme.txt`, where `<base>`
is `<cat_norm>` (single) or `<cat_norm>_<seg>` (armour).

---

## 7. Stage 6 — VALIDATE (inference sanity check)

Source: `poe2trade/db/validate_cat.py`.

Runs copy-pasted item strings from `tests/fixtures/sample_items.txt` (entries
separated by a line containing `$$$$`; `#` lines stripped) through the full
inference path and prints each step. It stubs `tkinter`/`tkinter.messagebox` so
it runs headless. For ad-hoc files use the wrapper:

```powershell
python tools\run_item_scoring.py --file path\to\items.txt
```

For developer validation after branch merges, run:

```powershell
python -m poe2trade.db validate --tests
```

That command writes the normal validation transcript plus a `pytest.txt`
transcript under `logs/db_pipeline_runs/<timestamp>/`.

---

## 8. Inference — how the app consumes the artifacts

Source: `poe2trade/utils/ml_super_utils.call_ml`.

- **Category normalization:** lowercase + underscores, plus alias fixes
  (`scepter→sceptre`, plurals→singular such as `rings→ring`, `foci→focus`).
- **Model lookup:** `base_name = category` (single) or `category_segment`
  (armour). Search order for model dirs: `STASHSAGE_SUPER_MODELS_DIR` env →
  generated dir → bundled `db/super_models/`. Models are cached in-process with
  mtime invalidation.
- **Predict:** reindex input `X` to each model's `feature_cols` (fill `0.0`),
  predict, then aggregate `min/max/mean/median`.
- **Bucketise:** `_bucketise(base_name, median)` reads
  `category_segment_stats.json` (whose keys come from Stage 4) and assigns
  Low/Medium/High with GUI-matched colors. The GUI/API display the `xgb`
  prediction first, then color the badge from its bucket.
- **Compatibility shims:** `_CompatUnpickler` rewrites the package prefix so
  pickles created as either `poe2trade` or `stashsage_serve` load, and remaps the
  `train_utils.ClippedRegressor` to the runtime shim in `ml_super_utils`.

---

## 9. Reference appendices

### A. Generated artifact map

| Location | Files |
| --- | --- |
| `db/files/<cat>/` | `<cat>_agg_parsed.{xlsx,parquet}`, `<cat>_agg_parsed_feature_matrix_model.{xlsx,parquet}`, `<cat>_agg_parsed_feature_matrix_overlay.{xlsx,parquet}` |
| `db/super_models/` | `<base>_<mtype>_model.pkl`, `_model_readme.txt`, optional `_shap.pkl`, `feature_importances_index.json` |
| `db/unsuper_models/` | `<base>_knn_model.pkl`, `_knn_model_readme.txt` |
| `poe2trade/generated/super_models/` | `<base>_scoring.{xlsx,json}`, `<base>_price_dists.png`, `category_segment_stats.json`, `score_super_report.pdf`, `validation_report.pdf` |

`<base>` = `<cat_norm>` for jewellery/simple, `<cat_norm>_<seg>` for armour.

### A.1 Asset delivery & freshness (keep all surfaces in sync)

Model assets — models, their `*_scoring.json`, `category_segment_stats.json`
(distributions), `feature_importances_index.json`, and the `*_price_dists.png`
viz — must travel **co-versioned** to every surface:

- **Self-update**: `tools/write_update_manifest.py` hashes the curated
  `super_models`/`unsuper_models` set (`DEFAULT_ASSET_INCLUDES`, now including
  `*_price_dists.png`) and refuses to publish a `super_models` set that fails
  `validate_super_model_artifacts.validate` (use `--skip-asset-validation` only
  for synthetic/partial sets). The in-app updater downloads into the per-user
  override `%APPDATA%/StashSage/generated/<bucket>`, rolls back a partial
  co-versioned sync (so a new model can't sit beside stale stats), and stamps
  `asset_provenance.json` with the delivered `asset_version`/`build_commit`.
- **Override vs bundle**: the override always shadows the bundle, so at startup
  `asset_paths.reconcile_override_with_bundle` deletes the override model
  buckets whenever the running bundle is newer than — or diverges in commit
  from — the provenance stamp (or there is no stamp). This is what stops a stale
  override (e.g. an old data snapshot) from shadowing a freshly built/swapped
  bundle.
- **Downstream**: `tools/Sync-Downstream.ps1` mirrors `*.pkl`/`*.json`/
  `*_price_dists.png` to StashSage_Serve, hash-verifies the mirror, and runs the
  same validator before pushing; the website gets the feature-importances index.

### B. Branch-detector cheat sheet (keep these consistent)

| Module | Jewellery test | Belt test | Simple test |
| --- | --- | --- | --- |
| `matrix_utils` | `belt`/`ring`/`amulet` in path | `jewelry & "belt" in stem` | jewel(s)/sceptre/staff/wand/quiver |
| `train_utils` | `ring`/`amulet` only | `belt & not ring/amulet` | jewel(s)/sceptre/staff/wand/quiver |
| `score_super_utils` | `ring`/`amulet` (separate belt fn) | `belt & not ring/amulet` | + quiver, dynamic from `jewel_list` |

All converge on: armour → segmented; belt/ring/amulet/simple → single global.

### C. Glossary

- **Overlay matrix** — human/GUI/KNN view; keeps `ar/ev/es` and `*_norm`.
- **Model matrix** — training input; drops raw defences and intermediates.
- **`*_base` vs `*_norm`** — `*_base` removes quality/rune/explicit scaling;
  `*_norm` re-applies explicits only, for cross-item comparison.
- **Winsorization** — clamping label outliers before fit (`ClippedRegressor`).
- **Median ensemble** — `pred_median` across active model types.
- **Stats key** — the `category[_segment]` string linking scoring output to
  inference bucket lookup.
