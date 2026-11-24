# Desktop Linux CI runner

GitHub schedules CI; the existing WSL Ubuntu desktop executes trusted Linux
jobs. The migration is reviewed in draft PR #328. Registration and API online
verification preceded the workflow switches; cold/warm evidence is required
before owner approval. The agent must not merge the pull request.

The dedicated account is `runner-poe2trade`, the runner is
`desktop-wsl-poe2trade`, and its installation is
`~runner-poe2trade/actions-runner` (under the dedicated account's home).
Jobs require all three labels:
`[self-hosted, linux, local]`.

The live manifest monitor remains hosted on its once-daily schedule (07:07 UTC). Native
Windows release-contract, packaged-build, and Tk jobs also remain hosted.

## Trust and data boundary

Every local job, including both routing jobs, permits PR execution only for a
same-repository head, draft or ready; fork heads never reach the runner. Main
pushes and explicitly requested manual runs also execute. Drafts were excluded
until November 2026; that flag never limited who can run code here, because
the same writers can dispatch any branch manually.
There is no `pull_request_target` workflow. Keep the repository private and
`run_workflows_from_fork_pull_requests` disabled in the repository Actions
settings; a guard inside editable workflow YAML is not the sole trust boundary.
Workflows use read-only permissions, SHA-pinned actions, and checkout with
`persist-credentials: false`.

Runner users are
separated from each other, but the shared WSL Docker daemon and Windows mounts
are not isolation from the Windows owner's data. This boundary is accepted only
for trusted own-repository work: same-repository PRs (draft or ready), main,
and explicit manual runs.
Membership in the shared `docker` group is privileged access to that daemon,
not container isolation from the host. This follows the SocialSyncFlask fleet
pattern. No owner authentication, release signing keys, or live scraper/model
data belongs in the runner checkout. Never use the Windows developer checkout
as the Actions workspace or mount its authoritative data into test containers.

## Host provisioning

Always target the existing distro explicitly with `wsl -d Ubuntu`. Create the
non-sudo account `runner-poe2trade`, its private home, and the runner directory
above. Add only the approved shared `docker` group. Download the official
GitHub Actions runner release and verify its published SHA-256 before unpacking.
Mint a short-lived repository registration token using the Windows desktop's
authenticated `gh`, pass it in memory to `config.sh` as the dedicated Linux
user, and never save or print the token. Do not copy the desktop's `gh` login.

Configure the repository URL `https://github.com/rheinze08/poe2trade`, runner
name `desktop-wsl-poe2trade`, and custom label `local`. GitHub supplies the
default `self-hosted`, `Linux`, and `X64` labels; matching `linux` is
case-insensitive. Install using `svc.sh install runner-poe2trade`, then disable
the resulting unit's boot autostart **without `--now`**. The unit is:

```text
actions.runner.rheinze08-poe2trade.desktop-wsl-poe2trade.service
```

Use a runner-owned toolcache at `~runner-poe2trade/toolcache` and Android
SDK at `~runner-poe2trade/android-sdk`. Do not make another runner's cache
world-writable. The prerequisites are:

| Work | Provisioned requirements |
| --- | --- |
| Runner and routing | Git, Bash, current runner native libraries; Node supporting `node --test` |
| Python checks | CPython 3.11, 3.12, 3.13; pip/venv; Tk support for each interpreter; `python3-tk`, `xvfb`, `xauth` |
| Browser integration | Chrome and Selenium-compatible driver resolution; synthetic providers only |
| Research/outreach integration | Shared Docker daemon; `postgres:17-alpine`; fresh `poe2trade_research_test` and `poe2trade_outreach_test` databases |
| Linux packaging | `rsync zip binutils python3-tk xclip xsel libx11-6 libxtst6 libayatana-appindicator3-1`; pinned application requirements/PyInstaller |
| Android | Temurin JDK 17, checked-in Gradle wrapper, SDK command-line tools, API 35 platform, AGP-compatible build-tools; explicit `ANDROID_HOME` |

The workflows retain their minor Python selections and all three matrix legs.
`actions/setup-python` can use the Ubuntu 26.04 x64 distributions, but verify
Tk imports in every interpreter. Each local Python check installs into a fresh
job environment; shared interpreter site-packages must not accumulate editable
installs. Local jobs keep pip's wheel/download cache in the runner home and
disable the redundant `setup-python` GitHub cache transfer. Hosted jobs retain
that transfer, including after a one-line runner rollback. On a persistent home,
even the lint cache key otherwise uploads the full accumulated application cache.
Linux build staging and its builder-managed environment stay under
runner-owned temporary storage. The developer checkout's `.venv` is unrelated
and must not be repaired or recreated for CI.

The system-package action checks exact installed package status on self-hosted
runners and fails with the missing list. Provision packages as administrator;
the CI user does not run `sudo apt-get`. Hosted fallback still installs them.
PostgreSQL uses a random host port from the Actions service context in every
DSN; never bind fixed port 5432. Only disposable test databases are used.

## Scheduling and resource sharing

The existing host night-window controller starts runners at 22:30
America/Chicago and checks for drained runners from 06:00. It discovers runner
services automatically. Reuse `Local-CI-WSL`; do not modify the controller.
Service boot autostart must remain disabled. The desktop must remain awake and
the owner signed in for its existing interactive scheduled tasks.

The controller checks every 15 minutes until 09:45 and only stops an idle
runner after its repository has no queued or in-progress workflow runs. Busy
work drains past 06:00; this is not a hard termination deadline. Its error path
holds runners rather than interrupting them. A missed interactive scheduled
task is not replayed later, and `Local-CI-WSL` does not prevent Windows sleep.

One repo runner serializes local jobs; pytest also sets `max-parallel: 1`.
The pytest job sets `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` to two. This bounds numerical
libraries on the shared eight-CPU host without dropping any Python matrix leg.
There are no new scheduled test matrices. RolyCode's long mutation work and
the other repos share the same CPU, RAM, Docker daemon and network. Cold/warm
timings must be measured with that contention in mind; hosted timings are not
a desktop guarantee. Do not restart WSL, Docker, or other runners to make a
job faster. Any later resource tuning belongs in this runner's service settings,
not a new controller. The manifest stays hosted at `7 7 * * *` (once daily,
07:07 UTC).

For this runner alone, status and an explicit idle stop are:

```powershell
wsl -d Ubuntu --exec systemctl status actions.runner.rheinze08-poe2trade.desktop-wsl-poe2trade.service --no-pager
# Only after confirming busy=false AND no queued/in-progress repository runs:
wsl -d Ubuntu -u root --exec systemctl stop actions.runner.rheinze08-poe2trade.desktop-wsl-poe2trade.service
```

Prefer the existing drain-aware controller for routine stopping. Its next
22:30 start will resume the installed service. Never stop another repo's runner.

## Workflow policy

Push triggers are restricted to `main`. PRs run on opened, synchronize,
reopened, and ready-for-review events, with fork jobs skipped before checkout.
Same-repository drafts run every local job; the hosted Windows jobs
(release-contract and native Tk) skip drafts and start on ready-for-review,
and the Windows packaged build stays on main pushes and manual dispatch.
Manual dispatches remain available and newer runs for the same
workflow/event/ref cancel superseded ones. Main pushes use the conservative
packaging-path gate; unknown diffs and manual requests retain build coverage.
APK and screenshot artifacts expire after seven days. Windows release-contract,
Windows packaged-build and Windows native Tk coverage remains hosted.

Before accepting a migration, run the focused Node policy/routing/package tests
and actionlint (declare `local` in its `self-hosted-runner.labels` configuration),
then manually dispatch tests, GUI overlay, and Android twice
against the same candidate commit. Record first-run and warm durations, runner
identity, all Python matrix results, and the retained Windows results. A first
run can restore an existing GitHub cache even when its local runner workspace
is new; record that distinction instead of claiming every dependency was cold.
Confirm a draft PR runs its local jobs while every hosted job is skipped, and
that a feature-branch push creates no push workflow run. Verify fork-workflow
settings again before review.

## Hosted rollback

Keep the security and safety fixes. Change only the runner selection below,
plus the draft guard noted after the table; hosted prerequisites remain
supported. No native Windows job needs rollback.

| Workflow job | One-line rollback |
| --- | --- |
| `tests.route` | `runs-on: ubuntu-latest` |
| `tests.lint` | `runs-on: ubuntu-latest` |
| `tests.typecheck` | `runs-on: ubuntu-latest` |
| `tests.pytest` | `runs-on: ubuntu-latest` |
| `tests.linux-build-smoke` | `runs-on: ubuntu-latest` |
| `gui-overlay.route` | `runs-on: ubuntu-latest` |
| `gui-overlay.shared-overlay-smoke` | `runs-on: ubuntu-latest` |
| `android.build` | `runs-on: ubuntu-latest` |

Local jobs run on draft PRs. A job moved to `ubuntu-latest` therefore bills
hosted minutes for every draft push unless its `if:` also regains
`&& github.event.pull_request.draft == false` inside the same-repository
clause.

The manifest is already hosted and requires no rollback. Reverting runner
selection does not remove the local service; after runs drain, stop only this
runner and leave the night-window controller and other repos unchanged.

## Migration evidence

Draft PR: https://github.com/rheinze08/poe2trade/pull/328.
On November 12, 2026, runner ID 21 was verified online through the GitHub API
before any `runs-on` switch, with `self-hosted`, `Linux`, `X64`, and `local`
labels. The service was active and boot-disabled. The execution evidence below
includes failed first attempts as well as successful follow-ups.

Provisioning probes passed as `runner-poe2trade`: Python 3.11.18, 3.12.16 and
3.13.18 each created a Tk window under Xvfb; Chrome headless rendering, Docker
access, Temurin 17.0.21, and Android API 35/build-tools 35.0.0 also passed.
The private Python 3.13 cache required its own `lib` path during installation;
`setup-python` supplies the selected interpreter's library path for each job.
No service-wide Python library override was added. A dry run of the existing
host controller discovered this service without any controller changes.
The existing scheduled start subsequently ran at 22:30 on November 12 and
logged this service's idempotent start at 22:30:29 America/Chicago, keeping
boot autostart disabled. This verified automatic discovery in the actual night
task as well as the earlier dry run.

| Policy evidence | Result |
| --- | --- |
| [Hosted manifest safety check](https://github.com/rheinze08/poe2trade/actions/runs/43348813009) | Passed in 22 seconds; still hosted, schedule unchanged |
| [Draft tests](https://github.com/rheinze08/poe2trade/actions/runs/43348940970) | All jobs skipped without runner assignment |
| [Draft GUI](https://github.com/rheinze08/poe2trade/actions/runs/43348940961) | All jobs skipped without runner assignment |
| [Draft Android](https://github.com/rheinze08/poe2trade/actions/runs/43348940957) | Build skipped without runner assignment |
| Feature push `codex/poe2trade-ci-push-evidence-20261112`, commit `ce1412fe6544b141c49ed50fc454ec9977cd43c2` | GitHub API returned zero push workflow runs after the push |

The first tests attempt exposed an existing release-contract assertion that
required feature-branch push triggers (811 other Windows tests passed). That
assertion was updated to the approved main-only/ready-PR policy, and the
superseded run was cancelled before its queued Python legs repeated the known
failure. The new Node policy tests also exposed a 100 ms VM execution-limit
flake under host contention; the bound is now five seconds without changing
the guard expressions. All 28 focused Node tests and actionlint pass.

The first GUI run passed, but its Python cache post step spent 6m13s preparing
and transferring an approximately 0.8 GB archive after the 14-second smoke test.
Lint then attempted
the same large transfer under its own key. The final candidate disables those
remote transfers only on self-hosted Python jobs and keeps the persistent local
pip cache. Its policy test verifies that hosted rollback still selects `pip`.
Consequently, first-versus-warm GUI timings include this policy improvement,
not just cache warming. Replacement tests run `43354576070` automatically
cancelled superseded manual run `43350338243`, verifying manual concurrency.

Android's initial empty-Gradle-home run `43349244223` reached the unchanged
30-minute cap: core tests passed in 13m21s, debug APK in 11m22s, and app unit tests
in 1m25s. The final unsigned release/lint step was cancelled; no artifact was
uploaded. This is an initial cold timeout, not a successful cold run. The cached
follow-up completed every task in 8m55s with the same 30-minute limit. Recreating
an empty Gradle home may encounter the cold timeout again; preserve the runner's
cache and retain this limitation when evaluating a replacement runner.

The first capped Python 3.11 run completed the suite in 4m49s (8m25s for the
job), with 2,511 passed, 111 skipped, and one documentation-path hygiene failure.
The dedicated account's directory references above now use tilde notation,
preserving their meaning without violating the existing public-docs contract.
That actual contract test was reproduced red and passed after the edit.
Earlier, the uncapped run had stalled at 37% for over 17 minutes with 37
threads; the capped run progressed beyond it with 15 observed threads.

| Workflow | First evidence | Warm evidence |
| --- | --- | --- |
| Tests | [43349237138](https://github.com/rheinze08/poe2trade/actions/runs/43349237138): cancelled after the obsolete push-trigger assertion failed; workflow elapsed 7m26s, incomplete matrix | [43362168625](https://github.com/rheinze08/poe2trade/actions/runs/43362168625): all nine jobs passed; workflow elapsed 44m35s, including 10m03s initial queue; local jobs totaled 34m21s |
| GUI overlay | [43349240380](https://github.com/rheinze08/poe2trade/actions/runs/43349240380): Linux passed in 10m30s; Windows 2m12s; workflow elapsed 41m39s including queue | [43359753778](https://github.com/rheinze08/poe2trade/actions/runs/43359753778): Linux passed in 3m18s; Windows 2m05s; workflow elapsed 32m28s including queue |
| Android | [43349244223](https://github.com/rheinze08/poe2trade/actions/runs/43349244223): timed out, job 30m21s; workflow elapsed 31m05s | [43359766480](https://github.com/rheinze08/poe2trade/actions/runs/43359766480): passed, job 8m55s; workflow elapsed 29m01s including 20m06s queue |

The GUI and Android warm runs used `cd022720`; the subsequent `3219079` commit
only corrected and expanded this documentation and was used for the final tests
run. Android reused its existing Gradle home, with
core tests 3m09s, debug APK 1m41s, app tests 15s, and release/lint 3m21s. Its APK
artifact and both GUI screenshot artifacts were verified to expire after seven
days. GUI passed 17 Linux tests (one platform skip) and all 18 Windows tests.
Shared-host load caused intermittent read-only WSL probe timeouts during Linux
packaging; the build continued and passed without restarting WSL or any service.

Final review also found that the policy tests themselves rejected the documented
hosted rollback. A test-only correction now accepts the exact local label set or
`ubuntu-latest`, rejects unsafe label variants, and verifies all eight rollback
entries. It was reproduced red and verified green locally, including complete
policy-suite probes against representative in-memory rollbacks. The executed
workflow configuration was unchanged by that correction.

Final tests-run job durations were: routing 13s, lint 44s, type-checking 50s,
Linux packaging 9m29s, Python 3.11 8m45s, Python 3.12 6m46s, and Python 3.13
7m34s. The hosted Windows release checks took 4m34s and its packaged-build/self-
update check took 5m15s. The Python 3.12 synthetic Chrome journey executed and
passed in 24.21s. All three Python matrix legs passed without raising timeouts.
Each full suite reported 2,512 passed, 111 skipped, and 36 subtests passed.
The earlier capped [trial](https://github.com/rheinze08/poe2trade/actions/runs/43358943042)
is retained as evidence of the documentation failure described above, rather
than presented as a successful cold matrix.

The three warm workflows consumed 46m45s of this runner's serial job time,
including their route jobs. Queueing stretched their individual wall times;
these observations are not a guarantee under the other repositories' nightly
load. At final verification the runner was online and idle, its service active
and boot-disabled, the repository private, and fork PR workflows still disabled.
No owner intervention blocked provisioning. The empty-cache Android timeout is
the remaining measured limitation; the PR stays draft for owner review.
