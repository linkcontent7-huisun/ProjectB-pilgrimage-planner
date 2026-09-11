"""Task 1 실험: LangChain ChatOpenAI + LangGraph ToolNode가 코디세이 API에서 도구 호출이 되는가.

실행: .venv/Scripts/python scripts/probe_tool_calling.py
"""

import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config import settings


@tool
def get_weather(city: str) -> str:
    """도시의 내일 날씨를 돌려준다."""
    return f"{city}의 내일 날씨: 맑음, 최저 18도 / 최고 27도, 강수확률 10%"


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


llm = ChatOpenAI(
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_MODEL,
).bind_tools([get_weather])


def call_llm(state: State) -> State:
    return {"messages": [llm.invoke(state["messages"])]}


def route(state: State) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


graph = StateGraph(State)
graph.add_node("llm", call_llm)
graph.add_node("tools", ToolNode([get_weather]))
graph.set_entry_point("llm")
graph.add_conditional_edges("llm", route, {"tools": "tools", END: END})
graph.add_edge("tools", "llm")
app = graph.compile()


if __name__ == "__main__":
    print(f"model={settings.OPENAI_MODEL} base_url={settings.OPENAI_BASE_URL}")
    result = app.invoke(
        {
            "messages": [
                SystemMessage(content="너는 여행 도우미다. 날씨는 반드시 get_weather 도구로 확인한다."),
                HumanMessage(content="대전의 내일 날씨를 알려줘"),
            ]
        }
    )
    for m in result["messages"]:
        print(f"[{m.type}] {m.content!r}")
        if getattr(m, "tool_calls", None):
            print(f"    tool_calls={m.tool_calls}")
