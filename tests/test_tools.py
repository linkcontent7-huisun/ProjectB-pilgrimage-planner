import math

import httpx
import pytest

from app.config import settings
from app.tools import ALL_TOOLS
from app.tools.geocode import fetch_geocode
from app.tools.route import fetch_route
from app.tools.search import fetch_web_search
from app.tools.weather import fetch_weather


def mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), timeout=10)


def test_weather_happy_path_and_wmo_mapping():
    def handler(request):
        assert request.url == httpx.URL(
            "https://api.open-meteo.com/v1/forecast?latitude=36.3258&longitude=127.4243"
            "&daily=weather_code%2Ctemperature_2m_max%2Ctemperature_2m_min%2Cprecipitation_probability_max"
            "&timezone=Asia%2FSeoul&start_date=2026-09-15&end_date=2026-09-15"
        )
        return httpx.Response(200, json={"daily": {
            "weather_code": [80], "temperature_2m_min": [17.2],
            "temperature_2m_max": [24.8], "precipitation_probability_max": [60],
        }})

    result = fetch_weather(36.3258, 127.4243, "2026-09-15", mock_client(handler))
    assert result == {"summary": "소나기", "temp_min": 17.2, "temp_max": 24.8, "precipitation_probability": 60.0}


def test_weather_out_of_forecast_range_returns_error():
    def handler(request):
        return httpx.Response(400, json={"reason": "date out of range"})

    assert "error" in fetch_weather(36.3, 127.4, "2030-01-01", mock_client(handler))


def test_geocode_happy_path_and_empty_result(monkeypatch):
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_ID", "test-id")
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_SECRET", "test-secret")

    def happy_handler(request):
        assert request.url.host == "maps.apigw.ntruss.com"
        assert request.url.path == "/map-geocode/v2/geocode"
        assert request.url.params["query"] == "대전 성심당"
        assert request.headers["x-ncp-apigw-api-key-id"] == "test-id"
        assert request.headers["x-ncp-apigw-api-key"] == "test-secret"
        return httpx.Response(200, json={"addresses": [{
            "x": "127.4273", "y": "36.3276", "roadAddress": "대전 중구 대종로480번길 15", "jibunAddress": "",
        }]})

    assert fetch_geocode("성심당", "대전", mock_client(happy_handler)) == {
        "lat": 36.3276, "lng": 127.4273, "address": "대전 중구 대종로480번길 15",
    }

    def empty_handler(request):
        return httpx.Response(200, json={"addresses": []})

    assert fetch_geocode("없는장소", "대전", mock_client(empty_handler)) == {
        "error": "not_found", "query": "대전 없는장소",
    }


def test_geocode_missing_key_does_not_request(monkeypatch):
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_ID", "")
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_SECRET", "")

    def handler(request):  # pragma: no cover - a request is a test failure
        raise AssertionError("missing API key must not make a request")

    assert fetch_geocode("성심당", client=mock_client(handler)) == {"error": "missing_api_key"}


def test_car_route_converts_ncp_units(monkeypatch):
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_ID", "test-id")
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_SECRET", "test-secret")

    def handler(request):
        assert request.url.path == "/map-direction/v1/driving"
        assert request.url.params["start"] == "127.4243,36.3258"
        assert request.url.params["goal"] == "127.4273,36.3276"
        assert request.url.params["option"] == "trafast"
        assert request.headers["x-ncp-apigw-api-key-id"] == "test-id"
        return httpx.Response(200, json={"route": {"trafast": [{"summary": {
            "distance": 1530, "duration": 185000,
        }}]}})

    assert fetch_route(36.3258, 127.4243, 36.3276, 127.4273, client=mock_client(handler)) == {
        "mode": "car", "distance_km": 1.53, "duration_min": 4,
    }


def test_walk_and_transit_routes_are_haversine_estimates():
    walk = fetch_route(36.3258, 127.4243, 36.3276, 127.4273, "walk")
    transit = fetch_route(36.3258, 127.4243, 36.3276, 127.4273, "transit")
    assert walk["mode"] == "walk"
    assert 0.3 <= walk["distance_km"] <= 0.5
    assert walk["duration_min"] == math.ceil(walk["distance_km"] / 4 * 60)
    assert transit == {"mode": "transit", "distance_km": walk["distance_km"], "duration_min": math.ceil(walk["distance_km"] / 20 * 60) + 10}


def test_car_route_falls_back_after_api_failure(monkeypatch):
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_ID", "test-id")
    monkeypatch.setattr(settings, "NAVER_MAP_CLIENT_SECRET", "test-secret")

    def handler(request):
        return httpx.Response(500)

    result = fetch_route(36.3258, 127.4243, 36.3276, 127.4273, client=mock_client(handler))
    assert result["mode"] == "car"
    assert result["estimated"] is True
    assert result["duration_min"] >= 1


def test_web_search_happy_path_and_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")

    def handler(request):
        assert request.method == "POST"
        assert request.url == httpx.URL("https://api.tavily.com/search")
        import json
        assert json.loads(request.content) == {
            "api_key": "test-key", "query": "대전 성당 미사", "max_results": 2, "search_depth": "basic",
        }
        return httpx.Response(200, json={"results": [{
            "title": "미사 안내", "content": "가" * 350, "url": "https://example.test/mass",
        }]})

    result = fetch_web_search("대전 성당 미사", 2, mock_client(handler))
    assert result == [{"title": "미사 안내", "snippet": "가" * 300, "url": "https://example.test/mass"}]

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    assert fetch_web_search("어떤 검색", client=mock_client(lambda request: (_ for _ in ()).throw(AssertionError()))) == [{"error": "missing_api_key"}]


def test_all_tools_expose_expected_names_and_arguments():
    assert [tool.name for tool in ALL_TOOLS] == ["web_search", "geocode_place", "get_route", "get_weather"]
    fields = {tool.name: set(tool.args_schema.model_fields) for tool in ALL_TOOLS}
    assert fields == {
        "web_search": {"query", "max_results"},
        "geocode_place": {"name", "region"},
        "get_route": {"from_lat", "from_lng", "to_lat", "to_lng", "mode"},
        "get_weather": {"lat", "lng", "date"},
    }
