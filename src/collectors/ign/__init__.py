import requests
from src.collectors.base import BaseCollector
from src.models import Event


class IGNCollector(BaseCollector):
    name = "IGN"
    interval_minutes = 15

    def collect(self):
        events = []
        try:
            resp = requests.get(
                "https://www.ign.es/web/ign/portal/ultimos-terremotos/-/ultimos-terremotos/ultimos.json",
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for eq in data.get("terremotos", [])[:20]:
                    lat = float(eq.get("latitud", 0))
                    lon = float(eq.get("longitud", 0))
                    mag = float(eq.get("magnitud", 0))
                    level = "info"
                    if mag >= 4.0:
                        level = "warning"
                    if mag >= 5.0:
                        level = "alert"
                    if mag >= 6.0:
                        level = "critical"
                    events.append(Event(
                        source="ign",
                        source_id=f"ign_{eq.get('id', '')}",
                        event_type="earthquake",
                        subtype=f"mag_{mag}",
                        lat=lat, lon=lon,
                        radius_m=max(mag * 10000, 5000),
                        level=level,
                        title=f"Terremoto M{mag} en {eq.get('localizacion', '')}",
                        description=f"Magnitud: {mag}. Profundidad: {eq.get('profundidad', '?')} km. {eq.get('localizacion', '')}",
                        country="ES",
                        region=eq.get("provincia", ""),
                        municipality=eq.get("municipio", ""),
                    ))
        except Exception as e:
            print(f"    [WARN] IGN terremotos: {e}")
        return events
