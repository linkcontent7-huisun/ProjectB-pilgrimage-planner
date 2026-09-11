# 순례길 플래너 — [Project B] 초개인화 여행 계획 수립 AI 에이전트

지역·일정·인원·예산·순례 스타일을 입력하면 AI 에이전트가 **네이버 지도 API와 실시간 검색 도구를
직접 호출**해 가톨릭 성지순례 코스를 짜고, 지도 위 동선과 타임라인으로 보여주는 웹 서비스.
에이전트가 왜 그 성지를 그 순서에 넣었는지 **의사결정 로그**를 실시간으로 확인할 수 있다.

- 명세: [`specs/spec-original.md`](specs/spec-original.md) · 대응표: [`specs/requirements-checklist.md`](specs/requirements-checklist.md)
- 설계: [`docs/architecture.md`](docs/architecture.md) · 일정 스키마: [`specs/plan-schema.json`](specs/plan-schema.json)

## 진행 상태

🚧 골격 단계 — 설계 문서·스키마 작성 완료, 구현 시작 전.

## 실행

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
copy .env.example .env                              # 키 채우기
uvicorn main:app --reload
```

## 구조

```
main.py            FastAPI 앱
app/agent/         LangGraph 그래프·노드·도구
app/schemas/       Pydantic 모델 (plan-schema.json과 동일)
app/routers/       /api/plans
data/              성지 시드 데이터
public/            프론트엔드 (지도·타임라인·로그)
specs/             명세·체크리스트·스키마
docs/              설계·증빙 문서
tests/
```
