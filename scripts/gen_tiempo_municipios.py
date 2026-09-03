#!/usr/bin/env python3
"""Genera páginas SEO "Tiempo en {municipio}" desde el histórico AEMET.
Para cada estación AEMET con observación reciente (event_history), geocodifica el
municipio y genera tiempo-{slug}.html con la última temperatura registrada.

Uso:
    python3 scripts/gen_tiempo_municipios.py            # genera páginas
    python3 scripts/gen_tiempo_municipios.py --dry     # muestra sin escribir
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "/home/deploy/nearme-osint"
FRONT = os.path.join(BASE, "frontend")
SITE = "https://nearme.viajeinteligencia.com"


def load_env(env_path):
    env = {}
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def slug(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def fetch_stations(conn):
    """Última observación AEMET por estación (DISTINCT ON lat/lon redondeado)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (round(lat::numeric,3), round(lon::numeric,3))
               lat, lon, title, snapshot_at
        FROM event_history
        WHERE source = 'aemet'
        ORDER BY round(lat::numeric,3), round(lon::numeric,3), snapshot_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows  # (lat, lon, title, snapshot_at)


def muni_for_point(conn, lat, lon):
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM spain_municipios "
        "WHERE ST_Within(ST_SetSRID(ST_MakePoint(%s, %s), 4326), geom) LIMIT 1",
        (lon, lat))
    r = cur.fetchone()
    cur.close()
    return r[0] if r else None


def parse_temp(title):
    m = re.search(r"T:\s*(-?[\d.]+)C", title or "")
    return float(m.group(1)) if m else None


def build_html(name, slugv, station_name, temp, ts, muni_code):
    if temp is None:
        return None
    icon = "🌡️" if temp >= 20 else ("❄️" if temp < 8 else "🌤️")
    temp_txt = ("%.1f" % temp).replace(".", ",")
    title = "Tiempo en %s ahora: %s °C" % (name, temp_txt)
    desc = ("Temperatura actual en %s: %s °C (estación %s). Datos en vivo de AEMET "
            "compilados por NearMe." % (name, temp_txt, station_name))
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = "%s/tiempo-%s" % (SITE, slugv)
    ts_txt = ts.strftime("%d/%m %H:%M") if hasattr(ts, "strftime") else str(ts)
    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s · NearMe</title>
