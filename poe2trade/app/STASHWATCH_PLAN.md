# StashWatch

StashWatch is an optional desktop listing monitor. It observes trade-visible
listings for an explicit account and league, with Merchant or All public listing
scope, optional categories, and a 15/30/60/120 minute or custom interval.

## Boundaries

- A lightweight collector searches/fetches listings without parsing, training,
  scoring, or writing into scraper output or model directories. It reuses the
  desktop's category definitions and listing status options.
- SQLite observations, watches, runs, and events live in the per-user StashSage
  directory. No credentials or personal history belong in this checkout.
- One worker serializes polls across watches. Timers do not overlap jobs, waits
  honor trade rate-limit headers, and cancellation interrupts waits. Enabled
  watches resume when the desktop app restarts; app exit stops the worker.
- Compare account, league, listing scope and categories consistently. Changing
  that scope starts a new baseline while preserving old observations/events.
- Record added, price_changed, no_longer_observed and reappeared events. Absence
  is only inferred from a complete search/fetch. Capped/failed searches retain
  previously observed listings. A disappearance is never confirmed sale/revenue.
- Preserve listing amount/currency and observation timestamps. Model currency
  conversions must not manufacture listing price changes.

## UI and remote access

A StashWatch sidebar view offers saved watches, account/league/category settings,
interval presets/custom minutes, Start/Pause/Check now, last/next check status,
Current Listings, Activity and CSV export. The same collector/store serve the
HTTP API and a phone-friendly web view.

The HTTP service is off by default, binds only 127.0.0.1:5006, and requires a
per-user random token for every data/control endpoint. Tailscale Serve can proxy
it explicitly without publishing anything or altering existing mappings.
Starting/enabling this listener is a user setting; remote requests cannot choose
filesystem paths. StashSage_Serve remains the separate pricing service.

API: GET/POST /stash/watches; PATCH /stash/watches/<id>; POST start, pause, check;
GET listings (JSON/CSV), events with a cursor, and GET /stash/runs/<id>.
GET /stash/catalog supplies selections and installed league labels. The browser
keeps its token in memory and sends Authorization headers, not URL parameters.

## Validation

Write focused tests first for event history/persistence, complete/partial
coverage, scope baselines, timers/overlap/cancellation, API authentication and
validation, and collector queries/rate limiting. Run them red before implementing.
Exercise the desktop view against fake results, then run the repository gates
only when no scrape is running. Verification makes no live trade calls.

## Using StashWatch

Launch the desktop normally (`python -m poe2trade.app`) and open **StashWatch**
in the sidebar. Enter an account and an explicit trade league, select Merchant
or All public listings, choose categories and an interval, and press **Start
watching**. **Check now** also works while paused. Settings and history survive
restarts; enabled watches resume on the next launch. Timers schedule the next
check after the previous one finishes, so checks never accumulate or overlap.

The collector includes unpriced and non-rare listings. No category selection
means one account-wide query. A capped result, missing fetched item, or failed
category marks the check incomplete and retains unseen listings. The UI shows
coverage and last-seen timestamps; absence events record a time interval, not an
exact sale time. Current Listings exports the last known visible rows to CSV.
StashWatch observes public listings; it cannot inspect private inventory or
change listing prices, and it does not rerun the ML scoring pipeline.

HTTP access is opt-in under **Enable HTTP access for phones and agents**. The
default port is 5006; another port can be selected while the service is off.
**Copy API token** copies the randomly generated per-user secret. **Open phone
view** opens the localhost page, where that token is required to connect.

To expose it privately without replacing the existing 443/8443 services, run
this on the desktop after enabling HTTP access:

```powershell
tailscale serve --bg --https=10000 http://127.0.0.1:5006
```

Open the HTTPS URL reported by Tailscale on a connected phone and enter the
token. Agent tool runners must also have tailnet access and send either
`Authorization: Bearer <token>` or `X-API-Key: <token>`. The page keeps its token
only in memory. There is no public publishing or automatic Tailscale change.

Example watch settings for `POST /stash/watches`:

```json
{
  "account": "Player#1234",
  "league": "Forbidden Rites",
  "listing_type": "merchant",
  "categories": ["Boots", "Ring"],
  "interval_minutes": 30
}
```

POST returns the saved watch (paused initially); its `id` selects all subsequent
routes. POST `/stash/watches/<id>/start` enables the timer; POST `check` returns
202 with a job ID to poll at `/stash/runs/<id>`. Repeated `check` calls while that
watch is running return the same job. GET `listings?format=csv` downloads CSV.
GET `events?after=<cursor>&limit=500` returns chronological events and a
`next_cursor`; persist that cursor to avoid logging events twice. Events include
their original scope and revision even after settings change. PATCH watch
settings while no job is running; duplicate scopes reuse a saved watch.

Native Android clients additionally send `X-Request-ID` with manual checks.
The saved request-to-job mapping survives completion and application restart,
so a lost response can be reconciled without starting another scrape. A reused
request ID returns its original completed, failed or interrupted job; use a new
ID only for a deliberate new check.

Watch responses include `settings_version`. Send that value in `If-Match` on
PATCH; stale edits return HTTP 409. Event pages include `generation` (persistent
database identity) and `head_cursor`, allowing clients to detect a reset and
reimport instead of skipping new history. Events carry a `baseline` flag through
the first complete poll of each scope revision; watchers expose
`last_complete_at` independently of the latest attempt. Android commits imported
events and the cursor together and suppresses baseline/backfill alerts.

To stop polling, press **Pause** (which cancels a running check). To stop HTTP,
uncheck its enable option or exit StashSage. To remove only this Tailscale proxy:

```powershell
tailscale serve --https=10000 off
```

Personal history is `%APPDATA%/StashSage/stashwatch.sqlite3` on Windows, or the
existing StashSage user config directory on other platforms. API settings and
the secret remain in the user's existing config file. No history or secrets are
synced into the project, Android APK, or hosted pricing service.
