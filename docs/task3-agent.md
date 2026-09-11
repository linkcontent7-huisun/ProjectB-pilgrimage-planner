# Task 3: LangGraph 순례 계획 에이전트

## 그래프

`collect → research(도구 루프) → compose → validate → finalize → END`

검증 실패 시에는 `validate → compose`로 되돌아가며, 세 번째 실패 뒤에는 종료한다.

## 상태와 노드

상태는 `request`, `candidates`, `messages`, `research_notes`, `draft`, `plan`,
`validation_errors`, `attempts`, `revise_request`, `previous_plan`, `tool_call_cap`을 가진다.

- `collect`: 요청을 Pydantic으로 검증하고 지역·반경 기반 성지 후보를 고른다.
- `research`: 최대 12회(수정은 6회) 도구를 직접 실행하며 호출/결과 로그를 낸다.
- `compose`: 조사 내용과 JSON 스키마를 바탕으로 초안을 만든다. 코드 펜스는 제거한다.
- `validate`: Pydantic 스키마와 일정 논리를 검사하고, 오류를 다음 초안 프롬프트에 전달한다.
- `finalize`: 누락된 같은 날 이동 경로를 계산하고 비용을 다시 합산한 뒤 결과 이벤트를 보낸다.

## 페르소나

- `mass_centered`: 매일 `mass_time`이 있는 장소를 넣고 해당 시간 중심으로 편성한다.
- `walking`: 도보권으로 묶고 카페/휴식을 넣으며 하루 도보 이동을 12km 이하로 제한한다.
- `frugal`: 대중교통과 저렴한 식사를 우선하며 예산과 절약 사유를 명시한다.

## 검증과 재시도

일수는 숙박 수+1, 날짜는 연속, 방문 순서와 시간은 오름차순이어야 한다. 미사 중심 일정의
매일 미사 시간, 도보 거리, 그리고 1인 비용(예산의 120% 초과 금지)도 검사한다. 실패 오류는
최대 3번째 초안까지 모델에 되돌려 준다.

## 수정 흐름

`run_revise`는 기존 계획과 조사 요약, 수정 요청을 상태에 넣어 같은 그래프를 실행한다. 도구 호출
한도는 6회이며, 프롬프트는 영향 없는 기존 내용을 유지하도록 지시한다.

## 이벤트

`status(stage, message)`, `log(thinking)`, `log(tool_call)`, `log(tool_output)`,
`log(decision)`, `result(plan)`, `error(message)`를 콜백에 전달한다. SSE 전달 계층은 이 dict를
그대로 사용할 수 있다.

## 테스트

구현 후 실행한 전체 테스트 출력:

```text
...............                                                          [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\_pytest\cacheprovider.py:469
  PytestCacheWarning: could not create cache path .pytest_cache\v\cache\nodeids:
  [WinError 5] 액세스가 거부되었습니다.

15 passed, 1 warning in 0.62s
```

## Task 3b 보강

- API 키가 없는 `web_search`와 `geocode_place`는 조사 단계의 도구 바인딩에서 제외한다. 프롬프트에는 실제 사용 가능 도구와 정확한 여행 날짜를 표시하며, `web_search`가 없으면 미사 시간은 방문 전 확인하도록 명시한다.
- 도구 이름과 정렬된 인자를 기준으로 중복 호출을 차단한다. 중복은 실행하지 않고 모델에 오류 결과를 돌려주며, 결정 로그로 남긴다.
- `travel_dates`를 프롬프트와 논리 검증에서 공용으로 사용해 `start_date`부터 `nights + 1`일의 연속 날짜를 일관되게 처리한다. 날씨 도구는 이 날짜에만 호출하도록 지시한다.
- LLM은 60초 타임아웃과 3회 재시도를 사용한다. 5xx, 연결, 타임아웃 오류는 2초·4초 간격으로 재시도하고, 조사 단계가 끝내 실패하면 후보와 수집된 도구 결과로 조사 요약을 만들어 일정 작성을 계속한다.
- 후보 선택 뒤 지역·후보 수 상태 이벤트를 추가했다. 최종화 단계에서는 비어 있는 일자별 날씨를 첫 방문지 좌표로 보완한다.
- 새 오프라인 테스트는 후보 선택, 날짜 계산, 도구 가용성, 논리 검증, JSON 펜스 제거, 중복 도구 호출을 포함한 전체 그래프, 일시적 502 재시도를 검증한다. 모든 외부 도구와 LLM은 가짜 응답으로 대체한다.

```text
22 passed, 1 warning in 3.88s
```
