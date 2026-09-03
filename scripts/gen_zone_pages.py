#!/usr/bin/env python3
"""Genera páginas SEO por zona+tema con datos reales de la API NearMe.
Página: "/{tema}-{zona}" (ej. /terremotos-granada, /calidad-del-aire-valencia).
Solo genera si hay >= MIN_EVENTS del tipo en la zona. Crédito/backlink + ko-fi + tema claro.
Uso: python3 gen_zone_pages.py [--push]
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

BASE = "/home/deploy/nearme-osint"
FRONT = os.path.join(BASE, "frontend")
API = "http://127.0.0.1:8100/api/nearby"
SITE = "https://nearme.viajeinteligencia.com"
PUSH = "/home/deploy/scripts/indexnow_push.py"
MIN_EVENTS = 2

TOPICS = {
    "terremotos": ("earthquake", "Terremotos en %s ahora"),
    "incendios": ("fire", "Incendios en %s hoy"),
    "calidad-del-aire": ("air_quality", "Calidad del aire en %s hoy"),
    "embalses": ("reservoir", "Nivel de embalses en %s hoy"),
    "trafico": ("road_incident", "Tráfico en %s hoy"),
}

# zonas: slug, nombre, lat, lon
ZONES = [
    ("madrid", "Madrid", "40.42", "-3.70"),
    ("barcelona", "Barcelona", "41.39", "2.17"),
    ("valencia", "Valencia", "39.47", "-0.38"),
    ("sevilla", "Sevilla", "37.39", "-5.98"),
    ("bilbao", "Bilbao", "43.26", "-2.94"),
    ("oviedo", "Oviedo", "43.36", "-5.85"),
    ("granada", "Granada", "37.17", "-3.60"),
    ("toledo", "Toledo", "39.86", "-4.03"),
    ("valladolid", "Valladolid", "41.65", "-4.72"),
    ("leon", "León", "42.61", "-5.57"),
    ("santander", "Santander", "43.46", "-3.81"),
    ("malaga", "Málaga", "36.72", "-4.42"),
    ("alicante", "Alicante", "38.35", "-0.48"),
    ("zaragoza", "Zaragoza", "41.65", "-0.89"),
    ("santiago", "Santiago", "42.88", "-8.54"),
    ("teruel", "Teruel", "40.34", "-1.11"),
    ("pamplona", "Pamplona", "42.82", "-1.64"),
    ("tarragona", "Tarragona", "41.12", "1.24"),
    ("cadiz", "Cádiz", "36.53", "-6.29"),
    ("almeria", "Almería", "36.83", "-2.46"),
    ("murcia", "Murcia", "37.98", "-1.13"),
    ("salamanca", "Salamanca", "40.96", "-5.66"),
    ("vitoria", "Vitoria", "42.86", "-2.72"),
    ("lleida", "Lleida", "41.62", "0.61"),
    ("caceres", "Cáceres", "39.49", "-6.37"),
    ("badajoz", "Badajoz", "38.88", "-6.97"),
    ("albacete", "Albacete", "38.98", "-1.86"),
    ("huelva", "Huelva", "37.26", "-6.95"),
    ("jaen", "Jaén", "37.77", "-3.79"),
    ("segovia", "Segovia", "40.94", "-4.12"),
    ("soria", "Soria", "41.81", "-3.74"),
    ("burgos", "Burgos", "42.33", "-3.70"),
    ("cuenca", "Cuenca", "40.32", "-1.94"),
    ("zamora", "Zamora", "41.53", "-5.99"),
    ("palma", "Palma", "39.57", "2.66"),
    ("santa-cruz", "Santa Cruz de Tenerife", "28.29", "-16.63"),
    ("las-palmas", "Las Palmas de Gran Canaria", "28.12", "-15.44"),
    ("avila", "Ávila", "40.66", "-4.70"),
    ("guadalajara", "Guadalajara", "40.63", "-3.17"),
    ("ciudad-real", "Ciudad Real", "38.99", "-3.93"),
    ("cordoba", "Córdoba", "37.89", "-4.78"),
    ("castellon", "Castellón", "39.99", "-0.05"),
    ("girona", "Girona", "41.98", "2.82"),
    ("huesca", "Huesca", "42.14", "-0.41"),
    ("san-sebastian", "San Sebastián", "43.32", "-1.98"),
    ("logrono", "Logroño", "42.47", "-2.45"),
    ("lugo", "Lugo", "43.01", "-7.56"),
    ("ourense", "Ourense", "42.34", "-7.86"),
    ("palencia", "Palencia", "42.01", "-4.53"),
    ("pontevedra", "Pontevedra", "42.43", "-8.64"),
    ("ceuta", "Ceuta", "35.89", "-5.32"),
    ("melilla", "Melilla", "35.29", "-2.94"),
]

EMOJI = {"terremotos": "🌍", "incendios": "🔥", "calidad-del-aire": "💨", "embalses": "💧", "trafico": "🚗"}
INTRO = {
    "terremotos": "Listado de terremotos y réplicas registrados en la zona en las últimas horas, con magnitud, profundidad y hora (fuente: IGN).",
    "incendios": "Incendios detectados por satélite (NASA FIRMS) en la zona, con focos activos y superficie afectada estimada.",
    "calidad-del-aire": "Índice de calidad del aire por estación oficial (MITECO/OpenAQ): PM2.5, PM10, ozono y NO2.",
    "embalses": "Nivel de llenado de los embalses de la zona (MITECO/SAIH): porcentaje y volumen embalsado.",
    "trafico": "Incidencias de tráfico activas en la zona según la DGT: cortes, obras y obstáculos en carretera.",
}


def fetch(lat, lon, radius=60):
    url = "%s?lat=%s&lon=%s&radius_km=%d" % (API, lat, lon, radius)
    req = urllib.request.Request(url, headers={"User-Agent": "NearMe-zone/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fmt_event(e, topic):
    t = e.get("title") or e.get("event_type") or ""
    d = (e.get("description") or "")[:140]
    if topic == "terremotos":
        m = re.search(r"M([\d.]+)", t)
        return t, d
    return t, d


def build_html(topic, zone, name, events, now):
    e_emoji = EMOJI.get(topic, "📌")
    title = (TOPICS[topic][1] % name)
    n = len(events)
    latest = events[0] if events else None
    latest_txt = ""
    if latest:
        lt = latest.get("title") or ""
        ld = (latest.get("description") or "")
        latest_txt = lt + ((" — " + ld[:120]) if ld else "")
    desc = "Datos en vivo de " + title.lower() + ": " + latest_txt[:180]
    items = ""
    for e in events[:15]:
        t = e.get("title") or ""
        d = (e.get("description") or "")[:110]
        items += "<li><b>%s</b><br><span class=\"evd\">%s</span></li>" % (t, d)
    if len(events) > 15:
        items += "<li><i>+%d más…</i></li>" % (len(events) - 15)
    iso = now.strftime("%Y-%m-%d")
    url = "%s/%s-%s" % (SITE, topic, zone)
    intro = INTRO.get(topic, "")
    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s · datos en vivo | NearMe</title>
<meta name="description" content="%s">
<meta name="robots" content="index, follow">
<link rel="canonical" href="%s">
<meta property="og:type" content="article">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<meta property="og:locale" content="es_ES">
<meta property="og:image" content="https://nearme.viajeinteligencia.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"NewsArticle","headline":"%s","datePublished":"%s","inLanguage":"es","url":"%s","publisher":{"@type":"Organization","name":"NearMe OSINT","url":"https://nearme.viajeinteligencia.com"}}
</script>
<style>
  :root{--bg:#F4F6FB;--panel:#FFFFFF;--line:#D6DDEA;--text:#16202E;--text2:#33415C;--dim:#5B6B84;--faint:#8A97AC;--amber:#D9820A;--green:#0E9F6E;--cyan:#0E9FAE;--code-bg:#E9EEF7;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:-apple-system,system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.65;}
  .wrap{max-width:720px;margin:0 auto;padding:28px 20px 60px;}
  .top{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:18px;border-bottom:1px solid var(--line);padding-bottom:16px;}
  h1{font-size:24px;font-weight:800;letter-spacing:-0.02em;}
  .meta{font-size:11px;color:var(--faint);font-family:ui-monospace,monospace;margin-bottom:20px;}
  .fresh{display:inline-block;background:var(--panel);border:1px solid var(--green);color:var(--green);font-family:ui-monospace,monospace;font-size:11px;padding:4px 12px;border-radius:999px;margin-bottom:18px;}
  p{font-size:14.5px;color:var(--text2);margin-bottom:12px;}
  ul{list-style:none;padding:0;}
  li{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:13.5px;color:var(--text);}
  li b{color:var(--text);}
  .evd{color:var(--dim);font-size:12px;}
  .foot{margin-top:34px;font-size:11px;color:var(--faint);text-align:center;font-family:ui-monospace,monospace;line-height:1.8;}
  .foot a{color:var(--amber);text-decoration:none;}
  .kofi{display:inline-block;margin-top:14px;background:#29ABE0;color:#fff;font-weight:700;padding:9px 16px;border-radius:9px;text-decoration:none;font-size:12px;}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1>%s %s</h1>
    <a href="%s" style="color:var(--dim);font-size:12px;">← NearMe</a>
  </div>
  <div class="meta">%s · %d eventos · actualizado %s</div>
  <div class="fresh">● DATOS EN VIVO · FUENTES OFICIALES</div>
  <p>%s</p>
  <ul>%s</ul>
  <div class="foot">
    Fuente: fuentes oficiales y públicas (IGN, NASA FIRMS, MITECO, DGT, AEMET, OpenAQ). Compilación independiente.
    <br><a href="https://nearme.viajeinteligencia.com">nearme.viajeinteligencia.com</a> · <a href="https://www.viajeinteligencia.com/ecosistema.html">🌐 ecosistema</a>
    <br>Si te resulta útil, apóyalo con un ☕ <a class="kofi" href="https://ko-fi.com/m_castillo">Ko-fi</a>
  </div>
</div>
</body>
</html>""" % (title, desc, url, title, desc, url, title, iso, url, e_emoji, title, url, intro, n, iso, intro, items)


