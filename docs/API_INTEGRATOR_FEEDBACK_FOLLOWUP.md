# API integrator feedback — follow-up work

Feedback received 2026-09-07 from an external client (`poe2-companion`) building
against the public `/predict` API. Four asks. Two were answerable from this repo
and shipped in the same change as this document; two need a change in the
private `StashSage_Serve` repo, which is not reachable from a `poe2trade`
checkout. One question cannot be answered by reading code at all and is waiting
on the maintainer.

This document exists so whoever picks up the serve-side work does not have to
re-derive any of it.

> **Update 2026-09-07 (second pass).** A later session ran with a
> `StashSage_Serve` checkout beside this repo, so **S2 is done** — the neighbor
> schema, the `/predict` vs `/predict-gui` question and the
> `currency_conversions` provenance were all read straight out of
> `stashsage_serve/app/api.py`, published, and pinned with tests. That pass also
> corrected several claims the first pass had guessed at; see "S2 — resolved"
> below. **S1 and the open question are still open**, unchanged.

| # | Ask | Status |
|---|-----|--------|
| 1 | Expose training-data freshness separately from `release.build_date` | **Done 2026-09-08.** `release.training_data_as_of` + `release.model_trained_at` — S1 below. |
| 2 | Document the full `knn.neighbors` schema and canonical units | **Done.** Units first pass; schema, endpoint parity and currency provenance in the second pass — S2 below. |
| 3 | Clarify what `release.api_version` versions | **Done.** It tracks the release, not the contract. |
| 4 | Whether `/predict` bodies or results are retained in logs | **Partly answered.** What the app stores is established (aggregate counters only); the platform access log still needs the maintainer. See "Open question". |

## Shipped in `poe2trade`

All doc-only, in the `#api-docs` section of `index.html.j2` and its rendered
mirror `docs/index.html`:

- **Response fields** table covering `request_id`, the `release` block,
  `currency_conversions`, `xgb`, `target_item`, and `knn`.
- **Units** — every price and estimate is exalts, and why there is no per-field
  currency to inspect.
- **Model and data freshness** — `build_date` is an upper bound on the age of
  the market data behind a prediction, usable for a staleness display until S1
  lands.
- **Versioning and change notice** — `api_version` follows the release, so
  clients must not gate schema checks on it; tolerate added fields.
- The optional `source` field now names the convention (a short stable slug,
  e.g. `poe2-companion`).

Added in the second pass, from the serve source rather than inference:

- **Neighbor objects** table — every field of a `knn.neighbors` entry, which of
  them are always present, and that both endpoints emit the same shape.
- **Currency conversions** — the rates are frozen per release, not live.
- `release.build_commit` / `release.git_sha`, `xgb_visual` (and its top-level
  aliases) and the `updates` block are now named as optional/display-only.
- `knn.summary.median` and `.mean` are documented as *omitted*, not `null`, when
  no neighbor has a readable price.
- The `500` error row now also lists `internal_error`, and `details` is
  described as optional.
- The trimmed example response was corrected: it showed a two-key
  `currency_conversions` and a `price_display` of `"3100e / 17d"`, neither of
  which the server ever emits.

## Verified facts and their evidence

Nothing below is inferred; each row was read out of the tree before it went into
the public docs.

