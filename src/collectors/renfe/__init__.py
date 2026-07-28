import requests
from google.transit import gtfs_realtime_pb2
from src.collectors.base import BaseCollector
from src.models import Event


class RENFEDelaysCollector(BaseCollector):
    name = "RENFE"
    interval_minutes = 15

    def collect(self):
        events = []
        events.extend(self._cercanias_delays())
        events.extend(self._av_ld_delays())
        return events

    def _parse_delays(self, url, feed_type):
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

                    level = 'warning' if delay < 1800 else 'alert'
                    events.append(Event(
                        source="renfe",
                        source_id=f"renfe_{feed_type}_{trip_id}_{stop_id}",
                        event_type="train_delay",
                        subtype=feed_type,
                        lat=0, lon=0,
                        radius_m=5000,
                        level=level,
                        title=f"Retraso {feed_type}: {delay//60}min (trip {trip_id})",
                        description=f"Retraso: {delay//60} minutos. Ruta: {route_id}. Parada: {stop_id}",
                        country="ES",
                    ))

            print(f"    RENFE {feed_type}: {len(events)} retrasos significativos")
        except Exception as e:
            print(f"    [WARN] RENFE {feed_type}: {e}")
        return events

    def _cercanias_delays(self):
        return self._parse_delays("https://gtfsrt.renfe.com/trip_updates.pb", "cercanias")

    def _av_ld_delays(self):
        return self._parse_delays("https://gtfsrt.renfe.com/trip_updates_LD.pb", "alta_velocidad")