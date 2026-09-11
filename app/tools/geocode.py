"""Naver Maps geocoding tool."""

import httpx
from langchain_core.tools import tool

from app.config import settings
from app.tools.http import get_client


def fetch_geocode(name: str, region: str = "", client: httpx.Client | None = None) -> dict:
    """Resolve a Korean place name to a coordinate and address."""
    if not settings.NAVER_MAP_CLIENT_ID or not settings.NAVER_MAP_CLIENT_SECRET:
        return {"error": "missing_api_key"}
    query = " ".join(part for part in (region.strip(), name.strip()) if part)
    headers = {
        "x-ncp-apigw-api-key-id": settings.NAVER_MAP_CLIENT_ID,
        "x-ncp-apigw-api-key": settings.NAVER_MAP_CLIENT_SECRET,
    }
    try:
        response = (client or get_client()).get(
            "https://maps.apigw.ntruss.com/map-geocode/v2/geocode",
            params={"query": query},
            headers=headers,
        )
        response.raise_for_status()
        addresses = response.json().get("addresses", [])
        if not addresses:
            return {"error": "not_found", "query": query}
        address = addresses[0]
        return {
            "lat": float(address["y"]),
            "lng": float(address["x"]),
            "address": address.get("roadAddress") or address.get("jibunAddress") or "",
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return {"error": "geocode_failed", "query": query}


@tool
def geocode_place(name: str, region: str = "") -> dict:
    """장소명과 선택 지역으로 좌표가 필요할 때 사용한다. 위도, 경도, 도로명 또는 지번 주소를 반환한다."""
    return fetch_geocode(name, region)
