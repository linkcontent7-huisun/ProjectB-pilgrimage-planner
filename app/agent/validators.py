"""Logical validation not expressible by the shared JSON/Pydantic schema."""

from app.agent.personas import PERSONAS
from app.agent.state import PlanRequest, travel_dates
from app.schemas.plan import PilgrimagePlan
from app.tools.geo import haversine_km


def logical_errors(plan: PilgrimagePlan, request: PlanRequest) -> list[str]:
    errors: list[str] = []
    if len(plan.days) != request.nights + 1:
        errors.append("일수는 숙박 수 + 1이어야 합니다")
    try:
        for index, day in enumerate(plan.days):
            if day.date != travel_dates(request)[index]:
                errors.append("날짜가 연속되지 않습니다")
                break
    except ValueError:
        errors.append("시작 날짜가 올바르지 않습니다")
    for day in plan.days:
        previous_end = ""
        orders = [place.order for place in day.places]
        if orders != list(range(1, len(orders) + 1)):
            errors.append(f"{day.day}일차 방문 순서가 올바르지 않습니다")
        for place in day.places:
            if place.start_time >= place.end_time:
                errors.append(f"{day.day}일차 시간 범위가 올바르지 않습니다")
            if previous_end and place.start_time < previous_end:
                errors.append(f"{day.day}일차 일정 시간이 겹칩니다")
            previous_end = place.end_time
        if request.persona.value == "mass_centered" and not any(
            p.mass_time and p.type.value in {"mass", "holy_site"} for p in day.places
        ):
            errors.append(f"{day.day}일차 미사 시간이 없습니다")
        if request.persona.value == "walking":
            walked = 0.0
            for index, place in enumerate(day.places):
                if index == 0:
                    continue
                leg = place.travel_from_previous
                if leg and leg.mode and leg.mode.value == "walk" and leg.distance_km is not None:
                    walked += leg.distance_km
                elif not leg:
                    previous = day.places[index - 1]
                    walked += haversine_km(previous.coordinates.lat, previous.coordinates.lng,
                                           place.coordinates.lat, place.coordinates.lng)
            if walked > PERSONAS["walking"]["daily_walk_km_limit"]:
                errors.append(f"{day.day}일차 도보 거리 초과: {walked:.1f}km")
    total = plan.estimated_cost_per_person
    if total is None:
        total = sum(place.estimated_cost or 0 for day in plan.days for place in day.places)
    if total > request.budget_per_person * 1.2:
        errors.append(f"예산 초과: {total}원")
    return errors
