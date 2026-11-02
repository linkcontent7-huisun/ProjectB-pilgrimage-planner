"""Thread-safe, in-memory storage for planning jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


class PlanStore:
    """Keep plan-job state for the lifetime of this process."""

    def __init__(self) -> None:
        self._records: dict[str, dict] = {}
        self._lock = Lock()

    def create(self, request: dict) -> str:
        plan_id = uuid4().hex[:12]
        with self._lock:
            # A collision is extremely unlikely, but do not overwrite a live record.
            while plan_id in self._records:
                plan_id = uuid4().hex[:12]
            self._records[plan_id] = {
                "id": plan_id,
                "request": request,
                "status": "pending",
                "plan": None,
                "research_notes": "",
                "error": None,
                "events": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        return plan_id

    def get(self, plan_id: str) -> dict | None:
        with self._lock:
            return self._records.get(plan_id)

    def append_event(self, plan_id: str, event: dict) -> None:
        with self._lock:
            if record := self._records.get(plan_id):
                record["events"].append(event)

    def set_result(self, plan_id: str, plan: dict, research_notes: str) -> None:
        with self._lock:
            if record := self._records.get(plan_id):
                record["plan"] = plan
                record["research_notes"] = research_notes
                record["error"] = None
                record["status"] = "done"

    def set_error(self, plan_id: str, message: str) -> None:
        with self._lock:
            if record := self._records.get(plan_id):
                record["error"] = message
                record["status"] = "error"

    def set_status(self, plan_id: str, status: str) -> None:
        if status not in {"pending", "running", "done", "error"}:
            raise ValueError(f"Unknown plan status: {status}")
        with self._lock:
            if record := self._records.get(plan_id):
                record["status"] = status

    def clear_events(self, plan_id: str) -> None:
        with self._lock:
            if record := self._records.get(plan_id):
                record["events"] = []

    def append_history(self, plan_id: str, plan: dict) -> None:
        with self._lock:
            if record := self._records.get(plan_id):
                record.setdefault("history", []).append(plan)

    def snapshot_events(self, plan_id: str) -> list[dict] | None:
        with self._lock:
            record = self._records.get(plan_id)
            return None if record is None else list(record["events"])


store = PlanStore()
