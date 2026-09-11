Task 2를 구현했습니다.

- 4개 LangChain 도구 및 순수 함수 추가: [app/tools](/C:/Users/noh%20hui%20sun/codyssey/assignments/ProjectB-pilgrimage-planner/app/tools)
- MockTransport 기반 테스트 추가: [test_tools.py](/C:/Users/noh%20hui%20sun/codyssey/assignments/ProjectB-pilgrimage-planner/tests/test_tools.py)
- 한국어 계약·키 누락 처리·pytest 전체 출력 문서화: [task2-tools.md](/C:/Users/noh%20hui%20sun/codyssey/assignments/ProjectB-pilgrimage-planner/docs/task2-tools.md)

검증 결과: `15 passed, 1 warning`. 경고는 `.pytest_cache` 생성 권한 문제이며 테스트 결과에는 영향이 없습니다.

NCP 응답은 요구사항의 `route.trafast[0].summary.distance/duration` 및 Geocoding `addresses[].x/y` 필드를 기준으로 구현했습니다.