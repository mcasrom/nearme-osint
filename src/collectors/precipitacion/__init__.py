import httpx
from datetime import datetime, timedelta, timezone

from src.collectors.base import BaseCollector
from src.config import (
    OPEN_METEO_URL,
    OPEN_METEO_REQUEST_TIMEOUT,
)
from src.collectors.uv import SPAIN_CITIES
from src.logging import get_logger
from src.models import Event

logger = get_logger("src.collectors.precipitacion")

PRECIP_RADIUS_M = 30000
PRECIP_TTL_HOURS = 3

# Códigos WMO para descripción del fenómeno
WMO_LABEL = {
    0: "despejado", 1: "poco nuboso", 2: "parcialmente nuboso", 3: "nuboso",
    45: "niebla", 48: "niebla engelante",
    51: "llovizna débil", 53: "llovizna", 55: "llovizna densa",
    61: "lluvia débil", 63: "lluvia moderada", 65: "lluvia fuerte",
    66: "lluvia helada", 67: "lluvia helada",
    71: "nieve débil", 73: "nieve", 75: "nevada fuerte",
    80: "chubascos débiles", 81: "chubascos", 82: "chubascos fuertes",
    95: "tormenta", 96: "tormenta con granizo", 99: "tormenta fuerte con granizo",
}

MIN_PRECIP = 0.5  # mm/h por debajo no se genera evento


class PrecipitacionCollector(BaseCollector):
    name = "Precipitación (Open-Meteo)"
    source = "precipitacion"
    interval_minutes = 30

    async def collect(self):
        events = []
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(hours=PRECIP_TTL_HOURS)).isoformat()

        for i in range(0, len(SPAIN_CITIES), 50):
            chunk = SPAIN_CITIES[i:i + 50]
            lats = ",".join(f"{lat:.4f}" for lat, _, _ in chunk)
            lons = ",".join(f"{lon:.4f}" for _, lon, _ in chunk)

            try:
                async with httpx.AsyncClient(timeout=OPEN_METEO_REQUEST_TIMEOUT) as client:
                    resp = await client.get(
                        OPEN_METEO_URL,
                        params={
                            "latitude": lats,
                            "longitude": lons,
                            "current": "precipitation,weather_code,temperature_2m",
                            "timezone": "Europe/Madrid",
                        },
                    )
                    resp.raise_for_status()
                    results = resp.json()
            except Exception as e:
                logger.warning("Precipitación Open-Meteo: %s", e)
                continue

            if not isinstance(results, list):
                continue

            for j, res in enumerate(results):
                if j >= len(chunk):
                    break
                lat, lon, name = chunk[j]
                cur = res.get("current", {}) or {}
                precip = cur.get("precipitation") or 0.0
                if precip < MIN_PRECIP:
                    continue
                code = cur.get("weather_code")
                label = WMO_LABEL.get(code, "—")
                temp = cur.get("temperature_2m")

                if precip >= 10:
                    level = "alert"
                elif precip >= 2:
                    level = "warning"
                else:
                    level = "info"

                if precip >= 10:
                    ph = "lluvia fuerte"
                elif precip >= 2:
                    ph = "lluvia moderada"
                else:
                    ph = "lluvia débil"

                t = f"{temp:.0f}" if temp is not None else "n/d"
                events.append(Event(
                    source="precipitacion",
                    source_id=f"precip_{name.lower().replace(' ', '_')}",
                    event_type="weather",
                    subtype="precipitacion",
                    lat=lat,
                    lon=lon,
                    radius_m=PRECIP_RADIUS_M,
                    level=level,
                    title=f"Lluvia en {name}: {precip:.1f} mm/h",
                    description=(
                        f"Precipitación actual en {name}: {precip:.1f} mm/h "
                        f"({ph}). Temperatura: {t} ºC. Fenómeno: {label}. "
                        f"Datos Open-Meteo, actualizados cada 30 min."
                    ),
                    country="España",
                    region="",
                    municipality=name,
                    expires_at=expires,
                ))

        logger.info("%d ciudades con lluvia activa", len(events))
        return events
