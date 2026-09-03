#!/usr/bin/env python3
"""Descarga municipios de España del WFS INSPIRE del IGN y los convierte a GeoJSON.
Robusto: cada lote se guarda en disco (lote_START.geojson) y al final se fusiona.
Si un lote falla/vuelve vacío se reintenta 2 veces antes de saltarlo.
Uso: python3 fetch_municipios.py
"""
import json, os, subprocess, sys, time, urllib.request

WORK = "/tmp/munis_batch"
os.makedirs(WORK, exist_ok=True)
OUT = "/tmp/municipios_espana.geojson"
WFS = "https://www.ign.es/wfs-inspire/unidades-administrativas"
PAGE = 500
MAX_START = 12000
HEADERS = {"User-Agent": "nearme-osint/1.0 (data load)"}

def fetch(start, count):
    url = ("%s?service=WFS&version=2.0.0&request=GetFeature"
           "&typenames=au:AdministrativeUnit&count=%d&startIndex=%d&sortBy=nationalCode"
           % (WFS, count, start))
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=150) as r:
        return r.read()

def gml_to_features(gml_bytes):
    """Convierte un GML a lista de features filtrando nivel Municipio. Retorna (n, features)."""
    if len(gml_bytes) < 500:
        return 0, []
    tmp_gml = "/tmp/_lote.gml"
    tmp_geo = "/tmp/_lote.geojson"
    for f in (tmp_gml, tmp_geo):
        if os.path.exists(f):
            os.remove(f)
    open(tmp_gml, "wb").write(gml_bytes)
    r = subprocess.run(["ogr2ogr", "-f", "GeoJSON", "-where",
                        "LocalisedCharacterString = 'Municipio'",
                        tmp_geo, tmp_gml, "-lco", "COORDINATE_PRECISION=6"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(tmp_geo):
        return 0, []
    try:
        with open(tmp_geo) as f:
            d = json.load(f)
    except Exception:
        return 0, []
    feats = d.get("features", [])
    return len(feats), feats

def main():
    # 1. Descargar lotes (skip si ya existen en disco)
    start = 0
    while start <= MAX_START:
        lote_file = os.path.join(WORK, "lote_%d.geojson" % start)
        if os.path.exists(lote_file):
            print("skip lote %d (ya en disco)" % start, flush=True)
            start += PAGE
            continue
        data = None
        for attempt in range(3):
            print("descargando lote startIndex=%d (intento %d/3)..." % (start, attempt + 1), flush=True)
            try:
                gml = fetch(start, PAGE)
                n, feats = gml_to_features(gml)
                if n > 0:
                    with open(lote_file, "w", encoding="utf-8") as f:
                        json.dump({"type": "FeatureCollection", "features": feats}, f)
                    print("  %d municipios -> %s" % (n, lote_file), flush=True)
                    data = True
                    break
                else:
                    print("  lote vacio (%d bytes)" % len(gml), flush=True)
            except Exception as e:
                print("  error: %s" % e, flush=True)
            time.sleep(3)
        if data is None:
            print("lote %d no descargable tras 3 intentos; continuando" % start, flush=True)
        start += PAGE
        time.sleep(1)

    # 2. Fusionar todos los lotes
    all_features = []
    for fn in sorted(os.listdir(WORK)):
        if not fn.startswith("lote_"):
            continue
        with open(os.path.join(WORK, fn)) as f:
            d = json.load(f)
        all_features.extend(d.get("features", []))
    print("TOTAL municipios fusionados: %d" % len(all_features), flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": all_features}, f)
    print("guardado:", OUT, "(%d bytes)" % os.path.getsize(OUT))

if __name__ == "__main__":
    main()
