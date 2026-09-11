import copy
import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from app.schemas.plan import PilgrimagePlan

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "specs" / "plan-schema.json"
JSON_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

GOOD = {
    "plan_name": "대전 1일 미사 중심 순례",
    "region": "대전",
    "persona": "mass_centered",
    "party_size": 2,
    "budget_per_person": 50000,
    "estimated_cost_per_person": 32000,
    "summary": "오전 미사 후 성지 두 곳",
    "days": [
        {
            "day": 1,
            "date": "2026-09-20",
            "weather": {"summary": "맑음", "temp_min": 18, "temp_max": 26, "precipitation_probability": 10},
            "places": [
                {
                    "order": 1,
                    "name": "대흥동 주교좌성당",
                    "type": "mass",
                    "start_time": "10:00",
                    "end_time": "11:00",
                    "coordinates": {"lat": 36.3258, "lng": 127.4243},
                    "address": "대전 중구 대흥로 62",
                    "description": "주일 10시 미사",
                    "mass_time": "10:00",
                    "estimated_cost": 0,
                    "reason": "미사 참례 중심 페르소나의 첫 일정",
                },
                {
                    "order": 2,
                    "name": "성심당",
                    "type": "restaurant",
                    "start_time": "11:30",
                    "end_time": "12:30",
                    "coordinates": {"lat": 36.3276, "lng": 127.4273},
                    "description": "점심",
                    "estimated_cost": 12000,
                    "travel_from_previous": {"mode": "walk", "duration_min": 8, "distance_km": 0.5},
                },
            ],
        }
    ],
}


def _bad_missing_field():
    d = copy.deepcopy(GOOD)
    del d["days"][0]["places"][0]["coordinates"]
    return d


def _bad_lat():
    d = copy.deepcopy(GOOD)
    d["days"][0]["places"][0]["coordinates"]["lat"] = 45.0
    return d


def _bad_time():
    d = copy.deepcopy(GOOD)
    d["days"][0]["places"][0]["start_time"] = "10am"
    return d


def _bad_extra_field():
    d = copy.deepcopy(GOOD)
    d["days"][0]["places"][0]["rating"] = 5
    return d


BAD_SAMPLES = [_bad_missing_field(), _bad_lat(), _bad_time(), _bad_extra_field()]


def test_good_sample_passes_both_validators():
    jsonschema.validate(GOOD, JSON_SCHEMA)
    plan = PilgrimagePlan.model_validate(GOOD)
    # 왕복: 모델 → JSON → 다시 JSON 스키마 통과 (직렬화가 스키마를 깨지 않는지)
    jsonschema.validate(json.loads(plan.model_dump_json(exclude_none=True)), JSON_SCHEMA)


@pytest.mark.parametrize("sample", BAD_SAMPLES, ids=["missing_field", "lat_out_of_range", "bad_time", "extra_field"])
def test_bad_samples_rejected_by_both(sample):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(sample, JSON_SCHEMA)
    with pytest.raises(ValidationError):
        PilgrimagePlan.model_validate(sample)


def test_required_fields_match_json_schema():
    """필수 필드·enum 목록이 두 스키마에서 같은지 확인한다."""
    pyd = PilgrimagePlan.model_json_schema()
    assert set(pyd["required"]) == set(JSON_SCHEMA["required"])
    assert set(pyd["$defs"]["Persona"]["enum"]) == set(JSON_SCHEMA["properties"]["persona"]["enum"])
    place_json = JSON_SCHEMA["properties"]["days"]["items"]["properties"]["places"]["items"]
    assert set(pyd["$defs"]["Place"]["required"]) == set(place_json["required"])
    assert set(pyd["$defs"]["PlaceType"]["enum"]) == set(place_json["properties"]["type"]["enum"])
