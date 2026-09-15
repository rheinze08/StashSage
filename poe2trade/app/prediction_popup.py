"""DPI-aware prediction presentation process.

The main StashSage window deliberately runs without CustomTkinter's automatic
per-monitor DPI watcher so moving it between mixed-DPI monitors remains smooth.
This module runs in a separate process, where the prediction overlay can enable
that watcher without affecting the main window.
"""

from __future__ import annotations

import logging
import multiprocessing
import queue
import threading
import time
from typing import Any, Mapping

from poe2trade.utils.craft_display import craft_delta_text

# How often the presenter confirms its parent app is still alive. A parent that
# was force-exited (or killed from Task Manager) never sends "close", and this
# non-daemon child would otherwise live on, holding the install dir's files.
_PARENT_CHECK_SECONDS = 1.0


def _parent_process_exited() -> bool:
    """True when this process was spawned by a parent that is no longer running."""
    try:
        parent = multiprocessing.parent_process()
    except Exception:
        return False
    if parent is None:
        return False
    try:
        return not parent.is_alive()
    except Exception:
        return False


def _cancel_pending_callbacks(root) -> None:
    """Cancel every callback owned by a short-lived popup Tk interpreter.

    CustomTkinter schedules DPI, scroll-frame, and progress-bar housekeeping
    directly on the root.  Unlike normal application shutdown, this helper
    process destroys its root while those callbacks are still pending, so they
    must be cancelled before the interpreter goes away.
    """
    try:
        callback_ids = root.tk.call("after", "info")
    except Exception:
        return
    for callback_id in callback_ids:
        try:
            root.after_cancel(callback_id)
        except Exception:
            pass


def _shutdown_popup(root, gui_tk=None, *, destroy_overlay: bool = False) -> None:
    """End a popup event loop without leaving Tcl callbacks behind."""
    if destroy_overlay and gui_tk is not None:
        try:
            gui_tk._destroy_overlay(invalidate_request=False)
        except Exception:
            pass
    _cancel_pending_callbacks(root)
    try:
        root.quit()
    except Exception:
        pass


def _destroy_popup_root(root) -> None:
    """Destroy only after the event loop and its scheduled callbacks stopped."""
    _cancel_pending_callbacks(root)
    try:
        root.destroy()
    except Exception:
        pass


