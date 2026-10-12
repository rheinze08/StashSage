# Inference Speed & Accuracy Improvement Plan

Scope: make the app's price predictions **faster** and **more accurate** without
changing the payload contract, the overlay layout, or any user-visible feature.
Every item below leaves `tests/test_dashboard_payload_contract.py` green by
construction — no new fields, no removed fields, no changed display semantics.

Two items (A1, B4) change numbers the user sees, because they change what the
models learn. That is the point of the accuracy tier; the *format* is untouched.

Ordered by (impact ÷ risk), highest first. Each item names the exact call site.

**Status:** step 0, B1, B2 and B3 are implemented — the no-retrain tier. Everything
else is still proposed. Implemented items are marked ✅ with what was measured.

---

## 0. Prerequisite — make the hot path measurable ✅

Nothing below should be merged on inferred timings. The instrumentation that
exists today cannot attribute cost:

- `_InferenceTimer` (`poe2trade/app/gui_tk.py:2192`, enabled by
  `STASHSAGE_PROFILE`) marks `prepare` / `super` / `knn` in
  `_score_dashboard_async`, but all three model stages run inside
  `_dashboard_model_payload_in_process`. So `prepare` absorbs the entire worker
  round-trip and `super`/`knn` both read ≈0ms. The breakdown is currently
  decorative.
- The worker already returns `timings={"build_ms": ...}`
  (`poe2trade/app/prediction_worker.py:61`) — one number for everything.

**Do first:** thread a stage dict back through the existing `timings` key inside
`_dashboard_process_entry` (`gui_tk.py:8383`) — `parse`, `super`, `knn`,
`charts`, `icons`, `serialize`. `timings` is already part of the worker event
envelope, so this adds no new payload field and no UI change.

Then record a baseline over `tests/fixtures/sample_items.txt` across categories,
cold (first hotkey after launch) and warm. Without that split, items 1 and 2
below cannot be told apart from item 5.

**Implemented.** `_dashboard_process_entry` now records `parse`, `super`, `knn`,
`charts`, `serialize`, `cards` and `icons` through `_StageTimings`, and reports
them under the private `prediction_worker.STAGE_TIMINGS_KEY`. The worker lifts
that key out of the payload and into the event's existing `timings` field, so
the dashboard payload the presenter consumes is unchanged. The completion log
line prints the breakdown costliest-stage-first. The three `_InferenceTimer`
marks that all resolved to the same worker round-trip collapsed into one
`worker` mark, since the real split now comes from the worker itself.

Still to do: capture the cold/warm baseline on real hardware. The numbers below
were measured in a Linux container against the repo's real assets, so treat
them as directional for a Windows install.

---

## Tier A — Accuracy (highest leverage, offline-only, no runtime change)

These change training only. The app loads the same artifact shapes and renders
the same overlay; the numbers inside get better. All require a retrain + rescore
(`python -m poe2trade.db matrix train_super score_super train_unsuper <cats>`).

### A1. Stop selecting hyperparameters on raw-price R² — the single biggest win

`train_super_log_price = True` (`poe2trade/__init__.py:88`), so the regressor
fits `log1p(price)` and `ClippedRegressor.predict` inverts with `expm1`
(`train_utils.py:327`). But the search scores the **inverted, raw-exalt**
predictions:

```python
RandomizedSearchCV(..., scoring="r2", cv=3, ...)   # train_utils.py:431-441
```

Item prices are heavy-tailed. Raw-space R² is dominated by squared error on the
handful of most expensive listings in each segment, so hyperparameters are
chosen to chase the tail — while the app's job is pricing the *typical* item and
placing it in a Low/Medium/High bucket. The two objectives are not aligned.

The same mismatch is baked into the reported score,
`r2val = r2_score(yte, final.predict(Xte))` (`train_utils.py:720` and `:847`),
which then flows into the model readme and `feature_importances_index.json` — so
the headline quality metric is also tail-dominated.

