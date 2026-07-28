import re
import sqlite3
from pathlib import Path
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event

HUB_DB = Path.home() / "intelligence-hub" / "data" / "news.db"

# Strong signal words - title MUST contain at least one
ACTIVE_FIRE_SIGNALS = [
    "incendio activo", "incendios activos", "fuego activo", "fuego sigue",
    "fuera de control", "fuera de control", "no controlado", "sin control",
    "evacu", "desaloj", "confinado",
    "avance del fuego", "avanza el fuego", "avanzen las llamas",
    "bomberos", "sapeurs-pompiers", "pompiers",
    "extincion", "extinción", "apagar", "extinguer",
    "hectáreas quem", "hectares brûl", "hectáreas arden",
    "operativo anti", "operativo de emergencia",
    "lucha contra el fuego", "combatir el fuego", "lutter contre le feu",
    "estabilizado", "controlado", "conten", "stabilisé", "fixé",
    "megaincendio", "megafeu", "mégafeu", "gran incendio",
    "incendio forestal", "feu de forêt", "wildfire", "incendies forest",
    "ola de calor", "canicule", "heatwave",
    "evacuación", "evacuación masiva",
    "emergencia", "urgence", "emergencia nacional",
    "intencionado", "piromane", "pyromane",
]

# Words that indicate NOT an active fire event (political/insurance/analysis)
NOISE_WORDS = [
    "seguro", "aseguradora", "indemnización", "reclamar",
    "pacto", "polític", "gobierno", "ayuso", "sánchez", "puente",
    "prestación", "ayudas", "subvención",
    "opinión", "análisis", "columna",
    "entrevista", "debate",
    "negacionismo", "cambio climático",
]

# Countries we care about (fire events only in these)
RELEVANT_COUNTRIES = {"espana", "francia", "internacional"}

# Strong location keywords for Spain/France with coordinates
LOCATION_COORDS = {
    # España - provincias y ciudades criticas
    "madrid": (40.42, -3.70), "avila": (40.66, -4.70), "ávila": (40.66, -4.70),
    "toledo": (39.86, -4.02), "cuenca": (40.07, -2.14), "guadalajara": (40.63, -3.17),
    "segovia": (40.95, -4.12), "zamora": (41.50, -5.74), "salamanca": (40.97, -5.66),
    "palencia": (42.01, -4.53), "burgos": (42.34, -3.70), "soria": (41.77, -2.47),
    "valladolid": (41.65, -4.72), "leon": (42.60, -5.57), "león": (42.60, -5.57),
    "ponferrada": (42.55, -6.60), "lugo": (43.01, -7.56), "ourense": (42.34, -7.86),
    "coruña": (43.37, -8.40), "pontevedra": (42.43, -8.64), "asturias": (43.36, -5.85),
    "oviedo": (43.36, -5.85), "gijon": (43.54, -5.66), "gijón": (43.54, -5.66),
    "cantabria": (43.20, -4.04), "santander": (43.46, -3.81),
    "bilbao": (43.26, -2.94), "san sebastián": (43.32, -1.98), "vitoria": (42.85, -2.67),
    "la rioja": (42.46, -2.45), "logroño": (42.46, -2.45),
    "navarra": (42.82, -1.65), "pamplona": (42.82, -1.65),
    "zaragoza": (41.65, -0.88), "huesca": (42.14, -0.41), "teruel": (40.34, -1.11),
    "cataluña": (41.59, 1.84), "catalunya": (41.59, 1.84),
    "barcelona": (41.39, 2.17), "tarragona": (41.12, 1.25), "lleida": (41.62, 0.62),
    "girona": (41.98, 2.82),
    "castellón": (39.98, -0.05), "castellon": (39.98, -0.05),
    "valencia": (39.47, -0.38), "alicante": (38.35, -0.48),
    "murcia": (37.98, -1.13),
    "sevilla": (37.38, -5.99), "huelva": (37.26, -6.95), "cádiz": (36.53, -6.28),
    "málaga": (36.72, -4.42), "malaga": (36.72, -4.42),
    "granada": (37.18, -3.60), "jaén": (37.77, -3.79), "córdoba": (37.88, -4.78),
    "almería": (36.84, -2.47), "almeria": (36.84, -2.47),
    "extremadura": (38.88, -6.97), "badajoz": (38.88, -6.97),
    "cáceres": (39.48, -6.37), "caceres": (39.48, -6.37),
    "albacete": (38.99, -1.86),
    "baleares": (39.57, 2.65), "palma": (39.57, 2.65),
    "canarias": (28.12, -15.43), "tenerife": (28.29, -16.63), "gran canaria": (28.12, -15.43),
    "las palmas": (28.12, -15.43),
    # Puntos criticos incendios España
    "sierra oeste": (40.35, -4.20), "valle del tietar": (40.20, -4.70),
    "cebreros": (40.40, -4.47), "el escorial": (40.58, -4.14),
    "robledo de chavela": (40.20, -4.23), "chapineria": (40.38, -4.21),
    "sotillo de la adrada": (40.28, -4.58), "burgohondo": (40.42, -4.62),
    "casavieja": (40.28, -4.77), "navahondilla": (40.33, -4.72),
    "villamanta": (40.27, -4.11), "pelayos de la presa": (40.36, -4.33),
    "valle de iruelas": (40.20, -4.50), "mstoles": (40.32, -3.87),
    "san martin de valdeiglesias": (40.37, -4.39),
    "la vall d'uixó": (39.82, -0.23), "vall d'uixó": (39.82, -0.23),
    "sierra de espadan": (39.90, -0.35), "manises": (39.49, -0.46),
    # Francia
    "gironde": (44.84, -0.58), "bordeaux": (44.84, -0.58), "arcachon": (44.66, -1.17),
    "cap ferret": (44.63, -1.25), "landes": (44.20, -0.80),
    "var": (43.12, 6.13), "corse": (42.15, 9.09),
    "lacanau": (44.98, -1.20), "le porge": (44.98, -1.24),
    "saint-medard-en-jalles": (44.87, -0.65),
}

