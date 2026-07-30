import os
import httpx
from datetime import datetime
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event

AEMET_API_KEY = os.environ.get("AEMET_API_KEY", "")
AEMET_BASE = "https://opendata.aemet.es/opendata/api"


logger = get_logger("src.collectors.aemet")


class AEMETCollector(BaseCollector):
    name = "AEMET"
    source = "aemet"
    interval_minutes = 15

    async def collect(self):
        if not AEMET_API_KEY:
            logger.warning("AEMET_API_KEY no configurada, saltando AEMET")
            return []
        return await self._real_data()

    async def _aemet_get_data(self, endpoint):
        headers = {"api_key": AEMET_API_KEY}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{AEMET_BASE}/{endpoint}", headers=headers)
                if resp.status_code != 200:
                    return None
                body = resp.json()
                if body.get("estado") != 200:
                    return None
                data_url = body.get("datos")
                if not data_url:
                    return None
                data_resp = await client.get(data_url, headers=headers, timeout=20)
                if data_resp.status_code != 200:
                    return None
                text = data_resp.text.strip()
                if not text or text in ("[]", "null"):
                    return None
                return data_resp.json()
        except Exception as e:
            logger.warning("AEMET %s: %s", endpoint, e)
            return None

    async def _real_data(self):
        events = []
        events.extend(await self._fetch_observaciones())
        return events

    async def _fetch_observaciones(self):
        events = []
        data = await self._aemet_get_data("observacion/convencional/todas")
        if not data:
            logger.info("AEMET: no se pudieron obtener observaciones")
            return events
        items = data if isinstance(data, list) else []
        weather_count = 0
        alert_count = 0
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

                has_data = any(v is not None for v in (temp, temp_max, temp_min, wind, wind_max, prec))
                if not has_data:
                    continue

                desc_parts = []
                if temp is not None:
                    desc_parts.append(f"T: {temp}C")
                if temp_max is not None:
                    desc_parts.append(f"Tmax: {temp_max}C")
                if temp_min is not None:
                    desc_parts.append(f"Tmin: {temp_min}C")
                if wind is not None:
                    desc_parts.append(f"viento: {wind} km/h")
                if wind_max is not None:
                    desc_parts.append(f"racha: {wind_max} km/h")
                if prec is not None:
                    desc_parts.append(f"lluvia: {prec} mm")

                station_level = "info"
                alert_list = []

                if temp_max is not None:
                    t = float(temp_max)
                    if t >= 40:
                        station_level = "alert"
                        alert_list.append(("heatwave", "alert", f"Temperatura extrema: {t}C"))
                    elif t >= 35:
                        if station_level == "info": station_level = "warning"
                        alert_list.append(("heatwave", "warning", f"Altas temperaturas: {t}C"))
                if temp_min is not None:
                    t = float(temp_min)
                    if t <= -10:
                        station_level = "alert"
                        alert_list.append(("snow", "alert", f"Temperatura extrema baja: {t}C"))
                    elif t <= -5:
                        if station_level == "info": station_level = "warning"
                        alert_list.append(("snow", "warning", f"Bajas temperaturas: {t}C"))
                if wind_max is not None:
                    w = float(wind_max)
                    if w >= 80:
                        station_level = "alert"
                        alert_list.append(("wind", "alert", f"Racha maxima: {w} km/h"))
                    elif w >= 50:
                        if station_level == "info": station_level = "warning"
                        alert_list.append(("wind", "warning", f"Viento fuerte: {w} km/h"))
                if prec is not None:
                    p = float(prec)
                    if p >= 20:
                        station_level = "alert"
                        alert_list.append(("storm", "alert", f"Precipitacion intensa: {p} mm"))
                    elif p >= 8:
                        if station_level == "info": station_level = "warning"
                        alert_list.append(("storm", "warning", f"Precipitacion: {p} mm"))

                events.append(Event(
                    source="aemet",
                    source_id=f"aemet_{station}_weather",
                    event_type="weather",
                    subtype="observacion",
                    lat=lat, lon=lon,
                    radius_m=25000,
                    level=station_level,
                    title=f"{name}: {desc_parts[0] if desc_parts else 'sin datos'}"[:80],
                    description=" | ".join(desc_parts) + f" | Estacion: {station}",
                    country="ES",
                    region=name,
                ))
                weather_count += 1

                for event_type, level, desc in alert_list:
                    events.append(Event(
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
                    alert_count += 1

            except (ValueError, TypeError):
                pass

        logger.info("%d estaciones, %d weather, %d alertas", len(items), weather_count, alert_count)
        return events


