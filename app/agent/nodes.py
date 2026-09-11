"""LangGraph nodes. Tool execution is explicit for event streaming and safety."""

import json
import time
from collections.abc import Callable
from typing import Any

import openai
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.agent import llm as llm_module
from app.agent.candidates import select_candidates
from app.agent.events import log_decision, log_thinking, log_tool_call, log_tool_output, result, status
from app.agent.personas import PERSONAS
from app.agent.prompts import compose_system_prompt, compose_user_prompt, research_system_prompt, strip_json_fences
from app.agent.state import PlanRequest
from app.agent.validators import logical_errors
from app.config import settings
from app.schemas.plan import PilgrimagePlan
from app.tools import ALL_TOOLS
from app.tools import route as route_module
from app.tools import weather as weather_module


def _emit(config: RunnableConfig) -> Callable[[dict], None]:
    return config.get("configurable", {}).get("emit") or (lambda event: None)


def _text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
    return str(content or "")


def available_tools() -> list:
    """Return only tools whose required credentials are currently configured."""
    unavailable = set()
    if not settings.TAVILY_API_KEY:
        unavailable.add("web_search")
    if not (settings.NAVER_MAP_CLIENT_ID and settings.NAVER_MAP_CLIENT_SECRET):
        unavailable.add("geocode_place")
    return [tool for tool in ALL_TOOLS if tool.name not in unavailable]


