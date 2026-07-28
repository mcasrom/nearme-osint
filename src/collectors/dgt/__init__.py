import os
import csv
import io
import re
import requests
from datetime import datetime
from collections import Counter
from src.collectors.base import BaseCollector
from src.models import Event

FIRMS_SOURCES = [
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv",
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv",
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv",
]

SPAIN_BBOX = {"min_lat": 27.5, "max_lat": 44.0, "min_lon": -18.5, "max_lon": 4.5}

DATEX_URL = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml"

DGT_TYPE_MAP = {
    "sit:RoadOrCarriagewayOrLaneManagement": "road_closure",
    "sit:GeneralObstruction": "road_incident",
    "sit:Accident": "road_incident",
    "sit:AbnormalTraffic": "traffic",
    "sit:VehicleObstruction": "road_incident",
    "sit:SpeedManagement": "traffic",
    "sit:NonWeatherRelatedRoadConditions": "road_incident",
    "sit:PoorEnvironmentConditions": "warning",
    "sit:GeneralInstructionOrMessageToRoadUsers": "warning",
}


def _in_spain(lat, lon):
    return SPAIN_BBOX["min_lat"] <= lat <= SPAIN_BBOX["max_lat"] and SPAIN_BBOX["min_lon"] <= lon <= SPAIN_BBOX["max_lon"]


