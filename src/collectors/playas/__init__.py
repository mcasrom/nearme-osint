import os
import re
import requests
from datetime import datetime, timezone
from src.collectors.base import BaseCollector
from src.logging import get_logger
from src.models import Event

EUSKADI_PLAYAS_URL = "https://opendata.euskadi.eus/contenidos/ds_informes_estudios/playas_euskadi_2026/es_def/adjuntos/playas.geojson"
EUSKADI_SANITARIO_URL = "https://opendata.euskadi.eus/contenidos/ds_informes_estudios/playas_euskadi_2026/es_def/adjuntos/estado_playas.geojson"
BIZKAIA_CKAN_URL = "https://www.opendatabizkaia.eus/es/api/3/action/datastore_search_sql"

FLAG_LEVEL = {
    "verde": "info",
    "berdea": "info",
    "amarilla": "warning",
    "horia": "warning",
    "roja": "alert",
    "gorria": "alert",
}

RECOM_LEVEL = {
    "baño libre": "info",
    "bainua librea": "info",
    "recomendación de no baño": "warning",
    "ez bainatzeko gomendioa": "warning",
    "prohibición de baño": "alert",
    "bainua debekatuta": "alert",
}


def _normalize(name: str) -> str:
    name = name.upper().strip()
    name = re.sub(r'^PLAYA\s+(DE\s+)?', '', name)
    name = re.sub(r'\s*\(.*?\)\s*', '', name)
    name = re.sub(r'\s*-\s*.*', '', name)
    name = name.strip()
    return name


def _get_json(url: str, timeout: int = 20):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.warning("Error fetching %s: %s", url, e)
    return None


logger = get_logger("src.collectors.playas")


