You are implementing Task 5 (frontend) of the project in the current directory. Read README.md, docs/architecture.md (sections "API" and "SSE 이벤트 형식"), specs/plan-schema.json and data/holy_sites.json (structure only). Write ONLY inside `public/` (create `public/index.html`, `public/css/style.css`, `public/js/app.js`, `public/js/map.js`, `public/js/timeline.js`, `public/js/log.js`, `public/js/api.js`). Do NOT touch any Python file, docs/, specs/, data/ or .env. Do not commit. No build tools, no npm, no frameworks - plain HTML/CSS/ES modules (`<script type="module">`), Korean UI text. Another engineer is implementing the backend in parallel against the contract below; do not wait for it.

## Backend contract (fixed)
- `GET /api/config` -> `{"naver_map_client_id": "...", "personas": [{"key":"mass_centered","label":"미사 참례 중심"}, {"key":"walking","label":"도보 순례"}, {"key":"frugal","label":"짠내 순례"}]}`
- `POST /api/plans` JSON body `{"region": "대전", "start_date": "2026-09-20", "nights": 1, "party_size": 2, "budget_per_person": 80000, "persona": "mass_centered", "preferences": "자유 텍스트"}` -> 202 `{"plan_id": "...", "stream_url": "/api/plans/<id>/stream"}`; 422 with `{"detail": ...}` on bad input.
- `GET /api/plans/<id>/stream` -> Server-Sent Events. Event names and JSON data:
  - `status`  `{"stage": "collect"|"research"|"compose"|"finalize", "message": "대전 성지 미사 시간 검색 중"}`
  - `log`     `{"kind": "thinking"|"tool_call"|"tool_output"|"decision", "message"?: str, "tool"?: str, "args"?: object, "summary"?: str}`
  - `result`  the full plan JSON (schema below)
  - `error`   `{"message": "..."}`
  The stream replays past events first, then live ones, and closes after result/error.
- `GET /api/plans/<id>` -> `{"id","status":"pending"|"running"|"done"|"error","request","plan","error"}`
- `POST /api/plans/<id>/revise` body `{"instruction": "2일차 솔뫼성지 빼고 신리성지 넣어줘"}` -> 202 `{"plan_id","stream_url"}` (same id; open the stream again), 409 if not done.
- Plan JSON (specs/plan-schema.json): `plan_name, region, persona, party_size, budget_per_person, estimated_cost_per_person?, summary?, days[]`; each day `{day, date, weather?{summary,temp_min,temp_max,precipitation_probability}, places[]}`; each place `{order, name, type (holy_site|mass|restaurant|cafe|lodging|transit|sight), start_time "HH:MM", end_time, coordinates{lat,lng}, address?, description, mass_time?, estimated_cost?, travel_from_previous?{mode,duration_min,distance_km}, reason?}`.

