#!/usr/bin/env python3
"""air_quality_daily_snapshot.py — Snapshot diario de la calidad del aire.

Guarda el estado de TODAS las estaciones MITECO activas una vez al dia en la
tabla air_quality_daily (region, nivel, contaminante, lat, lon, fecha). Asi,
pasadas semanas/meses, se puede reconstruir la cronologia real de 1/3/6 meses
de calidad del aire por estacion. El historico EMPIEZA a acumularse el dia que
se despliega este script (07/Sep/2026).

Uso (cron diario ~23:50):
  venv/bin/python scripts/air_quality_daily_snapshot.py
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# cargar .env
dotenv = Path(__file__).resolve().parent.parent / ".env"
if dotenv.exists():
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

from src.db import get_conn, release_conn


def asegurar_tabla(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS air_quality_daily (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL,
            region TEXT NOT NULL,
            municipality TEXT DEFAULT '',
            level TEXT NOT NULL,
            contaminante TEXT DEFAULT '',
            lat DOUBLE PRECISION NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            UNIQUE(fecha, region)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aqd_fecha ON air_quality_daily(fecha)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aqd_region ON air_quality_daily(region)")


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()
        asegurar_tabla(cur)
        # foto actual: una fila por estacion (la mas reciente)
        cur.execute("""
            SELECT DISTINCT ON (region)
                region, municipality, level, title, lat, lon
            FROM events
            WHERE source='miteco' AND status='active'
            ORDER BY region, updated_at DESC
        """)
        filas = cur.fetchall()
        if not filas:
            print("sin estaciones MITECO activas")
            return
        import re
        fecha = datetime.now(timezone.utc).date().isoformat()
        insertadas = 0
        for r in filas:
            region = r[0]
            muni = r[1] or ""
            level = r[2] or "info"
            title = r[3] or ""
            lat = r[4]
            lon = r[5]
            mm = re.search(r"\(([^)]+)\)\s*$", title)
            cont = mm.group(1) if mm else ""
            try:
                cur.execute("""
                    INSERT INTO air_quality_daily (fecha, region, municipality, level, contaminante, lat, lon)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (fecha, region) DO NOTHING
                """, (fecha, region, muni, level, cont, lat, lon))
                insertadas += 1
            except Exception:
                pass
        conn.commit()
        print(f"snapshot {fecha}: {insertadas} estaciones guardadas en air_quality_daily")
    finally:
        release_conn(conn)


if __name__ == "__main__":
    main()
