# 요구사항 체크리스트

명세 원본: [`spec-original.md`](spec-original.md). 이 과제는 명세의 "여행"을
**가톨릭 성지순례**로 특화한다 — 명세 항목은 하나도 빼지 않고, 여행지·테마만 순례 도메인으로 좁힌다.

상태: ⬜ 미착수 · 🚧 진행 중 · ✅ 완료 (증빙 파일 링크 필수)

## 필수 기능 (4장, 10항목)

| # | 명세 항목 | 이 과제에서의 구현 | 상태 | 증빙 |
|---|---|---|---|---|
| 1 | 여행 정보 입력 (목적지·N박M일·인원·예산·선호 테마) | 지역(시·도) · 출발일+박수 · 인원 · 1인 예산 · 순례 스타일(미사 참례 중심 / 도보 순례 / 역사 탐방) 입력 폼 | ⬜ | |
| 2 | 지도 API 연동 — Function Calling으로 좌표 획득 | 도구 `geocode_place(name)` → **Naver Geocoding API**. 에이전트가 성지·식당 이름을 좌표로 바꿀 때 스스로 호출 | ⬜ | |
| 3 | 실시간 검색 (Tavily / SerpApi) | 도구 `web_search(query)` → **Tavily**. 미사 시간·개방 시간·주변 식당·숙소 조회. 날씨는 `get_weather(lat,lng,date)` → Open-Meteo | ⬜ | |
| 4 | 진행 상태 표시 ('날씨 검색 중' 등) | **SSE** 스트림으로 `status` 이벤트 전송, 프론트 상단 진행 배지 | ⬜ | |
| 5 | 타임라인 시각화 (날짜별·시간대별) | 좌측 패널: Day 탭 → 시간·장소·유형·설명 카드 | ⬜ | |
| 6 | 지도 시각화 (마커 + 이동 순서 연결) | 우측 패널: **Naver Web Dynamic Map**, 번호 마커 + Polyline(Directions 5 경로 또는 직선) | ⬜ | |
| 7 | JSON 스키마 검증 (불일치 시 재생성/예외) | `schemas/plan-schema.json` + Pydantic 모델. 검증 실패 시 오류 메시지를 넣어 최대 2회 재생성, 그래도 실패면 422 | ⬜ | |
| 8 | 일정 수정 (장소 삭제·변경 → 동선 재계산) | `POST /api/plans/{id}/revise` — 기존 계획 + 수정 요청을 그래프에 재투입, 나머지 장소 순서·시간 재계산 | ⬜ | |
| 9 | LangChain 또는 LangGraph 필수 | **LangGraph** StateGraph: collect → research(도구 루프) → compose → validate → (fix) → done | ⬜ | |
| 10 | API 키 환경 변수 관리 | `.env` + `.env.example`, `.gitignore`로 `.env` 제외 | ✅ | `.env.example`, `.gitignore` |

## 최종 결과물 (2장)

| 항목 | 구현 | 상태 | 증빙 |
|---|---|---|---|
| 여행 계획 입력 및 시각화 | 1 + 5 + 6 | ⬜ | |
| 의사결정 로그 UI (실시간) | SSE `log` 이벤트: `[Thinking]` `[Tool Call]` `[Tool Output]` `[Decision]` 4종을 하단 패널에 스트리밍 | ⬜ | |
| JSON 스키마 정의 | `specs/plan-schema.json` | ✅ | `specs/plan-schema.json` |

## 개발 환경·제약 (6·7장)

| 항목 | 상태 | 증빙 |
|---|---|---|
| Python 3.10 이상 | ⬜ | `docs/environment.md` |
| LangGraph 사용 | ⬜ | `requirements.txt`, `app/agent/graph.py` |
| GPT-4o 동급 LLM — 코디세이 공개 API `gpt-5-mini` (필요 시 `gpt-5.4`) | ⬜ | |
| 지도 API — Naver Maps | ⬜ | |
| 검색 API — Tavily | ⬜ | |
| **지도 UI 필수** (텍스트 리스트만은 불인정) | ⬜ | 스크린샷 + `docs/run-log.md` |
| API 키 노출 금지 | ✅ | `.gitignore` |

## 보너스 (5장)

| 항목 | 구현 | 상태 | 증빙 |
|---|---|---|---|
| 페르소나 기반 계획 | 페르소나 3종(미사 중심 순례자 / 도보 순례자 / 짠내 순례자) — 시스템 프롬프트·예산 가중치·이동수단 선호가 달라짐 | ⬜ | |
| PDF 다운로드 | `GET /api/plans/{id}/pdf` (WeasyPrint 또는 reportlab) | ⬜ | |
| 이메일 발송 | 선택 — SMTP 설정이 있을 때만 활성화 | ⬜ | |

## 제출 증빙 문서 (평가는 .md만 본다)

| 문서 | 내용 | 상태 |
|---|---|---|
| `README.md` | 개요·실행법·구조·요구사항 대응표 | ⬜ |
| `docs/environment.md` | Python 버전, pip list 텍스트 | ⬜ |
| `docs/run-log.md` | 실행 터미널 출력 텍스트, 에이전트 로그 예시 | ⬜ |
| `docs/test-log.md` | pytest 출력 텍스트 | ⬜ |
| `docs/git-log.md` | 브랜치·커밋 이력 텍스트 (feature 브랜치 병합 포함) | ⬜ |
| `docs/architecture.md` | LangGraph 흐름도, 도구 목록, 스키마 검증·재생성 전략 | 🚧 |