**Fix:** score in the space the model actually optimizes. A
`make_scorer(lambda y, p: -mean_absolute_error(np.log1p(y), np.log1p(p)))` (or
median-AE in log space, which is even more robust) selects for proportional
accuracy across the whole price range. Report *both* metrics so historical R²
stays comparable.

**Risk:** low, mechanical. **Effort:** small. **Payoff:** the largest available,
and it compounds with everything else in this tier.

### A2. Refit the shipped model on 100% of the data

`train_test_split` holds out 20% (`train_utils.py:665`, `:837`), the search runs
on the remaining 80%, and `gs.best_estimator_` — fit on that 80% only — is what
gets pickled and shipped. The held-out fifth is used once, to print a score, then
discarded.

**Fix:** keep the split for *selection and reporting*, then refit the winning
params on the full `X, y` for the artifact. Standard practice, free accuracy,
disproportionately valuable for thin segments near `min_training_rows`
(`train_utils.py:120`) where 20% is the difference between a usable and a noisy
model.

**Risk:** low. **Effort:** small. Guard it: the reported score must stay the
held-out one, never an in-sample score on the refit model.

### A3. De-duplicate listings before training and before the KNN bundle

There is no dedup anywhere in the ML path — `drop_duplicates` appears only in
`chart_utils.py` (trade-history rendering), never in `parse_utils`,
`matrix_utils`, or `train_utils`.

Trade-API dumps repeat the same stash listing across pages and across refresh
cycles. Consequences, both real:

1. **Supervised:** identical rows land on both sides of `train_test_split`, so
   the held-out score is optimistic and A1's selection metric is partly measured
   on leaked duplicates. Fixing A1 without fixing this leaves the metric honest
   in *shape* but still inflated in *level*.
2. **Unsupervised:** duplicates crowd the k-nearest list, so a Price Mirror
   asking for 8 comparables can show the same listing several times. This is a
   visible quality problem the user reads as "the model found nothing".

**Fix:** dedup at matrix build on the feature signature + price (stash
coordinates are already parsed — `stash_name/x/y`, `PIPELINE.md` §2.1 — and make
a strong identity key). Do it in `matrix_utils.build_feature_matrix` so both
branches inherit it.

**Risk:** low-medium — verify row counts per category before/after, and confirm
no segment drops below `min_training_rows`. **Effort:** small-medium.

### A4. Give the KNN real feature weights (they are uniform today)

`train_unsuper_model_from_matrix` asks `_compute_shap_weights` for weights
(`train_utils.py:1024`, `:1123`), but that function returns `None` immediately
when SHAP is unavailable (`train_utils.py:475`) — and `shap_flag = False`
(`poe2trade/__init__.py:89`). So **every shipped bundle falls back to
`uniform`** (`train_utils.py:1031`, `:1123`).

Uniform weights over hundreds of sparse one-hot mod-pattern columns means
neighbour distance is driven by *how many mods two items happen to share*, not
by which mods carry price. The runtime already applies `sqrt(w)` correctly
(`ml_unsuper_utils.py:250`, `:388`) — the machinery is built and idle.

**Fix:** fall back to XGB gain importances, which are **already computed and
persisted** by `_append_fi_manifest` into
`feature_importances_index.json`, instead of falling back to uniform. Zero
format change: `feature_weights` / `feature_weights_source` are existing bundle
fields, and `super_models` is written before `train_unsuper` in
`ALL_ACTION_SEQUENCE`, so the importances are on disk when the KNN trainer runs.

**Risk:** low. **Effort:** small. **Payoff:** high — this is the "Price Mirror
picks bad comparables" fix, and it needs no SHAP dependency.

### A5. Shuffle the CV folds

`cv=3` as a bare int gives `RandomizedSearchCV` a non-shuffled `KFold` for
regression. Matrices are concatenated from per-category scrape files, so row
order carries scrape-batch structure; unshuffled folds are then non-iid and the
selection signal is noisier than it should be.

