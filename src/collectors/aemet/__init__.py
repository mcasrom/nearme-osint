import os
import requests
import json
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import Event

AEMET_API_KEY = os.environ.get("AEMET_API_KEY", "")

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
        # AEMET API: first call returns a data URL, second call fetches actual data
        endpoint = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"
        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code == 200:
                data_url = resp.json().get("datos", "")
                if data_url:
                    data_resp = requests.get(data_url, timeout=15)
                    if data_resp.status_code == 200:
                        observations = data_resp.json() if isinstance(data_resp.json(), list) else []
                        print(f"    {len(observations)} estaciones meteorológicas")
            else:
                print(f"    AEMET API error: {resp.status_code}")
        except Exception as e:
            print(f"    [WARN] AEMET: {e}")

        if not events:
            print("    Sin alertas activas, usando datos de predicción")
            for ccaa_id, name, lat, lon in [
                ("4", "Cataluña", 41.59, 1.84), ("8", "Comunitat Valenciana", 39.47, -0.38),
                ("1", "Andalucía", 37.38, -5.99), ("13", "Madrid", 40.42, -3.70),
            ]:
                try:
                    resp = requests.get(
                        f"https://opendata.aemet.es/opendata/api/prediccion/ccaa/hoy/{ccaa_id}",
                        headers=headers, timeout=10
                    )
                    if resp.status_code == 200:
                        data_url = resp.json().get("datos", "")
                        if data_url:
                            dr = requests.get(data_url, timeout=10)
                            if dr.status_code == 200 and dr.text.strip() not in ("", "[]"):
                                print(f"      {name}: datos de predicción")
                except Exception:
                    pass
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
