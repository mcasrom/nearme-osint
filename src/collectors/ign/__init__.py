import requests
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event


logger = get_logger("src.collectors.ign")


class IGNCollector(BaseCollector):
    name = "USGS (es)"
    interval_minutes = 15

    def collect(self):
        events = []
        try:
            resp = requests.get(
                "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&region=Spain&minmagnitude=1.5&orderby=time&limit=15",
                timeout=15,
                headers={"User-Agent": "NearMeOSINT/1.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                for feat in data.get("features", [])[:15]:
                    props = feat.get("properties", {})
                    coords = feat.get("geometry", {}).get("coordinates", [0, 0, 0])
                    mag = props.get("mag", 0)
                    lat, lon, depth = coords[1], coords[0], coords[2] if len(coords) >= 3 else 0
                    place = props.get("place", "España")
                    level = "info"
                    if mag >= 4:
                        level = "warning"
                    events.append(Event(
                        source="usgs_es",
                        source_id=f"usgses_{props.get('id', '')}",
                        event_type="earthquake",
                        subtype=f"mag_{mag}",
                        lat=lat, lon=lon,
                        radius_m=max(mag * 10000, 5000),
                        level=level,
                        title=f"Terremoto M{mag} - {place}",
                        description=f"Magnitud: {mag}. Profundidad: {depth} km. {place}",
                        country="ES",
                    ))
        except Exception as e:
            logger.warning("USGS: %s", e)
        return events
