import copy
import json

import httpx
import openai
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agent import llm as llm_module
from app.agent.candidates import select_candidates
from app.agent.graph import run_plan
from app.agent.nodes import _invoke_with_retry, available_tools
from app.agent.prompts import strip_json_fences
from app.agent.state import PlanRequest, travel_dates
from app.agent.validators import logical_errors
from app.config import settings
from app.schemas.plan import PilgrimagePlan


class ScriptedChat(BaseChatModel):
    responses: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        response = self.responses.pop(0)
        return ChatResult(generations=[ChatGeneration(message=response)])


def _request(**changes):
    value = {"region": "대전", "start_date": "2026-09-20", "nights": 1, "party_size": 2,
             "budget_per_person": 50000, "persona": "mass_centered"}
    value.update(changes)
    return value


def _plan():
    return {
        "plan_name": "대전 순례", "region": "대전", "persona": "mass_centered", "party_size": 2,
        "budget_per_person": 50000, "estimated_cost_per_person": 10000,
        "days": [
            {"day": 1, "date": "2026-09-20", "places": [{"order": 1, "name": "대흥동 주교좌성당",
                "type": "mass", "start_time": "10:00", "end_time": "11:00",
                "coordinates": {"lat": 36.3258, "lng": 127.4243}, "description": "미사",
                "mass_time": "10:00", "estimated_cost": 0, "reason": "미사 중심"}]},
            {"day": 2, "date": "2026-09-21", "places": [{"order": 1, "name": "대흥동 주교좌성당",
                "type": "holy_site", "start_time": "10:00", "end_time": "11:00",
                "coordinates": {"lat": 36.3258, "lng": 127.4243}, "description": "순례",
                "mass_time": "10:00", "estimated_cost": 10000, "reason": "성지 방문"}]},
        ],
    }


def test_candidates_prioritize_region_and_keep_coordinates_numeric():
    dangjin = select_candidates("당진", "mass_centered")
    assert dangjin and dangjin[0]["city"] == "당진"
    daejeon = select_candidates("대전", "walking")
    assert any(site["name"] == "대흥동 주교좌성당" for site in daejeon)
    assert all(isinstance(site["lat"], float) and isinstance(site["lng"], float) for site in dangjin + daejeon)


def test_travel_dates():
    assert travel_dates({"region": "대전", "start_date": "2026-09-20", "nights": 2,
                         "party_size": 1, "budget_per_person": 0, "persona": "walking"}) == [
        "2026-09-20", "2026-09-21", "2026-09-22"]


def test_available_tools_respects_credentials(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_ID", "id")
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_SECRET", "secret")
    assert "web_search" not in [tool.name for tool in available_tools()]
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "key")
    assert "web_search" in [tool.name for tool in available_tools()]


def test_logical_validators_cover_business_rules():
    request = PlanRequest.model_validate(_request())
    valid = PilgrimagePlan.model_validate(_plan())
    assert logical_errors(valid, request) == []

    wrong_count = _plan(); wrong_count["days"].pop()
    assert any("일수" in error for error in logical_errors(PilgrimagePlan.model_validate(wrong_count), request))
    bad_date = _plan(); bad_date["days"][1]["date"] = "2026-09-23"
    assert any("날짜" in error for error in logical_errors(PilgrimagePlan.model_validate(bad_date), request))
    overlap = _plan(); overlap["days"][0]["places"].append({"order": 2, "name": "식당", "type": "restaurant",
        "start_time": "10:30", "end_time": "11:30", "coordinates": {"lat": 36.326, "lng": 127.425},
        "description": "식사", "reason": "휴식"})
    assert any("겹" in error for error in logical_errors(PilgrimagePlan.model_validate(overlap), request))
    missing_mass = _plan()
    for day in missing_mass["days"]:
        day["places"][0]["mass_time"] = None
    assert any("미사" in error for error in logical_errors(PilgrimagePlan.model_validate(missing_mass), request))
    costly = _plan(); costly["estimated_cost_per_person"] = 60001
    assert any("예산 초과" in error for error in logical_errors(PilgrimagePlan.model_validate(costly), request))


def test_strip_json_fences():
    assert strip_json_fences("```json\n{\"a\": 1}\n```") == '{"a": 1}'
    assert strip_json_fences("```\n{\"a\": 1}\n```") == '{"a": 1}'
    assert strip_json_fences('{"a": 1}') == '{"a": 1}'


def test_full_graph_blocks_duplicate_tools_and_fills_weather(monkeypatch):
    call = {"name": "get_weather", "args": {"lat": 36.3258, "lng": 127.4243, "date": "2026-09-20"}, "id": "weather-1"}
    model = ScriptedChat(responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="", tool_calls=[call]),
                                   AIMessage(content="조사 요약: 날씨 확인"), AIMessage(content="{}"),
                                   AIMessage(content=json.dumps(_plan(), ensure_ascii=False))])
    monkeypatch.setattr(llm_module, "get_llm", lambda temperature=0.3: model)
    monkeypatch.setattr("app.tools.weather.fetch_weather", lambda lat, lng, date: {
        "summary": "맑음", "temp_min": 10.0, "temp_max": 20.0, "precipitation_probability": 0.0})
    monkeypatch.setattr("app.tools.route.fetch_route", lambda *args, **kwargs: {"mode": "car", "distance_km": 1.0, "duration_min": 3})
    monkeypatch.setattr("app.tools.geocode.fetch_geocode", lambda *args, **kwargs: {"lat": 36.3, "lng": 127.4})
    events = []
    generated = run_plan(_request(), emit=events.append)
    assert PilgrimagePlan.model_validate(generated["plan"])
    assert {event["data"]["stage"] for event in events if event["event"] == "status"} >= {"collect", "research", "compose", "finalize"}
    assert sum(event["data"].get("kind") == "tool_call" and event["data"].get("tool") == "get_weather" for event in events if event["event"] == "log") == 1
    decisions = [event["data"].get("message", "") for event in events if event["event"] == "log" and event["data"].get("kind") == "decision"]
    assert any("중복 도구 호출 차단" in message for message in decisions)
    assert any("검증 실패" in message for message in decisions)
    assert sum(event["event"] == "result" for event in events) == 1
    assert generated["plan"]["days"][0]["weather"]["summary"] == "맑음"


def test_invoke_with_retry_on_transient_server_error(monkeypatch):
    message = AIMessage(content="ok")

    class RetryModel:
        calls = 0

        def invoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                response = httpx.Response(502, request=httpx.Request("POST", "http://x"))
                raise openai.InternalServerError(message="provider error", response=response, body=None)
            return message

    monkeypatch.setattr("app.agent.nodes.time.sleep", lambda seconds: None)
    assert _invoke_with_retry(RetryModel(), []) is message