def run_prediction_popup(
    command_queue,
    event_queue,
    request_id: int = 0,
    monitor_rect=None,
    prewarm: bool = False,
    shutdown_event=None,
) -> None:
    """Show a loader immediately, then render the payload received by queue.

    The queue protocol intentionally stays tiny: ``("result", payload)``
    replaces the loader, and ``("close", None)`` exits.  Model objects and
    Tk objects never cross this boundary.
    """
    import customtkinter as ctk
    from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

    # Import only after entering the child process. gui_tk disables automatic
    # scaling for the main application, so restore it *before* CTk creates its
    # first root in this process. CTk then sets this process DPI-aware normally.
    ScalingTracker.deactivate_automatic_dpi_awareness = False
    ScalingTracker.deactivate_automatic_dpi_awareness = False
    root = ctk.CTk()
    root.withdraw()  # the visible UI is the frameless prediction overlay only
    from poe2trade.app.prediction_presenter import CraftPresenter, FilterPresenter, PredictionPresenter
    presenter = None
    craft = None
    filter_ui = None
    delivered_result = False

    def emit_lifecycle(stage: str, **details) -> None:
        """Forward child-process UI lifecycle to the parent's rotating log."""
        try:
            event_queue.put(("presenter_lifecycle", {
                "stage": stage,
                "request_id": request_id,
                **details,
            }))
        except Exception:
            pass

    def close_prediction_presenter(request: int) -> None:
        """Cancel the request while keeping the warm presenter process alive."""
        nonlocal presenter
        # PredictionPresenter._close() has already destroyed its windows. Drop
        # the stale object instead of quitting the child process; a hotkey
        # pressed immediately afterward can then safely issue the next show
        # command without racing process teardown.
        presenter = None
        emit_lifecycle("prediction_closed", request=request)
        try:
            event_queue.put(("presenter_closed", request))
        except Exception:
            pass

    parent_check_at = time.monotonic() + _PARENT_CHECK_SECONDS

    def poll_commands() -> None:
        nonlocal delivered_result, presenter, craft, filter_ui, parent_check_at
        # Full application exit uses this event instead of relying only on a
        # Queue command.  It is visible to the child even while the parent is
        # itself unwinding, so the Tk interpreter always gets a chance to
        # leave mainloop cleanly before any fallback termination.
        parent_gone = False
        now = time.monotonic()
        if now >= parent_check_at:
            parent_check_at = now + _PARENT_CHECK_SECONDS
            parent_gone = _parent_process_exited()
            if parent_gone:
                logging.warning("Prediction presenter parent exited; shutting down")
        if parent_gone or (shutdown_event is not None and shutdown_event.is_set()):
            try:
                event_queue.put(("shutdown_started", request_id))
            except Exception:
                pass
            if presenter is not None:
                # App shutdown does not need the normal presenter_closed
                # callback. Avoid producing a second, competing close command
                # while we are already leaving this child process.
                presenter.hide()
                presenter = None
            if craft is not None:
                craft.host.hide()
                craft = None
            if filter_ui is not None:
                filter_ui.host.hide()
                filter_ui = None
            _shutdown_popup(root)
            return
        try:
            while True:
                command, payload = command_queue.get_nowait()
                if command == "close":
                    if presenter is not None:
                        presenter.hide()
                        presenter = None
                    if craft is not None:
                        craft.host.hide()
                        craft = None
                    if filter_ui is not None:
                        filter_ui.host.hide()
                        filter_ui = None
                    _shutdown_popup(root)
                    return
                if command == "hide":
                    emit_lifecycle("hide_requested")
                    if presenter is not None:
                        presenter.hide()
                    presenter = None
                    if craft is not None:
                        craft.host.hide()
                    craft = None
                    if filter_ui is not None:
                        filter_ui.host.hide()
                    filter_ui = None
                    delivered_result = False
                    continue
                if command == "filtered_show" and isinstance(payload, Mapping):
                    emit_lifecycle("ctrl2_filter_shown")
                    if presenter is not None:
                        presenter.hide()
                        presenter = None
                    if craft is not None:
                        craft.host.hide()
                        craft = None
                    filter_ui = FilterPresenter(root, payload, event_queue)
                    filter_ui.show()
                    continue
                if command == "craft_show" and isinstance(payload, Mapping):
                    emit_lifecycle("ctrl4_craft_shown")
                    if presenter is not None:
                        presenter.hide()
                        presenter = None
                    if filter_ui is not None:
                        filter_ui.host.hide()
                        filter_ui = None
                    if craft is not None:
                        craft.host.hide()
                        craft = None
                    craft = CraftPresenter(
                        root, payload.get("monitor_rect"), event_queue,
                        # Backdrop dismissal should follow the same warm-hide
                        # route as prediction and Ctrl+2, not tear down the
                        # presenter process from inside its own Tk callback.
                        lambda session_id=int(payload.get("session_id", 0)): event_queue.put(
                            ("craft_cancel", {"session_id": session_id})
                        ),
                        session_id=int(payload.get("session_id", 0)),
                    )
                    craft.show_confirm()
                    continue
                if (command == "craft_progress" and craft is not None and isinstance(payload, Mapping)
                        and int(payload.get("session_id", -1)) == craft.session_id):
                    craft.show_progress(payload.get("done"), payload.get("total"))
                    continue
                if (command == "craft_result" and craft is not None and isinstance(payload, Mapping)
                        and int(payload.get("session_id", -1)) == craft.session_id):
                    craft.show_result(payload)
                    continue
                if (command == "craft_error" and craft is not None and isinstance(payload, Mapping)
                        and int(payload.get("session_id", -1)) == craft.session_id):
                    craft.show_error(str(payload.get("message") or "CraftOracle failed."))
                    continue
                if command == "show" and isinstance(payload, Mapping):
                    emit_lifecycle("prediction_loading_shown", request=payload.get("request_id"))
                    if presenter is not None:
                        presenter.hide()
                    if craft is not None:
                        craft.host.hide()
                        craft = None
                    if filter_ui is not None:
                        filter_ui.host.hide()
                        filter_ui = None
                    presenter = PredictionPresenter(
                        root,
                        int(payload.get("request_id", 0)),
                        lambda request=int(payload.get("request_id", 0)): close_prediction_presenter(request),
                        payload.get("monitor_rect"),
                    )
                    logging.info("Prediction presenter loading shown (request=%s)", payload.get("request_id"))
                    presenter.show_loading()
                    delivered_result = False
                    continue
                if command == "result" and not delivered_result and isinstance(payload, Mapping):
                    if presenter is not None:
                        delivered_result = True
                        emit_lifecycle("prediction_payload_received")
                        logging.info("Prediction presenter received complete payload")
                        presenter.present(payload)
        except queue.Empty:
            pass
        except Exception:
            logging.exception("Prediction popup command failed")
            if presenter is not None:
                presenter._close()
                presenter = None
            if craft is not None:
                craft.host._close()
                craft = None
            if filter_ui is not None:
                filter_ui.host._close()
                filter_ui = None
            # Keep the warm command loop alive after a recoverable rendering
            # error; otherwise the loading window can remain visible forever.
            root.after(30, poll_commands)
            return

        # Escape/click-out calls gui_tk._destroy_overlay(). Once that has
        # removed the only visible window, end this helper process too.
        if presenter is not None and presenter.closed:
            _shutdown_popup(root)
            return
        root.after(30, poll_commands)

    try:
        event_queue.put(("prewarmed" if prewarm else "ready", request_id))
    except Exception:
        pass
    # The process is prewarmed specifically for hotkey latency. Poll at the
    # next practical Tk turn so the opaque loading panel follows the hotkey
    # instead of waiting for the normal 10 ms heartbeat.
    root.after(1, poll_commands)
    try:
        root.mainloop()
    finally:
        try:
            if presenter is not None:
                presenter._close()
            if craft is not None:
                craft.host._close()
        except Exception:
            pass
        _destroy_popup_root(root)
        # The parent waits for this acknowledgement before it closes its end
        # of either queue or considers force-terminating us.  It must be sent
        # after Tk is gone: otherwise a successful queue message can still
        # race with CustomTkinter callbacks during interpreter teardown.
        try:
            event_queue.put(("stopped", request_id))
        except Exception:
            pass
        try:
            command_queue.close()
        except Exception:
            pass
        try:
            event_queue.close()
        except Exception:
            pass
        try:
            # This process is the producer for event_queue.  Finish its
            # feeder thread explicitly instead of leaving it to Python 3.13
            # interpreter finalization, which is unsafe alongside Tk/Pillow.
            event_queue.join_thread()
        except Exception:
            pass


