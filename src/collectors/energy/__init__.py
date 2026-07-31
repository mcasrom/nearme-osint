import httpx
from datetime import datetime, timedelta, timezone
from src.collectors.base import BaseCollector
from src.config import (
    ENERGY_PRICE_URL, ENERGY_REQUEST_TIMEOUT, ENERGY_TTL_HOURS,
    ENERGY_PRICE_ALERT_EUR_MWH, ENERGY_PRICE_WARNING_EUR_MWH,
    ENERGY_RADIUS_M, ENERGY_DEFAULT_LAT, ENERGY_DEFAULT_LON,
    REE_URL, REE_DEMAND_WARNING_MW, REE_DEMAND_ALERT_MW,
)
from src.logging import get_logger
from src.models import Event


logger = get_logger("src.collectors.energy")


class EnergyCollector(BaseCollector):
    name = "Energía (REE + ESIOS)"
    source = "energy"
    interval_minutes = 15

    async def collect(self):
        events = []
        events.extend(await self._demand())
        events.extend(await self._price())
        return events

    async def _demand(self):
        events = []
        try:
            now = datetime.now(timezone.utc)
            start = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
            end = now.strftime('%Y-%m-%dT%H:%M')
            params = {'start_date': start, 'end_date': end, 'time_trunc': 'hour'}

            async with httpx.AsyncClient(
                timeout=ENERGY_REQUEST_TIMEOUT,
                headers={"User-Agent": "NearMeOSINT/1.0"},
            ) as client:
                resp = await client.get(REE_URL, params=params)

            if resp.status_code != 200:
                logger.warning("Energía (REE demanda): HTTP %s", resp.status_code)
                return events

            data = resp.json()
            for series in data.get('included', []):
                attrs = series.get('attributes', {})
                values = attrs.get('values', [])
                series_type = attrs.get('title', '')
                if series_type.lower() != 'real':
                    continue
                if not values:
                    continue

                v = values[-1]
                demand = v.get('value', 0)
                dt = v.get('datetime', '')

                if demand >= REE_DEMAND_ALERT_MW:
                    level = 'alert'
                elif demand >= REE_DEMAND_WARNING_MW:
                    level = 'warning'
                else:
                    level = 'info'

                events.append(Event(
                    source="energy",
                    source_id=f"energy_demand_{series_type}_{dt}",
                    event_type="energy",
                    subtype="demand",
                    lat=ENERGY_DEFAULT_LAT,
                    lon=ENERGY_DEFAULT_LON,
                    radius_m=ENERGY_RADIUS_M,
                    level=level,
                    title=f"Demanda eléctrica: {demand:,.0f} MW",
                    description=(
                        f"Demanda de energía eléctrica en {series_type}: "
                        f"{demand:,.0f} MW a las {dt}"
                    ),
                    country="España",
                    region="Peninsular",
                    expires_at=(now + timedelta(hours=ENERGY_TTL_HOURS)).isoformat(),
                ))
        except Exception as e:
            logger.warning("Energía (REE demanda): %s", e)
        return events

    async def _price(self):
        events = []
        try:
            now = datetime.now(timezone.utc)
            async with httpx.AsyncClient(
                timeout=ENERGY_REQUEST_TIMEOUT,
                headers={"User-Agent": "NearMeOSINT/1.0"},
            ) as client:
                resp = await client.get(ENERGY_PRICE_URL)

            if resp.status_code != 200:
                logger.warning("Energía (PVPC): HTTP %s", resp.status_code)
                return events

            data = resp.json()
            rows = data.get('PVPC', [])
            if not rows:
                return events

            local_now = now.astimezone(timezone(timedelta(hours=1)))
            hour_label = f"{local_now.hour:02d}-{(local_now.hour + 1) % 24:02d}"

            row = None
            for r in rows:
                if r.get('Hora', '').startswith(f"{local_now.hour:02d}-"):
                    row = r
                    break
            if row is None:
                row = rows[0]
                hour_label = row.get('Hora', hour_label)

            price = float(row.get('PCB', '0').replace(',', '.'))

            if price >= ENERGY_PRICE_ALERT_EUR_MWH:
                level = 'alert'
            elif price >= ENERGY_PRICE_WARNING_EUR_MWH:
                level = 'warning'
            else:
                level = 'info'

            events.append(Event(
                source="energy",
                source_id=f"energy_price_{row.get('Dia', '')}_{hour_label}",
                event_type="energy",
                subtype="price",
                lat=ENERGY_DEFAULT_LAT,
                lon=ENERGY_DEFAULT_LON,
                radius_m=ENERGY_RADIUS_M,
                level=level,
                title=f"Precio luz (PVPC): {price:.2f} €/MWh",
                description=(
                    f"Precio del kWh en tarifa PVPC (Península) en la hora "
                    f"{hour_label} ({row.get('Dia', '')}): {price:.2f} €/MWh "
                    f"= {price / 1000:.3f} €/kWh"
                ),
                country="España",
                region="Peninsular",
                expires_at=(now + timedelta(hours=ENERGY_TTL_HOURS)).isoformat(),
            ))
        except Exception as e:
            logger.warning("Energía (PVPC): %s", e)
        return events
