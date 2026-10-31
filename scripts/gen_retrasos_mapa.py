#!/usr/bin/env python3
"""Mapa estático de estaciones AVE/LD con retrasos reportados."""
import json
import sys
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
WINDOW_MIN = 30
SERVICES = ("AVE", "AVE INT", "AVLO", "AVANT", "AVANT EXP", "ALVIA", "EUROMED", "Intercity")


def load(window_min=None):
    cur = get_conn().cursor()
    extra = "AND observed_at >= now() - interval '30 minutes'" if window_min else ""
    cur.execute(f"""
        WITH latest AS (
            SELECT DISTINCT ON (trip_id, stop_id)
                trip_id, stop_id, delay_seconds, observed_at
            FROM renfe_delay_obs
            WHERE subtype='alta_velocidad'
              AND observed_at >= date_trunc('day', now() AT TIME ZONE 'Europe/Madrid') AT TIME ZONE 'Europe/Madrid'
              AND delay_seconds >= 900
              {extra}
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
          AND t.route_short_name IN (%s, %s, %s, %s, %s, %s, %s, %s)
        GROUP BY s.stop_id, s.stop_name, s.stop_lat, s.stop_lon
        ORDER BY delay_seconds DESC
    """, SERVICES)
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


def unique_trains(window_min=None):
    cur = get_conn().cursor()
    extra = "AND observed_at >= now() - interval '30 minutes'" if window_min else ""
    cur.execute(f"""
        WITH latest AS (
            SELECT DISTINCT ON (trip_id, stop_id) trip_id
            FROM renfe_delay_obs
            WHERE subtype='alta_velocidad'
              AND observed_at >= date_trunc('day', now() AT TIME ZONE 'Europe/Madrid') AT TIME ZONE 'Europe/Madrid'
              AND delay_seconds >= 900
              {extra}
            ORDER BY trip_id, stop_id, observed_at DESC
        )
        SELECT COUNT(DISTINCT l.trip_id) FROM latest l
        LEFT JOIN renfe_gtfs_trips t ON t.feed='alta_velocidad' AND t.trip_id=l.trip_id
        WHERE t.route_short_name IN (%s, %s, %s, %s, %s, %s, %s, %s)
    """, SERVICES)
    row = cur.fetchone()
    return int(row[0] or 0)


def collect(window_min=None):
    stations = load(window_min)
    pairs = sum(x["trains"] for x in stations)
    return {
        "window_min": window_min,
        "stations": stations,
        "totals": {
            "stations": len(stations),
            "trains": unique_trains(window_min),
            "train_station_pairs": pairs,
            "max_delay_min": max((x["delay_min"] for x in stations), default=0),
        },
    }



def scheduled_today():
    cur = get_conn().cursor()
    today = datetime.now(MADRID).date().isoformat()
    cur.execute(
        "SELECT route_short_name, COUNT(*) FROM renfe_gtfs_trips "
        "WHERE feed='alta_velocidad' AND trip_id LIKE %s GROUP BY route_short_name",
        ("%" + today,),
    )
    return {r[0]: int(r[1]) for r in cur.fetchall() if r[0]}

def table_rows(stations):
    return "".join(
        f"<tr><td>{escape(x['station'])}</td><td>{escape(x['lines'])}</td>"
        f"<td>{x['trains']}</td><td><b>+{x['delay_min']} min</b></td>"
        f"<td>{escape(x['corridors'][:160])}</td></tr>"
        for x in stations
    )