| Claim | Evidence |
|-------|----------|
| `api_version` tracks the release, not the response contract | `tests/test_serve_api_contract.py:112` asserts `release["api_version"] == release["model_version"]` |
| Every price/estimate is in exalts | `poe2trade/utils/matrix_utils.py:359` converts each listing's price to exalts before it becomes the `price` target; training uses that column (`poe2trade/utils/train_utils.py:649`) |
| `knn.neighbors` is ordered nearest-first | `_nearest_indices` (`poe2trade/utils/ml_unsuper_utils.py:208`) returns ascending-distance order, and both KNN paths preserve it |
| Neighbor prices come from the training matrix | `result["price_in_exalts"] = model_price[local]` (`poe2trade/utils/ml_unsuper_utils.py:763`, `:829`, `:984`) |
| Per-model training timestamps already exist | `poe2trade/db/files/training_conversion_index.json`, built by `ConversionService.rebuild_training_conversion_index` (`poe2trade/pricing.py:189`) |
| `/predict` and `/predict-gui` serialize neighbors identically | Both call `_annotate_neighbor_mod_comparisons(_build_neighbor_payloads(...))` — `stashsage_serve/app/api.py:2165` and `:2220` |
| `currency_conversions` reports frozen release constants | `_currency_conversions` (`stashsage_serve/app/api.py:1209`) reads the literals at `stashsage_serve/__init__.py:44-46`, which the sync rewrites from source without the `rates.json` override (`tools/read_runtime_constants.py:47`) |
| `knn.summary` guarantees only `count` | `_summarize_knn` (`stashsage_serve/app/api.py:1562`) adds `median`/`mean` only when at least one row had a readable price |

## S1 — resolved (training-data timestamp)

**Shipped 2026-09-08.** `release.training_data_as_of` and
`release.model_trained_at` are now on every `/predict` and `/predict-gui`
success response, and the Discord bot prints a `Market data: <date>` line in its
summary.

The implementation turned out smaller than this section anticipated, because the
timestamps were **already reaching `api.py`**: `call_ml_super` reads each model's
`.pricing.json` on every prediction and returns it as `currency_conversions`
(`stashsage_serve/utils/ml_super_utils.py:773-776`), and `super_res` becomes
`resp["xgb"]` verbatim — so `xgb.currency_conversions.captured_at` was being
served all along, unnamed and undocumented. `_model_freshness` /
`_release_for_prediction` in `stashsage_serve/app/api.py` name them and lift them
into `release`; no file re-read, no new sync, no pipeline change.

Decisions made, and why:

- **`captured_at` (matrix build), not the PythonAnywhere upload date.** The
  upload date records when files moved, so shipping three-month-old models
  tomorrow would stamp tomorrow — exactly the staleness the requester wants to
  detect. `captured_at` is when the matrix was assembled from scraped listings.
- **Both fields, per model.** All 124 models currently share `2026-09-03`, but
  categories retrain independently, so the value is per model by construction.
- **`null`, never a missing key**, so clients distinguish unknown from
  unsupported.
- **A `source_note` on the sidecar suppresses `training_data_as_of`.** When
  `load_model_conversions` falls back it stamps `captured_at` with *now*;
  publishing that as a market-data cutoff would claim maximum freshness at the
  moment freshness is least known. 3 of 62 super-model sidecars (the waystone
  tiers) hit this and correctly report `null` while keeping their real
  `model_trained_at`.

Pinned by `test_release_reports_training_freshness_from_the_model_sidecar`
(both endpoints), `test_training_data_as_of_is_null_when_the_sidecar_was_a_fallback`
and `test_freshness_keys_are_present_but_null_when_no_conversions_ride_along`.
The public `#api-freshness` section and the response-fields table are rewritten
accordingly.

### Original analysis, kept for context

**The timestamps were already on the server.**
Training writes two JSON sidecars beside every model pickle, and both are
already mirrored into the serve package:

- `<model>.training.json` — written by `ConversionService.write_model_snapshot`
  (`poe2trade/pricing.py:166`). Carries `captured_at` = when the **model was
  trained**, plus a `context` block with category, segment and model type.
- `<model>.pricing.json` — written by `publish_model_conversions`
  (`poe2trade/utils/pricing_conversions.py:116`). Carries `captured_at` = when
  the **feature matrix was built** (i.e. when the market data was assembled,
  `poe2trade/utils/matrix_utils.py:410`), plus `trained_at` and `matrix_file`.
- `poe2trade/db/files/training_conversion_index.json` — the consolidated
  lookup, keyed `super_models/<artifact>.pkl`.

