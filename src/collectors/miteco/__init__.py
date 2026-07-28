import csv
import io
import requests
from src.collectors.base import BaseCollector
from src.models import Event

ICA_URL = "https://ica.miteco.es/datos/ica-ultima-hora.csv"
ICA_LABELS = {
    0: "Sin datos", 1: "Buena", 2: "Razonablemente buena",
    3: "Regular", 4: "Desfavorable", 5: "Muy desfavorable",
    10: "Buena", 20: "Regular", 30: "Desfavorable",
    40: "Muy desfavorable", 50: "Extremadamente desfavorable"
}
ICA_LEVELS = {
    0: "info", 1: "info", 2: "info",
    3: "warning", 4: "warning",
    5: "alert", 10: "info", 20: "warning",
    30: "warning", 40: "alert", 50: "alert"
}


class AirQualityCollector(BaseCollector):
    name = "MITECO-CalidadAire"
    interval_minutes = 30

    def collect(self):
        events = []
        try:
            resp = requests.get(ICA_URL, timeout=20, headers={"User-Agent": "NearMeOSINT/1.0"}, verify=False)
            if resp.status_code != 200:
                print(f"    MITECO: HTTP {resp.status_code}")
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
                    if indice < 3:
                        continue

                    level = ICA_LEVELS.get(indice, "info")
                    if indice < 3:
                        continue

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
                        description=f"Estacion: {nombre}. Indice ICA: {indice}/6 ({ica_label}). Contaminante principal: {contaminante}. Tipo: {tipo}. Fecha: {fecha}",
                        country="ES",
                        region=nombre,
                    ))
                    active_stations += 1
                except (ValueError, TypeError, KeyError):
                    pass

            print(f"    MITECO: {active_stations} estaciones con calidad aire >= Regular")
        except Exception as e:
            print(f"    [WARN] MITECO calidad aire: {e}")
        return events