**Fix:** `KFold(n_splits=5, shuffle=True, random_state=random_state)`. Do it in
the same commit as A1 (both edit `_build_pipeline`) and re-benchmark once.
Note 3→5 folds raises train time ~65%; pair it with A6 if that hurts.

**Risk:** very low. **Effort:** trivial.

### A6. (Secondary, train-time speed) XGB early stopping instead of a searched `n_estimators`

The grid searches `n_estimators ∈ [300, 600, 900]` (`train_utils.py:403`),
tripling search cost to learn something a validation curve determines directly.
Early stopping on a held-out fold picks the tree count per candidate and cuts
search time substantially — which buys back the budget A5 spends.

**Risk:** low. **Effort:** small. This is *training* throughput, not app latency.

---

## Tier B — App latency (runtime, no retrain needed)

### B1. Actually warm the process that does the work ✅

This is a cold-start bug, not a tuning opportunity.

- `PredictionWorkerManager.warmup()` exists (`prediction_worker.py:99`) and is
  **never called anywhere** in the app or tests — only `.start()` is
  (`_prewarm_prediction_worker`, `gui_tk.py:8622`).
- `_spawn_model_prewarm` (`gui_tk.py:10784`) does the real warming — sklearn/
  xgboost import, `_load_model` for every pickle, `_prewarm_unsuper_bundles` —
  on a background thread **in the main GUI process**, which never runs
  inference. Every prediction goes through the spawned worker
  (`_dashboard_model_payload_in_process`, `gui_tk.py:8629`).

So the warm caches are built in the wrong process, and the first hotkey after
launch pays full import + unpickle cost in the worker.

**Fix:** send a real `WARMUP` command and give
`_prediction_worker_payload_builder` (`gui_tk.py:8589`) a warmup branch that runs
the `_spawn_model_prewarm` body and returns `{}`. Required — the current
`WARMUP` path would call `_dashboard_process_entry("")` and raise. Then keep or
drop the main-process prewarm on measurement (it may still help the in-process
fallback at `gui_tk.py:8852`).

**Risk:** low. **Effort:** small. **Payoff:** removes the entire cold-start
penalty from the first user-visible prediction — likely the largest single
latency number in the app.

**Implemented.** The prewarm body moved into `_warm_model_caches`, which both
processes now call with different scopes. `_prewarm_prediction_worker` sends a
real `WARMUP`, and the builder answers it by warming rather than by scoring an
empty string (which would have raised).

The two scopes are deliberate and each has a traced reason:

- **KNN bundles are worker-only.** `call_ml` runs exclusively inside
  `_dashboard_process_entry`; in the main process `ml_unsuper_utils` is used
  only for the `set_*` config setters and `clear_runtime_caches`. Loading the
  bundles — which carry full overlay DataFrames — in the main process would
  duplicate that memory for no reader.
- **Supervised models stay in both.** CraftOracle calls `call_super_prepared`
  on a thread in the main process (`_launch_craft_potential_popup` → `work`),
  so dropping the main-process prewarm entirely would move that cost onto the
  first craft instead. (`_process_super_gui` also scores in-process, but it is
  currently unreferenced.)
- **Scoring-JSON compaction stays main-process-only.** It rewrites sidecars on
  disk; keeping one writer avoids two processes racing over the same files.

### B2. Re-warm after a cancel ✅

`cancel()` (`prediction_worker.py:110`) terminates the worker process to abort an
in-flight score — deliberate and correct, since the scorer can't poll a queued
cancel mid-predict. But it discards every warm cache with it, so the *next*
prediction is a full cold start again. A user rapidly re-copying items hits this
repeatedly.

**Fix:** after terminating, immediately `start()` + warm in the background so the
next request lands warm. Depends on B1.

**Risk:** low. **Effort:** small.

