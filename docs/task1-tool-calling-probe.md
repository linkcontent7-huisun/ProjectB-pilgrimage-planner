# Task 1 — LangGraph 도구 호출 실험 (실험 게이트)

## 목적

LangChain `ChatOpenAI` + LangGraph `ToolNode` 조합이 코디세이 공개 API(`https://copa.codyssey.kr/v1`, `gpt-5-mini`)에서
**도구 호출(Function Calling)** 과 **토큰 스트리밍**이 되는지 확인한다.
결과에 따라 LLM 호출 층을 `ChatOpenAI`로 갈지, M1-2의 raw `openai` SDK 코드를 재사용할지 결정한다.

M1-2에서 확인된 함정: `response_format` 400, assistant 메시지 되돌릴 때 모르는 필드 400.
LangChain이 보내는 부가 필드가 같은 문제를 일으키는지가 핵심 관심사였다.

## 환경

- Python 3.13.14 (venv), Windows 11
- langgraph 1.2.11 · langchain-core 1.6.2 · langchain-openai 1.6.2 · openai 3.13.0 · pydantic 2.13.5
- 전체 목록: [environment.md](environment.md)

## 실험 1 — 도구 호출 (`scripts/probe_tool_calling.py`)

그래프: `llm` 노드(ChatOpenAI.bind_tools) → 조건 분기 → `tools` 노드(ToolNode) → `llm` → END.
더미 도구 `get_weather(city)` 하나를 묶고 "대전의 내일 날씨를 알려줘"를 넣었다.

```
$ PYTHONUTF8=1 .venv/Scripts/python scripts/probe_tool_calling.py
model=gpt-5-mini base_url=https://copa.codyssey.kr/v1
[system] '너는 여행 도우미다. 날씨는 반드시 get_weather 도구로 확인한다.'
[human] '대전의 내일 날씨를 알려줘'
[ai] ''
    tool_calls=[{'name': 'get_weather', 'args': {'city': '대전'}, 'id': 'call_ZxMdvHbxhI4JuBWKFMgn8gPH', 'type': 'tool_call'}]
[tool] '대전의 내일 날씨: 맑음, 최저 18도 / 최고 27도, 강수확률 10%'
[ai] '대전의 내일 날씨는 맑음입니다.\n- 최저 기온: 18°C\n- 최고 기온: 27°C\n- 강수 확률: 10%\n\n외출 계획이 있으시면 가벼운 겉옷(얇은 자켓이나 가디건)을 준비하시는 걸 권합니다. 추가로 원하시면 시간대별 예상, 자외선 지수, 미세먼지 정보를 더 알려드릴게요.'
```

**결과: 성공.** 한 번에 통과했다.
- LLM이 `get_weather(city="대전")`을 호출 → ToolNode가 실행 → 도구 결과를 받은 LLM이 최종 답변.
- 두 번째 LLM 호출에는 tool_calls가 붙은 assistant 메시지와 tool 메시지가 그대로 되돌아갔는데 400이 나지 않았다.
  → LangChain이 메시지를 OpenAI 규격으로 정리해서 보내므로 M1-2의 "모르는 필드 400" 문제가 재현되지 않는다.
- `model_kwargs`·`disabled_params` 조정, raw SDK 대체 스크립트 모두 **불필요**했다.

첫 실행에서 `UnicodeEncodeError: 'cp949' codec can't encode character '\u2014'`가 났으나 이는 API가 아니라
Windows 콘솔 인코딩 문제다. `PYTHONUTF8=1`로 해결.

## 실험 2 — 토큰 스트리밍 (`scripts/probe_streaming.py`)

SSE로 진행 상황을 밀어주려면 `ChatOpenAI.stream()`이 되어야 한다.

```
$ PYTHONUTF8=1 .venv/Scripts/python scripts/probe_streaming.py
어떤 종류의 성지를 원하시나요? (예: 천주교 성지, 불교 사찰, 개신교 관련지 등) 원하시는 종류 알려주시면 대전 내에서 한 줄씩 두 곳 소개해 드릴게요.
--- chunks=57
```

**결과: 성공.** 57개 청크로 나뉘어 도착했다.
(답변 내용이 "어떤 종류의 성지?"라고 되물은 것은 시스템 프롬프트를 안 준 탓이며 실험 목적과 무관하다.)

## 스키마 테스트 (`tests/test_plan_schema.py`)

`specs/plan-schema.json` ↔ `app/schemas/plan.py`(Pydantic v2) 동치 검사.

```
$ .venv/Scripts/python -m pytest -q
......                                                                   [100%]
6 passed in 0.24s
```

- 정상 샘플: jsonschema·Pydantic 둘 다 통과, 모델 → JSON 왕복 후에도 통과
- 불량 샘플 4종(필수 필드 누락 / 위도 범위 밖 / 시간 형식 오류 / 정의 안 된 필드): 둘 다 거부
- 필수 필드·enum 목록이 두 스키마에서 일치

## 결정

**`ChatOpenAI`를 그대로 쓴다.** raw `openai` SDK 대체 경로는 만들지 않는다.
도구 호출·멀티턴 되돌림·스트리밍이 모두 코디세이 API에서 문제없이 동작했고, LangGraph의 `ToolNode`·
`add_messages`를 그대로 쓸 수 있어 에이전트 코드가 짧아진다. 남은 함정은 `response_format` 하나이며
이는 M1-2와 같이 프롬프트로 JSON을 요구하고 코드블록 울타리를 벗겨 `PilgrimagePlan.model_validate()`로
검증하는 방식으로 우회한다.

## 이 단계에서 만든 파일

| 파일 | 역할 |
|---|---|
| `requirements.txt` | 의존성 |
| `app/config.py` | `.env` 읽는 Settings |
| `app/schemas/plan.py` | 일정 Pydantic 모델 |
| `tests/test_plan_schema.py` | 스키마 동치 테스트 |
| `scripts/probe_tool_calling.py` | 도구 호출 실험 |
| `scripts/probe_streaming.py` | 스트리밍 실험 |
| `docs/environment.md` | 환경 증빙 |
