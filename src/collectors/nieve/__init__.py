import httpx
from datetime import datetime, timedelta, timezone

from src.collectors.base import BaseCollector
from src.config import (
    OPEN_METEO_URL,
    OPEN_METEO_REQUEST_TIMEOUT,
    NIEVE_TTL_HOURS,
    NIEVE_RADIUS_M,
)
from src.logging import get_logger
from src.models import Event

logger = get_logger("src.collectors.nieve")

# Estaciones de esquí principales de España (lat, lon, nombre, región)
SKI_RESORTS = [
    (42.69, 0.95, "Baqueira Beret", "Pirineos"),
    (42.76, -0.36, "Formigal-Panticosa", "Pirineos"),
    (42.79, -0.54, "Candanchú", "Pirineos"),
    (42.83, -0.50, "Astún", "Pirineos"),
    (42.57, 0.55, "Cerler", "Pirineos"),
    (42.34, 1.95, "La Molina", "Pirineos"),
    (42.36, 1.88, "Masella", "Pirineos"),
    (42.62, 1.08, "Espot Esquí", "Pirineos"),
    (42.46, 0.83, "Boí Taüll", "Pirineos"),
    (42.434, 1.204, "Port Ainé", "Pirineos"),
    (42.40, 2.15, "Vall de Núria", "Pirineos"),
    (40.78, -3.96, "Valdesquí", "Sistema Central"),
    (40.79, -4.00, "Navacerrada", "Sistema Central"),
    (41.24, -3.50, "La Pinilla", "Sistema Central"),
    (43.02, -4.38, "Alto Campoo", "Cantábrica"),
    (43.07, -5.33, "San Isidro", "Cantábrica"),
    (43.03, -5.75, "Valgrande-Pajares", "Cantábrica"),
    (42.98, -6.39, "Leitariegos", "Cantábrica"),
    (43.10, -5.47, "Fuentes de Invierno", "Cantábrica"),
    (40.43, -0.60, "Valdelinares", "Ibérico"),
    (40.10, -1.00, "Javalambre", "Ibérico"),
    (37.10, -3.40, "Sierra Nevada", "Sierra Nevada"),
]

# Códigos WMO que indican nieve o nieve engelante
SNOW_CODES = {
    71: "nieve débil",
    73: "nieve moderada",
    75: "nieve fuerte",
    77: "granos de nieve",
    85: "chubascos de nieve",
    86: "chubascos de nieve fuertes",
}

MIN_SNOWFALL_CM = 1.0  # cm/h para considerar nevada activa
MIN_SNOW_DEPTH_M = 0.05  # m de manto para considerar estación "con nieve"


def _slug(name: str) -> str:
    """source_id estable por estación (no cambia con la fecha -> no hincha la BD)."""
    s = name.lower().replace(" ", "-").replace("á", "a").replace("é", "e")
    s = s.replace("í", "i").replace("ó", "o").replace("ú", "u").replace(".", "")
    return s


class NieveCollector(BaseCollector):
    name = "Nieve / Estaciones de esquí"
    source = "nieve"
    interval_minutes = 60

    async def collect(self):
        events = []
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(hours=NIEVE_TTL_HOURS)).isoformat()

        async with httpx.AsyncClient(timeout=OPEN_METEO_REQUEST_TIMEOUT) as client:
            for lat, lon, nombre, region in SKI_RESORTS:
                ev = await self._fetch_estacion(client, lat, lon, nombre, region, expires)
                if ev:
                    events.append(ev)

        logger.info("%d estaciones de esquí con estado", len(events))
        return events

    async def _fetch_estacion(self, client, lat, lon, nombre, region, expires):
        try:
            resp = await client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,weather_code,snowfall,snow_depth,wind_speed_10m",
                    "hourly": "snowfall",
                    "forecast_days": 2,
                    "timezone": "Europe/Madrid",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("Nieve %s: %s", nombre, e)
            return None

        cur = data.get("current", {}) or {}
        temp = cur.get("temperature_2m")
        code = cur.get("weather_code")
        snowfall = cur.get("snowfall") or 0.0
        snow_depth = cur.get("snow_depth") or 0.0
        wind = cur.get("wind_speed_10m") or 0.0

        # Previsión de nevada en próximas 24h (suma)
        hourly = data.get("hourly", {}) or {}
        prev_sf = hourly.get("snowfall", []) or []
        prev24 = sum(prev_sf[:24]) or 0.0

        fenomeno = SNOW_CODES.get(code, "")
        nevando = code in SNOW_CODES and snowfall >= MIN_SNOWFALL_CM
        manto = snow_depth >= MIN_SNOW_DEPTH_M

        nivel = "info"
        if nevando:
            nivel = "alert"
        elif manto or prev24 >= MIN_SNOWFALL_CM:
            nivel = "warning"

        t = f"{temp:.0f}º" if temp is not None else "n/d"
        manto_cm = round(snow_depth * 100) if manto else 0

        # Título ESTABLE (sin fecha) -> event_history solo crece en cambios de estado
        if nevando:
            title = f"Nieva en {nombre}"
        elif manto:
            title = f"Nieve acumulada en {nombre}"
        else:
            title = f"Estación {nombre}"

        detalle = []
        if nevando and fenomeno:
            detalle.append(f"nevando ahora ({fenomeno})")
        if manto:
            detalle.append(f"manto {manto_cm} cm")
        elif temp is not None and temp <= 0:
            detalle.append("sin manto, bajo cero")
        if prev24 >= MIN_SNOWFALL_CM:
            detalle.append(f"{prev24:.1f} cm nieve últimas 24h")
        if temp is not None:
            detalle.append(f"temp {t}")
        if wind:
            detalle.append(f"viento {wind:.0f} km/h")

        desc = ", ".join(detalle) if detalle else (
            "Sin nieve y temperaturas positivas. "
            f"Temp {t}." if temp is not None else "Sin datos de nieve."
        )
        desc += " Datos Open-Meteo, actualizados cada hora."

        return Event(
            source="nieve",
            source_id=f"nieve_{_slug(nombre)}",
            event_type="snow",
            subtype="estacion_nieve",
            lat=lat,
            lon=lon,
            radius_m=NIEVE_RADIUS_M,
            level=nivel,
            title=title,
            description=desc,
            country="ES",
            region=region,
            municipality=nombre,
            expires_at=expires,
        )