def _popup_root():
    """Create a hidden DPI-aware CTk host and attach it to gui_tk globals."""
    import customtkinter as ctk
    from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

    ScalingTracker.deactivate_automatic_dpi_awareness = False
    from poe2trade.app import gui_tk

    ScalingTracker.deactivate_automatic_dpi_awareness = False
    root = ctk.CTk()
    root.withdraw()
    gui_tk.root = root
    gui_tk.state.root = root
    return root, gui_tk, ctk


def run_filtered_filter_popup(context: dict[str, Any], command_queue, event_queue) -> None:
    """Render Ctrl+2's modifier picker in the DPI-aware presenter process."""
    root, gui_tk, _ctk = _popup_root()
    submitted = False
    original_start = gui_tk._start_filtered_overlay_with_filters
    original_dialog = gui_tk._create_overlay_dialog

    def submit_filters(_context, filters) -> None:
        nonlocal submitted
        submitted = True
        event_queue.put(("apply_filters", filters))
        _shutdown_popup(root)

    def create_dialog(on_cancel):
        backdrop, popup = original_dialog(on_cancel)
        popup.bind("<Destroy>", lambda _event: root.after(50, _close_if_cancelled), add="+")
        return backdrop, popup

    def _close_if_cancelled() -> None:
        if not submitted and root.winfo_exists():
            try:
                event_queue.put(("cancel", None))
            except Exception:
                pass
            _shutdown_popup(root)

    gui_tk._start_filtered_overlay_with_filters = submit_filters
    gui_tk._create_overlay_dialog = create_dialog

    def poll_close() -> None:
        try:
            command, _payload = command_queue.get_nowait()
            if command == "close":
                _shutdown_popup(root)
                return
        except queue.Empty:
            pass
        except Exception:
            _shutdown_popup(root)
            return
        if root.winfo_exists():
            root.after(30, poll_close)

    try:
        gui_tk._show_filtered_filter_popup(context)
        root.after(30, poll_close)
        root.mainloop()
    except Exception:
        logging.exception("Could not show filtered popup")
        try:
            event_queue.put(("error", "Could not open filtered modifier picker."))
        except Exception:
            pass
    finally:
        gui_tk._start_filtered_overlay_with_filters = original_start
        gui_tk._create_overlay_dialog = original_dialog
        _destroy_popup_root(root)


