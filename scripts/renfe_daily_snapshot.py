#!/usr/bin/env python3
"""renfe_daily_snapshot.py — Acumulador diario de retrasos RENFE.

Guarda en la tabla `renfe_daily` el conteo agregado de retrasos del dia en
curso por (subtipo, banda de severidad). Se ejecuta VARIAS veces al dia
(cron ~05:50, 11:50, 17:50 y 23:50) porque los eventos train_delay tienen
TTL de 6h: un unico snapshot al cierre del dia perderia los retrasos de la
madrugada ya purgados. Al re-upsertar con `GREATEST` se conserva el MAXIMO
progresivo del dia (= el conteo mas completo alcanzado).

Bandas contiguas/excluyentes (el feed captura >=10 min):
  10-14, 15-29, 30-44, 45-59, >=60

Asi, pasados dias, se puede reconstruir un resumen semanal/mensual real.
El historico EMPIEZA a acumularse el dia que se despliega este script.

Uso (cron):
  cd /home/deploy/nearme-osint && PYTHONPATH=. venv/bin/python scripts/renfe_daily_snapshot.py
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# cargar .env (mismo patron que air_quality_daily_snapshot.py)
dotenv = Path(__file__).resolve().parent.parent / ".env"
if dotenv.exists():
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

from src.db import get_conn, release_conn  # noqa: E402


def bandas(delay_min):
    """Banda contigua de severidad para un retraso en minutos (>=10)."""
    if delay_min >= 60:
        return ">=60"
    if delay_min >= 45:
        return "45-59"
    if delay_min >= 30:
        return "30-44"
    if delay_min >= 15:
        return "15-29"
    return "10-14"


def asegurar_tabla(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS renfe_daily (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL,
            subtipo TEXT NOT NULL,
            banda TEXT NOT NULL,
            n INTEGER NOT NULL DEFAULT 0,
            UNIQUE(fecha, subtipo, banda)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rd_fecha ON renfe_daily(fecha)")


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()
        asegurar_tabla(cur)

        # solo eventos del dia en curso (created_at real, no estado actual)
        cur.execute("""
            SELECT subtype, title
            FROM events
            WHERE source='renfe' AND event_type='train_delay'
              AND created_at >= date_trunc('day', now())
              AND created_at <  date_trunc('day', now()) + interval '1 day'
        """)
        filas = cur.fetchall()

        import re
        conteo = {}  # (subtipo, banda) -> n
        for subtype, title in filas:
            m = re.search(r": \+(\d+)min", title or "")
            if not m:
                continue
            delay = int(m.group(1))
            st = subtype or "desconocido"
            key = (st, bandas(delay))
            conteo[key] = conteo.get(key, 0) + 1

        fecha = datetime.now(timezone.utc).date().isoformat()
        for (st, banda), n in sorted(conteo.items()):
            cur.execute("""
                INSERT INTO renfe_daily (fecha, subtipo, banda, n)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (fecha, subtipo, banda)
                DO UPDATE SET n = GREATEST(renfe_daily.n, EXCLUDED.n)
            """, (fecha, st, banda, n))
        conn.commit()
        total = sum(conteo.values())
        print(f"snapshot {fecha}: {len(conteo)} claves, {total} retrasos (maximo progresivo)")
    finally:
        release_conn(conn)


if __name__ == "__main__":
    main()