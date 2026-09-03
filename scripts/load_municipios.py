#!/usr/bin/env python3
"""Carga los límites municipales (GeoJSON del IGN) en PostGIS como spain_municipios.
Replica el patrón de spain_ccaa (ST_GeomFromGeoJSON + ST_SetSRID 4326).
Uso: python3 load_municipios.py /tmp/municipios_espana.geojson
"""
import json, os, sys
from pathlib import Path

def load_env(env_path):
    env = {}
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def main():
    if len(sys.argv) < 2:
        print("uso: python3 load_municipios.py <geojson>")
        sys.exit(1)
    geojson_path = sys.argv[1]
    env = load_env("/home/deploy/nearme-osint/.env")
    cfg = {
        "dbname": env.get("DB_NAME", "nearme_osint"),
        "user": env.get("DB_USER", "nearme"),
        "password": env.get("DB_PASSWORD", ""),
        "host": env.get("DB_HOST", "localhost"),
        "port": int(env.get("DB_PORT", "5432")),
    }
    try:
        import psycopg2
    except ImportError:
        sys.path.insert(0, "/home/deploy/nearme-osint/venv/lib/python3.12/site-packages")
        import psycopg2

    data = json.load(open(geojson_path))
    feats = data["features"]
    print("features a cargar:", len(feats))

    conn = psycopg2.connect(**cfg)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spain_municipios (
            cod_ine TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            geom GEOMETRY(MultiPolygon, 4326) NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_muni_geom ON spain_municipios USING GIST(geom)")
    cur.execute("SELECT count(*) FROM spain_municipios")
    existing = cur.fetchone()[0]
    print("filas existentes:", existing)

    n = 0
    for f in feats:
        props = f.get("properties", {})
        code = str(props.get("nationalCode") or props.get("localId") or "").strip()
        name = str(props.get("text") or "").strip()
        if not code or not name or not f.get("geometry"):
            continue
        cur.execute(
            "INSERT INTO spain_municipios (cod_ine, name, geom) VALUES (%s, %s, "
            "ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)) "
            "ON CONFLICT (cod_ine) DO UPDATE SET name = EXCLUDED.name, geom = EXCLUDED.geom",
            (code, name, json.dumps(f["geometry"])))
        n += 1
    conn.commit()
    cur.execute("SELECT count(*) FROM spain_municipios")
    print("cargados/actualizados:", n, "| total en tabla:", cur.fetchone()[0])
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
