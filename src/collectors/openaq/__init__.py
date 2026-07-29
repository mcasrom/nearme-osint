import os
import httpx
from src.collectors.base import BaseCollector
from src.logging import get_logger
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

logger = get_logger("src.collectors.openaq")


class OpenAQCollector(BaseCollector):
    name = "OpenAQ"
    source = "openaq"
    interval_minutes = 30

    async def collect(self):
        if not OPENAQ_API_KEY:
            logger.warning("OPENAQ_API_KEY no configurada, saltando")
            return []
        return await self._real_data()

    def _is_spain(self, lat, lon):
        try:
            lat, lon = float(lat), float(lon)
            return (SPAIN_BBOX["lat_min"] <= lat <= SPAIN_BBOX["lat_max"]
                    and SPAIN_BBOX["lon_min"] <= lon <= SPAIN_BBOX["lon_max"])
        except (ValueError, TypeError):
            return False

    async def _fetch_param_latest(self, param_id):
        param_name = PARAMETERS[param_id]
        events = []
        seen_locations = set()
        try:
            async with httpx.AsyncClient(timeout=15, headers={"X-API-Key": OPENAQ_API_KEY}) as client:
                for page in range(1, 4):
                    resp = await client.get(
                        f"{OPENAQ_BASE}/parameters/{param_id}/latest",
                        params={"limit": 1000, "page": page},
                    )
                    if resp.status_code != 200:
                        if page == 1:
                            logger.warning("OpenAQ %s: HTTP %s", param_name, resp.status_code)
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
            logger.info("OpenAQ %s: %d ES, %d alertas", param_name, len(seen_locations), len([e for e in events if e.level in ('alert','warning')]))
        except Exception as e:
            logger.warning("OpenAQ %s: %s", param_name, e)
        return events

    async def _real_data(self):
        all_events = []
        results = await asyncio.gather(*[
            self._fetch_param_latest(pid) for pid in PARAMETERS
        ])
        for param_events in results:
            all_events.extend(param_events)
        logger.info("OpenAQ total: %d eventos", len(all_events))
        return all_events
