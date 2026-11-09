# Windows hotkey hardening

Status: implemented; automated validation recorded below. Physical keypad/PoE
acceptance and confirmation from the reporting user remain pending.

## Implementation notes (2026-09-14)

- Added an internal native Windows hook adapter, keeping the existing public
  backend API and settings layout. It separates keypad/navigation events,
  ignores injected events, and observes physical releases even during the
  keyboard library's synthetic-input replay window.
- Added per-key press ownership, exact modifier matching, overlap checks,
  native physical-state reconciliation, and off-thread action callbacks.
  Native item copying avoids releasing a Ctrl already held by the user.
- A separate native probe consumed injected F24 events and confirmed that
  suppressed key-down leaves Windows asynchronous state up. Recovery therefore
  treats suppressed trigger state as unknown. It never rearms from that query:
  after two seconds without repeats AND all modifiers released, an inactive
  suppressed press becomes pass-through until an observed key-up. This permits
  ordinary input recovery without firing an action again on a possibly-held key.
  An actively repeating held key does not expire. A key held without repeats
  (for example while another key repeats) can become pass-through in this
  recovery case, but cannot re-trigger until release.
- Added `off`, active/disabled/unavailable summaries, guarded shortcut editing,
  failure-safe replacement, save rollback, and reset of swapped assignments.
  Blank still selects the default. Shutdown removes app-owned hooks.
- Updated regression tests for these cases and a Windows adapter start/stop
  smoke check that sends no keyboard input.
- Implementation refinement: Windows multi-step action chords are rejected
  explicitly rather than using the proposed upstream suppression fallback.
  That fallback would reintroduce the modifier/replay behavior this work removes.
  AltGr action chords are also rejected explicitly. Linux keeps pynput.
- The manual matrix below is still required before claiming that the original
  report is reproduced/resolved on the user's hardware. No physical keypad,
  game interaction, privilege mismatch, or suspend/resume check was performed
  by the automated tests.

Native callback timing reference: [Microsoft LowLevelKeyboardProc documentation](https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelkeyboardproc).
The asynchronous-state behavior for suppressed input above was measured locally;
the smoke/regression suite does not require sending keyboard input.

Validation on the final source:

- Focused hotkey/settings regression suite: 101 passed.
- Ruff: passed. Scoped mypy: passed (26 source files).
- Full pytest: 1,295 passed, 3 skipped, 36 subtests passed. Four NumPy warnings
  came from runtime-asset fixture tests.
- Release-readiness gate: passed, including its 1,294-test run, validation of
  both league model sets, and base image/icon freshness checks.
- Native GUI smoke tests were run on an isolated Windows desktop. Shared-desktop
  attempts intermittently dismissed real popup windows; the isolated full run
  passed without changing presenter code or relaxing those tests.
- A synthetic dispatch probe returned in 2.84 ms while its action callback
  remained blocked. This verifies off-thread dispatch, not end-to-end PoE latency.

## Goal and scope

Keep ordinary keyboard input reliable while retaining the existing app layout,
settings fields, default shortcut strings, and `utils.hotkeys` public API.
Implement primarily in `poe2trade/utils/hotkeys.py` and
`tests/test_hotkeys.py`. Limit GUI/config changes to binding validation,
cleanup, and existing settings help text if required. Keep Linux behavior stable.
Use existing settings fields and feedback surfaces for disabled/default status;
no new settings page is needed.

No dependency replacement, GUI redesign, scraper changes, or model changes are
needed. Game-only activation is a separate product decision: this work preserves
the existing global shortcut behavior.

## Evidence and uncertainty

These observations describe the pre-change implementation.

- GUI price-check and workspace shortcuts use `suppress=True`. The Windows
  wrapper registers a blocking `keyboard.hook_key` for their trigger.
- In this checkout, the installed Windows library resolves `1` to scan codes
  `(2, 79)`, `2` to `(3, 80)`, and `3` to `(4, 81)`. Keypad keys therefore share
  digit registrations. End, Down, and Page Down also resolve to 79, 80, and 81.
- The wrapper stores one `trigger_down` boolean per shortcut. It does not
  distinguish physical triggers or check keypad identity. While that flag is
  set, every subsequent down event reaching the handler is suppressed.
- Modifier matching uses `keyboard.is_pressed`, which reads library state.
  The library bypasses state updates during its own synthetic input replay.
  Interaction with the app's injected copy shortcut needs explicit coverage.
- The existing Windows suppression test checks one normal Ctrl+1 down/up cycle;
  it supplies no scan code or keypad metadata.

The aliasing and shared flag are confirmed code properties. A missed release,
stale Ctrl state, or replay race causing the reported symptoms remains a
hypothesis. Do not describe the report as reproduced until it is.

### Additional report: removed shortcut still works

The user reports that after removing a shortcut while trying to replace it,
Ctrl+1 still works and cannot be set as expected. Current code provides a direct
explanation for continued activation after clearing the field:

- `_bind_overlay_hotkey` uses `(custom or "").strip() or DEFAULT_OVERLAY_HOTKEY`.
  Clearing the field actively re-registers Ctrl+1; it does not disable it.
