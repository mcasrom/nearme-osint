import requests
from src.collectors.base import BaseCollector
from src.models import Event


class CopernicusCollector(BaseCollector):
    name = "Copernicus EMS"
    interval_minutes = 60

    def collect(self):
        events = []
        # CEMS Rapid Mapping - active activations
        try:
            resp = requests.get(
                "https://emergency.copernicus.eu/mapping/activations-rapid/feed",
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json() if "json" in resp.headers.get("content-type", "") else {}
                for act in data.get("features", [])[:10]:
                    props = act.get("properties", {})
                    coords = act.get("geometry", {}).get("coordinates", [0, 0])
                    etype = "fire" if "fire" in props.get("title", "").lower() else "flood"
                    lat, lon = coords[1], coords[0] if len(coords) >= 2 else (0, 0)
                    if lat == 0 and lon == 0:
                        continue
                    events.append(Event(
                        source="copernicus",
                        source_id=f"cems_{props.get('id', '')}",
                        event_type=etype,
                        subtype=props.get("type", ""),
                        lat=lat, lon=lon,
                        radius_m=props.get("radius", 2000),
                        level="alert",
                        title=props.get("title", f"Activación CEMS: {etype}"),
                        description=props.get("description", ""),
                        country=props.get("country", ""),
                    ))
        except Exception as e:
            print(f"    [WARN] Copernicus EMS: {e}")

        # GWIS - Wildfire statistics (active fires)
        try:
            resp = requests.get(
                "https://gwis.jrc.ec.europa.eu/api/active-fires",
                params={"limit": 20}, timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for fire in data.get("features", [])[:10]:
                    props = fire.get("properties", {})
                    coords = fire.get("geometry", {}).get("coordinates", [0, 0])
                    lat, lon = coords[1], coords[0] if len(coords) >= 2 else (0, 0)
                    events.append(Event(
                        source="gwis",
                        source_id=f"gwis_{props.get('id', '')}",
                        event_type="fire",
                        subtype="active_fire",
                        lat=lat, lon=lon,
                        radius_m=props.get("radius", 1000),
                        level="alert",
                        title=f"Incendio activo: {props.get('name', '')}",
                        description=f"Potencia: {props.get('frp', '?')} MW",
                        country=props.get("country", ""),
                    ))
        except Exception as e:
            print(f"    [WARN] GWIS: {e}")

        return events