Sync coverage is already in place: `tools/Sync-Downstream.ps1:884` copies the
index into the serve package, and the model mirror at
`tools/Sync-Downstream.ps1:922` copies `*.json` out of `super_models` /
`unsuper_models`, which includes both sidecars.

Serve can read them with code it already has — `poe2trade/pricing.py` is synced
as `stashsage_serve.pricing` (see `tests/test_release_contract.py:138`), so
`lookup_model_training_snapshot(model_path)` (`poe2trade/pricing.py:260`) and
`load_model_conversions(model_file)` (`poe2trade/utils/pricing_conversions.py:130`)
both work server-side.

**Recommended shape.** Per request, for the model actually used:

```json
"release": {
  "api_version": "0.5.15",
  "model_version": "0.5.15",
  "build_date": "2026-09-04",
  "training_data_as_of": "2026-07-29T14:16:59+00:00",
  "model_trained_at": "2026-07-29T14:16:59+00:00"
}
```

Notes for the implementer:

- Prefer the `.pricing.json` `captured_at` for `training_data_as_of` — it is the
  matrix build time, which is closer to the market-data cutoff than the training
  run. Use the `.training.json` / index `captured_at` for `model_trained_at`.
- Both are still *upper bounds* on the scrape itself: scraping precedes matrix
  build. Do not advertise either as an exact market cutoff. If an exact one is
  ever wanted, the scrape date has to be stamped into the matrix sidecar first,
  in `poe2trade`.
- The value is **per category/segment**, because categories retrain
  independently. That is a feature, not a wart — say so in the docs.
- Emit `null` when the sidecar is missing rather than omitting the key, so a
  client can tell "unknown" from "not supported", and document that.
- ISO 8601, UTC, to match what the sidecars already store.

**Then update the public docs** (in `poe2trade`): the freshness paragraph at
`#api-freshness` currently says no training timestamp is exposed. It must be
rewritten when this lands, along with a new row in the response-fields table.
*(Both done 2026-09-08.)*

### Still open, deliberately not done

- **`xgb.model_artifacts` publishes server filesystem paths** to external
  callers (`ml_super_utils.py:770`). Nothing outside needs it. Removing it from
  `/predict` is a payload change that needs a decision, so it was left alone and
  left undocumented rather than enshrined in the public reference.
- **`xgb.currency_conversions` can contradict top-level `currency_conversions`**
  — the model's training-time rates vs the release literals. Both read 394/40
  today; nothing enforces it.

## S2 — resolved (`knn.neighbors` schema, endpoint parity, currency provenance)

Read out of `StashSage_Serve` at `9be439a`. All four sub-items are answered and
published; the notes below are the evidence, kept so the next reader does not
re-open the serve repo to check.

1. **Neighbor object.** `_build_neighbor_payloads`
   (`stashsage_serve/app/api.py:1601`) always emits `item_name`, `price_exalts`,
   `price_display`, `price_simple` and `mods`, and conditionally `dps`,
   `base_type`/`icon_url`/`base_category` (only when `_resolve_base_icon` hits)
   and `stash_name`. `price_display` is
<!-- Retired currency reference:    `f"{exalt}e/{chaos}c/{divine}d/{annul}a"` (`api.py:1206`) — four currencies, -->
   whole numbers, no spaces.
2. **`/predict` vs `/predict-gui`: no difference.** Both call
   `_annotate_neighbor_mod_comparisons(_build_neighbor_payloads(...))`
   (`api.py:2165` and `api.py:2220`) and assemble the same response dict.
   `/predict` has done so since `326c587`, well before the API docs were
   written. **The premise this item was raised on was wrong**: the docstring at
   `tests/test_serve_api_contract.py:123` claimed `/predict-gui` was the only
   endpoint using the serializer. That docstring has been corrected, and
   `test_neighbor_payload_matches_public_api_reference` now runs the same
   assertions against both endpoints so the two cannot drift apart unnoticed.
