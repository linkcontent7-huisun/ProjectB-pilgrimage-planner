# Task 4: FastAPI API 및 SSE

## 엔드포인트

| 메서드 | 경로 | 요청 예시 | 응답 예시 |
|---|---|---|---|
| GET | `/api/config` | 없음 | `{"naver_map_client_id":"...","personas":[{"key":"mass_centered","label":"미사 중심 순례"}]}` |
| GET | `/api/sites?region=대전` | 쿼리 `region=대전` | 성지 후보 배열 (`name`, `lat`, `lng`, `address` 등) |
| POST | `/api/plans` | `{"region":"대전","start_date":"2026-09-20","nights":0,"party_size":2,"budget_per_person":50000,"persona":"mass_centered","preferences":"조용한 일정"}` | `202 {"plan_id":"a1b2c3d4e5f6","stream_url":"/api/plans/a1b2c3d4e5f6/stream"}` |
| GET | `/api/plans/{id}/stream` | 없음 | `text/event-stream` 진행 이벤트 |
| GET | `/api/plans/{id}` | 없음 | `{"id":"...","status":"done","request":{...},"plan":{...},"error":null}` |
| POST | `/api/plans/{id}/revise` | `{"instruction":"둘째 날 이동을 줄여 주세요"}` | `202 {"plan_id":"...","stream_url":"/api/plans/.../stream"}` |

존재하지 않는 계획은 404이며, 완료 전 수정 요청은 409이다. 생성 요청의 입력은 `PlanRequest`로 검증되어 잘못된 persona 등은 422를 반환한다. 설정 API는 공개용 Naver Map Client ID만 반환하며 secret은 절대 반환하지 않는다.

## SSE 형식

다음은 실제 전송 형식의 원문 예시다. `data`는 UTF-8 JSON 문자열이며, 연결 유지용으로 15초마다 `: ping` 주석을 보낸다.

```text
event: status
data: {"stage":"research","message":"대전 성지 조사 중"}

event: log
data: {"kind":"tool_call","tool":"web_search","args":{"query":"대전 성지"}}

event: result
data: {"plan_name":"대전 1일 순례", "days": [...]}

```

## 저장소 수명주기

`PlanStore`는 프로세스 메모리 안에서 `threading.Lock`으로 보호된다. 생성 시 12자리 UUID와 함께 `pending` 레코드가 만들어지고, 작업 시작 시 `running`, 성공 시 계획 및 조사 요약과 함께 `done`, 실패 시 오류 메시지와 함께 `error`가 된다. 이벤트는 레코드에 순서대로 보관되어 늦게 접속한 SSE 클라이언트도 이전 진행 상황을 재생받는다. 수정 성공 시 새 계획이 기존 계획을 대체하고 기존 계획은 `history` 배열에 남는다. 따라서 서버 재시작 시 저장된 계획은 사라진다.

## 스레드와 큐 설계

LangGraph 실행은 daemon `threading.Thread`에서 수행되어 HTTP 요청 스레드를 막지 않는다. 각 계획 ID에는 연결 중인 `asyncio.Queue` 집합이 있고, 에이전트 `emit` 콜백은 먼저 저장소에 이벤트를 추가한 뒤 각 구독자의 이벤트 루프에 `loop.call_soon_threadsafe(queue.put_nowait, event)`로 안전하게 전달한다. 작업 종료 시 센티널을 각 큐에 보내 스트림 제너레이터가 종료되도록 한다. 오류도 저장하고 `error` 이벤트로 방송한다.

## 테스트 결과

```text
...........................                                              [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\starlette\testclient.py:53
  C:\Users\noh hui sun\codyssey\assignments\ProjectB-pilgrimage-planner\.venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

.venv\Lib\site-packages\_pytest\cacheprovider.py:469
  C:\Users\noh hui sun\codyssey\assignments\ProjectB-pilgrimage-planner\.venv\Lib\site-packages\_pytest\cacheprovider.py:469: PytestCacheWarning: could not create cache path C:\Users\noh hui sun\codyssey\assignments\ProjectB-pilgrimage-planner\.pytest_cache\v\cache\nodeids: [WinError 5] Access is denied: 'C:\\Users\\noh hui sun\\codyssey\\assignments\\ProjectB-pilgrimage-planner\\.pytest_cache\\v\\cache'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
27 passed, 2 warnings in 10.54s
```
