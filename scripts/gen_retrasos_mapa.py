#!/usr/bin/env python3
"""Mapa estático de estaciones AVE/LD con retrasos reportados hoy."""
import json
import sys
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn  # noqa: E402

MADRID = ZoneInfo("Europe/Madrid")
OUT = Path("/var/www/radar/retrasos-renfe-mapa.html")
DATA = Path("/var/www/radar/datos/retrasos-renfe-mapa.json")
URL = "https://radar.viajeinteligencia.com/retrasos-renfe-mapa.html"


def load():
    cur = get_conn().cursor()
    cur.execute("""
        WITH latest AS (
            SELECT DISTINCT ON (trip_id, stop_id)
                trip_id, stop_id, delay_seconds, observed_at
            FROM renfe_delay_obs
            WHERE subtype='alta_velocidad'
              AND observed_at >= date_trunc('day', now() AT TIME ZONE 'Europe/Madrid') AT TIME ZONE 'Europe/Madrid'
              AND delay_seconds >= 900
            ORDER BY trip_id, stop_id, observed_at DESC
        )
        SELECT s.stop_id, s.stop_name, s.stop_lat, s.stop_lon,
               COUNT(DISTINCT l.trip_id) AS trains,
               MAX(l.delay_seconds) AS delay_seconds,
               STRING_AGG(DISTINCT COALESCE(t.route_short_name, 's/d'), ', ') AS lines,
               STRING_AGG(DISTINCT CASE WHEN t.origin_name <> '' AND t.dest_name <> ''
                    THEN t.origin_name || ' → ' || t.dest_name END, ' · ') AS corridors
        FROM latest l
        JOIN renfe_gtfs_stops s ON s.feed='alta_velocidad' AND s.stop_id=l.stop_id
        LEFT JOIN renfe_gtfs_trips t ON t.feed='alta_velocidad' AND t.trip_id=l.trip_id
        WHERE s.stop_lat IS NOT NULL AND s.stop_lon IS NOT NULL
        GROUP BY s.stop_id, s.stop_name, s.stop_lat, s.stop_lon
        ORDER BY delay_seconds DESC
    """)
    rows = []
    for sid, name, lat, lon, trains, delay, lines, corridors in cur.fetchall():
        rows.append({
            "id": sid,
            "station": name or sid,
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "trains": int(trains),
            "delay_min": round((delay or 0) / 60),
            "lines": lines or "s/d",
            "corridors": corridors or "",
        })
    return rows


def unique_trains():
    cur = get_conn().cursor()
    cur.execute("""
        WITH latest AS (
            SELECT DISTINCT ON (trip_id, stop_id) trip_id
            FROM renfe_delay_obs
            WHERE subtype='alta_velocidad'
              AND observed_at >= date_trunc('day', now() AT TIME ZONE 'Europe/Madrid') AT TIME ZONE 'Europe/Madrid'
              AND delay_seconds >= 900
            ORDER BY trip_id, stop_id, observed_at DESC
        )
        SELECT COUNT(DISTINCT trip_id) FROM latest
    """)
    row = cur.fetchone()
    return int(row[0] or 0)


def color(delay):
    if delay >= 60:
        return "#dc2626"
    if delay >= 30:
        return "#f97316"
    return "#f59e0b"


def main():
    stations = load()
    now = datetime.now(MADRID)
    gen = now.isoformat(timespec="seconds")
    trains = sum(x["trains"] for x in stations)
    unique = unique_trains()
    max_delay = max((x["delay_min"] for x in stations), default=0)
    payload = {
        "generated_at": gen,
        "source": "Renfe GTFS-RT vía NearMe; coordenadas del GTFS estático de Renfe",
        "disclaimer": "Punto = estación con retraso reportado; no es la posición del tren ni una confirmación oficial.",
        "threshold_min": 15,
        "totals": {"stations": len(stations), "trains": unique, "train_station_pairs": trains, "max_delay_min": max_delay},
        "stations": stations,
    }
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = "".join(
        f"<tr><td>{escape(x['station'])}</td><td>{escape(x['lines'])}</td>"
        f"<td>{x['trains']}</td><td><b>+{x['delay_min']} min</b></td>"
        f"<td>{escape(x['corridors'][:160])}</td></tr>"
        for x in stations
    )
    data_js = json.dumps(stations, ensure_ascii=False).replace("</", "<\\/")
    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Mapa de retrasos AVE y larga distancia",
        "description": "Estaciones con trenes AVE/LD y retraso reportado superior a 15 minutos.",
        "url": URL,
        "dateModified": gen,
        "creator": {"@type": "Person", "name": "Miguel Castillo"},
        "isAccessibleForFree": True,
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": "https://radar.viajeinteligencia.com/datos/retrasos-renfe-mapa.json"}],
    }, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retrasos de AVE y larga distancia en el mapa · España</title>
