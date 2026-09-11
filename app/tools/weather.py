"""Open-Meteo weather tool."""

import httpx
from langchain_core.tools import tool

from app.tools.http import get_client


def _weather_summary(code: int) -> str:
    if code == 0:
        return "맑음"
    if 1 <= code <= 3:
        return "구름 조금" if code == 1 else "구름 많음"
    if 45 <= code <= 48:
        return "안개"
    if 51 <= code <= 67:
        return "비"
    if 71 <= code <= 77:
        return "눈"
    if 80 <= code <= 82:
        return "소나기"
    if 95 <= code <= 99:
        return "뇌우"
    return "알 수 없음"


def fetch_weather(lat: float, lng: float, date: str, client: httpx.Client | None = None) -> dict:
    """Fetch a one-day forecast, returning an error dictionary on API failure."""
    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Asia/Seoul",
        "start_date": date,
        "end_date": date,
    }
    try:
        response = (client or get_client()).get("https://api.open-meteo.com/v1/forecast", params=params)
        response.raise_for_status()
        daily = response.json()["daily"]
        codes = daily.get("weather_code", [])
        mins = daily.get("temperature_2m_min", [])
        maxes = daily.get("temperature_2m_max", [])
        precipitation = daily.get("precipitation_probability_max", [])
        if not all((codes, mins, maxes, precipitation)):
            return {"error": "forecast_unavailable"}
        return {
            "summary": _weather_summary(int(codes[0])),
            "temp_min": float(mins[0]),
            "temp_max": float(maxes[0]),
            "precipitation_probability": float(precipitation[0]),
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return {"error": "forecast_unavailable"}


@tool
def get_weather(lat: float, lng: float, date: str) -> dict:
    """좌표와 날짜의 일기예보를 조회할 때 사용한다. 날씨 요약, 최저/최고 기온, 강수확률 또는 오류 정보를 반환한다."""
    return fetch_weather(lat, lng, date)
