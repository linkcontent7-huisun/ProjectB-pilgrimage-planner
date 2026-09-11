"""Local holy-site candidate lookup."""

import json
from functools import lru_cache
from pathlib import Path

from app.tools.geo import haversine_km

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "holy_sites.json"
FALLBACK_NAME = "대흥동 주교좌성당"


@lru_cache(maxsize=1)
def load_sites() -> list[dict]:
    with DATA_FILE.open(encoding="utf-8") as source:
        return json.load(source)["sites"]


def _public(site: dict) -> dict:
    return {key: site.get(key) for key in (
        "id", "name", "city", "address", "lat", "lng", "category",
        "plenary_indulgence", "website",
    )}


def select_candidates(region: str, persona: str, limit: int = 12) -> list[dict]:
    sites = [site for site in load_sites() if isinstance(site.get("lat"), (int, float)) and isinstance(site.get("lng"), (int, float))]
    direct = [site for site in sites if site.get("city") == region or region in (site.get("address") or "")]
    if direct:
        centroid = (sum(s["lat"] for s in direct) / len(direct), sum(s["lng"] for s in direct) / len(direct))
    else:
        fallback = next(site for site in sites if site["name"] == FALLBACK_NAME)
        centroid = (fallback["lat"], fallback["lng"])
    radius = 15 if persona == "walking" else 70
    scored = [(haversine_km(centroid[0], centroid[1], s["lat"], s["lng"]), s) for s in sites]
    # Direct matches always lead; expansion is only necessary when the local set is small.
    expanded = [s for distance, s in scored if distance <= radius]
    # Keep explicit city/address matches first, then use nearby sites only to fill gaps.
    def ranked(items: list[dict]) -> list[dict]:
        return sorted(items, key=lambda s: (
            round(haversine_km(centroid[0], centroid[1], s["lat"], s["lng"]), 5),
            not bool(s.get("plenary_indulgence")), s["name"],
        ))
    if len(direct) < 4:
        direct_ids = {site["id"] for site in direct}
        pool = ranked(direct) + ranked([site for site in expanded if site["id"] not in direct_ids])
    else:
        pool = ranked(direct)
    return [_public(site) for site in pool[:limit]]
