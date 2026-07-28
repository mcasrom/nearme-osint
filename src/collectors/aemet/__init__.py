import requests
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import Event

AEMET_API_KEY = ""

LEVEL_MAP = {"verde": "info", "amarillo": "warning", "naranja": "alert", "rojo": "critical"}
PHENOMENON_MAP = {
    "lluvias": "storm", "tormentas": "storm", "nevadas": "snow",
    "viento": "wind", "costeros": "storm", "ola de calor": "heatwave",
    "ola de frío": "snow", "polvo": "air_quality",
}


class AEMETCollector(BaseCollector):
    name = "AEMET"
    interval_minutes = 15

    def collect(self):
        if not AEMET_API_KEY:
            print("    [WARN] AEMET_API_KEY no configurada, usando datos simulados")
            return self._mock_data()
        return self._real_data()

    def _real_data(self):
        headers = {"api_key": AEMET_API_KEY}
        events = []
        for area in ["spain"]:
            try:
                resp = requests.get(
                    f"https://opendata.aemet.es/opendata/api/avisos/lista/{area}/hoy",
                    headers=headers, timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for alert in data.get("avisos", []):
                        level = LEVEL_MAP.get(alert.get("nivel", "").lower(), "info")
                        phenom = alert.get("fenomeno", "").lower()
                        etype = "warning"
                        for k, v in PHENOMENON_MAP.items():
                            if k in phenom:
                                etype = v
                                break
                        events.append(Event(
                            source="aemet",
                            source_id=f"aemet_{alert.get('id', '')}",
                            event_type=etype,
                            subtype=phenom,
                            lat=alert.get("lat", 40.0),
                            lon=alert.get("lon", -3.0),
                            radius_m=alert.get("radio", 50000),
                            level=level,
                            title=alert.get("titulo", f"Aviso {alert.get('nivel', '')}"),
                            description=alert.get("descripcion", ""),
                            country="ES",
                            region=alert.get("zona", ""),
                            municipality=alert.get("municipio", ""),
                        ))
            except Exception as e:
                print(f"    [WARN] AEMET: {e}")
        return events

    def _mock_data(self):
        return [
            Event(source="aemet", source_id="aemet_mock_01", event_type="storm",
                  subtype="tormentas", lat=40.42, lon=-3.70, radius_m=50000,
                  level="alert", title="Aviso naranja por tormentas",
                  description="Precipitación acumulada en 1h: 30 l/m2. Probabilidad: 80%",
                  country="ES", region="Madrid"),
            Event(source="aemet", source_id="aemet_mock_02", event_type="heatwave",
                  subtype="ola de calor", lat=37.38, lon=-5.99, radius_m=40000,
                  level="warning", title="Aviso amarillo por altas temperaturas",
                  description="Temperatura máxima: 38°C. Umbral: 36°C.",
                  country="ES", region="Sevilla"),
        ]
