"""Agregación diaria de estadísticas desde los eventos (tabla daily_stats).

Calcula métricas por día y fuente a partir de los eventos recolectados:
  - embalses: nivel medio (%)
  - renfe: retraso medio (min) y nº de retrasos
  - nasa_firms: incendios (nº), FRP total y hectáreas estimadas (área por píxel activo)
  - miteco: ICA medio y nº de días con calidad Regular/Bad

Uso:
  python3 compute_daily_stats.py            -> calcula ayer y hoy
  python3 compute_daily_stats.py --backfill  -> recalcula los últimos 30 días
  python3 compute_daily_stats.py --days 60   -> recalcula los últimos N días

Cron sugerido: 0 23 * * * (diario)
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_conn

# Área quemada estimada por detección activa (ha/píxel) según sensor, a partir
# del tamaño nominal del píxel (MODIS ~1 km², VIIRS ~375 m) y del factor de área
# quemada por detección típico de las estimaciones satelitales. Etiquetar como
# estimado (≈): una misma detección puede persistir varios días.
HA_PER_PIXEL_MODIS = 84.0
HA_PER_PIXEL_VIIRS = 14.0


def _row(cur, sql, params=()):
    cur.execute(sql, params)
    r = cur.fetchone()
    return r[0] if r else None


def compute_day(conn, day: date):
    cur = conn.cursor()
    start = day.strftime("%Y-%m-%d 00:00:00")
    end = (day + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

    stats = []

    # Embalses: nivel medio
    # Los eventos de embalse se upsertean (created_at fijo desde el primer insert,
    # updated_at se renueva cada 30 min). Para no perder el histórico (días con
    # created_at) ni quedarse atascado en el pasado, usamos la fecha más reciente
    # de ambas (GREATEST): los días antiguos cuentan por created_at, los recientes
    # por updated_at.
    cur.execute(
        "SELECT description FROM events WHERE source='embalses' "
        "AND GREATEST(created_at, updated_at) >= %s AND GREATEST(created_at, updated_at) < %s",
        (start, end))
    rows = cur.fetchall()
    niveles = []
    for (desc,) in rows:
        m = re.search(r"Nivel:\s*([\d.]+)%", desc or "")
        if m:
            niveles.append(float(m.group(1)))
    if niveles:
        stats.append(("embalses", "nivel_medio_pct", sum(niveles) / len(niveles)))

    # RENFE: retraso medio y nº
    cur.execute(
        "SELECT description, title FROM events WHERE source='renfe' AND created_at >= %s AND created_at < %s",
        (start, end))
    rows = cur.fetchall()
    delays = []
    for desc, title in rows:
        m = re.search(r"Retraso:\s*(\d+)\s*minutos", desc or "")
        if not m:
            m = re.search(r"\+(\d+)min", title or "")
        if m:
            delays.append(float(m.group(1)))
    if delays:
        stats.append(("renfe", "retraso_medio_min", sum(delays) / len(delays)))
        stats.append(("renfe", "num_retrasos", float(len(delays))))

    # Incendios (NASA FIRMS): nº, FRP total, ha estimadas
    cur.execute(
        "SELECT description FROM events WHERE source='nasa_firms' AND created_at >= %s AND created_at < %s",
        (start, end))
    rows = cur.fetchall()
    frps = []
    ha_est = 0.0
    for (desc,) in rows:
        m = re.search(r"FRP:\s*([\d.]+)\s*MW", desc or "")
        if m:
            frps.append(float(m.group(1)))
        s = re.search(r"Sat[ée]lite:\s*([^.\n]+)", desc or "")
        sat = s.group(1).strip().upper() if s else ""
        is_viirs = any(k in sat for k in ("NPP", "NOAA", "VIIRS"))
        ha_est += HA_PER_PIXEL_VIIRS if is_viirs else HA_PER_PIXEL_MODIS
    if rows:
        stats.append(("nasa_firms", "incendios", float(len(rows))))
    if frps:
        total_frp = sum(frps)
        stats.append(("nasa_firms", "frp_total_mw", total_frp))
    if ha_est:
        stats.append(("nasa_firms", "hectareas_est", ha_est))

    # Calidad del aire (MITECO): ICA medio y días Regular/Bad
    cur.execute(
        "SELECT description FROM events WHERE source='miteco' AND created_at >= %s AND created_at < %s",
        (start, end))
    rows = cur.fetchall()
    icas = []
    regular = 0
    for (desc,) in rows:
        m = re.search(r"Indice ICA:\s*(\d+)/", desc or "")
        if m:
            icas.append(float(m.group(1)))
        if re.search(r"\((Regular|Bad|Muy malo|Muy desfavorable)\)", desc or ""):
            regular += 1
    if icas:
        stats.append(("miteco", "ica_medio", sum(icas) / len(icas)))
        stats.append(("miteco", "dias_regular_bad", float(regular)))

    if not stats:
        return stats
    cur.execute(
        "DELETE FROM daily_stats WHERE stat_date=%s", (day.isoformat(),))
    for src, metric, value in stats:
        cur.execute(
            "INSERT INTO daily_stats (stat_date, source, metric, value) VALUES (%s, %s, %s, %s)",
            (day.isoformat(), src, metric, value))
    conn.commit()
    return stats


def main():
    args = sys.argv[1:]
    if "--backfill" in args or "--days" in args:
        if "--days" in args:
            n = int(args[args.index("--days") + 1])
        else:
            n = 30
        days = [date.today() - timedelta(days=i) for i in range(n)]
    else:
        days = [date.today() - timedelta(days=1), date.today()]
    conn = get_conn()
    total = 0
    for day in days:
        stats = compute_day(conn, day)
        if stats:
            total += len(stats)
            print(f"{day}: {len(stats)} métricas")
    conn.close()
    print(f"total métricas escritas: {total}")


if __name__ == "__main__":
    main()
