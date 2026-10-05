# Research dataset publication

The publisher archives a named, completed scrape and optionally rebuilds its
parsed/model/overlay Parquets using the existing feature code. It never trains
models, refreshes rates, alters scraper output, or reads unversioned matrices
from mutable `db/files` folders. This is independent of application releases.

## Local preparation

Use the existing virtual environment and install the updated requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m poe2trade.research prepare --output-root poe2trade/utils/scraper/output --dataset-id YOUR_SWEEP_ID --league forbidden-rites --categories rings --features
```

Pass all required category slugs to `--categories` for a full-sweep snapshot.
`--state-root` supports a separately configured scraper state tree. Preparation
requires v2 completion records; failed, incomplete and overridden runs are
rejected. Each category is copied under its existing writer lock and checked
against its completion manifest. A busy category fails without breaking its lock.

The printed directory is `output/research/datasets/<build_id>`. Its immutable
manifest includes source hashes, scrape windows, rates, transformation source
hashes, dependency versions, feature schemas, lineage and exclusions. Identical
inputs and recipes produce the same build. Original JSON is gzip-compressed
without changing its uncompressed bytes. The source scrape remains untouched.

```powershell
.\.venv\Scripts\python.exe -m poe2trade.research verify output/research/datasets/BUILD_ID
.\.venv\Scripts\python.exe -m poe2trade.research upload output/research/datasets/BUILD_ID --local-store output/research/local-objects
```

The local-store adapter exercises the upload protocol without an external account.
It is not a publicly served directory. `upload` alone does not publish a dataset
in the SQL catalog.

## Cloud storage and PostgreSQL

Use a private S3-compatible bucket (R2 or S3). Configure `RESEARCH_BUCKET`, optional
`RESEARCH_S3_ENDPOINT` (HTTPS), and the normal boto3 AWS credential environment or
credential file. Keep those credentials out of Git and job JSON. The upload role
needs list/head/get/put and multipart operations on the dataset prefix. A separate
portal credential needs only object-read access. R2's ordinary tokens are scoped
by bucket, not by curated prefix, so this server credential can also read raw
objects in the same bucket. Never distribute it to researchers; the catalog
authorizes only curated downloads.

Configure `RESEARCH_DATABASE_URL` locally. Use `sslmode=verify-full` with the
provider's CA configuration for an external database. PythonAnywhere's own
PostgreSQL can instead be reached from the publisher through its documented SSH
tunnel; bind the local tunnel only to loopback. Do not share the hosting account's
SSH credentials with students.

```powershell
.\.venv\Scripts\python.exe -m poe2trade.research migrate
.\.venv\Scripts\python.exe -m poe2trade.research publish output/research/datasets/BUILD_ID
```

`publish` uploads and verifies objects, imports SQL in one transaction, and then
marks the build published. `ingest` stops before publication. Remote object bytes
are verified using SHA-256; multipart ETags are not treated as content hashes.
Upload receipts are scoped to destination and rechecked on retry. Upload failures
leave reusable objects and failed state under `output/research/uploads`; repeat
the same command to resume. SQL failures roll back the dataset, and the ingestion
job records the error type without logging connection strings.

Migrations run only on explicit `migrate`, never during a web request. Applied
migrations are checksummed. Add a new migration instead of changing an applied one.

## Automatic publication

Set `research_queue_dir` to `output/research/queue` in the home-server schedule.
The orchestrator then enqueues exact dataset/category/run identities after a v2
completion. It never contacts object storage from a scrape worker. Queue failures
are reported without turning successful scraping into another scrape.

Run this finite command on a timer on the home server:

```powershell
.\.venv\Scripts\python.exe homeserver/publish_dataset.py --queue output/research/queue
```

The timer inherits the local database/storage configuration. The drain retries
pending, failed, or interrupted jobs; successful jobs are not repeated. Per-category
jobs publish category datasets. To publish one catalog entry for an entire sweep,
run `prepare` with all categories and then `publish`. No persistent service is
started by these commands. Stop future work by disabling the timer; timeout kills
the current CLI, leaving immutable source files and resumable upload state.

## Dataset contract

`dataset_id` identifies the collection sweep; `build_id` identifies its exact
export recipe, selected categories, and artifact bytes. Rebuilding features with
new code produces a new build without replacing an earlier publication.

Observation IDs include league, dataset, category, original source hash and record
position. They are not item IDs. The same item in two sweeps has two observations.
Parsed/model/overlay rows join through separate `*.rows.parquet` files; numeric
identity columns never enter the model matrices. Downloaded model Parquets precede
training's numeric selection, segment-specific constant pruning and preprocessing.

Jewel, Tablet, mace and shield subtypes use separate model folders; Waystone tiers
have their own matrices, lineage and pricing sidecars. Their row counts overlap:
do not sum parsed/model/overlay or combined/tier matrices as unique observations.

Original JSON is restricted to storage operators. The research observations table
uses an explicit field allowlist and excludes account/stash details. A published
SQL reader cannot access raw artifacts or unpublished builds. Raw data access must
be arranged separately under the applicable data-use policy.

Native asking price and currency remain in observations. Model prices use the
captured category rates and report the target as exalted. Historical snapshots
without a completion-time rate hash are labelled
`rate_hash_verified_at_completion=false`; the publisher hashes their current bytes
but cannot retroactively prove their history. Captured rates are category/run
snapshots, not a separate exchange-rate observation for every item. Resumed sweeps
can span multiple runs. Future fetch saves include collection/index timestamps;
historical missing timestamps stay null and only the collection window is known.

These are sampled asking prices, not completed-sale prices or a market census.
Search bands, fetch-depth caps, skipped bases and parser exclusions affect the
sample. Disappearance does not prove a sale. Keep repeated items out of both sides
of an evaluation split when measuring generalization. Record build IDs and feature
set IDs with experiments. Confirm permitted redistribution/commercial use of the
underlying data; access to the research service does not grant additional rights.

## Student access and SQL

Create a dedicated PostgreSQL login for each student using SQL `CREATE ROLE ...
LOGIN PASSWORD ...`, with no superuser/create-role/create-database privileges or
inherited writer roles. On Neon, roles created through the Console/API/CLI inherit
`neon_superuser`; SQL-created reader roles avoid that administrative membership.
Use a separate research database from the product database.

```powershell
.\.venv\Scripts\python.exe -m poe2trade.research grant-reader student_alice
```

This grants only `research.published_*` views, sets 30-second statement and
60-second idle-transaction limits, and limits connections to three. It does not
grant base-table or raw-file access. Account expiration/revocation is managed by
the database provider. Do not use your owner login in notebooks or the portal.

```sql
SELECT category, currency, count(*), avg(price_native)
FROM research.published_observations
WHERE build_id = 'PINNED_BUILD_ID'
GROUP BY category, currency;

