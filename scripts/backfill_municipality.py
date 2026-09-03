#!/usr/bin/env python3
"""Backfill espacial: asigna municipio a los eventos que lo tienen vacío.
Usa el índice GIST de events.geom contra spain_municipios.geom.
Solo actualiza events.municipality cuando está vacío y hay un municipio que lo contiene.
Uso: python3 backfill_municipality.py [--fuente ign]
"""
import os, sys

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
    filtro_fuente = None
    if len(sys.argv) > 2 and sys.argv[1] == "--fuente":
        filtro_fuente = sys.argv[2]

    sys.path.insert(0, "/home/deploy/nearme-osint/venv/lib/python3.12/site-packages")
    import psycopg2

    env = load_env("/home/deploy/nearme-osint/.env")
    cfg = {
        "dbname": env.get("DB_NAME", "nearme_osint"),
        "user": env.get("DB_USER", "nearme"),
        "password": env.get("DB_PASSWORD", ""),
        "host": env.get("DB_HOST", "localhost"),
        "port": int(env.get("DB_PORT", "5432")),
    }
    conn = psycopg2.connect(**cfg)
    cur = conn.cursor()

    where = "municipality = '' AND geom IS NOT NULL AND status IN ('active','updated')"
    if filtro_fuente:
        where += " AND source = %s"
        params = (filtro_fuente,)
    else:
        params = ()

    cur.execute("SELECT count(*) FROM events WHERE %s" % where, params)
    pending = cur.fetchone()[0]
    print("eventos con municipality vacio:", pending)

    sql = """
        UPDATE events e
        SET municipality = m.name,
            updated_at = NOW()
        FROM spain_municipios m
        WHERE e.%s AND ST_Within(e.geom, m.geom)
    """ % where
    # No se puede reutilizar el mismo WHERE con placeholders en UPDATE... ejecutamos
    # version con condicion duplicada. Mejor approach: usar subquery con CTE.
    conn.close()
    conn = psycopg2.connect(**cfg)
    cur = conn.cursor()
    if filtro_fuente:
        cur.execute("""
            WITH candidatos AS (
                SELECT e.id, m.name
                FROM events e
                JOIN spain_municipios m ON ST_Within(e.geom, m.geom)
                WHERE e.municipality = '' AND e.geom IS NOT NULL
                  AND e.status IN ('active','updated')
                  AND e.source = %s
            )
            UPDATE events e2
            SET municipality = c.name, updated_at = NOW()
            FROM candidatos c
            WHERE e2.id = c.id
        """, (filtro_fuente,))
    else:
        cur.execute("""
            WITH candidatos AS (
                SELECT e.id, m.name
                FROM events e
                JOIN spain_municipios m ON ST_Within(e.geom, m.geom)
                WHERE e.municipality = '' AND e.geom IS NOT NULL
                  AND e.status IN ('active','updated')
            )
            UPDATE events e2
            SET municipality = c.name, updated_at = NOW()
            FROM candidatos c
            WHERE e2.id = c.id
        """)
    conn.commit()
    print("actualizados:", cur.rowcount)
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
