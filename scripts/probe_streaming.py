"""Task 1 보조 실험: ChatOpenAI 토큰 스트리밍이 코디세이 API에서 되는가 (SSE 진행 표시에 필요).

실행: PYTHONUTF8=1 .venv/Scripts/python scripts/probe_streaming.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.config import settings

llm = ChatOpenAI(base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)

chunks = 0
for chunk in llm.stream([HumanMessage(content="대전 성지 두 곳을 한 줄씩 소개해줘")]):
    chunks += 1
    print(chunk.content, end="", flush=True)
print(f"\n--- chunks={chunks}")