**Implemented, with a scope correction.** Tracing when `cancel()` actually fires
turned up a second, larger problem, and fixing it was a prerequisite rather than
an extra:

`active_request_id` was set by `submit()` and cleared only by `cancel()` and
`shutdown()` — never when a request *finished*. So after a prediction completed,
the manager still believed it was in flight, and the next
`_destroy_overlay(invalidate_request=True)` matched that stale id and terminated
an idle, fully warm worker just to close its overlay. B2 alone would have made
that worse, adding a respawn and a full re-warm to every such dismissal. `poll()`
now retires the request when it hands out a terminal event (`result`, `error`,
`cancelled`), so only genuinely in-flight work is cancellable. The clear happens
after the drain, not inside it, so the rest of that batch is still matched
against the id it was polled for.

With that in place the re-warm itself is small: `cancel()` returns whether it
recycled the worker, and `_destroy_overlay` schedules
`_prewarm_prediction_worker` on the Tk loop when it did. Deferred rather than
inline for two reasons — dismissing an overlay must stay instant, and if the
user starts a new prediction first the warm simply queues behind it, where
`warmup()` reuses the running worker and re-warming an already-warm process is
close to free because the model caches are mtime-keyed.

Worth knowing for anyone reading the cancel path: the "user copied a new item
mid-score" case never reaches a real cancel. `_show_prediction_loading_overlay`
calls `_destroy_overlay(invalidate_request=False)`, so the id it passes is the
*new* request, which never matches the in-flight one. The paths that do recycle
are dismissal (Escape) and the two error handlers — all moments when the user
has gone idle, which is exactly when spending the re-warm is cheapest.

### B3. Cache the two per-prediction rebuilds that don't depend on the item ✅

Both are pure functions of data that doesn't change between predictions:

- **`_prepare_comparison_icon_pngs`** (`gui_tk.py:8032`) re-reads and re-parses
  **`base_images.json` (330 KB)** on *every prediction*, rebuilds `base_map` from
  scratch, then re-opens and LANCZOS-resizes icons for base types that recur
  constantly.
  → module-level cached manifest→`base_map`, plus an `lru_cache` on
  `(name, size) → png bytes`.
- **`_feature_importance_dashboard_buffer`** (`gui_tk.py:2478`) renders a
  matplotlib bar chart whose output depends only on `(cat, seg)` — never on the
  item — and re-renders it every prediction. Its two siblings are already cached
  this way (`chart_utils.py:325`, `:672`), so this is finishing an existing
  pattern.

**Risk:** very low — byte-identical output. **Effort:** small. **Payoff:** the
best latency-per-line-changed in the list.

**Implemented and measured** (median, container, against the repo's real
assets — a warm repeat prediction in the same category):

| Removed per-prediction cost | Measured |
| --- | --- |
| Feature-importance chart render | **125 ms** |
| Icon decode + LANCZOS resize (~9 distinct names at k=8) | **~9 ms** |
| `base_images.json` parse + base-map build (618 keys) | **2.3 ms** |

So ~135 ms per repeat prediction, overwhelmingly the chart. Two caveats worth
keeping straight: the chart saving only applies when `show_viz` is on, and only
from the *second* prediction in a given category/segment — the first still pays
the render. The earlier "5–15 ms" estimate for the manifest parse was too high;
the measured figure is 2.3 ms.

Both caches self-heal like the ones already in the file: the icon caches key on
the manifest's mtime, the chart cache resets when `_FI_MANIFEST_MTIME` moves,
and `_invalidate_asset_caches` clears all of them, because an update can also
move the asset search roots that the mtime keys do not cover. Two behaviours
that were easy to lose in the refactor are pinned by tests: an unreadable
manifest still yields no icons at all rather than falling through to the default
artwork, and an unreadable *image* still falls through to its category default.
`_feature_importance_dashboard_buffer` hands out a fresh `BytesIO` per call over
cached bytes, since callers read the buffer to exhaustion.

