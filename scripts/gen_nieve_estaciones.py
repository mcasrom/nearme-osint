#!/usr/bin/env python3
"""gen_nieve_estaciones.py — Nieve en las estaciones de esquí de España.

Lee los eventos `nieve_*` ya colectados cada hora (Open-Meteo) en Postgres y
genera /var/www/radar/nivel-nieve.html con el MISMO formato y footer que las
páginas hermanas del radar (nivel-embalses, pulso-espana, enjambre...).

KPIs + tabla + mapa Leaflet + metodología. Sin parte oficial de pistas.
"""
import html
import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
OUT = "/var/www/radar/nivel-nieve.html"

COL = {"alert": "#dc2626", "warning": "#d97706", "info": "#64748b"}


def esc(s):
    return html.escape(str(s or ""))


def kpi_card(label, value, sub, bg):
    return (f'<div style="flex:1 1 150px;background:{bg};border-radius:12px;padding:14px 16px;'
            f'box-shadow:0 1px 3px rgba(0,0,0,.06)">'
            f'<div style="font-size:.75rem;color:#475569;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:.04em">{label}</div>'
            f'<div style="font-size:1.7rem;font-weight:800;color:#0f172a;line-height:1.2">{value}</div>'
            f'<div style="font-size:.8rem;color:#64748b">{sub}</div></div>')


def mapa_html(pts):
    data_json = json.dumps(pts, ensure_ascii=False)
    return f'''<div id="mapa-nieve" style="height:520px;border-radius:12px;border:1px solid #e2e8f0"></div>
<div class="leyenda" style="margin-top:10px">
  <span><span class="dot" style="background:#dc2626"></span>Nevando</span>
  <span><span class="dot" style="background:#d97706"></span>Manto / nevada reciente</span>
  <span><span class="dot" style="background:#64748b"></span>Sin nieve</span>
  <span style="margin-left:8px;color:#64748b">Desplazamiento con la rueda desactivado (usa zoom +/-).</span>
</div>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(function(){{
  var pts = {data_json};
  var map = L.map('mapa-nieve', {{scrollWheelZoom:false}}).setView([40.4, -3.2], 6);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19, attribution: '© OpenStreetMap'
  }}).addTo(map);
  var bounds = [];
  pts.forEach(function(p){{
    if (p.lat === null || p.lng === null) return;
    bounds.push([p.lat, p.lng]);
    L.circleMarker([p.lat, p.lng], {{
      radius: 7, color:'#0f172a', weight:1, fillColor: p.col, fillOpacity: 0.9
    }}).bindPopup('<b>' + p.nombre + '</b><br>' + p.estado +
      '<br><small>' + p.detalle + '</small><br><small>Vigencia: ' + p.vigencia + '</small>').addTo(map);
  }});
  if (bounds.length) map.fitBounds(bounds, {{padding:[30,30]}});
}})();
</script>'''