# False positive substrings to exclude
FALSE_POSITIVES = [
    "brandenburg", "brande", "brandt", "brandi",
    "firewall", "firestone", "firefox", "firefighter", "firefighters",
    "facebook", "firenze", "firehouse",
    "feuerwerk",  # fireworks
    "cease-fire", "ceasefire",
    "armer",  # arms dealer
]


def extract_location(title, source_country=""):
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
    return None, None, None


def score_article(title, source_country):
    title_lower = title.lower()

    # Reject false positives
    for fp in FALSE_POSITIVES:
        if fp in title_lower:
            return 0

    # Reject noise topics
    noise_count = sum(1 for nw in NOISE_WORDS if nw in title_lower)

    # Count active fire signals
    signal_count = sum(1 for sig in ACTIVE_FIRE_SIGNALS if sig in title_lower)

    # Must have at least 1 strong signal
    if signal_count == 0:
        return 0

    # Bonus for location
    _, lat, lon = extract_location(title)
    location_bonus = 2 if lat is not None else 0

    # Penalty for noise
    score = signal_count + location_bonus - (noise_count * 2)

    return max(score, 0)


logger = get_logger("src.collectors.intelhub_bridge")


class IntelHubBridge(BaseCollector):
    name = "Intelligence Hub (incendios)"
    interval_minutes = 10

    def collect(self):
        events = []
        if not HUB_DB.exists():
            logger.warning("BD del Hub no encontrada: %s", HUB_DB)
            return events
        try:
            conn = sqlite3.connect(str(HUB_DB))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT title, source, country, url, published, fetched
                FROM articles
                WHERE published > datetime('now', '-24 hours')
                ORDER BY published DESC
            """).fetchall()

            matched = []
            for row in rows:
                title = row["title"]
                country = (row["country"] or "").lower()

                # Only Spain and France (and intl articles about these)
                if country not in RELEVANT_COUNTRIES:
                    continue

                score = score_article(title, country)
                if score <= 0:
                    continue

                loc_name, lat, lon = extract_location(title, country)
                if lat is None:
                    continue

                matched.append({
                    "title": title,
                    "source": row["source"],
                    "country": row["country"],
                    "url": row["url"],
                    "published": row["published"],
                    "score": score,
                    "lat": lat,
                    "lon": lon,
                    "loc_name": loc_name,
                })

            # Deduplicate by similar titles
            seen_titles = set()
            unique = []
            for m in matched:
                key = m["title"][:40].lower()
                if key not in seen_titles:
                    seen_titles.add(key)
                    unique.append(m)

            for m in unique[:30]:
                level = "warning"
                title_lower = m["title"].lower()
                if any(w in title_lower for w in ["fuera de control", "no controlado", "sin control", "evacu", "desaloj", "emergencia"]):
                    level = "alert"
                if any(w in title_lower for w in ["megaincendio", "megafeu", "mégafeu", "catastróf", "muerto", "muerte", "fallec"]):
                    level = "critical"

                events.append(Event(
                    source="intelhub",
                    source_id=f"ih_{m['url'][:50]}",
                    event_type="fire",
                    subtype="news",
                    lat=m["lat"],
                    lon=m["lon"],
                    radius_m=15000,
                    level=level,
                    title=m["title"][:100],
                    description=f"{m['source']} ({m['country']}). {m['title']}",
                    country=m["country"],
                    region=m["loc_name"] or "",
                ))

            conn.close()
            logger.info("%d artículos totales, %d incendios relevantes", len(rows), len(unique))
        except Exception as e:
            logger.warning("IntelHub bridge: %s", e)
        return events
