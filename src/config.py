"""NearMe OSINT configuration constants.

All tunable thresholds, URLs, timeouts and limits live here.
Import from this module instead of hard-coding values in collectors.
"""
from pathlib import Path

# ── Database ──────────────────────────────────────────────────
POOL_MINCONN = 5
POOL_MAXCONN = 200


# ── Server ────────────────────────────────────────────────────
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8100
API_TITLE = "NearMe OSINT API"
API_VERSION = "0.3"
JWT_EXPIRY_HOURS = 72
RATE_LIMIT_WINDOW = 3600   # seconds
RATE_LIMIT_MAX = 5         # requests per window


# ── AEMET ─────────────────────────────────────────────────────
AEMET_BASE_URL = "https://opendata.aemet.es/opendata/api"
AEMET_INTERVAL_MINUTES = 15
AEMET_REQUEST_TIMEOUT = 15
AEMET_DATA_TIMEOUT = 20
AEMET_TEMP_HEATWAVE_ALERT_C = 40
AEMET_TEMP_HEATWAVE_WARNING_C = 35
AEMET_TEMP_COLD_ALERT_C = -10
AEMET_TEMP_COLD_WARNING_C = -5
AEMET_WIND_ALERT_KMH = 80
AEMET_WIND_WARNING_KMH = 50
AEMET_RAIN_ALERT_MM = 20
AEMET_RAIN_WARNING_MM = 8
AEMET_STATION_RADIUS_M = 25000


# ── Copernicus / GWIS ────────────────────────────────────────
GWIS_URL = "https://gwis.jrc.ec.europa.eu/api/active-fires"
GWIS_LIMIT = 30
GWIS_COUNTRY = "ES"
GWIS_MAX_FIRES = 20
GWIS_FIRE_RADIUS_M = 1500
GWIS_FRP_ALERT_THRESHOLD = 50
CEMS_URL = "https://emergency.copernicus.eu/mapping/activations-rapid/feed"
CEMS_MAX_ACTIVATIONS = 10
CEMS_ACTIVATION_RADIUS_M = 20000
COPERNICUS_INTERVAL_MINUTES = 60


# ── USGS Earthquakes ─────────────────────────────────────────
USGS_EARTHQUAKE_URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    "?format=geojson&region=Spain&minmagnitude=1.5&orderby=time&limit=15"
)
USGS_GLOBAL_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
)
USGS_INTERVAL_MINUTES = 15
USGS_REQUEST_TIMEOUT = 15
USGS_MIN_MAGNITUDE_LOCAL = 2.5
USGS_MIN_MAGNITUDE_GLOBAL = 1.5
USGS_MAG_ALERT = 5
USGS_MAG_WARNING = 4
USGS_RADIUS_PER_MAG = 10000
USGS_RADIUS_MIN_M = 5000
USGS_MAX_GLOBAL_RESULTS = 30
USGS_USER_AGENT = "NearMeOSINT/1.0"


# ── FIRMS (NASA) ─────────────────────────────────────────────
FIRMS_SOURCES = (
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1"
    "/csv/MODIS_C6_1_Global_24h.csv",
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2"
    "/csv/J1_VIIRS_C2_Global_24h.csv",
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs-c2"
    "/csv/SUOMI_VIIRS_C2_Global_24h.csv",
)
FIRMS_REQUEST_TIMEOUT = 30
FIRMS_INTERVAL_MINUTES = 15
FIRMS_USER_AGENT = "Mozilla/5.0 (compatible; NearMeOSINT/1.0)"
FIRMS_SPAIN_BBOX = {
    "min_lat": 27.5,
    "max_lat": 44.0,
    "min_lon": -18.5,
    "max_lon": 4.5,
}
FIRMS_MODIS_CONFIDENCE_MIN = 60
FIRMS_FRP_ALERT = 100
FIRMS_BRIGHTNESS_ALERT = 330
FIRMS_FIRE_RADIUS_M = 1500


# ── DGT Traffic ──────────────────────────────────────────────
DGT_DATEX_URL = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml"
DGT_INTERVAL_MINUTES = 5
DGT_REQUEST_TIMEOUT = 30
DGT_ROAD_RADIUS_M = 2000
DGT_USER_AGENT = "NearMeOSINT/1.0"
DGT_SEVERITY_MAP = {
    "highest": "critical",
    "high": "alert",
    "medium": "warning",
    "low": "info",
}