def _invoke_with_retry(model: Any, messages: list, attempts: int = 3) -> Any:
    """Retry transient OpenAI provider failures with bounded exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return model.invoke(messages)
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            last_error = exc
        except openai.APIStatusError as exc:
            if exc.status_code < 500:
                raise
            last_error = exc
        if attempt < attempts - 1:
            time.sleep(2 ** (attempt + 1))
    assert last_error is not None
    raise last_error


def collect(state: dict, config: RunnableConfig) -> dict:
    emit = _emit(config)
    request = PlanRequest.model_validate(state["request"])
    candidates = select_candidates(request.region, request.persona.value)
    emit(status("collect", "요청 확인 및 후보 성지 선정 중"))
    emit(log_thinking("후보 성지: " + ", ".join(candidate["name"] for candidate in candidates)))
    emit(status("collect", f"{request.region} 후보 성지 {len(candidates)}곳 선정"))
    return {"request": request.model_dump(mode="json"), "candidates": candidates, "attempts": 0,
            "validation_errors": []}


def _research_fallback(candidates: list[dict], outputs: list[dict]) -> str:
    names = ", ".join(site["name"] for site in candidates[:6])
    tool_summary = json.dumps(outputs, ensure_ascii=False, default=str)[:500] if outputs else "도구 결과 없음"
    return f"조사 요약: (LLM 오류로 조사 생략) 후보: {names}; 도구 결과: {tool_summary}"


def research(state: dict, config: RunnableConfig) -> dict:
    emit = _emit(config)
    request = state["request"]
    emit(status("research", "성지·미사 시간·날씨 조사 중"))
    tools = available_tools()
    system = research_system_prompt(request, request["persona"], state["candidates"], [tool.name for tool in tools])
    user = "요청에 맞는 조사를 시작하라."
    if state.get("revise_request"):
        user = f"수정 요청: {state['revise_request']}\n기존 조사 사실: {state.get('research_notes', '')}\n" + user
    messages: list = [SystemMessage(content=system), HumanMessage(content=user)]
    model = llm_module.get_llm().bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}
    seen: dict[tuple[str, str], dict] = {}
    outputs: list[dict] = []
    calls_used, cap, final_text = 0, state.get("tool_call_cap", 12), ""
    try:
        while calls_used < cap:
            answer = _invoke_with_retry(model, messages)
            text = _text(answer)
            if text:
                emit(log_thinking(text))
            tool_calls = getattr(answer, "tool_calls", []) or []
            messages.append(answer)
            if not tool_calls:
                final_text = text
                break
            for call in tool_calls:
                if calls_used >= cap:
                    break
                name, args = call.get("name", ""), call.get("args", {})
                key = (name, json.dumps(args, ensure_ascii=False, sort_keys=True, default=str))
                if key in seen:
                    output = {"error": "duplicate_call", "hint": "같은 도구를 같은 인자로 다시 부르지 마라"}
                    emit(log_decision(f"중복 도구 호출 차단: {name}"))
                elif name not in tool_map:
                    emit(log_tool_call(name, args))
                    output = {"error": "unavailable_tool"}
                else:
                    emit(log_tool_call(name, args))
                    try:
                        output = tool_map[name].invoke(args)
                    except Exception as exc:
                        output = {"error": str(exc)}
                    seen[key] = output
                outputs.append({"tool": name, "output": output})
                emit(log_tool_output(name, json.dumps(output, ensure_ascii=False, default=str)[:200]))
                messages.append(ToolMessage(content=json.dumps(output, ensure_ascii=False, default=str),
                                            tool_call_id=call.get("id", name)))
                calls_used += 1
        else:
            messages.append(HumanMessage(content="도구 사용 횟수가 끝났다. 지금까지 조사 내용을 '조사 요약:'으로 정리하라."))
            answer = _invoke_with_retry(model, messages)
            final_text = _text(answer)
            if final_text:
                emit(log_thinking(final_text))
    except (openai.APIStatusError, openai.APIConnectionError, openai.APITimeoutError):
        emit(log_decision("조사 단계 LLM 오류, 후보 데이터만으로 일정을 작성한다"))
        final_text = _research_fallback(state["candidates"], outputs)
    return {"research_notes": final_text, "messages": messages}


def compose(state: dict, config: RunnableConfig) -> dict:
    emit = _emit(config)
    emit(status("compose", "일정 초안 작성 중"))
    prompt = compose_user_prompt(state["request"], state["candidates"], state.get("research_notes", ""),
                                 state.get("previous_plan"), state.get("revise_request"),
                                 state.get("validation_errors") or None)
    answer = _invoke_with_retry(llm_module.get_llm(temperature=0.2), [
        SystemMessage(content=compose_system_prompt(state["request"]["persona"])), HumanMessage(content=prompt),
    ])
    draft = strip_json_fences(_text(answer))
    try:
        emit(log_decision(f"초안 작성: {json.loads(draft).get('plan_name', '계획명 없음')}"))
    except (json.JSONDecodeError, AttributeError):
        emit(log_decision("초안 작성: JSON 형식 검증 대기"))
    return {"draft": draft}


def validate(state: dict, config: RunnableConfig) -> dict:
    emit = _emit(config)
    errors: list[str] = []
    try:
        raw = json.loads(state["draft"])
    except json.JSONDecodeError as exc:
        errors = [f"JSON 파싱 실패: {exc.msg}"]
    else:
        try:
            plan = PilgrimagePlan.model_validate(raw)
            errors = logical_errors(plan, PlanRequest.model_validate(state["request"]))
        except Exception as exc:
            if hasattr(exc, "errors"):
                errors = [f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}" for issue in exc.errors()[:10]]
            else:
                errors = [str(exc)]
        else:
            if not errors:
                return {"plan": plan.model_dump(exclude_none=True, mode="json"), "validation_errors": []}
    attempts = state.get("attempts", 0) + 1
    emit(log_decision(f"검증 실패 ({attempts}/3): " + "; ".join(errors[:3])))
    return {"validation_errors": errors[:10], "attempts": attempts}


def finalize(state: dict, config: RunnableConfig) -> dict:
    emit = _emit(config)
    emit(status("finalize", "이동 시간 계산 중"))
    plan = json.loads(json.dumps(state["plan"]))
    mode = PERSONAS[state["request"]["persona"]]["default_mode"]
    for day in plan["days"]:
        places = day["places"]
        if not day.get("weather") and places:
            coordinate = places[0]["coordinates"]
            weather = weather_module.fetch_weather(coordinate["lat"], coordinate["lng"], day["date"])
            if not weather.get("error"):
                day["weather"] = weather
        for index, place in enumerate(places):
            if index and not place.get("travel_from_previous"):
                before, here = places[index - 1]["coordinates"], place["coordinates"]
                route = route_module.fetch_route(before["lat"], before["lng"], here["lat"], here["lng"], mode)
                place["travel_from_previous"] = {key: route[key] for key in ("mode", "distance_km", "duration_min") if key in route}
    costs = [place["estimated_cost"] for day in plan["days"] for place in day["places"] if place.get("estimated_cost") is not None]
    if costs:
        plan["estimated_cost_per_person"] = sum(costs)
    plan = PilgrimagePlan.model_validate(plan).model_dump(exclude_none=True, mode="json")
    emit(result(plan))
    return {"plan": plan}
