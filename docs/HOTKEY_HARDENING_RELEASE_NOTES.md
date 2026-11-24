# Shortcut reliability changes

The existing Hotkeys settings now support `off` to disable an action shortcut.
A blank field continues to use its default (for example, Ctrl+1 for Overlay).
The summary shows the active shortcut or Disabled. Invalid replacements keep
the previous working shortcut and show an error; they no longer silently
restore Ctrl+1. Shortcuts pause while an action-shortcut field is being edited.

On Windows:

- Digit shortcuts target the main keyboard. To intentionally use the numeric
  keypad, enter `ctrl+num1`, `ctrl+num2`, etc. Keypad bindings use physical keys
  across Num Lock changes and do not capture dedicated navigation keys.
- Modifier sets match exactly: Ctrl+1 and Ctrl+Shift+1 are separate shortcuts.
  Left/right modifier names are supported. AltGr and multi-step action
  shortcuts are rejected with an error; choose a simple chord instead.
- Held/repeated keys are tracked separately, missed releases are reconciled,
  and item-copy injection does not turn injected events into shortcut presses.
- Reset Settings can restore defaults even when action shortcuts were swapped.

The default shortcut strings and settings layout are unchanged. Linux retains
the pynput backend. The native copy shortcut is not an action binding and does
not accept `off` as a way to disable copying.

Validation includes automated event/state tests, settings failure/rollback tests,
and a Windows hook installation/removal smoke check. Physical keypad and PoE
acceptance, non-US hardware layouts, suspend/resume, and privilege-mismatch
scenarios remain manual checks; this change does not establish the precise
cause of the original user's report.
