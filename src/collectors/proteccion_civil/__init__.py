import os
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
        """Get weather warnings from AEMET (official Spanish meteorological agency)"""
        events = []
        if not AEMET_API_KEY:
            logger.warning("AEMET_API_KEY no configurada, saltando avisos meteorológicos")
            return events

        try:
            base = "https://opendata.aemet.es/opendata/api"
            headers = {"api_key": AEMET_API_KEY}

            async with httpx.AsyncClient(timeout=20, headers=headers) as client:
                # Try to get latest warnings for all Spain
                resp = await client.get(f"{base}/avisos_cap/ultimoelaborado/area/es")
            if resp.status_code != 200:
                logger.warning("AEMET avisos: HTTP %s", resp.status_code)
                return events

            body = resp.json()
            data_url = body.get('datos')
            if not data_url:
                logger.warning("AEMET avisos: No data URL")
                return events

            # Download the CAP (Common Alerting Protocol) XML files
            async with httpx.AsyncClient(timeout=30, headers=headers) as client:
                data_resp = await client.get(data_url)
            if data_resp.status_code != 200:
                logger.warning("AEMET avisos data: HTTP %s", data_resp.status_code)
                return events

            # Parse CAP XML
            try:
                # AEMET returns a GTAR archive containing multiple CAP files
                import tempfile
                import zipfile
                import io

                content = data_resp.content
                if len(content) < 100:
                    return events

                # Try to parse as XML directly first
                try:
                    root = ET.fromstring(content)
                    events.extend(self._parse_cap_xml(root))
                except ET.ParseError:
                    # Try as zip archive
                    try:
                        with zipfile.ZipFile(io.BytesIO(content)) as zf:
                            for name in zf.namelist():
                                if name.endswith('.xml') or name.endswith('.cap'):
                                    cap_data = zf.read(name)
                                    cap_root = ET.fromstring(cap_data)
                                    events.extend(self._parse_cap_xml(cap_root))
                    except zipfile.BadZipFile:
                        pass

            except Exception as e:
                logger.warning("AEMET CAP parse: %s", e)

            logger.info("AEMET avisos: %d alertas meteorológicas", len(events))
        except Exception as e:
            logger.warning("AEMET avisos: %s", e)
        return events

    def _parse_cap_xml(self, root):
        """Parse CAP (Common Alerting Protocol) XML"""
        events = []
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}

        for alert in root.findall('.//cap:alert', ns):
            try:
                sender = alert.findtext('cap:sender', '', ns)
                sent = alert.findtext('cap:sent', '', ns)

                for info in alert.findall('cap:info', ns):
                    headline = info.findtext('cap:headline', '', ns)
                    description = info.findtext('cap:description', '', ns)
                    severity = info.findtext('cap:severity', '', ns)
                    urgency = info.findtext('cap:urgency', '', ns)
                    category = info.findtext('cap:category', '', ns)

                    # Get coordinates from area
                    for area in info.findall('cap:area', ns):
                        area_desc = area.findtext('cap:areaDesc', '', ns)
                        circle = area.findtext('cap:circle', '', ns)

                        lat, lon, radius = 40.4168, -3.7038, 50000
                        if circle:
                            parts = circle.split()
                            if len(parts) >= 2:
                                lat, lon = float(parts[0]), float(parts[1])
                                if len(parts) >= 3:
                                    radius = float(parts[2]) * 1000

                        # Map severity to level
                        level = 'info'
                        if severity.lower() in ('extreme', 'severe'):
                            level = 'alert'
                        elif severity.lower() == 'moderate':
                            level = 'warning'

                        events.append(Event(
                            source="aemet_avisos",
                            source_id=f"aemet_aviso_{sent}_{lat}_{lon}",
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