import re
import json
import sqlite3
from pathlib import Path
from src.collectors.base import BaseCollector
from src.models import Event

HUB_DB = Path.home() / "intelligence-hub" / "data" / "news.db"

FIRE_KEYWORDS = [
    "incendio", "incendios", "incendie", "incendies", "incendio",
    "fire", "fires", "feu", "feux", "fuego", "foc",
    "wildfire", "megafeu", "forestal", "forestier", "forêt", "forest",
    "pyromane", "pyromanes", "bomberos", "sapeurs",
]

FALSE_POSITIVES = [
    "brandenburg", "brande", "brandt", "brandi",
    "firewall", "firestone", "firefox", "firefighter",
    "facebook", "firenze",
]

FIRE_LEVELS = {
    "grave": "critical", "catastrófico": "critical", "megafeu": "critical",
    "alerta": "alert", "evacuación": "alert", "evacuation": "alert",
    "estabilizado": "warning", "contenido": "warning", "controlado": "warning",
}

# Approximate coordinates for common Spanish locations mentioned in fire news
LOCATION_COORDS = {
    # España - provincias
    "madrid": (40.42, -3.70), "ávila": (40.66, -4.70), "avila": (40.66, -4.70),
    "toledo": (39.86, -4.02), "cuenca": (40.07, -2.14), "guadalajara": (40.63, -3.17),
    "segovia": (40.95, -4.12), "zamora": (41.50, -5.74), "salamanca": (40.97, -5.66),
    "palencia": (42.01, -4.53), "burgos": (42.34, -3.70), "soria": (41.77, -2.47),
    "valladolid": (41.65, -4.72), "león": (42.60, -5.57), "leon": (42.60, -5.57),
    "ponferrada": (42.55, -6.60), "lugo": (43.01, -7.56), "ourense": (42.34, -7.86),
    "coruña": (43.37, -8.40), "pontevedra": (42.43, -8.64), "asturias": (43.36, -5.85),
    "oviedo": (43.36, -5.85), "gijón": (43.54, -5.66), "gijon": (43.54, -5.66),
    "cantabria": (43.20, -4.04), "santander": (43.46, -3.81),
    "país vasco": (43.00, -2.60), "pais vasco": (43.00, -2.60), "euskadi": (43.00, -2.60),
    "bilbao": (43.26, -2.94), "san sebastián": (43.32, -1.98), "vitoria": (42.85, -2.67),
    "la rioja": (42.46, -2.45), "logroño": (42.46, -2.45), "logrono": (42.46, -2.45),
    "navarra": (42.82, -1.65), "pamplona": (42.82, -1.65),
    "aragón": (41.65, -0.88), "aragon": (41.65, -0.88),
    "zaragoza": (41.65, -0.88), "huesca": (42.14, -0.41), "teruel": (40.34, -1.11),
    "cataluña": (41.59, 1.84), "catalunya": (41.59, 1.84), "catalunya": (41.59, 1.84),
    "barcelona": (41.39, 2.17), "tarragona": (41.12, 1.25), "lleida": (41.62, 0.62),
    "girona": (41.98, 2.82),
    "castellón": (39.98, -0.05), "castellon": (39.98, -0.05),
    "valencia": (39.47, -0.38), "alicante": (38.35, -0.48),
    "murcia": (37.98, -1.13),
    "andalucía": (37.38, -5.99), "andalucia": (37.38, -5.99),
    "sevilla": (37.38, -5.99), "huelva": (37.26, -6.95), "cádiz": (36.53, -6.28),
    "cadiz": (36.53, -6.28), "málaga": (36.72, -4.42), "malaga": (36.72, -4.42),
    "granada": (37.18, -3.60), "jaén": (37.77, -3.79), "jaen": (37.77, -3.79),
    "córdoba": (37.88, -4.78), "cordoba": (37.88, -4.78), "almería": (36.84, -2.47),
    "almeria": (36.84, -2.47),
    "extremadura": (38.88, -6.97), "badajoz": (38.88, -6.97),
    "cáceres": (39.48, -6.37), "caceres": (39.48, -6.37),
    "castilla-la mancha": (39.86, -4.02), "castilla la mancha": (39.86, -4.02),
    "albacete": (38.99, -1.86),
    "baleares": (39.57, 2.65), "palma": (39.57, 2.65), "menorca": (39.95, 4.10),
    "ibiza": (38.91, 1.43),
    "canarias": (28.12, -15.43), "tenerife": (28.29, -16.63), "gran canaria": (28.12, -15.43),
    "las palmas": (28.12, -15.43),
    # Francia
    "gironde": (44.84, -0.58), "bordeaux": (44.84, -0.58), "arcachon": (44.66, -1.17),
    "landes": (44.20, -0.80), "parís": (48.86, 2.35), "paris": (48.86, 2.35),
    # Puntos críticos de incendios
    "sierra oeste": (40.35, -4.20), "valle del tiétar": (40.20, -4.70),
    "valle del tietar": (40.20, -4.70),
    "cebreros": (40.40, -4.47), "el escorial": (40.58, -4.14),
    "tarancon": (40.04, -3.01), "tarancon": (40.04, -3.01),
}


def extract_location(title):
    title_lower = title.lower()
    found = []
    for name, (lat, lon) in LOCATION_COORDS.items():
        pos = title_lower.find(name)
        if pos >= 0:
            found.append((pos, name, lat, lon))
    if found:
        found.sort()
        _, name, lat, lon = found[0]
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
                    if any(fp in title_lower for fp in FALSE_POSITIVES):
                        continue
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