def main():
    from src.db import get_conn
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT DISTINCT ON (source_id) source_id, title, level, description,
               lat, lon, expires_at, created_at, municipality
        FROM events WHERE source_id LIKE 'nieve_%'
        ORDER BY source_id, created_at DESC""")
    rows = cur.fetchall()
    con.close()

    ahora = datetime.now(timezone.utc)
    evs = []
    for r in rows:
        sid, title, level, desc, lat, lon, exp, cre, muni = r
        nombre = muni or sid.replace("nieve_", "").replace("-", " ").title()
        evs.append({"sid": sid, "nombre": nombre, "title": title,
                    "level": level or "info", "desc": desc,
                    "lat": lat, "lon": lon, "exp": exp, "cre": cre})
    evs.sort(key=lambda e: e["nombre"])

    n_nieve = sum(1 for e in evs if (e["title"] or "").startswith(("Nieva en", "Nieve acumulada")))
    n_nevando = sum(1 for e in evs if (e["title"] or "").startswith("Nieva en"))
    frescos = sum(1 for e in evs if e["exp"] and e["exp"] > ahora)
    now_str = ahora.strftime("%d/%m/%Y %H:%M UTC")

    def fila(e):
        col = COL.get(e["level"], "#64748b")
        return (
            f"<tr><td><b>{esc(e['nombre'])}</b></td>"
            f"<td><span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
            f"background:{col}'></span> {esc(e['title'])}</td>"
            f"<td>{esc(e['desc'])}</td>"
            f"<td>{e['exp'].strftime('%d/%m %H:%M') if e['exp'] else '—'}</td>"
            f"<td>{e['cre'].strftime('%d/%m') if e['cre'] else '—'}</td></tr>")

    pts = []
    for e in evs:
        if e["lat"] is None or e["lon"] is None:
            continue
        pts.append({
            "nombre": e["nombre"], "lat": e["lat"], "lng": e["lon"],
            "estado": e["title"], "col": COL.get(e["level"], "#64748b"),
            "detalle": (e["desc"] or "")[:180],
            "vigencia": e["exp"].strftime("%d/%m %H:%M") if e["exp"] else "—",
        })

    cards = "".join([
        kpi_card("Estaciones", f"{len(evs)}", "monitorizadas", "#eff6ff"),
        kpi_card("Con nieve", f"{n_nieve}", "manto o nevada reciente", "#f0f9ff"),
        kpi_card("Nevando ahora", f"{n_nevando}", "precipitación en curso", "#fef2f2"),
        kpi_card("Vigentes", f"{frescos}", "dato &lt;12 h", "#f0fdf4"),
        kpi_card("Actualizado", now_str[6:16], "UTC", "#fafaf9"),
    ])

    page = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nieve en las estaciones de esquí de España · estado y nevadas</title>
<meta name="description" content="Manto de nieve y nevadas previstas en las principales estaciones de esquí de España (Pirineos, Sistema Central, Cantábrica, Galicia, Ibérico y Sierra Nevada). Datos abiertos Open-Meteo, actualizado dos veces al día.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/nivel-nieve.html">
<meta property="og:type" content="website">
<meta property="og:title" content="Nieve en las estaciones de esquí de España">
<meta property="og:description" content="Manto de nieve y nevadas previstas por estación. Datos abiertos (Open-Meteo); no es el parte oficial de pistas.">
<meta property="og:locale" content="es_ES">
<meta property="og:url" content="https://radar.viajeinteligencia.com/nivel-nieve.html">
<meta property="og:image" content="https://radar.viajeinteligencia.com/nivel-nieve-og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<style>
:root{{color-scheme:light}}
body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f8fafc;color:#0f172a}}
main{{max-width:960px;margin:0 auto;padding:20px 16px 56px}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin:18px 0;box-shadow:0 1px 2px rgba(15,23,42,.04)}}
.card h3{{margin-top:0;font-size:1.05rem}}
.caption{{font-size:.85rem;color:#64748b;margin:.2rem 0 0}}
.kpis{{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}}
a{{color:#c2410c}}
table{{border-collapse:collapse;width:100%;font-size:.86rem}}
th,td{{border-bottom:1px solid #e2e8f0;padding:7px 8px;text-align:left;vertical-align:top}}
th{{color:#475569;font-size:.75rem;text-transform:uppercase;letter-spacing:.03em}}
.leyenda{{display:flex;gap:14px;flex-wrap:wrap;font-size:.78rem;color:#475569;margin-top:10px}}
.leyenda span{{display:inline-flex;align-items:center;gap:5px}}
.dot{{width:11px;height:11px;border-radius:3px;display:inline-block}}
.aviso{{background:#fef3c7;border:1px solid #f59e0b;border-radius:10px;padding:10px 14px;margin:14px 0;font-size:.88rem}}
</style></head>
<body>
<main>
<p style="font-size:.85rem"><a href="/">← radar</a> · <a href="/nivel-embalses.html">💧 embalses</a> · <a href="/pulso-espana.html">💓 pulso</a> · <a href="/enjambre-granada.html">🌍 enjambre</a> · <a href="/incendios-meteorologia.html">🔥 incendios</a> · <a href="/retrasos-renfe-hoy.html">🚆 trenes</a></p>
<h1 style="font-size:1.6rem;margin:.2em 0">Nieve en las estaciones de esquí de España</h1>
<p style="color:#475569">Manto de nieve y nevadas previstas en las principales estaciones de esquí:
Pirineos, Sistema Central, Cantábrica, Galicia, Sistema Ibérico y Sierra Nevada.
Fuente abierta: <strong>Open-Meteo</strong> (temperatura, manto y nevada) por coordenadas de estación.</p>

<div class="aviso"><b>Fuera de temporada</b> es normal que no haya nieve. Se muestra el <b>último estado conocido</b>
con su vigencia; si no hay dato, no se inventa. Esto <b>no</b> es el parte oficial de pistas y remontes de cada estación.</div>

<div class="kpis">{cards}</div>

<div class="card">
  <h3>Mapa de estaciones</h3>
  <p class="caption">Cada punto es una estación, coloreado por su estado actual. Pulsa un marcador para ver el detalle.</p>
  {mapa_html(pts)}
</div>

<div class="card">
  <h3>Estado por estación</h3>
  <p class="caption">Ordenadas por nombre. «Vigencia» es hasta cuándo el dato se considera actual; «último cambio» es cuándo cambió el estado por última vez.</p>
  <table><tr><th>Estación</th><th>Estado</th><th>Detalle</th><th>Vigencia</th><th>Último cambio</th></tr>
  {"".join(fila(e) for e in evs)}</table>
</div>

<p style="font-size:.82rem;color:#64748b;margin-top:28px">
<strong>Metodología.</strong> Datos de modelo <strong>Open-Meteo</strong> (temperatura, manto de nieve en metros,
nevada prevista 24 h) por coordenadas de cada estación, colectados cada hora y publicados dos veces al día.
El «manto» es la nieve en el suelo en el punto de la estación, no las pistas abiertas. Página regenerada
automáticamente por cron, igual que el resto del radar. Las categorías de color son informativas y NO
constituyen partes oficiales ni alertas de ninguna estación de esquí.</p>

<footer style="border-top:1px solid #e5e5e5;margin-top:28px;padding-top:18px;text-align:center">
  <div style="font-size:.85rem;color:#666;line-height:1.9">
    <b>Ecosistema ViajeInteligencia</b><br>
    <a href="https://www.viajeinteligencia.com" style="color:#c2410c">Principal</a> ·
    <a href="https://municipal.viajeinteligencia.com" style="color:#c2410c">Municipal</a> ·
    <a href="https://nearme.viajeinteligencia.com" style="color:#c2410c">NearMe</a> ·
    <a href="https://country.viajeinteligencia.com" style="color:#c2410c">País a País</a> ·
    <a href="https://news.viajeinteligencia.com" style="color:#c2410c">Prensa global</a> ·
    <a href="https://radar.viajeinteligencia.com/estado.html" style="color:#c2410c">Estado de fuentes</a>
  </div>
  <a href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer"
     style="display:inline-flex;align-items:center;gap:8px;font-weight:700;font-size:13.5px;color:#fff;background:#13C3A5;border-radius:7px;padding:11px 18px;margin-top:14px;text-decoration:none">☕ Invítame a un café</a>
  <p style="font-size:.78rem;color:#888;margin:10px 0 0">Proyecto personal, sin rastreo ni cuentas. Los servidores los paga su autor.</p>
</footer>

</main>
</body></html>"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"OK {OUT} · {len(evs)} estaciones · con nieve {n_nieve} · vigentes {frescos} · puntos {len(pts)}")


if __name__ == "__main__":
    main()