def build_sitemap(zone_urls):
    """Regenera sitemap.xml escaneando todos los .html del frontend (idempotente).
    Las paginas de zona se marcan como hourly; el resto como monthly."""
    static_prio = {
        "https://nearme.viajeinteligencia.com/": ("daily", "1.0"),
        "https://nearme.viajeinteligencia.com/firms": ("monthly", "0.8"),
        "https://nearme.viajeinteligencia.com/calidad-aire": ("monthly", "0.8"),
        "https://nearme.viajeinteligencia.com/precio-luz": ("monthly", "0.8"),
        "https://nearme.viajeinteligencia.com/incendios": ("monthly", "0.8"),
        "https://nearme.viajeinteligencia.com/trafico": ("monthly", "0.8"),
    }
    urls = list(static_prio.items())
    seen = {u for u, _ in urls}
    # escanear todos los .html reales (zone pages, tiempo-*, resto)
    import os as _os
    files = sorted(f for f in _os.listdir(FRONT) if f.endswith(".html") and f != "index.html")
    for f in files:
        u = "%s/%s" % (SITE, f[:-5])
        if u in seen:
            continue
        seen.add(u)
        cf = "hourly" if f.startswith(("trafico-", "terremotos-", "incendios-", "embalses-",
                                       "calidad-del-aire-", "tiempo-")) else "monthly"
        urls.append((u, (cf, "0.8")))
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u, (cf, pr) in urls:
        xml += '  <url><loc>%s</loc><changefreq>%s</changefreq><priority>%s</priority></url>\n' % (u, cf, pr)
    xml += '</urlset>\n'
    open(os.path.join(FRONT, "sitemap.xml"), "w", encoding="utf-8").write(xml)
    return len(urls)


def main():
    now = datetime.now(timezone.utc)
    generated = []
    zone_urls = set()
    for topic, (etype, label) in TOPICS.items():
        for zslug, zname, lat, lon in ZONES:
            try:
                d = fetch(lat, lon)
            except Exception:
                continue
            evs = [e for e in d.get("events", []) if e.get("event_type") == etype]
            if len(evs) < MIN_EVENTS:
                continue
            evs.sort(key=lambda e: (e.get("level") or "info"), reverse=True)
            out = os.path.join(FRONT, "%s-%s.html" % (topic, zslug))
            open(out, "w", encoding="utf-8").write(build_html(topic, zslug, zname, evs, now))
            url = "%s/%s-%s.html" % (SITE, topic, zslug)
            generated.append("%s/%s-%s" % (SITE, topic, zslug))
            zone_urls.add(url)
            print("OK:", topic, zname, "(%d eventos)" % len(evs))
    print("total generadas:", len(generated))
    n_sitemap = build_sitemap(zone_urls)
    print("sitemap.xml regenerado: %d urls" % n_sitemap)
    if "--push" in sys.argv and generated:
        subprocess.run([sys.executable, PUSH] + generated, check=False)


if __name__ == "__main__":
    main()
