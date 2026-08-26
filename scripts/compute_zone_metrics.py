#!/usr/bin/env python3
"""compute_zone_metrics.py — métricas zonales diarias de NearMe (opción A).

Agrega por día y CCAA (spatial join contra spain_ccaa) + nacional:
  eventos totales/por nivel, diversidad de fuentes, persistencia media,
  convergencia (<50km y <6h entre fuentes distintas).

Recursos: 1 conexión, transacción por día, sin escaneos fuera de rango.
Uso:
  python3 compute_zone_metrics.py                 # agrega AYER (modo cron)
  python3 compute_zone_metrics.py --day 2026-08-01
  python3 compute_zone_metrics.py --backfill 2026-07-28 2026-08-25
"""
import sys, time, statistics
from datetime import date, timedelta
from src.db import get_conn

CCAA_FALLBACK = ("XX", "Sin asignar")

DDL = """
CREATE TABLE IF NOT EXISTS zone_metrics (
    stat_date        date NOT NULL,
    scope            text NOT NULL,
    zone_id          text NOT NULL,
    zone_name        text NOT NULL,
    source           text NOT NULL,
    events_total     int  NOT NULL DEFAULT 0,
    events_warning   int  NOT NULL DEFAULT 0,
    events_alert     int  NOT NULL DEFAULT 0,
    events_critical  int  NOT NULL DEFAULT 0,
    diversity        int  NOT NULL DEFAULT 0,
    persistence_h    real,
    convergence_events int NOT NULL DEFAULT 0,
    PRIMARY KEY (stat_date, scope, zone_id, source)
);
"""

def ensure_schema(cur):
    cur.execute(DDL)

def day_metrics(cur, d):
    # 1) agregado por ccaa x fuente (+ persistencia por zona)
    cur.execute("""
        WITH z AS (
            SELECT b.cod_ccaa AS zid, b.name AS zname, e.source, e.level,
                   EXTRACT(EPOCH FROM (e.expires_at - e.created_at))/3600.0 AS dur
            FROM events e
            JOIN spain_ccaa b ON ST_Within(e.geom, b.geom)
            WHERE e.created_at::date = %s AND e.geom IS NOT NULL
        )
        SELECT zid, zname, source, count(*),
               count(*) FILTER (WHERE level='warning'),
               count(*) FILTER (WHERE level='alert'),
               count(*) FILTER (WHERE level='critical')
        FROM z GROUP BY 1,2,3
    """, (d,))
    rows = cur.fetchall()

    cur.execute("""
        SELECT b.cod_ccaa, b.name,
               avg(EXTRACT(EPOCH FROM (e.expires_at - e.created_at))/3600.0)
        FROM events e JOIN spain_ccaa b ON ST_Within(e.geom, b.geom)
        WHERE e.created_at::date = %s AND e.geom IS NOT NULL
          AND e.expires_at IS NOT NULL AND e.expires_at > e.created_at
        GROUP BY 1,2
    """, (d,))
    pers = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    # 2) convergencia: eventos con vecino de OTRA fuente <50km y <6h
    cur.execute("""
        SELECT b.cod_ccaa, count(DISTINCT e.id)
        FROM events e
        JOIN spain_ccaa b ON ST_Within(e.geom, b.geom)
        WHERE e.created_at::date = %s AND e.geom IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM events e2
            WHERE e2.id <> e.id AND e2.source <> e.source
              AND e2.geom IS NOT NULL
              AND ST_DWithin(e.geom, e2.geom, 50000)
              AND e2.created_at BETWEEN e.created_at - interval '6 hours'
                                   AND e.created_at + interval '6 hours'
          )
        GROUP BY 1
    """, (d,))
    conv = dict(cur.fetchall())

    return rows, pers, conv

def write_day(cur, d):
    cur.execute("DELETE FROM zone_metrics WHERE stat_date = %s", (d,))
    rows, pers, conv = day_metrics(cur, d)

    zones = {}
    for zid, zname, src, tot, warn, aler, crit in rows:
        z = zones.setdefault(zid, {"name": zname, "tot": 0, "warn": 0, "ale": 0, "cri": 0, "srcs": {}, "rows": []})
        z["tot"] += tot; z["warn"] += warn; z["ale"] += aler; z["cri"] += crit
        z["srcs"][src] = z["srcs"].get(src, 0) + tot
        z["rows"].append((zid, zname, src, tot, warn, aler, crit))

    ins = """INSERT INTO zone_metrics VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    n = 0
    for zid, z in zones.items():
        pname, ph = pers.get(zid, (z["name"], None))
        cv = conv.get(zid, 0)
        # filas por fuente
        for r in z["rows"]:
            cur.execute(ins, (d, "ccaa", r[0], r[1], r[2], r[3], r[4], r[5], r[6], 0, None, 0)); n += 1
        # fila agregada de la zona
        cur.execute(ins, (d, "ccaa", zid, z["name"], "ALL", z["tot"], z["warn"], z["ale"],
                          z["cri"], len(z["srcs"]), round(ph, 2) if ph else None, cv)); n += 1
    # nacional (suma de zonas asignadas)
    if zones:
        tot = sum(z["tot"] for z in zones.values()); warn = sum(z["warn"] for z in zones.values())
        ale = sum(z["ale"] for z in zones.values()); cri = sum(z["cri"] for z in zones.values())
        div = max(len(z["srcs"]) for z in zones.values())
        phs = [ph for (_, ph) in pers.values() if ph]
        cvt = sum(conv.get(zid, 0) for zid in zones)
        cur.execute(ins, (d, "national", "ES", "España", "ALL", tot, warn, ale, cri, div,
                          round(statistics.mean(phs), 2) if phs else None, cvt)); n += 1
    return n, sum(z["tot"] for z in zones.values())

def main():
    args = sys.argv[1:]
    con = get_conn(); cur = con.cursor()
    ensure_schema(cur); con.commit()

    days = []
    if "--backfill" in args:
        i = args.index("--backfill")
        d0 = date.fromisoformat(args[i+1]); d1 = date.fromisoformat(args[i+2])
        days = [d0 + timedelta(days=k) for k in range((d1-d0).days + 1)]
    elif "--day" in args:
        days = [date.fromisoformat(args[args.index("--day")+1])]
    else:
        days = [date.today() - timedelta(days=1)]

    t0 = time.time()
    for d in days:
        nrows, nevents = write_day(cur, d)
        con.commit()   # transacción por día: reanudable y ligera
        print(f"{d} · zonas-filas={nrows} eventos-asignados={nevents}", flush=True)
    print(f"[FIN] {len(days)} días en {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()