# ── OpenAQ ───────────────────────────────────────────────────
OPENAQ_BASE_URL = "https://api.openaq.org/v3"
OPENAQ_INTERVAL_MINUTES = 30
OPENAQ_PAGE_LIMIT = 1000
OPENAQ_MAX_PAGES = 3
OPENAQ_REQUEST_TIMEOUT = 15
OPENAQ_MAX_WORKERS = 6
OPENAQ_AIR_QUALITY_RADIUS_M = 10000
OPENAQ_SPAIN_BBOX = {
    "lat_min": 35.8,
    "lat_max": 43.9,
    "lon_min": -10.5,
    "lon_max": 4.5,
}
OPENAQ_THRESHOLDS = {
    "pm25": {"warning": 25, "alert": 55},
    "pm10": {"warning": 50, "alert": 100},
    "o3": {"warning": 100, "alert": 180},
    "no2": {"warning": 100, "alert": 200},
    "co": {"warning": 10000, "alert": 30000},
    "so2": {"warning": 100, "alert": 350},
}
OPENAQ_PARAMETER_IDS = {
    1: "pm10", 2: "pm25", 3: "o3",
    5: "no2", 4: "co", 6: "so2",
}


# ── RENFE ────────────────────────────────────────────────────
RENFE_STATIONS_CSV_URL = (
    "https://ssl.renfe.com/ftransit/Fichero_estaciones/estaciones.csv"
)
RENFE_FEED_URLS = (
    "https://gtfsrt.renfe.com/trip_updates.pb",
    "https://gtfsrt.renfe.com/trip_updates_LD.pb",
)
RENFE_INTERVAL_MINUTES = 15
RENFE_REQUEST_TIMEOUT = 20
RENFE_MIN_DELAY_SECONDS = 600
RENFE_WARNING_DELAY_SECONDS = 1800
RENFE_RADIUS_M = 5000
RENFE_USER_AGENT = "NearMeOSINT/1.0"


# ── REE (Power) ──────────────────────────────────────────────
REE_URL = "https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real"
REE_INTERVAL_MINUTES = 15
REE_REQUEST_TIMEOUT = 20
REE_DEMAND_WARNING_MW = 38000
REE_DEMAND_ALERT_MW = 42000
REE_DEFAULT_LAT = 40.4168
REE_DEFAULT_LON = -3.7038
REE_RADIUS_M = 100000
REE_REGION = "Peninsular"
REE_USER_AGENT = "NearMeOSINT/1.0"


# ── MITECO Air Quality ───────────────────────────────────────
MITECO_URL = "https://ica.miteco.es/datos/ica-ultima-hora.csv"
MITECO_INTERVAL_MINUTES = 30
MITECO_REQUEST_TIMEOUT = 20
MITECO_USER_AGENT = "NearMeOSINT/1.0"
MITECO_MIN_ICA_INDEX = 3
MITECO_ICA_RADIUS_M = 5000
MITECO_ICA_LABELS = {
    0: "Sin datos", 1: "Buena", 2: "Razonablemente buena",
    3: "Regular", 4: "Desfavorable", 5: "Muy desfavorable",
    10: "Buena", 20: "Regular", 30: "Desfavorable",
    40: "Muy desfavorable", 50: "Extremadamente desfavorable",
}
MITECO_ICA_LEVELS = {
    0: "info", 1: "info", 2: "info",
    3: "warning", 4: "warning",
    5: "alert", 10: "info", 20: "warning",
    30: "warning", 40: "alert", 50: "alert",
}


# ── Intelligence Hub ─────────────────────────────────────────
HUB_DB_PATH = Path.home() / "intelligence-hub" / "data" / "news.db"
INTELHUB_INTERVAL_MINUTES = 10
INTELHUB_MAX_AGE_HOURS = 24
INTELHUB_MAX_EVENTS = 30
INTELHUB_FIRE_RADIUS_M = 15000
INTELHUB_DEDUP_KEY_LENGTH = 40
INTELHUB_URL_ID_LENGTH = 50
INTELHUB_MAX_TITLE_LENGTH = 100