- Invalid replacement registration also attempts to restore Ctrl+1.
- `_make_hotkey_commit` runs on focus loss/Enter, updates config before binding,
  and persists the attempted value even if the binder internally falls back.
  This can make the displayed/persisted setting differ from the active binding.
- Removal failures are logged, but the old handle is discarded anyway before
  registering a replacement. A surviving hook would then be untracked.

Default restoration is the leading explanation for the new symptom, without
requiring a stuck-key bug. Failed removal, editing while the shortcut remains
active, and another running app instance are separate possibilities. The
inability to set Ctrl+1 still needs reproduction and the user's app version.
The keypad/input-state investigation remains necessary for the original report.

## Behavior contract

1. Bare digits and ordinary navigation keys pass through without invoking app
   actions, unless the user explicitly configures a bare-key shortcut.
2. Plain digit shortcut tokens target the main keyboard, excluding the keypad.
   Intentional keypad bindings use an explicit token such as `num1` in the same
   settings field. This is a deliberate compatibility change for users who
   previously relied on Ctrl+keypad aliases; document it in release notes.
3. Navigation shortcuts distinguish dedicated navigation keys from keypad keys.
   Explicit keypad bindings retain physical identity across Num Lock changes.
4. Suppress only the trigger belonging to a matched chord. Modifier input stays
   native and immediate. One physical press starts at most one action; repeats
   do not spawn additional actions.
5. Match the configured modifier set exactly, so Ctrl+1 and Ctrl+Shift+1 can
   coexist. Define left/right modifier aliases explicitly and test AltGr before
   claiming support for it. Document this change from current subset matching.
6. Track ownership of suppressed presses through release, even if modifiers
   change first. Another physical key must never inherit that suppression.
7. Recover from stale state without requiring a restart or blindly injecting
   modifier releases. Internal errors must not leave unrelated input blocked.
8. Saving settings repeatedly must not multiply hooks or callbacks. Tray mode
   retains bindings; actual shutdown removes app-owned registrations.
9. Default, disabled, invalid, and active custom bindings must have distinct,
   visible outcomes. A failed save must not appear successful or silently
   activate a different shortcut.

## Implementation sequence

### 1. Capture regressions and define key identity

Extend the fake Windows event harness with scan code, keypad identity, repeat
sequences, modifier transitions, and a controllable physical-state provider.
Reproduce the current cross-key state interference in deterministic tests.
Keep hardware reproduction of the user's original report as a separate check.

Add an internal trigger resolver and matcher. Use the existing library's
layout-aware name mapping plus event metadata; do not globally hardcode US
keyboard digit scan codes. Specify main-keyboard, keypad, and navigation
matching independently. Audit metadata with Num Lock both on and off; if the
library cannot distinguish a case, resolve that limitation before shipping
rather than silently capturing both keys.

### 2. Replace the shared held flag with per-key state

Track suppressed physical presses by identity, including scan code and keypad
distinction where available. Keep callback dispatch off the input hook thread.
Record whether a press began suppressed so repeats/releases follow that
decision. A key held before modifiers are pressed should not become a fresh
shortcut merely through auto-repeat.

Use one internal dispatcher for app-owned simple suppressed chords if needed
to arbitrate overlapping registrations. Keep `add_hotkey` and callable removal
handles unchanged. Resolve exact modifiers deterministically; reject duplicate
chords instead of silently depending on registration order. Retain the existing
multi-step fallback initially, and label it outside the new simple-chord
guarantees until separately tested.

### 3. Reconcile physical state and synthetic copy input

Introduce a small mockable Windows state adapter. Evaluate native modifier
state at trigger time alongside event transitions, and reconcile stale held
records outside the low-level callback. Account for Windows state-query timing:
the current hook event may precede the OS state update. Do not reset legitimate
long-held keys using a fixed timeout alone.

Test `send`/`press_and_release` while a shortcut is held, including real release
events during replay. If the dependency's replay bypass loses state, contain
the remedy inside the wrapper and use supported Windows interfaces rather than
mutating the library's private pressed-key dictionaries. Do not replace input
injection speculatively before a failing test or trace demonstrates the need.

On reconciliation or callback-dispatch failure, log the error and clear the
affected internal state with an explicit pass-through recovery policy. Preserve
normal paired suppression when the state is healthy. Avoid periodic work on
the hook thread and avoid logging individual typed keys.

### 4. Make rebinding and cleanup predictable

Prioritize this settings work alongside the initial regression fixes, since
clearing a field restoring Ctrl+1 is already explained by current code.

Preserve legacy empty/missing values as "use default" to avoid silently
disabling shortcuts in existing installations. Accept an explicit `off` token
for action hotkeys in the current text fields; normalize case and whitespace,
persist it, and remove the binding without falling back. Show "Disabled" in
the existing summary. Add field help: "Blank uses the default; off disables."
Keep the native item-copy shortcut separate: it is an input-injection setting,
not a global action registration, and must not inherit `off` accidentally.

