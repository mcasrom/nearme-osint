import requests
from src.collectors.base import BaseCollector
from src.models import Event


class DGTCollector(BaseCollector):
    name = "DGT"
    interval_minutes = 10

    def collect(self):
        events = []
        try:
            resp = requests.get(
                "https://www.dgt.es/incidencias-json/incidencias.json",
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for inc in data.get("incidencias", [])[:30]:
                    lat = float(inc.get("latitud", 0))
                    lon = float(inc.get("longitud", 0))
                    if lat == 0 and lon == 0:
                        continue
                    severity = inc.get("nivel", "").lower()
                    level = "info"
                    if severity in ("alta", "grave"):
                        level = "alert"
                    elif severity in ("media", "moderada"):
                        level = "warning"
                    etype = "road_incident"
                    tipo = inc.get("tipo", "").lower()
                    if "corte" in tipo:
                        etype = "road_closure"
                    events.append(Event(
                        source="dgt",
                        source_id=f"dgt_{inc.get('id', '')}",
                        event_type=etype,
                        subtype=inc.get("tipo", ""),
                        lat=lat, lon=lon,
                        radius_m=inc.get("radio", 500),
                        level=level,
                        title=inc.get("titulo", f"Incidencia DGT en carretera"),
                        description=inc.get("descripcion", f"Carretera: {inc.get('carretera', '')}. Causa: {inc.get('causa', '')}"),
                        country="ES",
                        region=inc.get("provincia", ""),
                        municipality=inc.get("municipio", ""),
                    ))
        except Exception as e:
            print(f"    [WARN] DGT: {e}")
        return events
