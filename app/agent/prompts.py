"""Korean prompts for the research and composition phases."""

import json
from pathlib import Path

from app.agent.personas import PERSONAS
from app.agent.state import travel_dates

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "specs" / "plan-schema.json"
with _SCHEMA_PATH.open(encoding="utf-8") as _source:
    PLAN_SCHEMA = json.load(_source)


def _schema_outline(schema: dict, indent: str = "") -> str:
    lines: list[str] = []
    if schema.get("required"):
        lines.append(f"{indent}필수: {', '.join(schema['required'])}")
    for name, value in schema.get("properties", {}).items():
        if enum := value.get("enum"):
            lines.append(f"{indent}{name} enum: {', '.join(map(str, enum))}")
        if value.get("items", {}).get("properties"):
            lines.append(f"{indent}{name}[]:")
            lines.extend(_schema_outline(value["items"], indent + "  ").splitlines())
    return "\n".join(lines)


SCHEMA_OUTLINE = _schema_outline(PLAN_SCHEMA)


def _date_lines(request: dict) -> str:
    return "\n".join(f"여행 날짜: {day} ({index}일차)" for index, day in enumerate(travel_dates(request), 1))


def research_system_prompt(request: dict, persona: str, candidates: list[dict],
                           available: list[str] | None = None) -> str:
    details = "\n".join(f"- {site['name']} | {site['address']} | {site['lat']}, {site['lng']}" for site in candidates)
    available = available or ["web_search", "geocode_place", "get_route", "get_weather"]
    unavailable_search = ""
    if "web_search" not in available:
        unavailable_search = "web_search를 쓸 수 없다. 미사 시간은 조사하지 말고 일정 작성 시 '미사 시간은 방문 전 확인 필요'로 표시하라."
    return f"""당신은 가톨릭 순례 여행 조사 보조자다. 도구로 확인한 사실만 사용한다.
선택 페르소나: {PERSONAS[persona]['label']}
{PERSONAS[persona]['rules']}
후보 성지:
{details}
사용 가능한 도구: {', '.join(available)}
{_date_lines(request)}
get_weather는 위에 적힌 여행 날짜에만, 각 날짜별 성지 중심 좌표에서 정확히 한 번 호출하라.
사용할 성지의 미사 시간은 `성지명 미사 시간` 형식으로 web_search를 호출해 확인한다. 필요하면 식당·카페·숙소는 web_search 또는 geocode_place로 찾고, 연속 방문지는 get_route로 확인한다. 도구 호출은 최대 12회다.
{unavailable_search}
조사가 끝나면 JSON 없이 한국어 일반 텍스트로, 반드시 `조사 요약:`으로 시작해 결과를 정리하라."""


def compose_system_prompt(persona: str) -> str:
    return f"""당신은 한국 가톨릭 순례 일정 작성자다. {PERSONAS[persona]['label']} 규칙:
{PERSONAS[persona]['rules']}
아래 JSON 스키마의 필수 필드와 enum을 지켜라.
{SCHEMA_OUTLINE}
모든 place에는 reason을 포함하고, 응답은 JSON 객체만 출력하라."""


def compose_user_prompt(request: dict, candidates: list[dict], research_notes: str,
                        previous_plan: dict | None = None, revise_request: str | None = None,
                        validation_errors: list[str] | None = None) -> str:
    text = f"""요청: {json.dumps(request, ensure_ascii=False)}
후보 좌표(이 좌표 또는 조사에서 geocode한 좌표만 사용하고, 좌표를 지어내지 마라):
{json.dumps(candidates, ensure_ascii=False)}
조사 결과:
{research_notes}
days는 정확히 {len(travel_dates(request))}개이고, 아래의 정확한 날짜를 순서대로 써야 한다. 시간은 HH:MM 형식이다.
{_date_lines(request)}
JSON 객체만 출력하라."""
    if previous_plan and revise_request:
        text += f"\n기존 계획: {json.dumps(previous_plan, ensure_ascii=False)}\n수정 요청: {revise_request}\n영향받지 않는 내용은 유지하고, 나머지 순서·시간·이동은 다시 계산하라."
    if validation_errors:
        text += "\n검증 오류:\n- " + "\n- ".join(validation_errors) + "\n위 오류를 고쳐 다시 출력하라."
    return text


def strip_json_fences(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        first_end = value.find("\n")
        if first_end != -1:
            value = value[first_end + 1:]
        if value.rstrip().endswith("```"):
            value = value.rstrip()[:-3]
    start, end = value.find("{"), value.rfind("}")
    return value[start:end + 1].strip() if start >= 0 and end >= start else value.strip()
