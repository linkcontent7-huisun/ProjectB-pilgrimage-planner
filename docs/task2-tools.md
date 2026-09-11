# Task 2: 에이전트 도구

## 파일 목록

- `app/tools/__init__.py`: LangChain 도구 4개를 `ALL_TOOLS`로 내보낸다.
- `app/tools/http.py`: 10초 타임아웃의 공통 `httpx.Client` 생성 함수다.
- `app/tools/geo.py`: 오프라인 거리 추정을 위한 haversine 계산 함수다.
- `app/tools/weather.py`: Open-Meteo 일별 날씨 조회와 `get_weather` 도구다.
- `app/tools/geocode.py`: Naver Maps 지오코딩과 `geocode_place` 도구다.
- `app/tools/route.py`: Naver Directions 5 및 오프라인 이동 추정, `get_route` 도구다.
- `app/tools/search.py`: Tavily 검색과 `web_search` 도구다.
- `tests/test_tools.py`: `httpx.MockTransport`만 사용하는 도구 단위 테스트다.

## 도구 계약

| 도구 | 입력 | 반환 |
|---|---|---|
| `web_search` | `query: str`, `max_results: int = 5` | `[{title, snippet, url}]` (요약은 300자 이내) |
| `geocode_place` | `name: str`, `region: str = ""` | `{lat, lng, address}` |
| `get_route` | `from_lat`, `from_lng`, `to_lat`, `to_lng`, `mode="car"` | `{mode, distance_km, duration_min}` |
| `get_weather` | `lat: float`, `lng: float`, `date: str` | `{summary, temp_min, temp_max, precipitation_probability}` |

각 LangChain 도구는 같은 이름의 순수 Python 함수(`fetch_*`)를 호출한다. 순수 함수는 선택적 `client` 인자를 받아 테스트가 `httpx.MockTransport` 클라이언트를 주입할 수 있다. 클라이언트가 없을 때만 공통 `get_client()`를 사용한다.

`walk`와 `transit`은 API를 호출하지 않고 haversine 거리의 1.3배로 도로 거리를 추정한다. 보행은 시속 4km, 대중교통은 시속 20km와 대기 10분을 적용한다. 자동차 API가 실패하거나 Naver 키가 없으면 시속 40km 추정값에 `estimated: true`를 더해 반환한다.

## API 키 누락 처리

- Naver 지오코딩: `{ "error": "missing_api_key" }`를 반환하고 요청하지 않는다.
- Naver 자동차 경로: 외부 요청 없이 자동차 추정 경로와 `estimated: true`를 반환한다.
- Tavily 검색: `[{ "error": "missing_api_key" }]`를 반환하고 요청하지 않는다.
- Open-Meteo는 키가 필요 없다. API 오류 또는 빈 일별 배열은 `{ "error": "forecast_unavailable" }`로 반환한다.

## pytest 실행 결과

```text
...............                                                          [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\_pytest\cacheprovider.py:469
  C:\Users\noh hui sun\codyssey\assignments\ProjectB-pilgrimage-planner\.venv\Lib\site-packages\_pytest\cacheprovider.py:469: PytestCacheWarning: could not create cache path C:\Users\noh hui sun\codyssey\assignments\ProjectB-pilgrimage-planner\.pytest_cache\v\cache\nodeids: [WinError 5] 액세스가 거부되었습니다: 'C:\\Users\\noh hui sun\\codyssey\\assignments\\ProjectB-pilgrimage-planner\\.pytest_cache\\v\\cache'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
15 passed, 1 warning in 0.62s
```

## 실호출 검증 (Claude, 2026-09-11)

Codex는 네트워크 없이 작업했으므로 실제 API 호출은 별도로 확인했다. 키가 없는 도구는 설계대로 오류 dict를 돌려준다.

```
weather  : {'summary': '구름 많음', 'temp_min': 17.6, 'temp_max': 26.2, 'precipitation_probability': 0.0}
walk     : {'mode': 'walk', 'distance_km': 0.436, 'duration_min': 7}
car(nokey): {'mode': 'car', 'distance_km': 89.803, 'duration_min': 135, 'estimated': True}
geocode  : {'error': 'missing_api_key'}
search   : [{'error': 'missing_api_key'}]
```

- `get_weather`: Open-Meteo 실호출 성공 (대전 2026-09-13)
- `get_route` walk: 대흥동성당 → 성심당 0.44 km / 7분 (하버사인 × 1.3)
- `get_route` car: 키 없음 → 40 km/h 추정치 + `estimated: true`
- `geocode_place`, `web_search`: 키 없음 → `missing_api_key`. NCP Maps·Tavily 키 입력 후 재검증 필요

## 시드 데이터 (Claude)

- `data/holy_sites.json`: 대전교구 성지 28곳 + 대흥동 주교좌성당. 주소·전화·홈페이지·분류·전대사 지정 여부.
  좌표(`lat/lng`)는 지어내지 않고 `null`로 두었다 → 키 입력 후 `scripts/fill_coordinates.py`로 채운다.
- 미사 시간은 시드에 넣지 않는다. 실행 시 `web_search`로 최신 정보를 확인한다.
