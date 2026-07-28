import re
import json
import sqlite3
from pathlib import Path
from src.collectors.base import BaseCollector
from src.models import Event

HUB_DB = Path.home() / "intelligence-hub" / "data" / "news.db"

FIRE_KEYWORDS = [
    "incendio", "incendios", "incendie", "incendies", "fire", "fires",
    "feu", "feux", "fuego", "foc", "brand", "wildfire", "megafeu",
    "forestal", "forestier", "forêt", "forest",
]

FIRE_LEVELS = {
    "grave": "critical", "catastrófico": "critical", "megafeu": "critical",
    "alerta": "alert", "evacuación": "alert", "evacuation": "alert",
    "estabilizado": "warning", "contenido": "warning", "controlado": "warning",
}

# Approximate coordinates for common Spanish locations mentioned in fire news
LOCATION_COORDS = {
    # Provincias
    "madrid": (40.42, -3.70), "ávila": (40.66, -4.70), "avila": (40.66, -4.70),
    "toledo": (39.86, -4.02), "gironde": (44.84, -0.58), "bordeaux": (44.84, -0.58),
    "alicante": (38.35, -0.48), "valencia": (39.47, -0.38), "barcelona": (41.39, 2.17),
    "sevilla": (37.38, -5.99), "huelva": (37.26, -6.95), "badajoz": (38.88, -6.97),
    "cáceres": (39.48, -6.37), "caceres": (39.48, -6.37), "zaragoza": (41.65, -0.88),
    "murcia": (37.98, -1.13), "castellón": (39.98, -0.05), "castellon": (39.98, -0.05),
    "tarragona": (41.12, 1.25), "lleida": (41.62, 0.62), "girona": (41.98, 2.82),
    "palencia": (42.01, -4.53), "zamora": (41.50, -5.74), "salamanca": (40.97, -5.66),
    "segovia": (40.95, -4.12), "guadalajara": (40.63, -3.17), "cuenca": (40.07, -2.14),
    "albacete": (38.99, -1.86), "jaén": (37.77, -3.79), "jaen": (37.77, -3.79),
    "córdoba": (37.88, -4.78), "cordoba": (37.88, -4.78), "málaga": (36.72, -4.42),
    "malaga": (36.72, -4.42), "granada": (37.18, -3.60),
    # Puntos críticos de incendios
    "sierra oeste": (40.35, -4.20), "valle del tiétar": (40.20, -4.70),
    "cebreros": (40.40, -4.47), "el escorial": (40.58, -4.14),
    "arcachon": (44.66, -1.17), "landes": (44.20, -0.80),
}


def extract_location(title):
    title_lower = title.lower()
    found = []
    for name, (lat, lon) in LOCATION_COORDS.items():
        if name in title_lower:
            found.append((name, lat, lon))
    if found:
        name, lat, lon = found[0]
        return name, lat, lon
    return None, 40.0, -3.0


class IntelHubBridge(BaseCollector):
    name = "Intelligence Hub (incendios)"
    interval_minutes = 10

    def collect(self):
        events = []
        if not HUB_DB.exists():
            print(f"    [WARN] BD del Hub no encontrada: {HUB_DB}")
            return events
        try:
            conn = sqlite3.connect(str(HUB_DB))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT title, source, country, url, published, fetched
                FROM articles
                WHERE published > datetime('now', '-24 hours')
                ORDER BY published DESC LIMIT 50
            """).fetchall()
            for row in rows:
                title = row["title"]
                title_lower = title.lower()
                if any(kw in title_lower for kw in FIRE_KEYWORDS):
                    loc_name, lat, lon = extract_location(title)
                    level = "alert"
                    for kw, lvl in FIRE_LEVELS.items():
                        if kw in title_lower:
                            level = lvl
                            break
                    events.append(Event(
                        source="intelhub",
                        source_id=f"ih_fire_{row['url'][:40]}",
                        event_type="fire",
                        subtype="wildfire",
                        lat=lat, lon=lon,
                        radius_m=10000,
                        level=level,
                        title=f"🔥 {title[:80]}",
                        description=f"Fuente: {row['source']}. {title}",
                        country=row["country"] or "ES",
                    ))
            conn.close()
            print(f"    {len(events)} incendios desde Intelligence Hub")
        except Exception as e:
            print(f"    [WARN] IntelHub bridge: {e}")
        return events
