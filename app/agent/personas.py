"""Persona constraints shared by candidate selection and prompts."""

PERSONAS: dict[str, dict] = {
    "mass_centered": {
        "label": "미사 중심 순례",
        "rules": "- 매일 미사 시간(mass_time)이 있는 미사 또는 성지 한 곳을 포함한다.\n- 그 미사 시간을 중심으로 앞뒤 일정을 배치한다.",
        "default_mode": "car",
        "max_places_per_day": 4,
        "daily_walk_km_limit": None,
    },
    "walking": {
        "label": "도보 순례",
        "rules": "- 성지와 방문지를 도보 이동 범위 안에서 묶는다.\n- 매일 카페 또는 휴식 장소를 포함한다.\n- 이동 수단은 walk를 사용한다.",
        "default_mode": "walk",
        "max_places_per_day": 5,
        "daily_walk_km_limit": 12,
    },
    "frugal": {
        "label": "알뜰 순례",
        "rules": "- 1인 예상 비용은 예산 이하여야 한다.\n- 대중교통과 저렴한 식사를 우선한다.\n- 각 방문지 reason에 절약 근거를 적는다.",
        "default_mode": "transit",
        "max_places_per_day": 5,
        "daily_walk_km_limit": None,
    },
}