SELECT price_exalted, (features->>'# to maximum life')::double precision AS life
FROM research.published_feature_rows
WHERE build_id = 'PINNED_BUILD_ID' AND variant = 'model';
```

For large experiments download Parquet and use pandas or DuckDB locally. Modifier
labels are JSONB keys and dictionary values, not SQL identifiers (some exceed
PostgreSQL's identifier limit). `published_feature_definitions` supplies stable
short IDs, types and original column order. Null and zero stay distinct.

## Operations and recovery

Monitor queue age/failures, ingestion job states, newest published scrape window,
artifact counts/bytes and PostgreSQL storage/query latency. Error records contain
types only; inspect a failed operation in a controlled debugging environment for
provider details without exposing credentials in shared logs.

Use provider-managed PostgreSQL backups/PITR plus periodic `pg_dump` backups to a
separate private backup location. Test restoring to a new database, applying reader
grants, and querying published views. Object storage is the reconstruction source:
retain manifests, rates, source JSON and recipes together. Keep an independent
archive copy for datasets cited in research. Local upload caches are not backups.

No automatic data deletion is enabled. Start with explicit retained snapshot IDs
and a storage budget; do not add a bucket lifecycle rule that removes artifacts
still referenced by published datasets. To hide a bad dataset without deleting
its evidence:

```powershell
.\.venv\Scripts\python.exe -m poe2trade.research withdraw BUILD_ID
```

Published views immediately omit withdrawn builds. Existing signed links expire
within five minutes. A corrected build has a new ID; published history is not
rewritten. Source changes and manifests belong in Git; dataset bundles, outbox,
credentials and database dumps do not belong in Git or LFS.

## Verification

Unit tests use synthetic scrape trees and temporary directories. Set
`RESEARCH_TEST_DSN` to an isolated loopback database whose name ends in
`_research_test` to run real COPY/rollback/permissions tests; these tests drop only
the `research` schema in that explicitly named test database. Never point this
variable at a real research database. Full repository gates still require an idle
scraper window as described in AGENTS.md.

The separate PythonAnywhere WSGI service is documented in
[`research_service/README.md`](../research_service/README.md).
