Task 3b 보강을 완료했습니다.

- 도구 가용성 필터, 중복 도구 호출 차단, 명시적 여행 날짜, LLM 재시도/조사 실패 폴백을 추가했습니다.
- 후보 선택 상태 이벤트와 finalize 날씨 보완을 추가했습니다.
- `tests/test_agent.py`에 오프라인 가짜 LLM·도구 기반 회귀 테스트를 추가했습니다.
- [docs/task3-agent.md](C:\Users\noh hui sun\codyssey\assignments\ProjectB-pilgrimage-planner\docs\task3-agent.md)에 `Task 3b 보강` 내용을 반영했습니다.

검증: `.venv/Scripts/python -m pytest -q` → **22 passed, 1 warning** (pytest 캐시 디렉터리 권한 경고).