3. **Presence.** Captured in the "Neighbor objects" table's *Always present*
   column. The conditional keys are *absent*, not `null`, which is the trap
   worth documenting.
4. **`currency_conversions` is neither a runtime snapshot nor the model's
   training-time rates.** `_currency_conversions` (`api.py:1209`) reads the
   module constants imported at `api.py:33` from
   `stashsage_serve/__init__.py:44-46`, which are plain literals
<!-- Retired currency reference:    (`divine_exalt = 394`, `chaos_exalt = 40`, `annul_exalt = 361`). The sync -->
   rewrites those literals from `poe2trade/__init__.py` via
   `Ensure-ServeRuntimeConstants` (`tools/Sync-Downstream.ps1:435`), and its AST
   reader deliberately ignores the `data/rates.json` override that upstream
   applies at import (`tools/read_runtime_constants.py:47`). So serve's rates
   are the *static fallbacks* of the release, refreshed only when the literals
   are edited upstream and a release ships. `stashsage_serve/runtime_rates.py`
   exists but nothing in the API path calls it.

   Two consequences worth knowing: the published docs now say the rates are
   fixed per release; and because training in `poe2trade` converts prices with
   the live `rates.json` values while the API renders displays with the frozen
   literals, the two can disagree. Exalt values are unaffected — they are the
   canonical unit end to end — but a `price_display` divine figure is only as
   good as the literals in the shipped `__init__.py`. **If those literals are
   left stale across leagues, `price_display` and `price_simple` quietly drift
   from reality.** Refreshing them is a `poe2trade` edit plus a sync, not serve
   work.

   Checked 2026-09-08: **currently aligned** — the literals (394 / 40) equal
   `poe2trade/data/rates.json` (refreshed 2026-09-02, "Runes of Aldur"), so
   nothing is stale today. Latent risk, not a live bug; nothing enforces the
   agreement, so a guard test comparing the two would be cheap insurance.

Pinned by `test_neighbor_payload_matches_public_api_reference`,
`test_currency_conversions_expose_every_documented_rate` and
`test_knn_summary_omits_median_and_mean_without_a_priced_neighbor` in
`tests/test_serve_api_contract.py`, which still skips cleanly when the sibling
checkout is absent (`tests/test_serve_api_contract.py:10`).

## Open question for the maintainer — API request retention

The requester asked whether submitted `item_text` bodies or prediction results
are retained in server logs. **This must not be answered from the existing
privacy policy.** That policy (`#privacy` in `index.html.j2`) describes the
desktop app operating locally; it says nothing about the hosted API, and a Flask
app behind PythonAnywhere has a web-server access log regardless of what the
application itself writes.

To answer it, someone with serve access needs to establish:

- what the application logs per request (`request_id`, category, `source`,
  timings — and whether `item_text` or the response payload ever reaches a log
  line, including on the error paths that return `inference_failed`),
- what the platform's own access log retains and for how long,
- whether anything is persisted beyond logs (usage counters, analytics).

Once known, add an API-specific data-handling paragraph to the `#api-docs`
section. Until then the honest answer to the integrator is "we'll confirm rather
than guess".

## Working notes

- **Repo boundary.** The Flask app, Discord bot, WSGI config and deployment live
  in `StashSage_Serve` (`README.md:71`). Do not copy the serve app back into
  `poe2trade`; shared ML/runtime assets flow one way, via
  `tools/Sync-Downstream.ps1 -Target Serve`.
- **Serve-dependent tests skip silently** when `../../StashSage_Serve` is not
  checked out beside this repo, so a green run here proves nothing about serve.
- **The public site is generated.** `docs/index.html` is rendered from
  `index.html.j2` by `tools/render_index.py` (driven by `build_index.bat`). Edit
  the template and mirror the same text into `docs/index.html`; a render should
  differ only in the `dateModified` / build-date stamps, which the release build
  sets. Do not hand-bump those in a docs-only change.
