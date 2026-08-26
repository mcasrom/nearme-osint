import json
import asyncio
import urllib.request
from datetime import datetime, timedelta, timezone
from src.collectors.base import BaseCollector
from src.config import (
    IGN_EARTHQUAKE_URL, IGN_REQUEST_TIMEOUT, IGN_TTL_HOURS,
    IGN_BBOX, IGN_MAG_ALERT, IGN_MAG_WARNING,
    IGN_EARTHQUAKE_RADIUS_M, IGN_MAX_AGE_DAYS,
)
from src.logging import get_logger
from src.models import Event

logger = get_logger("src.collectors.ign")


def _parse_ign_payload(text):
    """El fichero es `var dias3={...};var dias10={...};var dias30={...}`."""
    features = []
    for segment in text.split("var "):
        eq = segment.find("=")
        if eq == -1:
            continue
        start = segment.find("{", eq)
        if start == -1:
            continue
        payload = segment[start:].strip()
        if payload.endswith(";"):
            payload = payload[:-1].strip()
        if not payload:
            continue
        try:
            obj = json.loads(payload)
            features.extend(obj.get("features", []))
        except Exception:
            continue
    return {"features": features}


def _fetch_ign_sync(url, timeout):
    """Descarga sincrónica con urllib — funciona siempre con IGN."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; NearMeBot/1.0; +https://nearme.viajeinteligencia.com)"
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


class IGNSeismicCollector(BaseCollector):
    name = "IGN (sismología)"
    source = "ign"
    interval_minutes = 15

    async def collect(self):
        events = []
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None, _fetch_ign_sync, IGN_EARTHQUAKE_URL, IGN_REQUEST_TIMEOUT
            )
            data = _parse_ign_payload(text)
        except Exception as e:
            logger.warning("Error fetching IGN sismología: %s", e)
            return events

        features = data.get("features", [])
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=IGN_MAX_AGE_DAYS)

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates")
            if not coords or len(coords) < 2:
                continue

            lon, lat = coords[0], coords[1]
            if not (IGN_BBOX["min_lat"] <= lat <= IGN_BBOX["max_lat"]
                    and IGN_BBOX["min_lon"] <= lon <= IGN_BBOX["max_lon"]):
                continue

            fecha = props.get("fecha", "")
            evid = props.get("evid", "")
            if not evid:
                continue

            try:
                evt_time = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                evt_time = now
            if evt_time < cutoff:
                continue

            try:
                mag = float(props.get("mag", 0) or 0)
            except Exception:
                mag = 0.0
            depth = props.get("depth", "?")
            loc = props.get("loc", "Desconocida").strip()
            magtype = props.get("magtype", "mbLg")

            if mag >= IGN_MAG_ALERT:
                level = "alert"
            elif mag >= IGN_MAG_WARNING:
                level = "warning"
            else:
                level = "info"

            events.append(Event(
                source="ign",
                source_id=f"ign_{evid}",
                event_type="earthquake",
                subtype="seismic",
                lat=lat,
                lon=lon,
                radius_m=IGN_EARTHQUAKE_RADIUS_M,
                level=level,
                title=f"Terremoto M{mag:.1f} ({magtype}) — {loc}",
                description=(
                    f"Terremoto en {loc}. Magnitud {mag:.1f} ({magtype}). "
                    f"Profundidad: {depth} km. Hora: {fecha} UTC"
                ),
                country="España",
                region="",
                municipality="",
                expires_at=(evt_time + timedelta(hours=IGN_TTL_HOURS)).isoformat(),
            ))

        logger.info("%d terremotos IGN recolectados", len(events))
        return events