Audit initialization, save-all, per-field commit, reset-to-default, and summary
formatting so they use the same default/disabled interpretation. Ensure `off`
survives restart and reset explicitly restores defaults. Avoid introducing
another fallback path through existing `or DEFAULT_*` expressions.

Validate and normalize a candidate before replacing a working binding. If
registration fails, retain the old binding and report the failure using existing
logging/settings mechanisms. Make removal idempotent and clean up only hooks
owned by this app; never use blanket global unhooking as routine recovery.

Have the internal GUI binders return a structured outcome (active chord,
disabled status, or failure) while retaining the backend's public API. Commit
config only after successful application; on failure keep the last working
setting and show the error. Handle persistence failure visibly and roll back
where possible. Do not discard a handle after failed removal or register a
replacement over a hook whose ownership is unresolved. Registration rollback
must also retain ownership information if cleanup fails.

Reproduce editing Ctrl+1 while it remains globally active. Suspend action
dispatch and trigger suppression while an existing action-hotkey entry has
focus, using existing focus events and a small backend guard if necessary.
Typing/editing must pass through; already-suppressed held presses still need
their release cleanup. Resume predictably after commit, cancellation, window
close, or focus change, and test this separately from game/global activation.

Handle rebinding during a held suppressed key: retain a minimal release cleanup
record until that press finishes or physical-state reconciliation clears it.
Check existing GUI fallback behavior so a rejected setting is not silently
shown as active. Keep any required GUI edits limited to these existing call sites.

Log binding registration/removal, normalized trigger scope, conflicts, fallback,
and stale-state recovery. Include app version and backend in diagnostics.
Do not collect clipboard contents or raw keystroke streams.

## Validation

### Automated regression matrix

- Bare 0-9, keypad 0-9, and navigation input passes through as specified.
- Ctrl+1/2/3/4 triggers only the intended action on the intended physical key.
- Explicit keypad bindings work with Num Lock on/off without capturing the
  dedicated End/Down/Page Down keys.
- Interleaved top-row/keypad presses do not share suppression state.
- Repeats fire once; release-before-modifier and modifier-before-release both
  clean up correctly; pressing modifiers after holding a digit does not fire.
- Missing release followed by physical-state recovery restores ordinary input;
  a genuinely held key is not incorrectly reset by reconciliation.
- Left/right Ctrl, exact extra-modifier matching, overlapping shortcuts, and
  unsupported/ambiguous aliases have defined outcomes.
- Synthetic Ctrl+C and real Ctrl releases during replay do not leave a sticky
  logical modifier or cause a subsequent bare digit to trigger.
- Rebind failure, repeated saves, removal twice, removal while held, callback
  failure, and shutdown leave no duplicate actions or abandoned suppression.
- Clearing a field deterministically selects and displays the default; `off`
  removes it, including after save-all and restart; reset restores it.
- Invalid replacement and failed removal retain a truthful active setting and
  tracked handle; no invisible default or duplicate hook is installed.
- Focus-loss commits, Enter commits, disk-write failure, and shortcut editing
  while its old chord is active do not produce misleading saved state or
  trigger price checks from the settings entry.
- Existing Linux conversion and public API behavior remain covered.

Keep the state-machine tests platform-independent where practical; run Windows
adapter tests on Windows. Mock-only success does not establish native hook
correctness.

### Windows manual acceptance

Use an actual numeric keypad in Notepad and PoE. Check Num Lock on/off, left and
right Ctrl, fast repeated checks, long holds, Alt+Tab, suspend/resume, tray mode,
settings changes while held, and actual exit. Include a non-US layout with AltGr
and a different privilege level between app/game if available. Verify that plain
keypad digits remain usable while the app is open and that modifier response
does not regress. Measure callback dispatch under repeated use and confirm it
does not wait on clipboard/model/UI work inside the hook.

Specifically reproduce clear -> focus loss -> Ctrl+1, replace -> old/new chord,
`off` -> old chord, and restart -> old/new chord. Verify actual tray exit, and
check for a second process/older build if a supposedly disabled chord still
fires. Treat duplicate-instance behavior as a diagnostic first; inspect the
existing single-instance guard before proposing changes to it.

Before calling the implementation complete, run the repository gates using the
existing venv:

```powershell
.\venv\Scripts\python.exe -m ruff check .
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe -m mypy --ignore-missing-imports --follow-imports=silent poe2trade/__init__.py poe2trade/app/updater.py poe2trade/app/asset_paths.py tools/
.\venv\Scripts\python.exe -m poe2trade.db test
```

Report unavailable manual scenarios and unrelated baseline gate failures
explicitly. Do not retrain or modify model artifacts to make this gate pass.

## Delivery and acceptance

Deliver in reviewable steps: identity/regression coverage, state recovery and
dispatch, then lifecycle integration and manual verification. Keep each step
internally consistent; do not ship a half-migrated binding system.

Accept when the automated matrix and repository gates pass, Windows manual
checks confirm ordinary keypad input and reliable shortcuts, and the existing
app/settings structure remains intact. Include release notes for the explicit
keypad syntax and exact-modifier behavior. A user's original report is resolved
only after reproduction or confirmation from their environment; backend
hardening alone is not proof of its precise cause.
