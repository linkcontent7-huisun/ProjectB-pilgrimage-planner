"""LangChain tools available to the pilgrimage planning agent."""

from app.tools.geocode import geocode_place
from app.tools.route import get_route
from app.tools.search import web_search
from app.tools.weather import get_weather

ALL_TOOLS = [web_search, geocode_place, get_route, get_weather]
