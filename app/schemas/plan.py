"""specs/plan-schema.json과 1:1로 대응하는 Pydantic 모델.

LLM이 만든 일정 JSON은 반드시 PilgrimagePlan.model_validate()를 통과해야 한다.
스키마를 바꿀 때는 JSON 파일과 이 파일을 함께 고친다 (tests/test_plan_schema.py가 동치를 검사).
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Persona(str, Enum):
    mass_centered = "mass_centered"  # 미사 참례 중심
    walking = "walking"  # 도보 순례
    frugal = "frugal"  # 짠내 순례


class PlaceType(str, Enum):
    holy_site = "holy_site"
    mass = "mass"
    restaurant = "restaurant"
    cafe = "cafe"
    lodging = "lodging"
    transit = "transit"
    sight = "sight"


class TravelMode(str, Enum):
    walk = "walk"
    car = "car"
    transit = "transit"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Coordinates(_Strict):
    lat: float = Field(ge=33, le=39)
    lng: float = Field(ge=124, le=132)


class TravelLeg(_Strict):
    mode: TravelMode | None = None
    duration_min: int | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)


class Weather(_Strict):
    summary: str | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    precipitation_probability: float | None = Field(default=None, ge=0, le=100)


class Place(_Strict):
    order: int = Field(ge=1)
    name: str = Field(min_length=1)
    type: PlaceType
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    coordinates: Coordinates
    address: str | None = None
    description: str
    mass_time: str | None = None
    estimated_cost: int | None = Field(default=None, ge=0)
    travel_from_previous: TravelLeg | None = None
    reason: str | None = None


class Day(_Strict):
    day: int = Field(ge=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    weather: Weather | None = None
    places: list[Place] = Field(min_length=1)


class PilgrimagePlan(_Strict):
    plan_name: str = Field(min_length=1)
    region: str
    persona: Persona
    party_size: int = Field(ge=1)
    budget_per_person: int = Field(ge=0)
    estimated_cost_per_person: int | None = Field(default=None, ge=0)
    summary: str | None = None
    days: list[Day] = Field(min_length=1)
