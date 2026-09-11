You are doing Task 3b: fixes and tests for the LangGraph agent in `app/agent/` that you built in Task 3 (read docs/codex-tasks/task3.md for the original contract, and docs/task3-agent.md). Do NOT modify specs/, docs/architecture.md, app/tools/, app/schemas/, data/, public/, or .env. Do not commit. No network in tests.

## What a live run revealed (real LLM + real tools, see below)
```
[Thinking] 후보 성지: 대흥동 주교좌성당, 진산 성지, ...
[Tool Call] web_search {"query": "대흥동 주교좌성당 미사 시간", "max_results": 5}
[Tool Output] web_search [{"error": "missing_api_key"}]
... (the same web_search call repeated 9 times, always missing_api_key)
[Tool Call] get_weather {"lat": 36.32, "lng": 127.41, "date": "2026-09-12"}   <- request was start_date 2026-09-20, nights 0
[Tool Call] get_weather {... "date": "2026-09-13"}
[Tool Call] get_weather {... "date": "2026-09-14"}
openai.InternalServerError: Error code: 502 - {'error': {'message': 'Provider returned an error.', 'type': 'api_error', 'code': 'provider_error'}}
```

## Fixes (all required)
1. **Unavailable tools are not offered.** In `research`, build the tool list with a new helper `available_tools() -> list` in `app/agent/nodes.py` (or `app/tools/__init__.py` is off-limits, so put it in nodes.py): drop `web_search` when `settings.TAVILY_API_KEY` is empty, drop `geocode_place` when NAVER keys are empty (`get_route` and `get_weather` stay - they degrade gracefully). Bind only those. In `research_system_prompt`, add a line listing which tools are available and, when web_search is missing, say: "web_search를 쓸 수 없다. 미사 시간은 조사하지 말고 일정 작성 시 '미사 시간은 방문 전 확인 필요'로 표시하라." Pass the available tool names into the prompt builder (new optional parameter `available: list[str] | None`).
2. **Duplicate tool calls are short-circuited.** Keep a `seen: dict[(name, json.dumps(args, sort_keys=True))] -> output` in the research loop; if the same call repeats, do not execute it again - append a ToolMessage with `{"error": "duplicate_call", "hint": "같은 도구를 같은 인자로 다시 부르지 마라"}` and still count it toward the cap. Emit a log_decision("중복 도구 호출 차단: name") once per duplicate.
3. **Explicit dates in the prompt.** `research_system_prompt` and `compose_user_prompt` must list the exact travel dates computed from start_date + nights (e.g. "여행 날짜: 2026-09-20 (1일차)"), and the research prompt must say get_weather is to be called only for those dates. Add `travel_dates(request) -> list[str]` in `app/agent/state.py` (or validators.py) and reuse it in validators.
4. **Robust LLM calls.** In `app/agent/llm.py` set `max_retries=3` and `timeout=60` on ChatOpenAI. In nodes.py add a helper `_invoke_with_retry(model, messages, attempts=3)` that retries on `openai.APIStatusError` with status >= 500 and on `openai.APIConnectionError`/`APITimeoutError` (sleep 2s, 4s), and re-raises the last error. Use it for every `.invoke` in research and compose. If research still fails after retries, do not crash: emit log_decision("조사 단계 LLM 오류, 후보 데이터만으로 일정을 작성한다") and set `research_notes` to "조사 요약: (LLM 오류로 조사 생략) " + a compact summary of candidates and any tool outputs collected so far.
5. **Persona label leak**: in `collect`, the thinking log currently lists all 12 candidate names - fine, keep - but also emit status("collect", f"{region} 후보 성지 {n}곳 선정") after selection.
6. **Weather for the plan**: in `finalize`, if a day has no `weather`, call `fetch_weather` at the first place's coordinates for that date and fill `day["weather"]` when the result has no error (skip silently otherwise).

## Tests - create `tests/test_agent.py` (this file does NOT exist yet - you must create it)
No network, no real LLM. Implement a small fake `BaseChatModel` subclass in the test with `bind_tools(...)` returning self and scripted `_generate` responses consumed in order. Monkeypatch `app.agent.llm.get_llm` (nodes call `llm_module.get_llm`, so patching the module attribute works) and patch `app.tools.weather.fetch_weather` / `app.tools.route.fetch_route` / `app.tools.geocode.fetch_geocode` to canned dicts. Also monkeypatch `app.config.settings.TAVILY_API_KEY = ""` and NAVER keys non-empty for the availability test.
Cover:
- `select_candidates("당진", "mass_centered")` returns 당진 sites first; `select_candidates("대전", "walking")` includes 대흥동 주교좌성당; lat/lng are floats.
- `travel_dates({"start_date": "2026-09-20", "nights": 2})` == ["2026-09-20", "2026-09-21", "2026-09-22"].
- `available_tools()` excludes web_search when TAVILY key is empty and includes it when set.
- validators: a valid 2-day plan -> []; wrong day count / non-consecutive date / overlapping times / missing mass_time (mass_centered) / budget exceeded -> expected substrings.
- `strip_json_fences` for ```json, ``` and bare JSON.
- full graph: scripted responses = research: AIMessage with tool_call get_weather -> AIMessage with the SAME tool_call again (must be blocked as duplicate) -> AIMessage "조사 요약: ..." ; compose: invalid JSON (missing days) -> valid plan JSON. Assert run_plan returns a valid plan; events contain status stages collect/research/compose/finalize, one tool_call log for get_weather, a decision log containing "중복 도구 호출 차단", a decision log containing "검증 실패", exactly one result event, and the result's day has `weather` filled from the canned fetch_weather.
- retry helper: a fake model whose first invoke raises `openai.APIStatusError`-like 502 (construct via `openai.InternalServerError(message, response=httpx.Response(502, request=httpx.Request("POST","http://x")), body=None)`) and second returns an AIMessage -> `_invoke_with_retry` returns the message (patch `time.sleep`).
Run `.venv/Scripts/python -m pytest -q` - all tests (15 existing + new) must pass. Update docs/task3-agent.md with a "Task 3b 보강" section (what changed, why, new pytest output).

## Report
End your reply with a summary of changes and the test count.
