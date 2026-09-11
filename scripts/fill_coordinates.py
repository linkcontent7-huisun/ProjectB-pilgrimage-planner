"""data/holy_sites.json의 lat/lng가 비어 있는 성지를 NCP Geocoding으로 채운다.

실행: PYTHONUTF8=1 .venv/Scripts/python scripts/fill_coordinates.py
.env에 NAVER_MAP_CLIENT_ID/SECRET이 있어야 한다. 이미 채워진 항목은 건너뛴다.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.tools.geocode import fetch_geocode  # noqa: E402

DATA = ROOT / "data" / "holy_sites.json"

if __name__ == "__main__":
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    filled = skipped = failed = 0
    for site in doc["sites"]:
        if site["lat"] is not None:
            skipped += 1
            continue
        result = fetch_geocode(site["address"])
        if "error" in result:
            failed += 1
            print(f"FAIL {site['name']}: {result}")
            continue
        site["lat"], site["lng"] = result["lat"], result["lng"]
        filled += 1
        print(f"OK   {site['name']}: {result['lat']}, {result['lng']}")
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"filled={filled} skipped={skipped} failed={failed}")
