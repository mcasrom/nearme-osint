import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from src.logging import setup_logging, get_logger

# Load .env if exists
dotenv = Path(__file__).parent / ".env"
if dotenv.exists():
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

logger = get_logger("nearme")

setup_logging()

COLLECTORS = []


def register_collectors():
    try:
        from src.collectors.aemet import AEMETCollector
        COLLECTORS.append(AEMETCollector())
    except Exception as e:
        logger.warning("No se pudo cargar AEMET: %s", e)
    try:
        from src.collectors.copernicus import CopernicusCollector
        COLLECTORS.append(CopernicusCollector())
    except Exception as e:
        logger.warning("No se pudo cargar Copernicus: %s", e)
    try:
        from src.collectors.openaq import OpenAQCollector
        COLLECTORS.append(OpenAQCollector())
    except Exception as e:
        logger.warning("No se pudo cargar OpenAQ: %s", e)
    try:
        from src.collectors.dgt import EarthquakesCollector
        COLLECTORS.append(EarthquakesCollector())
    except Exception as e:
        logger.warning("No se pudo cargar USGS/FIRMS: %s", e)
    try:
        from src.collectors.dgt import DGTTrafficCollector
        COLLECTORS.append(DGTTrafficCollector())
    except Exception as e:
        logger.warning("No se pudo cargar DGT Tráfico: %s", e)
    try:
        from src.collectors.renfe import RENFEDelaysCollector
        COLLECTORS.append(RENFEDelaysCollector())
    except Exception as e:
        logger.warning("No se pudo cargar RENFE: %s", e)
    try:
        from src.collectors.proteccion_civil import ProteccionCivilCollector
        COLLECTORS.append(ProteccionCivilCollector())
    except Exception as e:
        logger.warning("No se pudo cargar Protección Civil: %s", e)
    try:
        from src.collectors.ree import REEPowerCollector
        COLLECTORS.append(REEPowerCollector())
    except Exception as e:
        logger.warning("No se pudo cargar REE: %s", e)
    try:
        from src.collectors.miteco import AirQualityCollector
        COLLECTORS.append(AirQualityCollector())
    except Exception as e:
        logger.warning("No se pudo cargar MITECO calidad aire: %s", e)
    try:
        from src.collectors.intelhub_bridge import IntelHubBridge
        COLLECTORS.append(IntelHubBridge())
    except Exception as e:
        logger.warning("No se pudo cargar IntelHub bridge: %s", e)
    try:
        from src.collectors.playas import PlayasCollector
        COLLECTORS.append(PlayasCollector())
    except Exception as e:
        logger.warning("No se pudo cargar Playas: %s", e)


def run_all():
    now = datetime.now(timezone.utc)
    logger.info("============================================")
    logger.info("NearMe OSINT — Pipeline de recolección")
    logger.info("Fecha: %s UTC", now.strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("============================================")

    from src.db import init_db, clean_expired
    init_db()
    cleaned = clean_expired()
    logger.info("Eventos expirados eliminados: %d", cleaned)

    register_collectors()
    logger.info("Colectores registrados: %d", len(COLLECTORS))

    total_events = 0
    for collector in COLLECTORS:
        events = collector.run()
        total_events += len(events)

    logger.info("Total eventos recolectados: %d", total_events)
    logger.info("Pipeline completado")


if __name__ == "__main__":
    run_all()