class PlayasCollector(BaseCollector):
    name = "Playas"
    interval_minutes = 60

    def collect(self):
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        events = []

        playas = self._fetch_playas_list()
        if not playas:
            logger.warning("No se pudo obtener lista de playas")
            return []

        sanitario = self._fetch_sanitario()
        bizkaia = self._fetch_bizkaia_status()

        for nombre, info in playas.items():
            try:
                event = self._build_event(nombre, info, sanitario, bizkaia, hoy)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning("Error con playa %s: %s", nombre, e)

        logger.info("%d playas, %d eventos", len(playas), len(events))
        return events

    def _fetch_playas_list(self) -> dict:
        data = _get_json(EUSKADI_PLAYAS_URL)
        if not data:
            return {}
        result = {}
        for f in data.get("features", []):
            p = f["properties"]
            name = p.get("bainueremuazonadebano", "")
            if "EMBALSE" in name.upper():
                continue
            coords = f["geometry"]["coordinates"]
            norm = _normalize(name)
            result[norm] = {
                "name": name,
                "municipality": p.get("udalerriamunicipio", ""),
                "territory": p.get("lurraldeaterritorio", ""),
                "lat": float(coords[1]),
                "lon": float(coords[0]),
                "eustat_code": p.get("eustatkodeacodigoeustat", ""),
                "msc_code": p.get("msckodeacodigomsc", ""),
            }
        return result

    def _fetch_sanitario(self) -> dict:
        data = _get_json(EUSKADI_SANITARIO_URL)
        if not data:
            return {}
        result = {}
        for f in data.get("features", []):
            p = f["properties"]
            name = p.get("bainueremuazonadebano", "")
            if "EMBALSE" in name.upper():
                continue
            norm = _normalize(name)
            rec = p.get("bainurakogomendioarecomendacio", "")
            clasif = p.get("urtekosailkapenaclasificaciona", "")
            # Keep worst-case per beach
            if norm not in result:
                result[norm] = {
                    "recomendacion": rec,
                    "clasificacion": clasif,
                    "ecoli": p.get("ecolinmp100ml", ""),
                    "enterococos": p.get("enterococosnmp100ml", ""),
                    "fecha": p.get("laginketadatafechamuestreo", ""),
                }
            else:
                existing = result[norm]
                if "insuficiente" in clasif.lower() and "insuficiente" not in existing.get("clasificacion", "").lower():
                    result[norm] = {
                        "recomendacion": rec,
                        "clasificacion": clasif,
                        "ecoli": p.get("ecolinmp100ml", ""),
                        "enterococos": p.get("enterococosnmp100ml", ""),
                        "fecha": p.get("laginketadatafechamuestreo", ""),
                    }
        return result

    def _fetch_bizkaia_status(self) -> dict:
        sql = """SELECT * FROM "845e3c78-344d-4015-a367-79bd3ae60744"
                 ORDER BY "DATA/FECHA" DESC LIMIT 200"""
        try:
            r = requests.get(BIZKAIA_CKAN_URL, params={"sql": sql}, timeout=15)
            if r.status_code != 200:
                return {}
            data = r.json()
            if not data.get("success"):
                return {}
            result = {}
            for rec in data["result"].get("records", []):
                norm = _normalize(rec.get("HONDARTZA/PLAYA", ""))
                if norm not in result:
                    result[norm] = {
                        "flag": rec.get("BANDERA_CAS/BANDERA_CAS", ""),
                        "temp_agua": rec.get("UR TENPERATURA/TEMPERATURA AGUA (ºC)", ""),
                        "temp_ambiente": rec.get("GIROKO TENPERATURA/TEMPERATURA AMBIENTE (ºC)", ""),
                        "oleaje": rec.get("OLATUAK_CAS/OLEAJE_CAS", ""),
                        "viento": rec.get("HAIZEA_CAS/VIENTO_CAS", ""),
                        "ocupacion": rec.get("OKUPAZIOA_CAS/OCUPACION_CAS", ""),
                        "medusas": rec.get("MARMOKENGATIKO ABISUA_CAS/AVISO POR MEDUSAS_CAS", ""),
                        "fecha": rec.get("DATA/FECHA", ""),
                        "municipio": rec.get("UDALERRIA/MUNICIPIO", ""),
                    }
            return result
        except Exception as e:
            logger.warning("Error Bizkaia CKAN: %s", e)
            return {}

    def _build_event(self, nombre: str, info: dict, sanitario: dict, bizkaia: dict, hoy: str):
        lat = info["lat"]
        lon = info["lon"]

        status = sanitario.get(nombre, {})
        bzk = bizkaia.get(nombre, {})

        flag = bzk.get("flag", "")
        temp_agua = bzk.get("temp_agua", "")
        oleaje = bzk.get("oleaje", "")
        medusas = bzk.get("medusas", "")
        ocupacion = bzk.get("ocupacion", "")
        viento = bzk.get("viento", "")

        recomendacion = status.get("recomendacion", "")
        clasificacion = status.get("clasificacion", "")
        ecoli = status.get("ecoli", "")
        enterococos = status.get("enterococos", "")

        level = "info"
        # Priority: flag > sanitary recommendation > default
        for flag_val in [flag.lower()]:
            if flag_val in FLAG_LEVEL:
                level = FLAG_LEVEL[flag_val]
                break
        if level == "info":
            for rec_val in [recomendacion.lower()]:
                for key, lvl in RECOM_LEVEL.items():
                    if key in rec_val:
                        level = lvl
                        break

        parts = []
        if flag:
            parts.append(f"Bandera: {flag}")
        if temp_agua:
            parts.append(f"Agua: {temp_agua}°C")
        if oleaje:
            parts.append(f"Oleaje: {oleaje}")
        if medusas:
            parts.append(f"Medusas: {medusas}")
        if ocupacion:
            parts.append(f"Ocupación: {ocupacion}")
        if viento:
            parts.append(f"Viento: {viento}")
        if recomendacion:
            parts.append(f"Recomendación: {recomendacion}")
        if clasificacion:
            parts.append(f"Clasif: {clasificacion}")
        if ecoli:
            parts.append(f"E. coli: {ecoli}")
        if enterococos:
            parts.append(f"Enterococos: {enterococos}")

        desc = " | ".join(parts) if parts else "Sin datos disponibles"
        title = info["name"]
        if flag:
            title += f" ({flag})"

        source_id = f"playa_{info['msc_code']}_{hoy}"

        return Event(
            source="playas",
            source_id=source_id,
            event_type="beach",
            subtype="estado",
            lat=lat, lon=lon,
            radius_m=500,
            level=level,
            title=title,
            description=desc,
            country="ES",
            region=info.get("territory", ""),
            municipality=info.get("municipality", ""),
            expires_at=f"{hoy}T23:59:59Z",
        )
