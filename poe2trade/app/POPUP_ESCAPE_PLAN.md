# Popup Escape dismissal

Restore Escape on presenter overlays without taking game focus. Each Tk root
owns a dismissal registry. Visible windows register their existing cancellation
handler; destroying or hiding a window removes its eligibility. Main-window
workspaces and native dialogs are not registered as popups.

The isolated presenter process uses the existing WindowsHook adapter to consume
physical Escape down/repeat/up while an overlay is eligible. The hook only
captures an identity and writes to a queue; Tk callbacks run on the Tk thread.
Dismiss after release and validate the captured registration so replacements
cannot be closed by stale input. Keep the hook for the warm process lifetime,
passing input through while idle. Ordinary dialogs use local Tk bindings.

Cover registry ordering, stale requests, held keys, idle passthrough, popup
destruction, native-dialog grabs, prediction cancellation and Craft/filter
callbacks. Run the repository gates and native-window tests. Physical PoE focus
and menu-leakage checks remain a manual acceptance step.