# ── Playas ───────────────────────────────────────────────────
PLAYAS_EUSKADI_URL = (
    "https://opendata.euskadi.eus/contenidos/ds_informes_estudios/"
    "playas_euskadi_2026/es_def/adjuntos/playas.geojson"
)
PLAYAS_SANITARIO_URL = (
    "https://opendata.euskadi.eus/contenidos/ds_informes_estudios/"
    "playas_euskadi_2026/es_def/adjuntos/estado_playas.geojson"
)
PLAYAS_BIZKAIA_CKAN_URL = (
    "https://www.opendatabizkaia.eus/es/api/3/action/datastore_search_sql"
)
PLAYAS_INTERVAL_MINUTES = 60
PLAYAS_REQUEST_TIMEOUT = 20
PLAYAS_BEACH_RADIUS_M = 500


# ── IGN Sismología ───────────────────────────────────────────
IGN_EARTHQUAKE_URL = "https://www.ign.es/web/resources/sismologia/tproximos/terremotos.js"
IGN_INTERVAL_MINUTES = 15
IGN_REQUEST_TIMEOUT = 20
IGN_TTL_HOURS = 48
IGN_BBOX = {"min_lat": 27.0, "max_lat": 44.5, "min_lon": -19.0, "max_lon": 4.5}
IGN_MAG_ALERT = 5.0
IGN_MAG_WARNING = 3.0
IGN_EARTHQUAKE_RADIUS_M = 15000
IGN_MAX_AGE_DAYS = 7


# ── Open-Meteo (Índice UV) ───────────────────────────────────
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_INTERVAL_MINUTES = 60
OPEN_METEO_REQUEST_TIMEOUT = 20
OPEN_METEO_TTL_HOURS = 24
OPEN_METEO_UV_CRITICAL = 11.0
OPEN_METEO_UV_ALERT = 8.0
OPEN_METEO_UV_WARNING = 6.0
OPEN_METEO_UV_RADIUS_M = 50000


# ── Energía (REE demanda + precios PVPC) ─────────────────────
ENERGY_PRICE_URL = "https://api.esios.ree.es/archives/70/download_json"
ENERGY_INTERVAL_MINUTES = 15
ENERGY_REQUEST_TIMEOUT = 20
ENERGY_TTL_HOURS = 3
ENERGY_PRICE_ALERT_EUR_MWH = 150
ENERGY_PRICE_WARNING_EUR_MWH = 100
ENERGY_RADIUS_M = 100000
ENERGY_DEFAULT_LAT = 40.4168
ENERGY_DEFAULT_LON = -3.7038
ENERGY_USER_AGENT = "NearMeOSINT/1.0"


# ── Event Status & TTL ───────────────────────────────────────
EVENT_STATUS_ACTIVE = "active"
EVENT_STATUS_RESOLVED = "resolved"
EVENT_STATUS_UPDATED = "updated"

DEFAULT_TTL_HOURS = {
    "road_closure": 12,
    "road_incident": 12,
    "traffic": 6,
    "fire": 24,
    "earthquake": 48,
    "warning": 48,
    "train_delay": 6,
    "air_quality": 6,
    "beach": 24,
    "flood": 48,
    "storm": 24,
    "wind": 12,
    "snow": 24,
    "heatwave": 24,
    "blackout": 24,
    "water_cut": 24,
    "weather": 3,
    "reservoir": 6,
    "radiation": 24,
    "pollen": 24,
    "energy": 3,
}

DEFAULT_TTL_FALLBACK_HOURS = 72

# Fiabilidad base por fuente (0-100) para el confidence score de cada evento.
# Fuentes oficiales en tiempo real -> alto; agregadores/procesados -> medio.
SOURCE_CONFIDENCE = {
    "dgt": 95, "renfe": 94, "aemet": 93, "ign": 92, "proteccion_civil": 92,
    "ree": 90, "energy": 90, "nasa_firms": 90, "usgs": 88, "miteco": 88,
    "embalses": 85, "playas": 85, "copernicus": 85, "uv": 85, "openaq": 84,
    "open_meteo": 82, "intelhub": 60,
}



# ── Pipeline ─────────────────────────────────────────────────
PIPELINE_MAX_EVENTS_PER_COLLECTOR = 5000
PIPELINE_COLLECT_TIMEOUT = 120
PIPELINE_CLEAN_EXPIRED_ON_START = True
PIPELINE_RUN_IN_PARALLEL = True