def main():
    now_view = collect(WINDOW_MIN)
    day_view = collect(None)
    now = datetime.now(MADRID)
    gen = now.isoformat(timespec="seconds")
    scheduled = scheduled_today()
    expected = {"AVE", "AVLO", "AVANT", "EUROMED", "ALVIA", "Intercity"}
    missing = sorted(expected - set(scheduled))
    all_stations = now_view["stations"] + day_view["stations"]
    services = sorted({s.strip() for x in all_stations for s in x["lines"].split(",") if s.strip() and s.strip() != "s/d"})
    payload = {
        "generated_at": gen,
        "source": "Renfe GTFS-RT vía NearMe; coordenadas del GTFS estático de Renfe",
        "disclaimer": "Punto = estación con retraso reportado; no es la posición del tren ni una confirmación oficial.",
        "threshold_min": 15,
        "services": services,
        "scheduled_today": scheduled,
        "missing_scheduled": missing,
        "views": {
            "now": {"label": "Ahora", "note": "Últimas observaciones de los últimos 30 minutos.", **now_view},
            "day": {"label": "Acumulado de hoy", "note": "Todo lo reportado desde las 00:00 de hoy.", **day_view},
        },
    }
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    data_js = json.dumps(payload["views"], ensure_ascii=False).replace("</", "<\\/")
    services_html = "".join(f'<option value="{escape(s)}">{escape(s)}</option>' for s in services)
    initial_rows = table_rows(now_view["stations"])
    if missing:
        missing_txt = ", ".join(missing)
        coverage_note = f'<p class="warn"><b>Hoy el GTFS estático no programa: {escape(missing_txt)}.</b> No aparecen en el mapa porque no hay circulaciones de referencia para hoy; no es un fallo de captura.</p>'
    else:
        coverage_note = ""
    max_delay = max(now_view["totals"]["max_delay_min"], 0)
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
<title>Retrasos de Renfe AVE y larga distancia en el mapa · España</title>
<meta name="description" content="Mapa de estaciones con retrasos de Renfe AVE y larga distancia en España: ahora (últimos 30 min) y acumulado del día. Puntos por estación, no posiciones de trenes.">
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
.controls{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0}} .seg{{display:flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}} .seg button{{border:0;background:#fff;padding:8px 12px;cursor:pointer;font:inherit;font-size:.85rem;color:#475569}} .seg button.on{{background:#fef3c7;color:#92400e;font-weight:700}}
select{{font:inherit;font-size:.85rem;padding:8px;border:1px solid var(--line);border-radius:8px;background:#fff}} .refresh{{font-size:.78rem;color:var(--muted)}}
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
<p class="top"><a href="/">← radar</a> · <a href="/retrasos-renfe-hoy.html">retrasos hoy</a> · <a href="/retrasos-renfe-trenes.html">trenes</a> · <a href="/retrasos-renfe-estaciones.html">estaciones</a></p>
<h1>Retrasos de Renfe AVE y larga distancia en el mapa</h1>
<p class="lead">Cada punto es una <b>estación</b> donde Renfe ha reportado al menos un tren AVE o de larga distancia con retraso de <b>15 minutos o más</b>. No es la posición del tren.</p>
<p class="meta">Vista inicial: <b>Ahora</b> (últimos 30 min). <span id="updated">Actualizado: {now.strftime('%d/%m/%Y %H:%M')} Europe/Madrid</span> · datos GTFS-RT de Renfe vía NearMe · no es una web oficial.</p>
{coverage_note}
<div class="controls"><div class="seg" role="group" aria-label="Ventana temporal"><button type="button" class="on" data-view="now" aria-pressed="true">Ahora</button><button type="button" data-view="day" aria-pressed="false">Acumulado de hoy</button></div><label>Servicio <select id="service"><option value="all">Todos</option>{services_html}</select></label><span class="refresh" id="refresh-note">Se actualiza cada 15 min al abrir la página.</span></div>
<div class="stats"><div class="stat"><b id="stat-stations">{now_view['totals']['stations']}</b><span>estaciones con retraso ≥15 min</span></div><div class="stat"><b id="stat-trains">{now_view['totals']['trains']}</b><span id="stat-trains-label">trenes únicos afectados</span></div><div class="stat"><b id="stat-max">+{max_delay} min</b><span>retraso máximo reportado</span></div></div>
<p class="map-note" id="view-note">Ahora: últimas observaciones de los últimos 30 minutos.</p>
<div id="map" role="img" aria-label="Mapa de estaciones con retrasos de AVE y larga distancia"></div>
<p id="empty" class="map-note" hidden>No hay retrasos de AVE/LD ≥15 minutos en esta vista. No significa que no existan: puede ser falta de datos del feed.</p>
<div class="legend"><span><i class="dot" style="background:#f59e0b"></i>15–29 min</span><span><i class="dot" style="background:#f97316"></i>30–59 min</span><span><i class="dot" style="background:#dc2626"></i>≥60 min</span><span class="muted">Tamaño = retraso y trenes en esa estación</span></div>
<div class="card"><h2>Cómo se lee</h2><ul>
<li><b>Punto = estación.</b> No es un tren geolocalizado ni una interpolación de su recorrido.</li>
<li><b>Ahora</b> usa observaciones de los últimos 30 minutos. <b>Acumulado</b> incluye todo lo reportado desde las 00:00 de hoy; una estación puede seguir en el mapa aunque el tren ya haya pasado.</li>
<li>Un mismo tren puede aparecer en varias estaciones si el retraso se reporta en varias paradas.</li>
<li>El tamaño y el color resumen el retraso máximo y el número de trenes observados en esa estación.</li>
<li>Solo se muestran <b>Renfe AVE y larga distancia</b>; Cercanías no entra en este mapa.</li>
<li><b>No incluye Iryo ni Ouigo.</b> El feed usado es el GTFS-RT de Renfe; no hay integración con esos operadores.</li>
</ul></div>
<div class="warn"><b>Límites.</b> La fuente es el GTFS-RT de Renfe y las coordenadas del GTFS estático. No incluye Iryo ni Ouigo. No confirma causas, no atribuye responsabilidades y no mide la puntualidad oficial. La cobertura depende del feed: un hueco en el mapa no prueba que no haya retrasos. Los datos pueden cambiar entre ciclos.</div>
<div class="card"><h2>Estaciones en esta vista</h2><table><thead><tr><th>Estación</th><th>Servicio</th><th>Trenes</th><th>Máximo</th><th>Corredor</th></tr></thead><tbody id="table-body">{initial_rows or '<tr><td colspan="5">Sin estaciones con retraso ≥15 min.</td></tr>'}</tbody></table><p class="muted" id="table-note">Trenes distintos por estación; un mismo tren puede sumar en varias estaciones.</p></div>
<div class="card"><h2>Datos y método</h2><p>Fuente: <a href="https://data.renfe.com/" target="_blank" rel="noopener">Renfe GTFS-RT</a>, capturado por NearMe cada 15 minutos. Las coordenadas y los nombres de estación proceden del <b>GTFS estático oficial</b> de Renfe. No hay datos manuales en esta página.</p><p><a href="/datos/retrasos-renfe-mapa.json">Descargar JSON</a> · <a href="/retrasos-renfe-hoy.html">Estado completo del día</a> · <a href="/retrasos-renfe-estaciones.html">Fichas por estación</a></p></div>
<footer class="foot"><b>Ecosistema ViajeInteligencia</b><br><a href="https://www.viajeinteligencia.com">Principal</a><a href="https://municipal.viajeinteligencia.com">Municipal</a><a href="https://nearme.viajeinteligencia.com">NearMe</a><a href="https://country.viajeinteligencia.com">País a País</a><a href="https://vivienda.pruebapublica.com">Vivienda</a><a href="https://analisis.pruebapublica.com">Análisis</a><a href="/estado.html">Estado de fuentes</a><br><a class="kofi" href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer">☕ Invítame a un café</a><p class="muted">Proyecto personal, sin rastreo ni cuentas. Los servidores los paga su autor.</p></footer>
</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DATA={data_js};
let state={{view:'now',service:'all'}};
const map=L.map('map',{{scrollWheelZoom:false}}).setView([40.2,-3.5],5);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:18,attribution:'© OpenStreetMap'}}).addTo(map);
const layer=L.layerGroup().addTo(map);
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function color(d){{return d>=60?'#dc2626':d>=30?'#f97316':'#f59e0b'}}
function filtered(){{
 const view=DATA[state.view]||DATA.now; let list=view.stations||[];
 if(state.service!=='all') list=list.filter(x=>String(x.lines||'').split(',').map(s=>s.trim()).includes(state.service));
 return list;
}}
function render(){{
 const view=DATA[state.view]||DATA.now; const list=filtered();
 layer.clearLayers(); const pts=[];
 list.forEach(function(s){{
  const c=color(s.delay_min); const r=Math.max(7,Math.min(22,7+Math.sqrt(s.delay_min)*1.2));
  const popup='<b>'+esc(s.station)+'</b><br>+'+s.delay_min+' min · '+s.trains+' tren(es)<br>'+esc(s.lines)+(s.corridors?'<br><span class="muted">'+esc(s.corridors)+'</span>':'')+'<br><span class="muted">Estación, no posición del tren</span>';
  L.circleMarker([s.lat,s.lon],{{radius:r,color:c,weight:1.5,fillColor:c,fillOpacity:.45}}).bindPopup(popup).addTo(layer); pts.push([s.lat,s.lon]);
 }});
 if(pts.length){{map.fitBounds(pts,{{padding:[35,35],maxZoom:6}});}} else {{map.setView([40.2,-3.5],5);}}
 document.getElementById('empty').hidden=!!list.length;
 document.getElementById('stat-stations').textContent=list.length;
 document.getElementById('stat-trains').textContent=state.service==='all'?view.totals.trains:list.reduce((a,x)=>a+x.trains,0);
 document.getElementById('stat-trains-label').textContent=state.service==='all'?'trenes únicos afectados':'trenes-estación';
 document.getElementById('stat-max').textContent='+'+Math.max(0,...list.map(x=>x.delay_min))+' min';
 document.getElementById('view-note').textContent=(view.note||'')+(state.service==='all'?'':' · filtro: '+state.service);
 document.getElementById('table-body').innerHTML=list.map(x=>'<tr><td>'+esc(x.station)+'</td><td>'+esc(x.lines)+'</td><td>'+x.trains+'</td><td><b>+'+x.delay_min+' min</b></td><td>'+esc((x.corridors||'').slice(0,160))+'</td></tr>').join('')||'<tr><td colspan="5">Sin estaciones con retraso ≥15 min.</td></tr>';
 document.getElementById('table-note').textContent='Trenes distintos por estación; un mismo tren puede sumar en varias estaciones. Pares tren×estación en esta vista: '+view.totals.train_station_pairs+'.';
 document.querySelectorAll('.seg button').forEach(b=>{{const on=b.dataset.view===state.view;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));}});
}}
document.querySelectorAll('.seg button').forEach(b=>b.onclick=()=>{{state.view=b.dataset.view;render();}});
document.getElementById('service').onchange=e=>{{state.service=e.target.value;render();}};
async function refresh(){{
 try{{
  const r=await fetch('/datos/retrasos-renfe-mapa.json?x='+Date.now(),{{cache:'no-store'}});
  if(!r.ok) throw new Error('HTTP '+r.status);
  const d=await r.json(); DATA=d.views||DATA;
  const ts=d.generated_at?new Date(d.generated_at).toLocaleString('es-ES',{{dateStyle:'short',timeStyle:'short'}}):'';
  if(ts) document.getElementById('updated').textContent='Actualizado: '+ts+' Europe/Madrid';
  render();
 }}catch(e){{document.getElementById('refresh-note').textContent='No se pudo refrescar; se mantiene la última captura.';}}
}}
render(); setInterval(refresh,15*60*1000);
</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"OK {OUT} · ahora {now_view['totals']['stations']} estaciones / {now_view['totals']['trains']} trenes · hoy {day_view['totals']['stations']} / {day_view['totals']['trains']}")


if __name__ == "__main__":
    main()
