import requests
from src.collectors.base import BaseCollector
from src.models import Event


class CopernicusCollector(BaseCollector):
    name = "Copernicus + GWIS"
    interval_minutes = 60

    def collect(self):
        events = []
        events.extend(self._gwis_fires())
        events.extend(self._copernicus_emergency())
        return events

    def _gwis_fires(self):
        events = []
        try:
            resp = requests.get(
                "https://gwis.jrc.ec.europa.eu/api/active-fires",
                params={"limit": 30, "country": "ES"},
                timeout=20
            )
            if resp.status_code != 200:
                print(f"    GWIS: HTTP {resp.status_code}")
                return events
            data = resp.json()
            features = data.get("features", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            for fire in features[:20]:
                try:
                    props = fire.get("properties", fire) if isinstance(fire, dict) else {}
                    geometry = fire.get("geometry", {}) if isinstance(fire, dict) else {}
                    coords = geometry.get("coordinates", [0, 0])
                    if isinstance(coords, list) and len(coords) >= 2:
                        lon_val = coords[0]
                        lat_val = coords[1]
                        if isinstance(lon_val, list):
                            lon_val = lon_val[0] if lon_val else 0
                        if isinstance(lat_val, list):
                            lat_val = lat_val[0] if lat_val else 0
                        lat = float(lat_val)
                        lon = float(lon_val)
                    else:
                        continue
                    if lat == 0 and lon == 0:
                        continue
                    frp = props.get("frp", props.get("fire_radiative_power", 0))
                    name = props.get("name", props.get("location", ""))
                    events.append(Event(
                        source="gwis",
                        source_id=f"gwis_{lat}_{lon}_{frp}",
                        event_type="fire",
                        subtype="active_fire",
                        lat=lat, lon=lon,
                        radius_m=1500,
                        level="alert" if float(frp or 0) > 50 else "warning",
                        title=f"Incendio activo: {name}" if name else f"Incendio activo ({lat:.2f},{lon:.2f})",
                        description=f"FRP: {frp} MW" if frp else "",
                        country="ES",
                    ))
                except (ValueError, TypeError, IndexError):
                    pass
            if events:
                print(f"    {len(events)} incendios GWIS activos")
            else:
                print("    GWIS: sin incendios activos en Espana")
        except Exception as e:
            print(f"    [WARN] GWIS: {e}")
        return events

    def _copernicus_emergency(self):
        events = []
        try:
            resp = requests.get(
                "https://emergency.copernicus.eu/mapping/activations-rapid/feed",
                timeout=15
            )
            if resp.status_code != 200:
                print(f"    Copernicus EMS: HTTP {resp.status_code}")
                return events
            ct = resp.headers.get("content-type", "")
            if "json" not in ct:
                print(f"    Copernicus EMS: respuesta no es JSON ({ct})")
                return events
            data = resp.json()
            features = data.get("features", []) if isinstance(data, dict) else []
            for act in features[:10]:
                try:
                    props = act.get("properties", {})
                    geometry = act.get("geometry", {})
                    coords = geometry.get("coordinates", [])
                    if not isinstance(coords, list) or len(coords) < 2:
                        continue
                    lon_val = coords[0]
                    lat_val = coords[1]
                    if isinstance(lon_val, list):
                        lon_val = lon_val[0] if lon_val else 0
                    if isinstance(lat_val, list):
                        lat_val = lat_val[0] if lat_val else 0
                    lat = float(lat_val)
                    lon = float(lon_val)
                    if lat == 0 and lon == 0:
                        continue
                    title_str = props.get("title", "")
                    etype = "fire" if "fire" in title_str.lower() else "flood"
                    events.append(Event(
                        source="copernicus",
                        source_id=f"cems_{props.get('id', act.get('id', ''))}",
                        event_type=etype,
                        subtype="ems_activation",
                        lat=lat, lon=lon,
                        radius_m=20000,
                        level="alert",
                        title=title_str or f"Activacion CEMS: {etype}",
                        description=props.get("description", ""),
                        country=props.get("country", ""),
                    ))
                except (ValueError, TypeError, IndexError):
                    pass
            if events:
                print(f"    {len(events)} activaciones Copernicus EMS")
            else:
                print("    Copernicus EMS: sin activaciones activas")
        except Exception as e:
            print(f"    [WARN] Copernicus EMS: {e}")
        return events