## UI requirements (from the assignment spec - all mandatory)
1. **Input form** (top or left drawer): 지역(text, default 대전, with datalist suggestions 대전·당진·서산·공주·홍성·예산·아산·논산·부여·청양·보령·천안·금산·세종), 출발일(date, default = today+7), 박수(number 0-4, label "N박 M일" auto-computed, default 1), 인원(number, default 2), 1인 예산(number, 원, default 80000, step 10000), 순례 스타일(select from /api/config personas), 추가 요청(textarea, optional). Submit button "순례 일정 만들기". Disable while running. Show 422 errors inline.
2. **Progress badge** ("진행 상태 표시"): a pill at the top showing the latest `status.message` with a spinner while running, green check on result, red on error. Stage stepper: 후보 수집 → 조사 → 일정 작성 → 이동 계산 (highlight current stage).
3. **Decision log panel** ("의사결정 로그 UI"): bottom (or right column below map) scrolling panel; each log line prefixed with a colored tag `[Thinking]`, `[Tool Call]`, `[Tool Output]`, `[Decision]`; tool_call shows `tool(args as compact JSON)`; auto-scroll to bottom; a "지우기" button; keep entries after result so the user can review.
4. **Timeline panel** (left): Day tabs (`1일차 (2026-09-20)` with weather chip `맑음 18°/26° ☔10%` if present); vertical timeline of places with time range, type badge (Korean labels: 성지/미사/식당/카페/숙소/이동/명소, with distinct colors), name, description, mass_time (⛪ 미사 11:00) if present, estimated_cost (₩), travel_from_previous rendered as a small connector line between cards (🚶 8분 0.5km / 🚗 / 🚌), and a collapsible "선정 근거" showing `reason`. Header shows plan_name, summary, and `예상 1인 비용 / 예산` with a bar (red if over budget).
5. **Map panel** (right): Naver Maps JS v3. Load the script dynamically AFTER fetching /api/config: `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=<naver_map_client_id>` (parameter name is `ncpKeyId`; if the global `naver.maps` fails to load within 5 s show a fallback message "지도 로딩 실패 - Client ID / Web 서비스 URL 확인"). For the selected day: numbered markers (custom HTML marker with the `order` number, color by place type), a `naver.maps.Polyline` connecting places in order (blue, 4px, arrow-ish via strokeOpacity), fitBounds to the markers, InfoWindow on marker click with name/time/description. Switching day tabs re-renders markers. Hovering a timeline card highlights its marker (bounce or size change) and vice-versa.
6. **Revise box** ("일정 수정 기능"): under the timeline, textarea + button "수정 요청" (enabled only when a plan is done), e.g. placeholder "2일차 솔뫼성지 빼고 신리성지 넣어줘". POST to /revise, then re-open the SSE stream, clear the log, show progress, and re-render on result. Show a toast "일정을 다시 계산했습니다".
7. **Buttons**: "JSON 보기" (modal with pretty JSON + copy), "PDF 다운로드" linking to `/api/plans/<id>/pdf` (may 404 for now - open in new tab).
8. Layout: responsive CSS grid - desktop: left 380px timeline, right map (min 480px tall), log panel full-width bottom (220px, resizable not required); mobile (<900px): stacked. Clean, readable, no external CSS/JS except the Naver Maps script. Light theme with a subtle pilgrimage feel (deep blue/gold accents), system font stack.
9. Persist the last plan_id in localStorage and, on load, if present, fetch `/api/plans/<id>` and render if done (so refresh does not lose the plan).

## Code structure
- `api.js`: `getConfig()`, `createPlan(body)`, `getPlan(id)`, `revisePlan(id, instruction)`, `openStream(id, handlers)` using `EventSource` with `addEventListener` for each event name; close on result/error.
- `map.js`: `loadNaverMaps(clientId) -> Promise`, `createMap(el)`, `renderDay(map, places, {onMarkerHover, onMarkerClick})`, `highlight(order)`.
- `timeline.js`: `renderPlan(plan, {onDayChange, onCardHover})`, day tab state.
- `log.js`: `appendLog(event)`, `clearLog()`, `setStatus(stage, message, state)`.
- `app.js`: wiring, form handling, state `{planId, plan, currentDay}`.
- Keep functions small; add short Korean comments explaining each block for a non-developer reader.

## Verification (no backend available to you)
Create `public/dev/mock-plan.json` - a realistic 2-day 대전·당진 sample plan matching the schema (use real coordinates from data/holy_sites.json for holy sites: 대흥동 주교좌성당 36.3223,127.4187; 솔뫼 성지 36.8201,126.7861; 신리 성지 36.7626,126.7711; 합덕 성당 36.7925,126.7859; add a restaurant 성심당 36.3276,127.4273 and a cafe). Add a `?mock=1` query switch in app.js that skips the API, plays a scripted sequence of status/log events with 300 ms delays, then renders the mock plan - so the UI can be demoed without a backend. Open `public/index.html` mentally; make sure there are no syntax errors by running `node --check` on each JS file if node is available (`node --version`), otherwise re-read carefully.

## Report
Write `public/README-frontend.md` in Korean: file map, how events map to UI, how to demo with `?mock=1`, and known limitations. End your reply with a summary.
