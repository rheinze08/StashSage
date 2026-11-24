"""Resident, process-safe prediction worker runtime.

The main application owns UI and request ordering.  This module owns one
long-lived scoring process and communicates only with serializable mappings.
"""
from __future__ import annotations

import multiprocessing
import queue
import time
import traceback
from collections.abc import Callable, Mapping
from typing import Any

PROTOCOL_VERSION = 1
PREDICT = "predict"
WARMUP = "warmup"
CANCEL = "cancel"
SHUTDOWN = "shutdown"

# A builder may report its own stage breakdown under this key.  The worker
# lifts it out of the payload and into the event's `timings` field, so the
# profile reaches the log without becoming part of the dashboard payload the
# presenter consumes.
STAGE_TIMINGS_KEY = "_stage_timings"

# Events that end a request. Once one is handed to the caller the request is no
# longer in flight, so a later dismissal must not recycle the worker over it.
_TERMINAL_KINDS = frozenset({"result", "error", "cancelled"})


def _event(kind: str, generation: int, **values: Any) -> dict[str, Any]:
    return {"protocol_version": PROTOCOL_VERSION, "kind": kind, "generation": generation, **values}


def prediction_worker_main(command_queue, result_queue, builder: Callable[[Mapping[str, Any]], Mapping[str, Any]], *, generation: int) -> None:
    """Run one scoring request at a time, retaining imported model caches."""
    result_queue.put(_event("ready", generation))
    cancelled: set[int] = set()
    while True:
        command = command_queue.get()
        if not isinstance(command, Mapping) or command.get("protocol_version") != PROTOCOL_VERSION:
            result_queue.put(_event("error", generation, category="protocol", message="Invalid worker command."))
            continue
        kind = command.get("kind")
        request_id = command.get("request_id")
        if kind == SHUTDOWN:
            result_queue.put(_event("stopped", generation))
            return
        if kind == CANCEL:
            if isinstance(request_id, int):
                cancelled.add(request_id)
                result_queue.put(_event("cancelled", generation, request_id=request_id))
            continue
        if kind not in {PREDICT, WARMUP}:
            result_queue.put(_event("error", generation, category="protocol", message="Unknown worker command."))
            continue
        if kind == PREDICT and (not isinstance(request_id, int) or request_id in cancelled):
            if isinstance(request_id, int):
                cancelled.discard(request_id)
                result_queue.put(_event("cancelled", generation, request_id=request_id))
            continue
        started = time.perf_counter()
        try:
            payload = builder(command)
            if not isinstance(payload, Mapping):
                raise TypeError("Prediction payload must be a mapping")
            payload = dict(payload)
            timings = {"build_ms": round((time.perf_counter() - started) * 1000)}
            stages = payload.pop(STAGE_TIMINGS_KEY, None)
            if isinstance(stages, Mapping):
                timings.update({str(name): value for name, value in stages.items()})
            result_queue.put(_event(
                "warmed" if kind == WARMUP else "result", generation,
                **({} if kind == WARMUP else {"request_id": request_id, "payload": payload}),
                timings=timings,
            ))
        except Exception as exc:
            result_queue.put(_event(
                "error", generation, request_id=request_id,
                category="missing" if isinstance(exc, FileNotFoundError) else "failed",
                message=str(exc) or type(exc).__name__,
                traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            ))


class PredictionWorkerManager:
    """Non-blocking main-process owner for one resident predictor."""
    def __init__(self, builder: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        self.builder = builder
        self.context = multiprocessing.get_context("spawn")
        self.process = None
        self.command_queue = None
        self.result_queue = None
        self.generation = 0
        self.active_request_id: int | None = None

    def start(self) -> None:
        if self.process is not None and self.process.is_alive():
            return
        self.shutdown(timeout=0)
        self.generation += 1
        self.command_queue = self.context.Queue()
        self.result_queue = self.context.Queue()
        self.process = self.context.Process(
            target=prediction_worker_main,
            args=(self.command_queue, self.result_queue, self.builder),
            kwargs={"generation": self.generation},
            name="StashSagePredictionWorker",
            daemon=True,
        )
        self.process.start()

    def warmup(self) -> None:
        self.start()
        self.command_queue.put({"protocol_version": PROTOCOL_VERSION, "kind": WARMUP})

    def submit(self, request: Mapping[str, Any]) -> None:
        self.start()
        request_id = request.get("request_id")
        if not isinstance(request_id, int):
            raise ValueError("Prediction request requires an integer request_id")
        self.active_request_id = request_id
        self.command_queue.put({"protocol_version": PROTOCOL_VERSION, "kind": PREDICT, **dict(request)})

    def cancel(self, request_id: int) -> bool:
        """Abort an in-flight score instead of merely queueing a cancel.

        The scorer is intentionally single-threaded inside its worker process,
        so it cannot receive a queued CANCEL while model code is executing.
        Recycling this compute-only child is safe and releases CPU immediately.

        Returns whether the worker was recycled, which is the caller's cue to
        warm a replacement: the terminated child took its model caches with it,
        so without a re-warm the next prediction pays a full cold start. A
        request that is not the one in flight is not cancellable and returns
        False, having changed nothing.
        """
        if request_id != self.active_request_id:
            return False
        process = self.process
        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=0.15)
        for name in ("command_queue", "result_queue"):
            value = getattr(self, name)
            if value is not None:
                try:
                    value.close()
                except Exception:
                    pass
                setattr(self, name, None)
        self.process = None
        self.active_request_id = None
        return True

    def poll(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        finished = False
        if self.result_queue is not None:
            while True:
                try:
                    message = self.result_queue.get_nowait()
                except queue.Empty:
                    break
                if isinstance(message, dict) and message.get("generation") == self.generation:
                    request_id = message.get("request_id")
                    if request_id is None or request_id == self.active_request_id:
                        messages.append(message)
                        if request_id is not None and message.get("kind") in _TERMINAL_KINDS:
                            finished = True
        if finished:
            # Cleared after the drain rather than inside it, so the rest of
            # this batch is still matched against the id it was polled for.
            self.active_request_id = None
        return messages

    def restart(self, *, timeout: float = 0.35) -> None:
        """Replace the resident process with a fresh one.

        The worker keeps imported model caches and its own live-rate snapshot
        for the life of the process. After the user switches league, none of
        that describes the league now selected, so the process is replaced
        rather than asked to invalidate state it holds in several modules.

        Started eagerly so the reload happens now instead of inside the
        user's next prediction.
        """
        self.shutdown(timeout=timeout)
        self.start()

    def shutdown(self, *, timeout: float = 0.35) -> None:
        process = self.process
        if process is not None:
            if process.is_alive() and self.command_queue is not None:
                self.command_queue.put({"protocol_version": PROTOCOL_VERSION, "kind": SHUTDOWN})
                process.join(timeout)
            if process.is_alive():
                process.terminate()
                process.join(timeout)
        for name in ("command_queue", "result_queue"):
            value = getattr(self, name)
            if value is not None:
                try:
                    value.close()
                except Exception:
                    pass
                setattr(self, name, None)
        self.process = None
        self.active_request_id = None
