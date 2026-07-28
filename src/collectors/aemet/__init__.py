import os
import requests
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import Event

AEMET_API_KEY = os.environ.get("AEMET_API_KEY", "")
AEMET_BASE = "https://opendata.aemet.es/opendata/api"


class AEMETCollector(BaseCollector):
    name = "AEMET"
    interval_minutes = 15

    def collect(self):
        if not AEMET_API_KEY:
            print("    [WARN] AEMET_API_KEY no configurada, saltando AEMET")
            return []
        return self._real_data()

    def _aemet_get_data(self, endpoint):
        headers = {"api_key": AEMET_API_KEY}
        try:
            resp = requests.get(f"{AEMET_BASE}/{endpoint}", headers=headers, timeout=15)
            if resp.status_code != 200:
                return None
            body = resp.json()
            if body.get("estado") != 200:
                return None
            data_url = body.get("datos")
            if not data_url:
                return None
            data_resp = requests.get(data_url, headers=headers, timeout=20)
            if data_resp.status_code != 200:
                return None
            text = data_resp.text.strip()
            if not text or text in ("[]", "null"):
                return None
            return data_resp.json()
        except Exception as e:
            print(f"    [WARN] AEMET {endpoint}: {e}")
            return None

    def _real_data(self):
        events = []
        events.extend(self._fetch_observaciones())
        return events

    def _fetch_observaciones(self):
        events = []
        data = self._aemet_get_data("observacion/convencional/todas")
        if not data:
            print("    AEMET: no se pudieron obtener observaciones")
            return events
        items = data if isinstance(data, list) else []
        alerts = []
        for obs in items:
            try:
                lat = obs.get("lat")
                lon = obs.get("lon")
                if lat is None or lon is None:
                    continue
                lat = float(lat)
                lon = float(lon)
                name = obs.get("ubi", obs.get("idema", ""))
                station = obs.get("idema", "")

                temp = obs.get("ta")
                temp_max = obs.get("tamax")
                temp_min = obs.get("tamin")
                wind = obs.get("vv")
                wind_max = obs.get("vmax")
                prec = obs.get("prec")

                detected = []

                if temp_max is not None:
                    t = float(temp_max)
                    if t >= 40:
                        detected.append(("heatwave", "alert", f"Temperatura extrema: {t}C"))
                    elif t >= 35:
                        detected.append(("heatwave", "warning", f"Altas temperaturas: {t}C"))

                if temp_min is not None:
                    t = float(temp_min)
                    if t <= -10:
                        detected.append(("snow", "alert", f"Temperatura extrema baja: {t}C"))
                    elif t <= -5:
                        detected.append(("snow", "warning", f"Bajas temperaturas: {t}C"))

                if wind_max is not None:
                    w = float(wind_max)
                    if w >= 80:
                        detected.append(("wind", "alert", f"Racha maxima: {w} km/h"))
                    elif w >= 50:
                        detected.append(("wind", "warning", f"Viento fuerte: {w} km/h"))

                if prec is not None:
                    p = float(prec)
                    if p >= 20:
                        detected.append(("storm", "alert", f"Precipitacion intensa: {p} mm"))
                    elif p >= 8:
                        detected.append(("storm", "warning", f"Precipitacion: {p} mm"))

                for event_type, level, desc in detected:
                    alerts.append(Event(
                        source="aemet",
                        source_id=f"aemet_{station}_{event_type}",
                        event_type=event_type,
                        subtype="observacion",
                        lat=lat, lon=lon,
                        radius_m=25000,
                        level=level,
                        title=f"{event_type} en {name}",
                        description=f"{desc}. Estacion: {station}",
                        country="ES",
                        region=name,
                    ))
            except (ValueError, TypeError):
                pass
        events.extend(alerts)
        print(f"    {len(items)} estaciones, {len(alerts)} con alertas")
        return events


