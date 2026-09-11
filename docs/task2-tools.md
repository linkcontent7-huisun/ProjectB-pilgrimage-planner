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

## NCP Maps 키 입력 후 재검증 (2026-09-11 23:40 이후)

```
$ python -c "fetch_geocode('충남 당진시 우강면 솔뫼로 132'); fetch_route(대전→솔뫼, car)"
geocode : {'lat': 36.8200608, 'lng': 126.786066, 'address': '충청남도 당진시 우강면 솔뫼로 132 솔뫼성지'}
car     : {'mode': 'car', 'distance_km': 109.528, 'duration_min': 78}
```

- `geocode_place`: NCP Geocoding 실호출 성공 — 도로명 주소가 "솔뫼성지"까지 붙어 돌아옴
- `get_route` car: NCP Directions 5 실호출 성공 — 하버사인 추정(89.8 km/135분)과 달리 실경로 109.5 km/78분, `estimated` 없음

### 시드 좌표 채우기 (`scripts/fill_coordinates.py`)

```
OK   갈매못 순교 성지: 36.4282032, 126.5080074
OK   강경 김대건 신부 유숙지 (구순오의 집): 36.1625003, 127.0187423
OK   강경 성당: 36.1608408, 127.0166926
OK   공세리 성당: 36.8833547, 126.9134191
OK   남방제 성지: 36.7988035, 126.9460994
OK   다락골 성지: 36.4434424, 126.6924806
OK   대전교구청 성모당 순례지: 36.4922659, 127.3062453
OK   대흥 봉수산 순교 성지: 36.6061313, 126.7887867
OK   덕산 순교 성지: 36.7060973, 126.6676633
OK   도앙골 성지: 36.2623628, 126.7339999
OK   배나드리 성지: 36.7110993, 126.7227791
OK   산막골 성지 · 작은재 성지: 36.1602948, 126.7098355
OK   삽티 성지: 36.2562601, 126.7449913
OK   서짓골 성지: 36.2331096, 126.6575014
OK   성거산 성지: 36.8767963, 127.2389925
OK   솔뫼 성지: 36.8200608, 126.786066
OK   수리치골 성모 성지: 36.5200749, 126.8964977
OK   신리 성지: 36.7626201, 126.7711159
OK   여사울 성지: 36.756689, 126.8238804
OK   원머리 성지: 36.8994267, 126.7915922
OK   정산 순교 성지: 36.411949, 126.9486177
OK   지석리 성지: 36.1868788, 126.8024777
OK   진산 성지: 36.1801328, 127.3534722
OK   합덕 성당: 36.7924739, 126.7858567
OK   해미 순교자 국제 성지: 36.712918, 126.5377144
FAIL 홍주 순교 성지: {'error': 'not_found', 'query': '충남 홍성군 홍성읍 아문길 37-1'}
OK   황무실 성지: 36.7823103, 126.7375919
OK   황새바위 순교 성지: 36.4638739, 127.1200687
OK   대흥동 주교좌성당: 36.3223147, 127.4186725
filled=28 skipped=0 failed=1
```

홍주 순교 성지 1건 실패 → 출처 블로그 주소("아문길 37-1")가 틀린 것. 공식 홈페이지 주소 **홍성읍 조양로 108**로
고친 뒤 재실행해 채움. 최종 **29/29 좌표 확보**, `null` 0건.

남은 미검증: `web_search` (Tavily 키 대기)
