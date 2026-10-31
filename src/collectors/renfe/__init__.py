import csv
import io
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from google.transit import gtfs_realtime_pb2
from src.config import (RENFE_FEED_URLS, RENFE_MIN_DELAY_SECONDS, RENFE_RADIUS_M,
                        RENFE_STATIONS_CSV_URL, RENFE_USER_AGENT, RENFE_WARNING_DELAY_SECONDS)
from src.db import save_renfe_observations
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event

logger = get_logger("src.collectors.renfe")


class RENFEDelaysCollector(BaseCollector):
    name = "RENFE"
    source = "renfe"
    interval_minutes = 15

    def __init__(self):
        self._stations = None
        self._stations_ts = 0.0

    def _service_date(self, trip_id):
        m = re.search(r"(\d{4}-\d{2}-\d{2})$", trip_id or "")
        return m.group(1) if m else None

    async def _load_stations(self):
        if self._stations is not None and time.monotonic() - self._stations_ts < 6 * 3600:
            return self._stations
        parsed = {}
        try:
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": RENFE_USER_AGENT}) as client:
                resp = await client.get(RENFE_STATIONS_CSV_URL)
            if resp.status_code != 200:
                logger.warning("RENFE estaciones: HTTP %s", resp.status_code)
                return self._stations or {}
            reader = csv.DictReader(io.StringIO(resp.text), delimiter=";", quotechar='"')
            for row in reader:
                code = row.get("CODIGO", "").strip()
                try:
                    lat = float(row.get("LATITUD", "0").replace(",", "."))
                    lon = float(row.get("LONGITUD", "0").replace(",", "."))
                    name = row.get("DESCRIPCION", "")
                    if code and lat and lon:
                        parsed[code] = (lat, lon, name)
                except (ValueError, TypeError):
                    pass
            if parsed:
                self._stations = parsed
                self._stations_ts = time.monotonic()
                logger.info("RENFE: %d estaciones geolocalizadas", len(parsed))
            else:
                logger.warning("RENFE estaciones: descarga vacía; se conserva la caché anterior")
        except Exception as e:
            logger.warning("RENFE estaciones: %s", e)
        return self._stations or {}

    async def collect(self):
        events = []
        stations = await self._load_stations()
        for url, feed_type in zip(RENFE_FEED_URLS, ("cercanias", "alta_velocidad")):
            events.extend(await self._parse_delays(url, feed_type, stations))
        return events

    async def _parse_delays(self, url, feed_type, stations):
        events = []
        observations = []
        try:
            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": RENFE_USER_AGENT}) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning("RENFE %s: HTTP %s", feed_type, resp.status_code)
                return events

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(resp.content)

            seen = set()
            trips_all = set()
            unresolved = 0
            for entity in feed.entity:
                if not entity.HasField('trip_update'):
                    continue
                tu = entity.trip_update
                trip_id = tu.trip.trip_id
                route_id = tu.trip.route_id

                sd = self._service_date(trip_id)
                today = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
                if sd and sd != today:
                    continue

                trips_all.add(trip_id)

                for stu in tu.stop_time_update:
                    sched = stu.schedule_relationship
                    evt = stu.arrival if stu.HasField('arrival') else (stu.departure if stu.HasField('departure') else None)
                    if sched in (1, 2):
                        observations.append((datetime.now(timezone.utc), trip_id, route_id, stu.stop_id, feed_type, 0, sched, False, None, stu.stop_id))
                        continue
                    if evt is None:
                        continue
                    delay = evt.delay
                    raw_t = evt.time if evt.time else None
                    pred = datetime.fromtimestamp(raw_t, timezone.utc) if raw_t else None
                    is_forecast = bool(pred and pred > datetime.now(timezone.utc) + timedelta(minutes=1))
                    if delay < RENFE_MIN_DELAY_SECONDS:
                        continue
                    stop_id = stu.stop_id
                    dedup_key = f"{trip_id}_{stop_id}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    if stop_id not in stations:
                        unresolved += 1
                        observations.append((datetime.now(timezone.utc), trip_id, route_id, stop_id, feed_type, delay, sched, is_forecast, pred, stop_id))
                        continue
                    lat, lon, station_name = stations[stop_id]
                    observations.append((datetime.now(timezone.utc), trip_id, route_id, stop_id, feed_type, delay, sched, is_forecast, pred, station_name))

                    level = 'warning' if delay < RENFE_WARNING_DELAY_SECONDS else 'alert'
                    events.append(Event(
                        source="renfe",
                        source_id=f"renfe_{feed_type}_{trip_id}_{stop_id}",
                        event_type="train_delay",
                        subtype=feed_type,
                        lat=lat, lon=lon,
                        radius_m=RENFE_RADIUS_M,
                        level=level,
                        title=f"Retraso {feed_type}: +{delay//60}min ({station_name})",
                        description=f"Retraso: {delay//60} minutos. Ruta: {route_id}. Parada: {station_name} ({stop_id}). Trip: {trip_id}",
                        country="ES",
                    ))

            logger.info("RENFE %s: %d retrasos significativos · %d paradas sin geolocalizar", feed_type, len(events), unresolved)
            try:
                save_renfe_observations(observations)
            except Exception as e:
                logger.warning("RENFE %s: observaciones %s", feed_type, e)
            # Denominador: registrar TODOS los trip_id vistos hoy (con o sin
            # retraso) para poder calcular el % de trenes con retraso.
            try:
                from src.db import record_trips_seen
                hoy = datetime.now(ZoneInfo("Europe/Madrid")).date()
                record_trips_seen(hoy, feed_type, trips_all)
                logger.info("RENFE %s: %d trenes vistos (denominador)", feed_type, len(trips_all))
            except Exception as e:
                logger.warning("RENFE %s: record_trips_seen %s", feed_type, e)
        except Exception as e:
            logger.warning("RENFE %s: %s", feed_type, e)
        return events
