import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.collectors.base import BaseCollector
from src.models import Event

OPENAQ_API_KEY = os.environ.get("OPENAQ_API_KEY", "")
OPENAQ_BASE = "https://api.openaq.org/v3"

PARAMETERS = {
    1: "pm10", 2: "pm25", 3: "o3",
    5: "no2", 4: "co", 6: "so2"
}

SPAIN_BBOX = {"lat_min": 35.8, "lat_max": 43.9, "lon_min": -10.5, "lon_max": 4.5}

THRESHOLDS = {
    "pm25": {"warning": 25, "alert": 55},
    "pm10": {"warning": 50, "alert": 100},
    "o3": {"warning": 100, "alert": 180},
    "no2": {"warning": 100, "alert": 200},
    "co": {"warning": 10000, "alert": 30000},
    "so2": {"warning": 100, "alert": 350},
}

class OpenAQCollector(BaseCollector):
    name = "OpenAQ"
    interval_minutes = 30

    def collect(self):
        if not OPENAQ_API_KEY:
            print("    [WARN] OPENAQ_API_KEY no configurada, saltando")
            return []
        return self._real_data()

    def _is_spain(self, lat, lon):
        try:
            lat, lon = float(lat), float(lon)
            return (SPAIN_BBOX["lat_min"] <= lat <= SPAIN_BBOX["lat_max"]
                    and SPAIN_BBOX["lon_min"] <= lon <= SPAIN_BBOX["lon_max"])
        except (ValueError, TypeError):
            return False

    def _fetch_param_latest(self, param_id):
        param_name = PARAMETERS[param_id]
        events = []
        seen_locations = set()
        try:
            for page in range(1, 4):
                resp = requests.get(
                    f"{OPENAQ_BASE}/parameters/{param_id}/latest",
                    params={"limit": 1000, "page": page},
                    headers={"X-API-Key": OPENAQ_API_KEY},
                    timeout=15
                )
                if resp.status_code != 200:
                    if page == 1:
                        print(f"    [WARN] OpenAQ {param_name}: HTTP {resp.status_code}")
                    break
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break
                for r in results:
                    lat = r.get("coordinates", {}).get("latitude")
                    lon = r.get("coordinates", {}).get("longitude")
                    val = r.get("value")
                    loc_id = r.get("locationsId")
                    if not self._is_spain(lat, lon) or val is None or loc_id in seen_locations:
                        continue
                    seen_locations.add(loc_id)
                    val = float(val)
                    level = "info"
                    thr = THRESHOLDS.get(param_name, {})
                    if val >= thr.get("alert", 999999):
                        level = "alert"
                    elif val >= thr.get("warning", 999999):
                        level = "warning"
                    events.append(Event(
                        source="openaq",
                        source_id=f"openaq_{loc_id}_{param_name}",
                        event_type="air_quality",
                        subtype=param_name,
                        lat=float(lat),
                        lon=float(lon),
                        radius_m=10000,
                        level=level,
                        title=f"{param_name.upper()}: {val} µg/m³",
                        description=f"{param_name.upper()}: {val} µg/m³ (estación {loc_id})",
                        country="ES",
                    ))
            print(f"    OpenAQ {param_name}: {len(seen_locations)} ES, {len([e for e in events if e.level in ('alert','warning')])} alertas")
        except Exception as e:
            print(f"    [WARN] OpenAQ {param_name}: {e}")
        return events

    def _real_data(self):
        all_events = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(self._fetch_param_latest, pid): pname for pid, pname in PARAMETERS.items()}
            for f in as_completed(futs):
                all_events.extend(f.result())
        print(f"    OpenAQ total: {len(all_events)} eventos")
        return all_events
