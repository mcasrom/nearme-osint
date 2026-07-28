import requests
from src.collectors.base import BaseCollector
from src.models import Event


class EarthquakesCollector(BaseCollector):
    name = "USGS Earthquakes"
    interval_minutes = 15

    def collect(self):
        events = []
        try:
            resp = requests.get(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
                timeout=15,
                headers={"User-Agent": "NearMeOSINT/1.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                for feat in data.get("features", [])[:30]:
                    props = feat.get("properties", {})
                    coords = feat.get("geometry", {}).get("coordinates", [0, 0, 0])
                    mag = props.get("mag", 0)
                    lat, lon, depth = coords[1], coords[0], coords[2] if len(coords) >= 3 else 0
                    place = props.get("place", "Desconocido")
                    level = "info"
                    if mag >= 5:
                        level = "alert"
                    elif mag >= 4:
                        level = "warning"
                    events.append(Event(
                        source="usgs",
                        source_id=f"usgs_{props.get('id', '')}",
                        event_type="earthquake",
                        subtype=f"mag_{mag}",
                        lat=lat, lon=lon,
                        radius_m=max(mag * 10000, 5000),
                        level=level,
                        title=f"Terremoto M{mag} - {place}",
                        description=f"Magnitud: {mag}. Profundidad: {depth} km. {place}",
                        country=props.get("net", ""),
                    ))
        except Exception as e:
            print(f"    [WARN] USGS: {e}")

        # NASA FIRMS - fuegos activos
        try:
            resp = requests.get(
                "https://firms.modaps.eosdis.nasa.gov/api/area/csv/10/0.0/0.0/1",
                timeout=15,
                headers={"User-Agent": "NearMeOSINT/1.0"}
            )
            if resp.status_code == 200 and resp.text.strip() != "":
                lines = resp.text.strip().split("\n")
                for line in lines[1:11]:
                    parts = line.split(",")
                    if len(parts) >= 10:
                        try:
                            lat = float(parts[0])
                            lon = float(parts[1])
                            frp = float(parts[9])
                            events.append(Event(
                                source="nasa_firms",
                                source_id=f"firms_{parts[3]}_{parts[4]}",
                                event_type="fire",
                                subtype="active_fire",
                                lat=lat, lon=lon,
                                radius_m=1000,
                                level="alert" if frp > 100 else "warning",
                                title=f"Incendio activo (FRP: {frp:.0f} MW)",
                                description=f"Potencia radiativa: {frp:.0f} MW. Coord: {lat:.2f}, {lon:.2f}",
                            ))
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            print(f"    [WARN] NASA FIRMS: {e}")

        return events
