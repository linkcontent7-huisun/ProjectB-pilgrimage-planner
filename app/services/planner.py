"""Background execution and fan-out of agent events to SSE subscribers."""

from __future__ import annotations

import asyncio
from threading import Lock, Thread

from app.agent.graph import PlanGenerationError, run_plan, run_revise
from app.store import store

_SENTINEL = object()
_subscriber_lock = Lock()
subscribers: dict[str, set[asyncio.Queue]] = {}
_threads: dict[str, Thread] = {}


def subscribe(plan_id: str) -> asyncio.Queue:
    """Register the current event loop as a recipient for a plan's events."""
    queue: asyncio.Queue = asyncio.Queue()
    # The callback runs in a worker thread, so preserve the owning loop explicitly.
    queue._planner_loop = asyncio.get_running_loop()  # type: ignore[attr-defined]
    with _subscriber_lock:
        subscribers.setdefault(plan_id, set()).add(queue)
    return queue


def unsubscribe(plan_id: str, queue: asyncio.Queue) -> None:
    with _subscriber_lock:
        queues = subscribers.get(plan_id)
        if queues is None:
            return
        queues.discard(queue)
        if not queues:
            subscribers.pop(plan_id, None)


def _publish(plan_id: str, item: dict | object) -> None:
    with _subscriber_lock:
        queues = list(subscribers.get(plan_id, set()))
    for queue in queues:
        loop = queue._planner_loop  # type: ignore[attr-defined]
        loop.call_soon_threadsafe(queue.put_nowait, item)


def _emit(plan_id: str, event: dict) -> None:
    store.append_event(plan_id, event)
    _publish(plan_id, event)


def _run_job(plan_id: str, revise_instruction: str | None = None) -> None:
    try:
        record = store.get(plan_id)
        if record is None:
            return
        emit = lambda event: _emit(plan_id, event)
        if revise_instruction is None:
            outcome = run_plan(record["request"], emit=emit)
        else:
            previous_plan = record["plan"]
            if previous_plan is None:
                raise RuntimeError("수정할 기존 계획이 없습니다.")
            outcome = run_revise(
                previous_plan, record["request"], revise_instruction,
                record.get("research_notes", ""), emit=emit,
            )
            # History belongs to the record, but retaining it is not part of result replacement.
            store.append_history(plan_id, previous_plan)
        store.set_result(plan_id, outcome["plan"], outcome.get("research_notes", ""))
    except PlanGenerationError as exc:
        message = str(exc)
        store.set_error(plan_id, message)
        _emit(plan_id, {"event": "error", "data": {"message": message}})
    except Exception as exc:  # Keep worker failures visible to SSE clients.
        message = str(exc) or exc.__class__.__name__
        store.set_error(plan_id, message)
        _emit(plan_id, {"event": "error", "data": {"message": message}})
    finally:
        _publish(plan_id, _SENTINEL)


def _start(plan_id: str, revise_instruction: str | None = None) -> None:
    store.set_status(plan_id, "running")
    thread = Thread(target=_run_job, args=(plan_id, revise_instruction), daemon=True)
    _threads[plan_id] = thread
    thread.start()


def start_plan_job(plan_id: str) -> None:
    _start(plan_id)


def start_revise_job(plan_id: str, revise_request: str) -> None:
    _start(plan_id, revise_request)