<meta name="description" content="%s">
<meta name="robots" content="index, follow">
<link rel="canonical" href="%s">
<meta property="og:type" content="article">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<meta property="og:locale" content="es_ES">
<meta property="og:image" content="https://nearme.viajeinteligencia.com/og-image.png">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"NewsArticle","headline":"%s","datePublished":"%s","inLanguage":"es","url":"%s","publisher":{"@type":"Organization","name":"NearMe OSINT","url":"https://nearme.viajeinteligencia.com"}}
</script>
<style>
  :root{--bg:#F4F6FB;--panel:#FFFFFF;--line:#D6DDEA;--text:#16202E;--text2:#33415C;--dim:#5B6B84;--faint:#8A97AC;--amber:#D9820A;--green:#0E9F6E;--cyan:#0E9FAE;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:-apple-system,system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.65;}
  .wrap{max-width:720px;margin:0 auto;padding:28px 20px 60px;}
  .top{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:18px;border-bottom:1px solid var(--line);padding-bottom:16px;}
  h1{font-size:26px;font-weight:800;letter-spacing:-0.02em;}
  .meta{font-size:11px;color:var(--faint);font-family:ui-monospace,monospace;margin-bottom:20px;}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;display:flex;align-items:center;gap:18px;margin-bottom:18px;}
  .big{font-size:52px;font-weight:800;letter-spacing:-0.03em;color:var(--text);line-height:1;}
  .unit{font-size:20px;color:var(--dim);font-weight:600;}
  .stat{font-size:13px;color:var(--text2);}
  .stat b{color:var(--text);}
  .fresh{display:inline-block;background:var(--panel);border:1px solid var(--green);color:var(--green);font-family:ui-monospace,monospace;font-size:11px;padding:4px 12px;border-radius:999px;margin-bottom:18px;}
  p{font-size:14.5px;color:var(--text2);margin-bottom:12px;}
  .foot{margin-top:34px;font-size:11px;color:var(--faint);text-align:center;font-family:ui-monospace,monospace;line-height:1.8;}
  .foot a{color:var(--amber);text-decoration:none;}
  .kofi{display:inline-block;margin-top:14px;background:#29ABE0;color:#fff;font-weight:700;padding:9px 16px;border-radius:9px;text-decoration:none;font-size:12px;}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1>%s %s</h1>
    <a href="https://nearme.viajeinteligencia.com" style="color:var(--dim);font-size:12px;">← NearMe</a>
  </div>
  <div class="meta">Estación %s · observación %s UTC</div>
  <div class="fresh">● DATOS EN VIVO · AEMET</div>
  <div class="card">
    <div class="big">%s<span class="unit">°C</span></div>
    <div class="stat"><b>Temperatura en %s</b><br>Observación de la estación meteorológica %s<br>Fuente: AEMET (Agencia Estatal de Meteorología)</div>
  </div>
  <p>Temperatura actual registrada por la red de estaciones automáticas de AEMET en %s. Los datos se actualizan automáticamente y se compilan de forma independiente en NearMe.</p>
  <div class="foot">
    Fuente: AEMET · Compilación independiente NearMe OSINT
    <br><a href="https://nearme.viajeinteligencia.com">nearme.viajeinteligencia.com</a> · <a href="https://www.viajeinteligencia.com/ecosistema.html">🌐 ecosistema</a>
    <br>Si te resulta útil, apóyalo con un ☕ <a class="kofi" href="https://ko-fi.com/m_castillo">Ko-fi</a>
  </div>
</div>
</body>
</html>""" % (title, desc, url, title, desc, url, title, iso, url,
           icon, name, station_name, ts_txt, temp_txt, name, station_name, name)


def main():
    dry = "--dry" in sys.argv
    env = load_env(os.path.join(BASE, ".env"))
    try:
        import psycopg2
    except ImportError:
        sys.path.insert(0, os.path.join(BASE, "venv/lib/python3.12/site-packages"))
        import psycopg2
    cfg = {
        "dbname": env.get("DB_NAME", "nearme_osint"),
        "user": env.get("DB_USER", "nearme"),
        "password": env.get("DB_PASSWORD", ""),
        "host": env.get("DB_HOST", "localhost"),
        "port": int(env.get("DB_PORT", "5432")),
    }
    conn = psycopg2.connect(**cfg)
    stations = fetch_stations(conn)
    print("estaciones AEMET con obs:", len(stations))

    # municipio -> {slug, estacion, temp, ts, code}
    by_muni = {}
    n_geo = 0
    for lat, lon, title, ts in stations:
        muni = muni_for_point(conn, lat, lon)
        if not muni:
            continue
        temp = parse_temp(title)
        if temp is None:
            continue
        n_geo += 1
        if muni not in by_muni or ts > by_muni[muni]["ts"]:
            by_muni[muni] = {"slug": slug(muni), "station": title.split(":")[0].strip(),
                             "temp": temp, "ts": ts}
    conn.close()
    print("estaciones geocodificadas a municipio:", n_geo, "| municipios unicos:", len(by_muni))

    # resolver colisiones de slug
    seen = {}
    for muni in sorted(by_muni):
        s = by_muni[muni]["slug"]
        if s in seen:
            # colisión: añadir sufijo numerico
            seen[s] += 1
            by_muni[muni]["slug"] = "%s-%d" % (s, seen[s])
        else:
            seen[s] = 1

    written = 0
    sitemap_urls = []
    for muni in sorted(by_muni):
        d = by_muni[muni]
        html = build_html(muni, d["slug"], d["station"], d["temp"], d["ts"], "")
        if not html:
            continue
        if dry:
            print("  [dry] %s (%.1fC via %s)" % (muni, d["temp"], d["station"]))
            written += 1
            continue
        out = os.path.join(FRONT, "tiempo-%s.html" % d["slug"])
        open(out, "w", encoding="utf-8").write(html)
        sitemap_urls.append("%s/tiempo-%s.html" % (SITE, d["slug"]))
        written += 1

    if not dry and sitemap_urls:
        # Reconstruir sitemap desde los .html reales (idempotente, evita duplicados)
        smap_path = os.path.join(FRONT, "sitemap.xml")
        all_files = sorted(f for f in os.listdir(FRONT) if f.endswith(".html") and f != "index.html")
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml += '  <url><loc>%s/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n' % SITE
        for f in all_files:
            u = "%s/%s" % (SITE, f[:-5])
            cf = "hourly"
            xml += '  <url><loc>%s</loc><changefreq>%s</changefreq><priority>0.8</priority></url>\n' % (u, cf)
        xml += '</urlset>\n'
        with open(smap_path, "w", encoding="utf-8") as f:
            f.write(xml)
        print("sitemap reconstruido con %d urls" % (len(all_files) + 1))

    print("paginas generadas:", written)


if __name__ == "__main__":
    main()
