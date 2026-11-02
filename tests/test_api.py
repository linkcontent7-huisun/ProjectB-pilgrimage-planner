import copy
import json
import threading

import pytest
from fastapi.testclient import TestClient

from app.agent.events import log_tool_call, result, status
from app.services import planner
from app.store import store
from main import create_app
from tests.test_plan_schema import GOOD


REQUEST = {
    "region": "대전",
    "start_date": "2026-09-20",
    "nights": 0,
    "party_size": 2,
    "budget_per_person": 50000,
    "persona": "mass_centered",
    "preferences": "조용한 일정",
}


@pytest.fixture(autouse=True)
def clean_store():
    with store._lock:
        store._records.clear()
    planner._threads.clear()
    yield


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def _fake_plan(request, emit=None):
    plan = copy.deepcopy(GOOD)
    emit(status("research", "테스트 조사 중"))
    emit(log_tool_call("web_search", {"query": request["region"]}))
    emit(result(plan))
    return {"plan": plan, "research_notes": "조사 요약: 테스트"}


def _wait(plan_id):
    planner._threads[plan_id].join(timeout=2)
    assert not planner._threads[plan_id].is_alive()


def test_config_hides_secret(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"naver_map_client_id", "personas"}
    assert all(set(persona) == {"key", "label"} for persona in body["personas"])
    assert "secret" not in response.text.lower()


def test_create_plan_validation_and_result(client, monkeypatch):
    monkeypatch.setattr(planner, "run_plan", _fake_plan)
    accepted = client.post("/api/plans", json=REQUEST)
    assert accepted.status_code == 202
    plan_id = accepted.json()["plan_id"]
    assert accepted.json()["stream_url"] == f"/api/plans/{plan_id}/stream"
    _wait(plan_id)
    saved = client.get(f"/api/plans/{plan_id}")
    assert saved.status_code == 200
    assert saved.json()["status"] == "done"
    assert saved.json()["plan"] == GOOD
    assert client.post("/api/plans", json={**REQUEST, "persona": "unknown"}).status_code == 422


def test_stream_replays_events_in_order(client, monkeypatch):
    monkeypatch.setattr(planner, "run_plan", _fake_plan)
    reply = client.post("/api/plans", json=REQUEST).json()
    _wait(reply["plan_id"])
    with client.stream("GET", reply["stream_url"]) as response:
        assert response.status_code == 200
        lines = list(response.iter_lines())
    events = [line for line in lines if line.startswith("event: ")]
    assert events[:3] == ["event: status", "event: log", "event: result"]
    for line in lines:
        if line.startswith("data: "):
            json.loads(line.removeprefix("data: "))


def test_revise_conflict_then_replaces_plan_and_keeps_history(client, monkeypatch):
    release = threading.Event()

    def slow_plan(request, emit=None):
        release.wait(timeout=2)
        return _fake_plan(request, emit)

    def fake_revise(previous, request, instruction, notes, emit=None):
        plan = copy.deepcopy(previous)
        plan["plan_name"] = f"수정: {instruction}"
        emit(status("compose", "수정 중"))
        emit(log_tool_call("compose", {"instruction": instruction}))
        emit(result(plan))
        return {"plan": plan, "research_notes": notes}

    monkeypatch.setattr(planner, "run_plan", slow_plan)
    monkeypatch.setattr(planner, "run_revise", fake_revise)
    plan_id = client.post("/api/plans", json=REQUEST).json()["plan_id"]
    assert client.post(f"/api/plans/{plan_id}/revise", json={"instruction": "더 천천히"}).status_code == 409
    release.set()
    _wait(plan_id)
    assert client.post(f"/api/plans/{plan_id}/revise", json={"instruction": "더 천천히"}).status_code == 202
    _wait(plan_id)
    record = store.get(plan_id)
    assert record["plan"]["plan_name"] == "수정: 더 천천히"
    assert record["history"] == [GOOD]


def test_unknown_plan_returns_404(client):
    assert client.get("/api/plans/missing").status_code == 404
    assert client.get("/api/plans/missing/stream").status_code == 404
    assert client.post("/api/plans/missing/revise", json={"instruction": "변경"}).status_code == 404
