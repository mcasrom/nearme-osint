import os
import sys
import asyncio
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
    # Copernicus EMS retirado: el feed de activaciones se movio a un portal web
    # (mapping.emergency.copernicus.eu) sin feed JSON publico; incendios cubiertos
    # por NASA FIRMS y terremotos por USGS (colector DGT).
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
    try:
        from src.collectors.embalses import EmbalsesCollector
        COLLECTORS.append(EmbalsesCollector())
    except Exception as e:
        logger.warning("No se pudo cargar Embalses: %s", e)
    try:
        from src.collectors.ign import IGNSeismicCollector
        COLLECTORS.append(IGNSeismicCollector())
    except Exception as e:
        logger.warning("No se pudo cargar IGN sismología: %s", e)
    try:
        from src.collectors.uv import UVCollector
        COLLECTORS.append(UVCollector())
    except Exception as e:
        logger.warning("No se pudo cargar UV: %s", e)
    try:
        from src.collectors.energy import EnergyCollector
        COLLECTORS.append(EnergyCollector())
    except Exception as e:
        logger.warning("No se pudo cargar Energía: %s", e)


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

    total_events = asyncio.run(_run_collectors())
    logger.info("Total eventos recolectados: %d", total_events)
    logger.info("Pipeline completado")


async def _run_collectors():
    from src.metrics import PipelineMetrics

    metrics = PipelineMetrics.get()
    start = datetime.now(timezone.utc)

    async def timed_run(collector):
        cstart = datetime.now(timezone.utc)
        try:
            result = await collector.run()
            elapsed = (datetime.now(timezone.utc) - cstart).total_seconds()
            metrics.record_run(collector.name, success=True, latency_s=elapsed, events=len(result))
            return result
        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - cstart).total_seconds()
            metrics.record_run(collector.name, success=False, latency_s=elapsed, events=0)
            logger.error("Error en colector %s: %s", collector.name, e)
            return []

    futures = [timed_run(c) for c in COLLECTORS]
    results = await asyncio.gather(*futures)
    total_events = sum(len(r) for r in results)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("Colectores ejecutados en %.1fs", elapsed)
    return total_events


if __name__ == "__main__":
    run_all()
