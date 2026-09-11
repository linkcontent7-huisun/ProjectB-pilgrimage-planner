"""Input and graph state definitions."""

from datetime import date, timedelta
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.schemas.plan import Persona


class PlanRequest(BaseModel):
    region: str
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    nights: int = Field(ge=0)
    party_size: int = Field(ge=1)
    budget_per_person: int = Field(ge=0)
    persona: Persona
    preferences: str = ""


def travel_dates(request: PlanRequest | dict) -> list[str]:
    """Return every calendar date covered by a request, including departure day."""
    value = request if isinstance(request, PlanRequest) else PlanRequest.model_validate(request)
    start = date.fromisoformat(value.start_date)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(value.nights + 1)]


class AgentState(TypedDict, total=False):
    request: dict
    candidates: list[dict]
    messages: Annotated[list, add_messages]
    research_notes: str
    draft: str
    plan: dict
    validation_errors: list[str]
    attempts: int
    revise_request: str | None
    previous_plan: dict | None
    tool_call_cap: int
