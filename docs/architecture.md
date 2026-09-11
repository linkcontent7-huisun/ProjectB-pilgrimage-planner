# 아키텍처

## 왜 성지순례인가

명세는 "목적지·기간·인원·예산·테마"를 받는 범용 여행 플래너를 요구한다. 이 과제는 테마를
**가톨릭 성지순례**로 고정한다. 이유는 둘이다.

1. 명세 항목이 하나도 빠지지 않는다 — 성지는 좌표가 필요하고(지도 API), 미사 시간은 실시간으로
   바뀌며(검색 도구), 미사 시간에 맞춰 동선을 짜야 하므로(추론) 오히려 범용 여행보다 제약이 많다.
2. M1-2 → 이 과제 → Final Project가 하나의 "AI 순례 비서"로 이어진다. 여기서 만든 일정 JSON
   스키마·성지 데이터·LangGraph 골격을 Final Project가 그대로 이어받는다.

## 스택

| 층 | 선택 | 근거 |
|---|---|---|
| LLM | 코디세이 공개 API `gpt-5-mini` (OpenAI 호환, `OPENAI_BASE_URL`) | 기관 키로 정산. M1-2에서 Function Calling 작동 확인. `response_format` 미지원 → JSON은 프롬프트로 요구하고 코드블록 울타리를 벗겨 파싱 |
| 에이전트 | **LangGraph** `StateGraph` | 명세 필수. 상태(입력·조사 결과·초안·검증 오류·로그)를 명시적으로 들고 다녀야 "일정 수정 → 재계산"이 자연스럽다 |
| 백엔드 | FastAPI + SSE (`sse-starlette`) | M1-2와 동일. 진행 상태·로그를 실시간으로 밀어주는 데 WebSocket보다 단순 |
| 지도 | Naver Maps — Geocoding(좌표), Directions 5(경로·소요시간), Web Dynamic Map(프론트 렌더링) | 사용자 선택. 한국 성지 주소 해석 정확도 |
| 검색 | Tavily | 명세 예시. 무료 1,000회/월 |
| 날씨 | Open-Meteo | 키 불필요, 일별 예보 16일 |
| 프론트 | 정적 HTML/JS (`public/`) — 빌드 도구 없음 | M1-2와 동일. Vercel 정적 배포 |
| 검증 | Pydantic v2 모델 ← `specs/plan-schema.json` | 한 스키마를 두 곳(백엔드 검증·프론트 계약)에서 공유 |
| 성지 데이터 | `data/holy_sites.json` 시드 (이름·교구·주소·좌표·기본 미사시간) | 검색 결과가 비어도 최소한의 후보를 보장. 좌표는 Geocoding으로 채움 |

## LangGraph 흐름

```
[collect]  입력 정규화 → 페르소나 규칙 로드 → 성지 후보 조회(data/holy_sites.json, 지역 필터)
    │
    ▼
[research] ReAct 도구 루프 (최대 N회)
    │   도구: web_search / geocode_place / get_route / get_weather
    │   각 호출을 log 이벤트로 스트림: [Thinking] [Tool Call] [Tool Output]
    ▼
[compose]  조사 결과 + 페르소나 규칙 → 일정 JSON 초안 생성 ([Decision] 로그)
    │
    ▼
[validate] plan-schema 검증 + 논리 검증(시간 겹침·예산 초과·미사시간 불일치)
    │  실패 → 오류 목록을 붙여 [compose]로 (최대 2회)   성공 → [done]
    ▼
[done]     계획 저장(in-memory dict, plan_id 발급) → result 이벤트
```

**일정 수정**(`/revise`): 기존 계획 + 수정 요청("2일차 ○○성지 빼줘")을 상태에 실어
`[compose]`부터 재진입한다. 조사 결과는 재사용하므로 도구 호출 없이 재계산되고, 새 장소가
필요할 때만 `[research]`로 돌아간다.

## 도구 목록

| 도구 | 입력 | 출력 | 외부 API |
|---|---|---|---|
| `web_search(query)` | 검색어 | 상위 5건 제목·요약·URL | Tavily |
| `geocode_place(name, region)` | 장소명 (+지역) | lat, lng, 도로명주소 | Naver Geocoding |
| `get_route(from, to, mode)` | 두 좌표, walk/car/transit | 거리 km, 소요 분 | Naver Directions 5 (car) / 직선거리×보정(walk) |
| `get_weather(lat, lng, date)` | 좌표, 날짜 | 요약·최저/최고·강수확률 | Open-Meteo |

## API

| 메서드 | 경로 | 역할 |
|---|---|---|
| POST | `/api/plans` | 입력 받고 `plan_id` 발급 |
| GET | `/api/plans/{id}/stream` | SSE — `status`, `log`, `result`, `error` 이벤트 |
| GET | `/api/plans/{id}` | 완성된 계획 JSON |
| POST | `/api/plans/{id}/revise` | 수정 요청 → 재계산, 같은 스트림으로 진행 상황 전송 |
| GET | `/api/plans/{id}/pdf` | (보너스) PDF |

## SSE 이벤트 형식

```
event: status   data: {"stage": "research", "message": "대전 성지 미사 시간 검색 중"}
event: log      data: {"kind": "tool_call", "tool": "web_search", "args": {...}}
event: log      data: {"kind": "tool_output", "tool": "web_search", "summary": "..."}
event: log      data: {"kind": "thinking" | "decision", "message": "..."}
event: result   data: <PilgrimagePlan JSON>
event: error    data: {"message": "..."}
```

## 코디세이 API 함정 (M1-2에서 실측)

- `response_format` 400 → 사용 금지. 프롬프트로 JSON만 요구하고 ```json 울타리 제거 후 파싱
- assistant 메시지를 되돌려 보낼 때 `model_dump()` 그대로 넣으면 모르는 필드 때문에 400 →
  `role/content/tool_calls`만 골라서 보낸다
- LangChain `ChatOpenAI`가 보내는 부가 필드가 같은 문제를 일으킬 수 있음 → **첫 실험(Task 1)에서 확인**.
  안 되면 LangGraph는 상태·흐름만 맡고 LLM 호출은 M1-2의 `openai` SDK 코드를 재사용한다
