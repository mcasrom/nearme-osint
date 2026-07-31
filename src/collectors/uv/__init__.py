import httpx
from datetime import datetime, timedelta, timezone
from src.collectors.base import BaseCollector
from src.config import (
    OPEN_METEO_URL, OPEN_METEO_REQUEST_TIMEOUT, OPEN_METEO_TTL_HOURS,
    OPEN_METEO_UV_CRITICAL, OPEN_METEO_UV_ALERT, OPEN_METEO_UV_WARNING,
    OPEN_METEO_UV_RADIUS_M,
)
from src.logging import get_logger
from src.models import Event

# 50 capitales de provincia + Ceuta/Melilla (lat, lon, nombre)
SPAIN_CITIES = [
    (40.4168, -3.7038, "Madrid"), (41.3851, 2.1734, "Barcelona"),
    (39.4699, -0.3763, "Valencia"), (37.3891, -5.9845, "Sevilla"),
    (43.2630, -2.9350, "Bilbao"), (43.3619, -5.8494, "Oviedo"),
    (37.1773, -3.5986, "Granada"), (39.8628, -4.0273, "Toledo"),
    (41.6523, -4.7245, "Valladolid"), (42.6050, -5.5700, "León"),
    (43.4623, -3.8099, "Santander"), (36.7213, -4.4214, "Málaga"),
    (38.3452, -0.4810, "Alicante"), (41.6488, -0.8891, "Zaragoza"),
    (42.8782, -8.5448, "Santiago"), (40.3400, -1.1069, "Teruel"),
    (42.8169, -1.6432, "Pamplona"), (41.1189, 1.2445, "Tarragona"),
    (36.5297, -6.2926, "Cádiz"), (36.8340, -2.4637, "Almería"),
    (37.9802, -1.1302, "Murcia"), (40.9638, -5.6639, "Salamanca"),
    (42.8587, -2.7248, "Vitoria"), (41.6184, 0.6145, "Lleida"),
    (39.4865, -6.3724, "Cáceres"), (38.8786, -6.9703, "Badajoz"),
    (38.9847, -1.8583, "Albacete"), (37.2620, -6.9450, "Huelva"),
    (37.7733, -3.7890, "Jaén"), (40.9438, -4.1248, "Segovia"),
    (41.8056, -3.7369, "Soria"), (42.3344, -3.6998, "Burgos"),
    (40.3180, -1.9378, "Cuenca"), (41.5274, -5.9943, "Zamora"),
    (39.5728, 2.6554, "Palma"), (28.2916, -16.6291, "Santa Cruz"),
    (28.1236, -15.4366, "Las Palmas"), (40.6566, -4.7004, "Ávila"),
    (40.6333, -3.1667, "Guadalajara"), (38.9861, -3.9292, "Ciudad Real"),
    (37.8882, -4.7794, "Córdoba"), (39.9864, -0.0514, "Castellón"),
    (41.9794, 2.8214, "Girona"), (42.1398, -0.4089, "Huesca"),
    (43.3183, -1.9812, "San Sebastián"), (42.4650, -2.4499, "Logroño"),
    (43.0099, -7.5561, "Lugo"), (42.3358, -7.8639, "Ourense"),
    (42.0096, -4.5311, "Palencia"), (42.4310, -8.6444, "Pontevedra"),
    (35.8883, -5.3162, "Ceuta"), (35.2937, -2.9383, "Melilla"),
]

CITIES = SPAIN_CITIES

logger = get_logger("src.collectors.uv")


class UVCollector(BaseCollector):
    name = "UV (Open-Meteo)"
    source = "open_meteo"
    interval_minutes = 60

    async def collect(self):
        events = []
        chunk_size = 50
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(hours=OPEN_METEO_TTL_HOURS)).isoformat()

        for i in range(0, len(CITIES), chunk_size):
            chunk = CITIES[i:i + chunk_size]
            lats = ",".join(f"{lat:.4f}" for lat, _, _ in chunk)
            lons = ",".join(f"{lon:.4f}" for _, lon, _ in chunk)

            try:
                async with httpx.AsyncClient(timeout=OPEN_METEO_REQUEST_TIMEOUT) as client:
                    resp = await client.get(
                        OPEN_METEO_URL,
                        params={
                            "latitude": lats,
                            "longitude": lons,
                            "daily": "uv_index_max",
                            "timezone": "Europe/Madrid",
                        },
                    )
                    resp.raise_for_status()
                    results = resp.json()
            except Exception as e:
                logger.warning("UV Open-Meteo: %s", e)
                continue

            if not isinstance(results, list):
                continue

            for j, res in enumerate(results):
                if j >= len(chunk):
                    break
                lat, lon, name = chunk[j]
                daily = res.get("daily", {})
                uv_values = daily.get("uv_index_max", [])
                if not uv_values:
                    continue
                uv_today = uv_values[0]
                if uv_today is None:
                    continue

                if uv_today >= OPEN_METEO_UV_CRITICAL:
                    level = "critical"
                elif uv_today >= OPEN_METEO_UV_ALERT:
                    level = "alert"
                elif uv_today >= OPEN_METEO_UV_WARNING:
                    level = "warning"
                else:
                    level = "info"

                events.append(Event(
                    source="open_meteo",
                    source_id=f"uv_{name.lower().replace(' ', '_')}",
                    event_type="radiation",
                    subtype="uv_index",
                    lat=lat,
                    lon=lon,
                    radius_m=OPEN_METEO_UV_RADIUS_M,
                    level=level,
                    title=f"Índice UV: {uv_today:.0f} — {name}",
                    description=(
                        f"Radiación UV máxima hoy en {name}: {uv_today:.0f} "
                        f"(nivel {level}). Protección solar recomendada "
                        f"según OMS: {uv_today:.0f}"
                    ),
                    country="España",
                    region="",
                    municipality=name,
                    expires_at=expires,
                ))

        logger.info("%d ciudades UV recolectadas", len(events))
        return events
