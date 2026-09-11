"""Tavily web-search tool."""

import httpx
from langchain_core.tools import tool

from app.config import settings
from app.tools.http import get_client


def fetch_web_search(query: str, max_results: int = 5, client: httpx.Client | None = None) -> list[dict]:
    """Search Tavily and normalize its results for the planning agent."""
    if not settings.TAVILY_API_KEY:
        return [{"error": "missing_api_key"}]
    try:
        response = (client or get_client()).post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
        )
        response.raise_for_status()
        return [
            {"title": item.get("title", ""), "snippet": item.get("content", "")[:300], "url": item.get("url", "")}
            for item in response.json().get("results", [])
        ]
    except (httpx.HTTPError, TypeError, ValueError):
        return [{"error": "search_failed"}]


@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """순례 일정에 필요한 최신 장소·미사·정보를 웹에서 찾을 때 사용한다. 제목, 300자 이내 요약, URL 목록을 반환한다."""
    return fetch_web_search(query, max_results)
