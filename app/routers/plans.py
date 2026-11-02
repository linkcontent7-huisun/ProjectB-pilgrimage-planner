"""Planning REST and SSE endpoints."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent.candidates import select_candidates
from app.agent.personas import PERSONAS
from app.agent.state import PlanRequest
from app.config import settings
from app.services import planner
from app.store import store

router = APIRouter(prefix="/api")


class ReviseRequest(BaseModel):
    instruction: str


@router.get("/config")
def config() -> dict:
    return {
        "naver_map_client_id": settings.NAVER_MAP_CLIENT_ID,
        "personas": [{"key": key, "label": value["label"]} for key, value in PERSONAS.items()],
    }


@router.get("/sites")
def sites(region: str = "대전") -> list[dict]:
    return select_candidates(region, "mass_centered")


@router.post("/plans", status_code=status.HTTP_202_ACCEPTED)
def create_plan(request: PlanRequest) -> dict:
    plan_id = store.create(request.model_dump(mode="json"))
    planner.start_plan_job(plan_id)
    return {"plan_id": plan_id, "stream_url": f"/api/plans/{plan_id}/stream"}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str) -> dict:
    record = store.get(plan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {key: record[key] for key in ("id", "status", "request", "plan", "error")}


@router.get("/plans/{plan_id}/stream")
async def stream_plan(plan_id: str):
    if store.get(plan_id) is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    async def events():
        queue = planner.subscribe(plan_id)
        replay = store.snapshot_events(plan_id) or []
        replayed_ids = {id(event) for event in replay}
        try:
            for event in replay:
                yield {"event": event["event"], "data": json.dumps(event["data"], ensure_ascii=False)}
            # A completed job has no future sentinel for this late subscriber.
            record = store.get(plan_id)
            if record and record["status"] in {"done", "error"}:
                return
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield {"comment": "ping"}
                    continue
                if item is planner._SENTINEL:
                    return
                # It may have been captured in the replay after subscription.
                if id(item) in replayed_ids:
                    continue
                yield {"event": item["event"], "data": json.dumps(item["data"], ensure_ascii=False)}
        finally:
            planner.unsubscribe(plan_id, queue)

    return EventSourceResponse(events(), ping=None)


@router.post("/plans/{plan_id}/revise", status_code=status.HTTP_202_ACCEPTED)
def revise_plan(plan_id: str, request: ReviseRequest) -> dict:
    record = store.get(plan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if record["status"] != "done":
        raise HTTPException(status_code=409, detail="Plan is not ready for revision")
    store.clear_events(plan_id)
    store.set_status(plan_id, "running")
    planner.start_revise_job(plan_id, request.instruction)
    return {"plan_id": plan_id, "stream_url": f"/api/plans/{plan_id}/stream"}
