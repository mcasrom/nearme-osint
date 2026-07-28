import os
import requests
from src.collectors.base import BaseCollector
from src.models import Event

FIRMS_KEY = os.environ.get("NASA_FIRMS_KEY", "")


class EarthquakesCollector(BaseCollector):
    name = "USGS + FIRMS"
    interval_minutes = 15

    def collect(self):
        events = []
        events.extend(self._earthquakes())
        if FIRMS_KEY:
            events.extend(self._firms_fires())
        else:
            print("    [WARN] NASA_FIRMS_KEY no configurada, saltando incendios satelitales")
        return events

    def _earthquakes(self):
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
                    lat = coords[1]
                    lon = coords[0]
                    depth = coords[2] if len(coords) >= 3 else 0
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
                print(f"    {len(events)} terremotos USGS (ultimas 24h)")
        except Exception as e:
            print(f"    [WARN] USGS: {e}")
        return events

    def _firms_fires(self):
        events = []
        try:
            # Spain bounding box: SW(35.9,-9.3) NE(43.8,4.3)
            url = (
                f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
                f"{FIRMS_KEY}/VIIRS_SNPP_NRT/-9.3,35.9,4.3,43.8,1"
            )
            resp = requests.get(url, timeout=20, headers={"User-Agent": "NearMeOSINT/1.0"})
            if resp.status_code != 200:
                print(f"    NASA FIRMS: HTTP {resp.status_code}")
                return events
            text = resp.text.strip()
            if not text:
                return events
            lines = text.split("\n")
            if len(lines) < 2:
                return events
            headers_line = lines[0].split(",")
            for line in lines[1:20]:
                parts = line.split(",")
                if len(parts) < len(headers_line):
                    continue
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    frp = float(parts[8]) if len(parts) > 8 else 0
                    bright = float(parts[9]) if len(parts) > 9 else 0
                    satellite = parts[11] if len(parts) > 11 else "VIIRS"
                    confidence = parts[12] if len(parts) > 12 else ""
                    level = "alert" if frp > 100 or bright > 330 else "warning"
                    events.append(Event(
                        source="nasa_firms",
                        source_id=f"firms_{lat}_{lon}_{frp}",
                        event_type="fire",
                        subtype="satellite_fire",
                        lat=lat, lon=lon,
                        radius_m=1500,
                        level=level,
                        title=f"Incendio activo ({satellite}) FRP:{frp:.0f}MW",
                        description=f"FRP: {frp:.0f} MW. Brillo: {bright:.0f}K. Confianza: {confidence}. Coord: {lat:.3f},{lon:.3f}",
                        country="ES",
                    ))
                except (ValueError, IndexError):
                    pass
            print(f"    {len(events)} incendios satelitales FIRMS")
        except Exception as e:
            print(f"    [WARN] NASA FIRMS: {e}")
        return events