<meta name="description" content="Mapa de estaciones con retrasos de AVE y larga distancia en España: puntos por estación, no posiciones de trenes. Datos GTFS-RT de Renfe, actualizados cada 15 minutos.">
<link rel="canonical" href="{URL}">
<meta property="og:title" content="Mapa de retrasos de AVE y larga distancia">
<meta property="og:description" content="Estaciones con retrasos reportados ≥15, ≥30 y ≥60 min. Punto = estación, no posición del tren.">
<meta property="og:type" content="website">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="https://radar.viajeinteligencia.com/retrasos-renfe-og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--amber:#f59e0b;--orange:#f97316;--red:#dc2626;--paper:#fffaf5}}
*{{box-sizing:border-box}} body{{margin:0;background:#fafafa;color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.6}}
.wrap{{max-width:980px;margin:0 auto;padding:24px 16px 56px}} a{{color:#c2410c}}
.top{{font-size:.85rem;margin-bottom:14px}} h1{{font-size:1.8rem;line-height:1.2;margin:.1em 0}} .lead{{font-size:1rem;color:#334155;max-width:800px}}
.meta{{font-size:.82rem;color:var(--muted)}} .stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}}
.stat{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:11px;text-align:center}} .stat b{{display:block;font-size:1.35rem;color:#b45309}} .stat span{{font-size:.75rem;color:var(--muted)}}
#map{{height:520px;border:1px solid var(--line);border-radius:12px;background:#eef3f7}} .map-note{{font-size:.8rem;color:var(--muted);margin:8px 0 0}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;font-size:.82rem;margin:12px 0}} .dot{{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:17px;margin:18px 0}} h2{{font-size:1.13rem;margin:0 0 8px;border-bottom:2px solid #fde68a;padding-bottom:5px}}
.card p,.card li{{font-size:.9rem;color:#334155}} .card li{{margin:5px 0}} .muted{{color:var(--muted);font-size:.82rem}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}} th,td{{border-bottom:1px solid var(--line);padding:7px;text-align:left;vertical-align:top}} th{{font-size:.75rem;color:var(--muted)}}
.warn{{background:#fff7ed;border-left:4px solid #b45309;padding:10px 14px;border-radius:7px;font-size:.9rem}}
.foot{{border-top:1px solid var(--line);margin-top:28px;padding-top:18px;font-size:.85rem;color:#475569}} .foot a{{display:inline-block;margin:2px 7px 2px 0}} .kofi{{display:inline-flex;align-items:center;gap:7px;font-weight:700;color:#fff!important;background:#13C3A5;border-radius:7px;padding:9px 14px;text-decoration:none;margin-top:10px}}
@media(max-width:650px){{.stats{{grid-template-columns:1fr 1fr}}#map{{height:420px}}}}
</style>
<script type="application/ld+json">{json_ld}</script></head>
<body><main class="wrap">
<p class="top"><a href="/">← radar</a> · <a href="/retrasos-renfe-hoy.html">retrasos hoy</a> · <a href="/retrasos-renfe-estaciones.html">estaciones</a></p>
<h1>Retrasos de AVE y larga distancia en el mapa</h1>
<p class="lead">Cada punto es una <b>estación</b> donde Renfe ha reportado al menos un tren con retraso de <b>15 minutos o más</b> hoy. No es la posición del tren.</p>
<p class="meta">Actualizado: <b>{now.strftime('%d/%m/%Y %H:%M')} Europe/Madrid</b> · datos GTFS-RT de Renfe vía NearMe · no es una web oficial.</p>
<div class="stats"><div class="stat"><b>{len(stations)}</b><span>estaciones con retraso ≥15 min</span></div><div class="stat"><b>{unique}</b><span>trenes únicos afectados</span></div><div class="stat"><b>+{max_delay} min</b><span>retraso máximo reportado</span></div></div>
<div id="map" role="img" aria-label="Mapa de estaciones con retrasos de AVE y larga distancia"></div>
<p id="empty" class="map-note" hidden>No hay retrasos de AVE/LD ≥15 minutos en la captura actual. No significa que no existan: puede ser falta de datos del feed.</p>
<div class="legend"><span><i class="dot" style="background:#f59e0b"></i>15–29 min</span><span><i class="dot" style="background:#f97316"></i>30–59 min</span><span><i class="dot" style="background:#dc2626"></i>≥60 min</span><span class="muted">Tamaño = retraso y trenes en esa estación</span></div>
<div class="card"><h2>Cómo se lee</h2><ul>
<li><b>Punto = estación.</b> No es un tren geolocalizado ni una interpolación de su recorrido.</li>
<li>Un mismo tren puede aparecer en varias estaciones si el retraso se reporta en varias paradas.</li>
<li>El tamaño y el color resumen el retraso máximo y el número de trenes observados en esa estación.</li>
<li>La hora es la de la captura; el retraso es el reportado por el feed, no una medición independiente.</li>
<li>Solo se muestran <b>AVE y larga distancia</b>; Cercanías no entra en este mapa.</li>
</ul></div>
<div class="warn"><b>Límites.</b> La fuente es el GTFS-RT de Renfe y las coordenadas del GTFS estático. No confirma causas, no atribuye responsabilidades y no mide la puntualidad oficial. La cobertura depende del feed: un hueco en el mapa no prueba que no haya retrasos. Los datos pueden cambiar entre ciclos.</div>
<div class="card"><h2>Estaciones en esta captura</h2><table><thead><tr><th>Estación</th><th>Servicio</th><th>Trenes</th><th>Máximo</th><th>Corredor</th></tr></thead><tbody>{rows or '<tr><td colspan="5">Sin estaciones con retraso ≥15 min.</td></tr>'}</tbody></table><p class="muted">Un tren puede sumar en varias estaciones; la columna «Trenes» cuenta trenes distintos observados en esa estación, no el total global ({trains} pares tren×estación).</p></div>
<div class="card"><h2>Datos y método</h2><p>Fuente: <a href="https://data.renfe.com/" target="_blank" rel="noopener">Renfe GTFS-RT</a>, capturado por NearMe cada 15 minutos. Las coordenadas y los nombres de estación proceden del <b>GTFS estático oficial</b> de Renfe. No hay datos manuales en esta página.</p><p><a href="/datos/retrasos-renfe-mapa.json">Descargar JSON</a> · <a href="/retrasos-renfe-hoy.html">Estado completo del día</a> · <a href="/retrasos-renfe-estaciones.html">Fichas por estación</a></p></div>
<footer class="foot"><b>Ecosistema ViajeInteligencia</b><br><a href="https://www.viajeinteligencia.com">Principal</a><a href="https://municipal.viajeinteligencia.com">Municipal</a><a href="https://nearme.viajeinteligencia.com">NearMe</a><a href="https://country.viajeinteligencia.com">País a País</a><a href="https://vivienda.pruebapublica.com">Vivienda</a><a href="https://analisis.pruebapublica.com">Análisis</a><a href="/estado.html">Estado de fuentes</a><br><a class="kofi" href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer">☕ Invítame a un café</a><p class="muted">Proyecto personal, sin rastreo ni cuentas. Los servidores los paga su autor.</p></footer>
</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DATA={data_js};
const map=L.map('map',{{scrollWheelZoom:false}}).setView([40.2,-3.5],5);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:18,attribution:'© OpenStreetMap'}}).addTo(map);
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function color(d){{return d>=60?'#dc2626':d>=30?'#f97316':'#f59e0b'}}
const pts=[];
DATA.forEach(function(s){{
 const c=color(s.delay_min);
 const r=Math.max(7,Math.min(22,7+Math.sqrt(s.delay_min)*1.2));
 const popup='<b>'+esc(s.station)+'</b><br>+'+s.delay_min+' min · '+s.trains+' tren(es)<br>'+esc(s.lines)+(s.corridors?'<br><span class="muted">'+esc(s.corridors)+'</span>':'')+'<br><span class="muted">Estación, no posición del tren</span>';
 const m=L.circleMarker([s.lat,s.lon],{{radius:r,color:c,weight:1.5,fillColor:c,fillOpacity:.45}}).bindPopup(popup).addTo(map);
 pts.push([s.lat,s.lon]); m.on('click',function(){{map.panTo([s.lat,s.lon]);}});
}});
if(pts.length){{map.fitBounds(pts,{{padding:[35,35],maxZoom:6}});}} else {{document.getElementById('empty').hidden=false;}}
</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"OK {OUT} · {len(stations)} estaciones · {unique} trenes únicos · max +{max_delay} min")


if __name__ == "__main__":
    main()
