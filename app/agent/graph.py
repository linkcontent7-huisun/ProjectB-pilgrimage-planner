"""Public planning and revision API."""

from langgraph.graph import END, START, StateGraph

from app.agent.events import Emit, error
from app.agent.nodes import collect, compose, finalize, research, validate
from app.agent.state import AgentState


class PlanGenerationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _after_validate(state: AgentState) -> str:
    if not state.get("validation_errors"):
        return "finalize"
    return "compose" if state.get("attempts", 0) < 3 else "end"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("collect", collect)
    graph.add_node("research", research)
    graph.add_node("compose", compose)
    graph.add_node("validate", validate)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "collect")
    graph.add_edge("collect", "research")
    graph.add_edge("research", "compose")
    graph.add_edge("compose", "validate")
    graph.add_conditional_edges("validate", _after_validate, {"compose": "compose", "finalize": "finalize", "end": END})
    graph.add_edge("finalize", END)
    return graph.compile()


def _run(initial: dict, emit: Emit | None) -> dict:
    callback = emit or (lambda event: None)
    final = build_graph().invoke(initial, config={"configurable": {"emit": callback}})
    if not final.get("plan"):
        errors = final.get("validation_errors") or ["계획을 생성하지 못했습니다"]
        callback(error("; ".join(errors)))
        raise PlanGenerationError(errors)
    return {"plan": final["plan"], "research_notes": final.get("research_notes", "")}


def run_plan(request: dict, emit: Emit | None = None) -> dict:
    return _run({"request": request}, emit)


def run_revise(previous_plan: dict, request: dict, revise_request: str, research_notes: str,
               emit: Emit | None = None) -> dict:
    return _run({"request": request, "previous_plan": previous_plan, "revise_request": revise_request,
                 "research_notes": research_notes, "tool_call_cap": 6}, emit)
