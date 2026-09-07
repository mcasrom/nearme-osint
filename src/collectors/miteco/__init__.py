import csv
import io
import httpx
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event

ICA_URL = "https://ica.miteco.es/datos/ica-ultima-hora.csv"
# Escala ICA real de MITECO (0-5). El CSV tambien trae 10/20/30/40/50 (misma
# escala x10 de otra codificacion): se normaliza dividiendo por 10 cuando >5.
ICA_LABELS = {
    0: "Sin datos", 1: "Buena", 2: "Razonablemente buena",
    3: "Regular", 4: "Desfavorable", 5: "Muy desfavorable",
}
# Nivel del sistema NearMe para cada ICA (coherente con LEVEL_COLORS del mapa:
# info=azul/verde, warning=amarillo, alert=naranja, critical=rojo). Se guardan
# TODAS las estaciones activas (no solo >=Regular) para poder mostrar el mapa
# completo de mejor/peor calidad en verde/naranja/rojo.
ICA_LEVELS = {
    0: "info", 1: "info", 2: "info",
    3: "warning", 4: "alert", 5: "critical",
}


logger = get_logger("src.collectors.miteco")


class AirQualityCollector(BaseCollector):
    name = "MITECO-CalidadAire"
    source = "miteco"
    interval_minutes = 30

    async def collect(self):
        events = []
        try:
            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "NearMeOSINT/1.0"}, verify=False) as client:
                resp = await client.get(ICA_URL)
            if resp.status_code != 200:
                logger.warning("MITECO: HTTP %s", resp.status_code)
                return events

            reader = csv.DictReader(io.StringIO(resp.text))
            active_stations = 0
            for row in reader:
                try:
                    if row.get("activa", "").lower() != "true":
                        continue
                    indice = row.get("indice", "")
                    if not indice:
                        continue
                    indice = int(indice)
                    # normalizar: el CSV mezcla escala 0-5 con 10-50 (x10)
                    if indice > 5 and indice % 10 == 0:
                        indice = indice // 10

                    level = ICA_LEVELS.get(indice, "info")

                    lat = float(row["latitud"])
                    lon = float(row["longitud"])
                    nombre = row.get("nombre", "")
                    contaminante = row.get("debido_a", "")
                    tipo = row.get("tipo", "")
                    fecha = row.get("fecha", "")

                    ica_label = ICA_LABELS.get(indice, f"Nivel {indice}")
                    events.append(Event(
                        source="miteco",
                        source_id=f"ica_{row.get('cod_estacion', '')}_{fecha}",
                        event_type="air_quality",
                        subtype=tipo.lower(),
                        lat=lat, lon=lon,
                        radius_m=5000,
                        level=level,
                        title=f"Calidad del aire: {ica_label} ({contaminante})",
                        description=f"Estacion: {nombre}. Indice ICA: {indice}/5 ({ica_label}). Contaminante principal: {contaminante}. Tipo: {tipo}. Fecha: {fecha}",
                        country="ES",
                        region=nombre,
                    ))
                    active_stations += 1
                except (ValueError, TypeError, KeyError):
                    pass

            logger.info("MITECO: %d estaciones de calidad del aire (escala completa 0-5)", active_stations)
        except Exception as e:
            logger.warning("MITECO calidad aire: %s", e)
        return events
