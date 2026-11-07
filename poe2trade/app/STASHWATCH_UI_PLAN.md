# StashWatch desktop workspace redesign

Keep StashScrape focused on local pricing and StashWatch focused on listing
observations. Help's Setups tab owns device guidance and the existing opt-in
desktop connection controls. All views reuse the single WatchRuntime.

StashWatch opens to Listings, Checks and Activity tables. Watch creation and
editing use a dialog with four preset intervals; saved non-preset intervals
remain valid until explicitly changed. Main controls operate on saved settings.

Capture a watch revision and observation timestamp on new runs, link new
observations/events to their run, and save the complete desktop projection for
each captured result. A saved projection includes missing rows, prior asking
prices and unknown states for incomplete coverage. Failed/cancelled attempts
do not create empty snapshots. Reads use bounded queries and one transaction.

Migrations only add nullable columns, indexes and snapshot storage. Preserve
legacy records and generation IDs; do not infer old run associations from
timestamps. Legacy last-known rows remain readable, while old runs without
snapshots explicitly report that limitation. Keep the existing monitoring API,
CSV columns, request IDs and Android history contracts unchanged.

Implement with focused tests first for migration, observation projections,
scope isolation, failure/empty-check distinctions, paging, explicit watch edits,
legacy intervals, UI state, stable selection and shared setup controls. Verify
with fake collectors and isolated stores. Run repository gates only when no
scrape is active. Public guidance labels screenshots of the redesign as previews
until a desktop release ships the new controls.
The website switches to the dashboard guide at v0.5.26; the current v0.5.25
downloads keep their existing instructions and preview labels.
