# Documentation Index

This directory separates current references and runbooks from historical plans.
Start with the repository [README](../README.md) for setup and common commands.

## Current Technical References

- [Pipeline Reference](PIPELINE.md) — parse, matrix, supervised training,
  scoring, KNN training, validation, inference, and generated artifacts.
- [Weapon Feature Algorithm](WEAPON_FEATURES.md) — weapon damage extraction,
  normalization, DPS features, and offline/runtime parity.
- [Craft Potential](CRAFT_POTENTIAL.md) — current CraftOracle counterfactual
  simulation behavior and limitations.
- [CraftOracle Affix Catalog](CRAFT_ORACLE_AFFIX_CATALOG.md) — catalog design,
  tier eligibility, provenance, and completed rollout details.

## Active Planning

- [Implementation Notes](IMPLEMENTATION_NOTES.md) — the consolidated active
  backlog and unresolved product, release, and updater decisions.
- [Update-Release Optimization Review](../update_release_optimize_20260903.md) —
  measured release-pipeline bottlenecks, installer-size safeguards, and the
  recommended speed-to-risk implementation order.

## Release Operations

- [Release QA Checklist](RELEASE_QA_CHECKLIST.md) — manual checks before and
  after publishing.
- [Release Rollback Runbook](RELEASE_ROLLBACK_RUNBOOK.md) — asset repair,
  binary retirement, revocation, and recovery verification.
- [Supply-Chain Hardening](SUPPLY_CHAIN.md) — optional hashed dependency lock
  workflow and rollback.
- [Git Storage Reclaim](GIT_STORAGE_RECLAIM.md) — safe cleanup and explicitly
  destructive history-rewrite procedures.
- [Discord Bot Setup](Discord%20Bot%20Setup.docx) — end-user Discord bot setup
  guide in its original formatted document.
- [`installer/legal_notice.txt`](../installer/legal_notice.txt) — legal notice
  retained as a standalone distribution artifact.
- `build-size-report.txt` — generated report from the latest Windows package;
  do not edit it manually.

## Subsystem Documentation

- [Home-server rotation](../homeserver/README.md)
- [Scraper overview](../poe2trade/utils/scraper/README.md)
- [Scraper operations](../poe2trade/utils/scraper/SCRAPER_OPERATIONS.md)
- [POE2Scout API](../poe2trade/utils/scraper/POE2SCOUT_API.md)
- `poe2trade/db/readme` — concise legacy database-module file map. The detailed
  pipeline source of truth is `docs/PIPELINE.md`.
- `poe2trade/utils/readme` — concise legacy utility-module file map.

The two extensionless `readme` files are retained because packaging and curation
rules refer to those exact names. Rename them only together with those rules and
the associated release-contract tests.

## Generated Model Reports

Files matching these patterns are generated model diagnostics, not standalone
human-maintained documentation:

- `poe2trade/db/super_models/*_model_readme.txt`
- `poe2trade/db/unsuper_models/*_model_readme.txt`

They intentionally remain beside their model artifacts. Regenerate them through
the model pipeline; do not consolidate or hand-edit them.

## Archive

Historical plans, completed implementation notes, dated communication, and old
release media are catalogued in the [archive index](archive/README.md). Archived
documents retain evidence and design context but are not the current backlog or
operating procedure.
