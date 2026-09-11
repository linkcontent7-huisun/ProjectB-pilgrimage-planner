"""Naver driving directions and local fallback route estimates."""

import math

import httpx
from langchain_core.tools import tool

from app.config import settings
from app.tools.geo import haversine_km
from app.tools.http import get_client


def _estimated_route(from_lat: float, from_lng: float, to_lat: float, to_lng: float, mode: str, speed_kmh: float) -> dict:
    distance_km = haversine_km(from_lat, from_lng, to_lat, to_lng) * 1.3
    duration_min = math.ceil(distance_km / speed_kmh * 60)
    if mode == "transit":
        duration_min += 10
    return {"mode": mode, "distance_km": round(distance_km, 3), "duration_min": duration_min}


def fetch_route(
    from_lat: float, from_lng: float, to_lat: float, to_lng: float,
    mode: str = "car", client: httpx.Client | None = None,
) -> dict:
    """Fetch driving directions, or calculate an offline walking/transit estimate."""
    if mode == "walk":
        return _estimated_route(from_lat, from_lng, to_lat, to_lng, mode, 4)
    if mode == "transit":
        return _estimated_route(from_lat, from_lng, to_lat, to_lng, mode, 20)

    fallback = _estimated_route(from_lat, from_lng, to_lat, to_lng, mode, 40)
    fallback["estimated"] = True
    if mode != "car" or not settings.NAVER_MAP_CLIENT_ID or not settings.NAVER_MAP_CLIENT_SECRET:
        return fallback
    headers = {
        "x-ncp-apigw-api-key-id": settings.NAVER_MAP_CLIENT_ID,
        "x-ncp-apigw-api-key": settings.NAVER_MAP_CLIENT_SECRET,
    }
    try:
        response = (client or get_client()).get(
            "https://maps.apigw.ntruss.com/map-direction/v1/driving",
            params={
                "start": f"{from_lng},{from_lat}",
                "goal": f"{to_lng},{to_lat}",
                "option": "trafast",
            },
            headers=headers,
        )
        response.raise_for_status()
        summary = response.json()["route"]["trafast"][0]["summary"]
        return {
            "mode": mode,
            "distance_km": round(float(summary["distance"]) / 1000, 3),
            "duration_min": math.ceil(float(summary["duration"]) / 60_000),
        }
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return fallback


@tool
def get_route(from_lat: float, from_lng: float, to_lat: float, to_lng: float, mode: str = "car") -> dict:
    """두 좌표 사이의 이동 거리와 시간을 구할 때 사용한다. walk, car, transit 모드의 거리 km와 소요 분을 반환한다."""
    return fetch_route(from_lat, from_lng, to_lat, to_lng, mode)
