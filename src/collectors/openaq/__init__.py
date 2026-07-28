import requests
from src.collectors.base import BaseCollector
from src.models import Event

MAJOR_CITIES = [
    {"name": "Madrid", "lat": 40.42, "lon": -3.70},
    {"name": "Barcelona", "lat": 41.39, "lon": 2.17},
    {"name": "Valencia", "lat": 39.47, "lon": -0.38},
    {"name": "Sevilla", "lat": 37.38, "lon": -5.99},
    {"name": "Bilbao", "lat": 43.26, "lon": -2.94},
    {"name": "Zaragoza", "lat": 41.65, "lon": -0.88},
    {"name": "Málaga", "lat": 36.72, "lon": -4.42},
    {"name": "Murcia", "lat": 37.98, "lon": -1.13},
    {"name": "Palma", "lat": 39.57, "lon": 2.65},
    {"name": "Las Palmas", "lat": 28.12, "lon": -15.43},
]


class OpenAQCollector(BaseCollector):
    name = "OpenAQ"
    interval_minutes = 30

    def collect(self):
        events = []
        for city in MAJOR_CITIES:
            try:
                resp = requests.get(
                    "https://api.openaq.org/v2/latest",
                    params={"coordinates": f"{city['lat']},{city['lon']}", "radius": 25000, "limit": 3},
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", [])[:1]:
                        for param in r.get("measurements", [])[:3]:
                            val = param.get("value", 0)
                            param_name = param.get("parameter", "")
                            unit = param.get("unit", "")
                            level = "info"
                            if param_name == "pm25" and val > 35:
                                level = "warning"
                            elif param_name == "pm25" and val > 55:
                                level = "alert"
                            elif param_name == "pm10" and val > 50:
                                level = "warning"
                            elif param_name == "pm10" and val > 100:
                                level = "alert"
                            events.append(Event(
                                source="openaq",
                                source_id=f"openaq_{r.get('location', '')}_{param_name}",
                                event_type="air_quality",
                                subtype=param_name,
                                lat=city["lat"],
                                lon=city["lon"],
                                radius_m=10000,
                                level=level,
                                title=f"Calidad del aire {city['name']}: {param_name}={val} {unit}",
                                description=f"{param_name}: {val} {unit} en {city['name']}. Estación: {r.get('location', '')}",
                                country="ES",
                                region="",
                                municipality=city["name"],
                            ))
            except Exception as e:
                print(f"    [WARN] OpenAQ {city['name']}: {e}")
        return events
