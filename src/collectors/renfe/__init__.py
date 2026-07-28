import csv
import io
import requests
from google.transit import gtfs_realtime_pb2
from src.collectors.base import BaseCollector
from src.models import Event

STATIONS_CSV = "https://ssl.renfe.com/ftransit/Fichero_estaciones/estaciones.csv"


class RENFEDelaysCollector(BaseCollector):
    name = "RENFE"
    interval_minutes = 15

    def __init__(self):
        self._stations = None

    def _load_stations(self):
        if self._stations is not None:
            return self._stations
        self._stations = {}
        try:
            resp = requests.get(STATIONS_CSV, timeout=15, headers={"User-Agent": "NearMeOSINT/1.0"})
            if resp.status_code != 200:
                return self._stations
            reader = csv.DictReader(io.StringIO(resp.text), delimiter=";", quotechar='"')
            for row in reader:
                code = row.get("CODIGO", "").strip()
                try:
                    lat = float(row.get("LATITUD", "0").replace(",", "."))
                    lon = float(row.get("LONGITUD", "0").replace(",", "."))
                    name = row.get("DESCRIPCION", "")
                    if code and lat and lon:
                        self._stations[code] = (lat, lon, name)
                except (ValueError, TypeError):
                    pass
            print(f"    RENFE: {len(self._stations)} estaciones geolocalizadas")
        except Exception as e:
            print(f"    [WARN] RENFE estaciones: {e}")
        return self._stations

    def collect(self):
        events = []
        stations = self._load_stations()
        events.extend(self._parse_delays("https://gtfsrt.renfe.com/trip_updates.pb", "cercanias", stations))
        events.extend(self._parse_delays("https://gtfsrt.renfe.com/trip_updates_LD.pb", "alta_velocidad", stations))
        return events

    def _parse_delays(self, url, feed_type, stations):
        events = []
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "NearMeOSINT/1.0"})
            if resp.status_code != 200:
                print(f"    RENFE {feed_type}: HTTP {resp.status_code}")
                return events

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(resp.content)

            seen = set()
            for entity in feed.entity:
                if not entity.HasField('trip_update'):
                    continue
                tu = entity.trip_update
                trip_id = tu.trip.trip_id
                route_id = tu.trip.route_id

                for stu in tu.stop_time_update:
                    if not stu.HasField('arrival') or stu.arrival.delay <= 300:
                        continue

                    delay = stu.arrival.delay
                    stop_id = stu.stop_id
                    dedup_key = f"{trip_id}_{stop_id}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    if delay < 600:
                        continue

                    lat, lon, station_name = 0, 0, stop_id
                    if stop_id in stations:
                        lat, lon, station_name = stations[stop_id]

                    level = 'warning' if delay < 1800 else 'alert'
                    events.append(Event(
                        source="renfe",
                        source_id=f"renfe_{feed_type}_{trip_id}_{stop_id}",
                        event_type="train_delay",
                        subtype=feed_type,
                        lat=lat, lon=lon,
                        radius_m=5000,
                        level=level,
                        title=f"Retraso {feed_type}: +{delay//60}min ({station_name})",
                        description=f"Retraso: {delay//60} minutos. Ruta: {route_id}. Parada: {station_name} ({stop_id}). Trip: {trip_id}",
                        country="ES",
                    ))

            print(f"    RENFE {feed_type}: {len(events)} retrasos significativos")
        except Exception as e:
            print(f"    [WARN] RENFE {feed_type}: {e}")
        return events