### B4. Fast single-row supervised predict

`call_ml_super` aligns a 1-row DataFrame and calls through the sklearn Pipeline
(`ml_super_utils.py:716`, `:721`). For a single row, DMatrix construction and
feature-name validation dominate the actual tree traversal.

**Fix:** cache the aligned column order per artifact and predict on a
preallocated numpy row via `Booster.inplace_predict`, keeping the StandardScaler
and `ClippedRegressor` clip/`expm1` math bit-for-bit identical.

**Risk:** medium — this is the one runtime item that can change output values if
done carelessly. **Gate it:** a test asserting exact equality against the current
Pipeline path across every fixture item before the fast path is enabled. Only
worth doing if step 0 shows `super` is a meaningful slice of warm latency;
measure before writing it.

### B5. Ship pre-scaled KNN matrices

`_prepare_bundle_runtime_cache` (`ml_unsuper_utils.py:376`) derives
`_scaled_X_all` and `_scaled_sq_norms` at runtime, so each bundle holds both the
raw `X_all` and a scaled float32 copy — roughly double the memory, plus an n×d
pass per bundle load.

**Fix:** precompute both in the bundle at train time; keep the runtime derivation
as the fallback for older bundles (the loader already validates required fields
at `ml_unsuper_utils.py:366`).

**Risk:** low, but it changes bundle contents, so it needs a retrain and the
`Sync-Downstream` artifact SHA check has to be re-run. Prewarm already hides most
of this cost — the real payoff is worker RSS and faster post-cancel respawn
(B2). **Do it as part of a Tier A retrain, not on its own.**

### B6. Minor: drop the poll sleep

`_dashboard_model_payload_in_process` spins with `time.sleep(0.01)`
(`gui_tk.py:8657`), adding up to 10ms of pure wait to every prediction. Small,
but free to reclaim with a short blocking `get` while keeping the generation
filter. Include it as a rider on B1/B2, not as its own change.

---

## Recommended order

| # | Item | Tier | Risk | Retrain? |
|---|------|------|------|----------|
| 0 | ✅ Per-stage timings in `timings` | prereq | none | no |
| 1 | ✅ B1 warm the worker process | latency | low | no |
| 2 | ✅ B3 cache icons + FI chart | latency | very low | no |
| 3 | A1 log-space selection metric | accuracy | low | yes |
| 4 | A4 XGB-gain KNN weights | accuracy | low | yes |
| 5 | A2 refit on full data | accuracy | low | yes |
| 6 | A3 de-duplicate listings | accuracy | med | yes |
| 7 | ✅ B2 re-warm after cancel | latency | low | no |
| 8 | A5 + A6 shuffled folds, early stopping | accuracy/train | low | yes |
| 9 | B4 fast single-row predict | latency | med | no |
| 10 | B5 pre-scaled KNN bundles | latency | low | yes |

Items 1, 2, and 7 are done; they needed no retrain and no model redistribution,
so they ship in a normal release. Items 3–6 and 8 are one retrain cycle; batch them into a single
`train_super score_super train_unsuper` pass and compare against the step-0
baseline plus the existing `python -m poe2trade.db validate` inference check.

## What this plan deliberately does not do

- No change to the dashboard payload contract, overlay layout, bucket semantics,
  or `quantile_splitters`.
- No new runtime dependency (A4 specifically avoids re-enabling SHAP).
- No change to scraping, parsing, or the trade-API surface.
- No change to `divine_exalt`/`chaos_exalt` conversion handling or the frozen
  per-model conversion snapshots.

## Open question

A1 changes model *selection*, so bucket cutoffs shift when `score_super` reruns:
an item near a Low/Medium boundary can move a bucket. That is a correctness
improvement, not a regression — but if bucket stability across releases is a
product commitment, decide that before item 3, not after.
