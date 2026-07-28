import httpx
from datetime import datetime, timedelta, timezone
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event


logger = get_logger("src.collectors.ree")


class REEPowerCollector(BaseCollector):
    name = "REE"
    interval_minutes = 15

    async def collect(self):
        events = []
        events.extend(await self._demand_data())
        return events

    async def _demand_data(self):
        events = []
        try:
            now = datetime.now(timezone.utc)
            start = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
            end = now.strftime('%Y-%m-%dT%H:%M')

            url = "https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real"
            params = {
                'start_date': start,
                'end_date': end,
                'time_trunc': 'hour'
            }

            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "NearMeOSINT/1.0"}) as client:
                resp = await client.get(url, params=params)

            if resp.status_code != 200:
                logger.warning("REE: HTTP %s", resp.status_code)
                return events

            data = resp.json()
            included = data.get('included', [])

            for series in included:
                values = series.get('attributes', {}).get('values', [])
                series_type = series.get('attributes', {}).get('title', '')

                for v in values[-3:]:
                    demand = v.get('value', 0)
                    if demand > 42000:
                        level = 'alert'
                    elif demand > 38000:
                        level = 'warning'
                    else:
                        continue

                    dt = v.get('datetime', '')
                    events.append(Event(
                        source="ree",
                        source_id=f"ree_demand_{dt}",
                        event_type="blackout",
                        subtype="high_demand",
                        lat=40.4168, lon=-3.7038,
                        radius_m=100000,
                        level=level,
                        title=f"Alta demanda eléctrica: {demand} MW ({series_type})",
                        description=f"Demanda: {demand} MW ({series_type}). Hora: {dt}",
                        country="ES",
                        region="Peninsular",
                    ))

            logger.info("REE: %d eventos de demanda", len(events))
        except Exception as e:
            logger.warning("REE: %s", e)
        return events