def run_craft_potential_popup(text: str, command_queue) -> None:
    """Run Ctrl+3's confirmation, progress, and result UI out-of-process."""
    root, gui_tk, ctk = _popup_root()
    from poe2trade.utils import craft_potential

    closed = False

    def close() -> None:
        nonlocal closed
        if closed:
            return
        closed = True
        try:
            gui_tk._destroy_overlay(invalidate_request=False)
        except Exception:
            pass
        _shutdown_popup(root)

    backdrop, popup = gui_tk._create_overlay_dialog(on_cancel=close)
    frame = ctk.CTkFrame(popup)
    frame.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(frame, text="CraftOracle", font=("Segoe UI", 16, "bold")).pack(anchor="w")
    ctk.CTkLabel(
        frame,
        text="Analyze this item's crafting potential?",
        wraplength=440, justify="left",
    ).pack(anchor="w", pady=12)
    buttons = ctk.CTkFrame(frame, fg_color="transparent")
    buttons.pack(fill="x")

    def start() -> None:
        try:
            popup.destroy()
            backdrop.destroy()
        except Exception:
            pass
        progress_backdrop, progress = gui_tk._create_overlay_dialog(on_cancel=close)
        progress_frame = ctk.CTkFrame(progress)
        progress_frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(progress_frame, text="Preparing CraftOracle analysis…", font=("Segoe UI", 16, "bold")).pack(pady=(0, 8))
        status = ctk.CTkLabel(progress_frame, text="Please wait. This may take a while.")
        status.pack()
        gui_tk._center_overlay_dialog(progress)

        def report(done: int, total: int) -> None:
            root.after(0, lambda: status.configure(text=f"Evaluating modifier {done} of {total}…"))

        def work() -> None:
            try:
                result = craft_potential.analyze(text, progress=report)
                root.after(0, lambda: show_result(progress_backdrop, progress, result))
            except craft_potential.CraftPotentialError as exc:
                # ``exc`` is unbound once the except block exits, so the message
                # must be captured now rather than read inside the callback.
                message = str(exc)
                root.after(0, lambda: show_error(progress_backdrop, progress, message))
            except Exception as exc:
                logging.exception("Craft Potential failed")
                message = f"Analysis failed:\n{exc}"
                root.after(0, lambda: show_error(progress_backdrop, progress, message))

        threading.Thread(target=work, daemon=True).start()

    def show_error(progress_backdrop, progress, message: str) -> None:
        try:
            progress.destroy()
            progress_backdrop.destroy()
        except Exception:
            pass
        error_backdrop, error = gui_tk._create_overlay_dialog(on_cancel=close)
        content = ctk.CTkFrame(error)
        content.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(content, text=message, wraplength=500, justify="left").pack(pady=(0, 12))
        ctk.CTkButton(content, text="Close", command=close).pack()
        gui_tk._center_overlay_dialog(error)

    def show_result(progress_backdrop, progress, result) -> None:
        try:
            progress.destroy()
            progress_backdrop.destroy()
        except Exception:
            pass
        result_backdrop, result_popup = gui_tk._create_overlay_dialog(on_cancel=close)
        content = ctk.CTkFrame(result_popup)
        content.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(content, text=result.item_name, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            content,
            text=(f"Baseline prediction: {gui_tk._triple(result.baseline_prediction)} | "
                  f"{result.explicit_count} explicit modifier(s) | {len(result.rows)} simulations"),
        ).pack(anchor="w", pady=(2, 10))
        table = ctk.CTkScrollableFrame(content, width=760, height=460)
        table.pack(fill="both", expand=True)
        for rank, row in enumerate(result.rows, start=1):
            colour = "#4CC2A0" if row.delta > 0 else ("#D26A6A" if row.delta < 0 else "#C8D2DC")
            text_line = (
                f"{rank}. {gui_tk._craft_roll_label(row)}    "
                f"{gui_tk._triple(row.prediction)}    "
                f"{craft_delta_text(row.delta, row.delta_percent)}"
            )
            ctk.CTkLabel(table, text=text_line, anchor="w", text_color=colour).pack(fill="x", pady=2)
        ctk.CTkButton(content, text="Close", command=close).pack(pady=(10, 0))
        gui_tk._center_overlay_dialog(result_popup)

    ctk.CTkButton(buttons, text="Start", command=start).pack(side="left", expand=True, fill="x", padx=(0, 6))
    ctk.CTkButton(buttons, text="Cancel", command=close).pack(side="left", expand=True, fill="x")
    gui_tk._center_overlay_dialog(popup)

    def poll_close() -> None:
        try:
            command, _payload = command_queue.get_nowait()
            if command == "close":
                close()
                return
        except queue.Empty:
            pass
        except Exception:
            close()
            return
        if root.winfo_exists():
            root.after(30, poll_close)

    root.after(30, poll_close)
    try:
        root.mainloop()
    finally:
        _destroy_popup_root(root)
