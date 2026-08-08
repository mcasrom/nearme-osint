import httpx
from datetime import datetime, timedelta, timezone
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event

API_URL = "https://estadoembalses.es/api/embalses?limit=500"
TIMEOUT = 20
TTL_HOURS = 6

logger = get_logger("src.collectors.embalses")


class EmbalsesCollector(BaseCollector):
    name = "Embalses (MITECO/SAIH)"
    source = "embalses"
    interval_minutes = 30

    async def collect(self):
        events = []
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(API_URL)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Error fetching embalses API: %s", e)
            return events

        items = data.get("data", [])
        now = datetime.now(timezone.utc)
        for emb in items:
            lat = emb.get("lat")
            lng = emb.get("lng")
            if lat is None or lng is None:
                continue

            pct = emb.get("porcentaje")
            vol = emb.get("volumen_hm3")
            cap = emb.get("capacidad_hm3")

            if pct is None:
                level = "info"
            elif pct >= 90:
                level = "info"
            elif pct >= 70:
                level = "info"
            elif pct >= 40:
                level = "warning"
            elif pct >= 20:
                level = "alert"
            else:
                level = "critical"

            nombre = emb.get("nombre", "Embalse desconocido")
            cuenca = emb.get("cuenca", "")
            provincia = emb.get("provincia", "")
            comunidad = emb.get("comunidad_autonoma", "")

            title = f"{nombre}"
            desc_parts = [f"Embalse en {provincia} ({comunidad})", f"Cuenca: {cuenca}"]
            if pct is not None:
                desc_parts.append(f"Nivel: {pct}%")
            if vol is not None and cap is not None:
                desc_parts.append(f"Volumen: {vol} hm³ / {cap} hm³")
            ultima = emb.get("ultima_lectura")
            if ultima:
                try:
                    ults = datetime.fromisoformat(ultima)
                    desc_parts.append(f"Medición: {ults.strftime('%d/%m/%Y %H:%M')}")
                except Exception:
                    pass
            description = " · ".join(desc_parts)

            # Los datos de nivel de embalse son estables durante dias y la
            # fuente (estadoembalses.es) no renueva la ultima_lectura de todos
            # los embalses con la misma frecuencia (p. ej. Alarcon lleva semanas
            # con lectura del 22-Jul). Si expiramos basandonos en
            # ultima_lectura + TTL_HOURS, esos embalses quedan con expires_at
            # en el pasado y el backend los excluye del mapa (bug: 83 embalses
            # invisibles). Como este colector se re-ejecuta cada 30 min y
            # refresca expires_at, usamos una expiracion larga desde la
            # recoleccion: el embalse es visible 7 dias desde cada coleccion.
            EMBALSE_TTL_DAYS = 7
            expires = (now + timedelta(days=EMBALSE_TTL_DAYS)).isoformat()

            events.append(Event(
                source="embalses",
                source_id=f"emb_{emb.get('id', nombre)}",
                event_type="reservoir",
                subtype="dam",
                lat=lat,
                lon=lng,
                radius_m=20000,
                level=level,
                title=title[:100],
                description=description[:300],
                country="España",
                region=provincia or "",
                municipality="",
                expires_at=expires,
            ))

        logger.info("%d embalses recolectados", len(events))
        return events
