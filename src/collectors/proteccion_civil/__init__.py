import os
import re
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event

AEMET_API_KEY = os.environ.get("AEMET_API_KEY", "")

logger = get_logger("src.collectors.proteccion_civil")


class ProteccionCivilCollector(BaseCollector):
    name = "ProtecciónCivil"
    source = "aemet_avisos"
    interval_minutes = 30

    async def collect(self):
        events = []
        events.extend(await self._aemet_warnings())
        return events

    async def _aemet_warnings(self):
        """Avisos meteorológicos oficiales de AEMET (CAP / Common Alerting Protocol)."""
        events = []
        if not AEMET_API_KEY:
            logger.warning("AEMET_API_KEY no configurada, saltando avisos meteorológicos")
            return events

        try:
            base = "https://opendata.aemet.es/opendata/api"
            headers = {"api_key": AEMET_API_KEY}

            async with httpx.AsyncClient(timeout=20, headers=headers) as client:
                resp = await client.get(f"{base}/avisos_cap/ultimoelaborado/area/esp")
            if resp.status_code != 200:
                logger.warning("AEMET avisos: HTTP %s", resp.status_code)
                return events

            body = resp.json()
            data_url = body.get('datos')
            if not data_url:
                logger.warning("AEMET avisos: No data URL")
                return events

            async with httpx.AsyncClient(timeout=30, headers=headers) as client:
                data_resp = await client.get(data_url)
            if data_resp.status_code != 200:
                logger.warning("AEMET avisos data: HTTP %s", data_resp.status_code)
                return events

            # El contenido es un archivo GTAR (concatenación) con múltiples XML CAP.
            content = data_resp.content
            if len(content) < 100:
                return events

            starts = [m.start() for m in re.finditer(rb"<\?xml", content)]
            for s in starts:
                e = content.find(b"</alert>", s)
                if e == -1:
                    continue
                try:
                    root = ET.fromstring(content[s:e + 8])
                    events.extend(self._parse_cap_xml(root))
                except ET.ParseError:
                    continue

            logger.info("AEMET avisos: %d alertas meteorológicas", len(events))
        except Exception as e:
            logger.warning("AEMET avisos: %s", e)
        return events

    def _parse_cap_xml(self, root):
        """Parse CAP XML (el root ES el <alert>). Geolocaliza por centroide del polígono."""
        events = []
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}

        if root.tag.split('}')[-1] != 'alert':
            root = root.find('.//cap:alert', ns)
            if root is None:
                return events

        try:
            sent = root.findtext('cap:sent', '', ns)
            for info in root.findall('cap:info', ns):
                headline = info.findtext('cap:headline', '', ns)
                description = info.findtext('cap:description', '', ns)
                severity = info.findtext('cap:severity', '', ns)
                urgency = info.findtext('cap:urgency', '', ns)

                for area in info.findall('cap:area', ns):
                    area_desc = area.findtext('cap:areaDesc', '', ns)
                    lat, lon, radius = 40.4168, -3.7038, 50000

                    poly = area.findtext('cap:polygon', '', ns)
                    if poly:
                        pts = []
                        for tok in poly.split():
                            if ',' in tok:
                                p = tok.split(',')
                                try:
                                    pts.append((float(p[0]), float(p[1])))
                                except ValueError:
                                    pass
                        if pts:
                            lat = sum(p[0] for p in pts) / len(pts)
                            lon = sum(p[1] for p in pts) / len(pts)

                    circle = area.findtext('cap:circle', '', ns)
                    if not poly and circle:
                        parts = circle.split()
                        if len(parts) >= 2:
                            try:
                                lat, lon = float(parts[0]), float(parts[1])
                                if len(parts) >= 3:
                                    radius = float(parts[2]) * 1000
                            except ValueError:
                                pass

                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        continue

                    level = 'info'
                    if severity.lower() in ('extreme', 'severe'):
                        level = 'alert'
                    elif severity.lower() == 'moderate':
                        level = 'warning'

                    events.append(Event(
                        source="aemet_avisos",
                        source_id=f"aemet_aviso_{sent}_{lat:.3f}_{lon:.3f}",
                        event_type="warning",
                        subtype="alerta_meteorologica",
                        lat=lat, lon=lon,
                        radius_m=radius,
                        level=level,
                        title=f"Aviso: {headline}",
                        description=f"{description}. Zona: {area_desc}. Severidad: {severity}. Urgencia: {urgency}",
                        country="ES",
                    ))
        except Exception:
            pass

        return events