class EarthquakesCollector(BaseCollector):
    name = "USGS + FIRMS"
    interval_minutes = 15

    def collect(self):
        events = []
        events.extend(self._earthquakes())
        events.extend(self._firms_fires())
        return events

    def _earthquakes(self):
        events = []
        try:
            resp = requests.get(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
                timeout=15,
                headers={"User-Agent": "NearMeOSINT/1.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                for feat in data.get("features", [])[:30]:
                    props = feat.get("properties", {})
                    coords = feat.get("geometry", {}).get("coordinates", [0, 0, 0])
                    mag = props.get("mag", 0)
                    lat = coords[1]
                    lon = coords[0]
                    depth = coords[2] if len(coords) >= 3 else 0
                    place = props.get("place", "Desconocido")
                    level = "info"
                    if mag >= 5:
                        level = "alert"
                    elif mag >= 4:
                        level = "warning"
                    events.append(Event(
                        source="usgs",
                        source_id=f"usgs_{props.get('id', '')}",
                        event_type="earthquake",
                        subtype=f"mag_{mag}",
                        lat=lat, lon=lon,
                        radius_m=max(mag * 10000, 5000),
                        level=level,
                        title=f"Terremoto M{mag} - {place}",
                        description=f"Magnitud: {mag}. Profundidad: {depth} km. {place}",
                        country=props.get("net", ""),
                    ))
                print(f"    {len(events)} terremotos USGS (ultimas 24h)")
        except Exception as e:
            print(f"    [WARN] USGS: {e}")
        return events

    def _firms_fires(self):
        events = []
        seen = set()
        for url in FIRMS_SOURCES:
            try:
                resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (compatible; NearMeOSINT/1.0)"})
                if resp.status_code != 200:
                    continue
                reader = csv.DictReader(io.StringIO(resp.text))
                is_viirs = "bright_ti4" in (reader.fieldnames or [])
                for row in reader:
                    try:
                        lat = float(row["latitude"])
                        lon = float(row["longitude"])
                        if not _in_spain(lat, lon):
                            continue
                        frp = float(row.get("frp", 0))
                        satellite = row.get("satellite", "?").strip()
                        conf_raw = row.get("confidence", "0").strip()
                        if is_viirs:
                            if conf_raw.lower() in ("low", "none"):
                                continue
                            confidence_pct = 0
                        else:
                            confidence_pct = int(conf_raw) if conf_raw.isdigit() else 0
                            if confidence_pct < 60:
                                continue
                        acq_date = row.get("acq_date", "")
                        acq_time = row.get("acq_time", "")
                        brightness_col = "brightness" if not is_viirs else "bright_ti4"
                        brightness = float(row.get(brightness_col, 0))
                        key = f"{lat:.4f}_{lon:.4f}_{acq_date}"
                        if key in seen:
                            continue
                        seen.add(key)
                        level = "alert" if frp > 100 or brightness > 330 else "warning"
                        events.append(Event(
                            source="nasa_firms",
                            source_id=f"firms_{lat:.4f}_{lon:.4f}",
                            event_type="fire",
                            subtype="satellite_fire",
                            lat=lat, lon=lon,
                            radius_m=1500,
                            level=level,
                            title=f"Incendio activo ({satellite}) FRP:{frp:.0f}MW",
                            description=f"FRP: {frp:.0f} MW. Brillo: {brightness:.0f}K. Satélite: {satellite}. Confianza: {conf_raw}.",
                            country="ES",
                        ))
                    except (ValueError, KeyError):
                        continue
            except Exception as e:
                print(f"    [WARN] FIRMS ({url.split('/')[-1]}): {e}")
        print(f"    {len(events)} incendios activos en España (FIRMS)")
        return events


class DGTTrafficCollector(BaseCollector):
    name = "DGT-Tráfico"
    interval_minutes = 5

    def collect(self):
        events = []
        try:
            resp = requests.get(DATEX_URL, timeout=30, headers={"User-Agent": "NearMeOSINT/1.0"})
            if resp.status_code != 200:
                print(f"    DGT DATEX II: HTTP {resp.status_code}")
                return events
            text = resp.text
            records = re.findall(r'<sit:situationRecord[^>]*>(.*?)</sit:situationRecord>', text, re.DOTALL)
            for record in records:
                ev = self._parse_record(record)
                if ev:
                    events.append(ev)
            print(f"    {len(events)} incidencias de tráfico DGT")
        except Exception as e:
            print(f"    [WARN] DGT DATEX II: {e}")
        return events

    def _parse_record(self, record):
        xsi_type_m = re.search(r'xsi:type="([^"]+)"', record)
        xsi_type = xsi_type_m.group(1) if xsi_type_m else "sit:GenericSituationRecord"
        event_type = DGT_TYPE_MAP.get(xsi_type, "road_incident")
        subtype = self._get_subtype(record)
        severity_m = re.search(r'<sit:overallSeverity[^>]*>([^<]+)</sit:overallSeverity>', record)
        severity = severity_m.group(1).lower() if severity_m else "unknown"
        level = self._severity_to_level(severity)
        road_m = re.search(r'<loc:roadName[^>]*>([^<]+)</loc:roadName>', record)
        road = road_m.group(1) if road_m else ""
        province_m = re.search(r'<lse:province[^>]*>([^<]+)</lse:province>', record)
        province = province_m.group(1) if province_m else ""
        municipality_m = re.search(r'<lse:municipality[^>]*>([^<]+)</lse:municipality>', record)
        municipality = municipality_m.group(1) if municipality_m else ""
        ccmm_m = re.search(r'<lse:autonomousCommunity[^>]*>([^<]+)</lse:autonomousCommunity>', record)
        ccmm = ccmm_m.group(1) if ccmm_m else ""
        lat, lon = self._get_coords(record)
        if lat is None or lon is None:
            return None
        start_time_m = re.search(r'<com:overallStartTime[^>]*>([^<]+)</com:overallStartTime>', record)
        start_time = start_time_m.group(1) if start_time_m else ""
        source_id_m = re.search(r'id="([^"]+)"', record)
        source_id = f"dgt_{source_id_m.group(1) if source_id_m else f'{lat}_{lon}'}"
        municipality_clean = municipality.encode("utf-8", errors="ignore").decode("utf-8") if municipality else ""
        province_clean = province.encode("utf-8", errors="ignore").decode("utf-8") if province else ""
        title = f"DGT: {road}"
        if municipality_clean:
            title += f" - {municipality_clean}"
        if subtype:
            title += f" ({subtype})"
        desc_parts = [f"Carretera: {road}"]
        if municipality_clean:
            desc_parts.append(f"Municipio: {municipality_clean}")
        if province_clean:
            desc_parts.append(f"Provincia: {province_clean}")
        if subtype:
            desc_parts.append(f"Tipo: {subtype}")
        if start_time:
            desc_parts.append(f"Inicio: {start_time}")
        return Event(
            source="dgt",
            source_id=source_id,
            event_type=event_type,
            subtype=subtype,
            lat=lat, lon=lon,
            radius_m=2000,
            level=level,
            title=title,
            description=". ".join(desc_parts),
            country="ES",
            region=ccmm,
            municipality=municipality_clean,
        )

    def _get_subtype(self, record):
        patterns = [
            r'<sit:roadOrCarriagewayOrLaneManagementType[^>]*>([^<]+)</',
            r'<sit:accidentType[^>]*>([^<]+)</',
            r'<sit:obstructionType[^>]*>([^<]+)</',
            r'<sit:activityType[^>]*>([^<]+)</',
            r'<sit:conditionsType[^>]*>([^<]+)</',
            r'<sit:operatorActionTypeStatus[^>]*>([^<]+)</',
            r'<sit:catastrophicEventType[^>]*>([^<]+)</',
            r'<sit:causeType[^>]*>([^<]+)</',
        ]
        for p in patterns:
            m = re.search(p, record)
            if m:
                return m.group(1)
        return ""

    def _severity_to_level(self, severity):
        return {"highest": "critical", "high": "alert", "medium": "warning", "low": "info"}.get(severity, "info")

    def _get_coords(self, record):
        lats = re.findall(r'<loc:latitude[^>]*>([^<]+)</loc:latitude>', record)
        lons = re.findall(r'<loc:longitude[^>]*>([^<]+)</loc:longitude>', record)
        if lats and lons:
            try:
                return float(lats[0]), float(lons[0])
            except ValueError:
                pass
        return None, None
