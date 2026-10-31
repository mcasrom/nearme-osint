#!/usr/bin/env python3
"""Página estática de trenes Renfe AV/LD con retraso actual."""
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
OUT = Path("/var/www/radar/retrasos-renfe-trenes.html")
DATA = Path("/var/www/radar/datos/retrasos-renfe-trenes.json")
URL = "https://radar.viajeinteligencia.com/retrasos-renfe-trenes.html"
SERVICES = ("AVE", "AVE INT", "AVLO", "AVANT", "AVANT EXP", "ALVIA", "EUROMED", "Intercity")
WINDOW_MIN = 30


def trains():
    cur = get_conn().cursor()
    cur.execute("""
        WITH obs AS (
            SELECT o.trip_id, o.stop_id, o.delay_seconds, o.is_forecast,
                   o.schedule_relationship, o.observed_at,
                   COALESCE(s.stop_name, o.station_name, o.stop_id) AS station
            FROM renfe_delay_obs o
            LEFT JOIN renfe_gtfs_stops s ON s.feed=o.subtype AND s.stop_id=o.stop_id
            WHERE o.subtype='alta_velocidad'
              AND o.observed_at >= now() - interval '30 minutes'
        ),
        agg AS (
            SELECT trip_id, MAX(delay_seconds) AS delay, COUNT(DISTINCT stop_id) AS stops,
                   BOOL_OR(schedule_relationship = 2) AS cancelled, MAX(observed_at) AS last_obs
            FROM obs GROUP BY trip_id
        ),
        latest AS (
            SELECT DISTINCT ON (trip_id) trip_id, station, is_forecast, schedule_relationship
            FROM obs ORDER BY trip_id, observed_at DESC
        )
        SELECT a.trip_id, a.delay, a.stops, a.cancelled, a.last_obs,
               l.station, l.is_forecast, l.schedule_relationship,
               t.route_short_name, t.trip_short_name, t.origin_name, t.dest_name
        FROM agg a
        JOIN latest l USING (trip_id)
        LEFT JOIN renfe_gtfs_trips t ON t.feed='alta_velocidad' AND t.trip_id=a.trip_id
        WHERE t.route_short_name = ANY(%s)
        ORDER BY a.delay DESC
    """, (list(SERVICES),))
    rows = []
    for r in cur.fetchall():
        tid, delay, stops, cancelled, last_obs, station, forecast, sched, service, number, origin, dest = r
        status = "cancelado" if cancelled or sched == 2 else ("previsto" if forecast else "observado")
        rows.append({
            "trip_id": tid, "service": service or "s/d", "number": number or tid,
            "origin": origin or "", "dest": dest or "", "station": station or "s/d",
            "delay_min": round((delay or 0) / 60), "stops": int(stops or 0),
            "status": status, "observed_at": last_obs.isoformat() if last_obs else None,
        })
    return rows


def scheduled_today():
    cur = get_conn().cursor()
    today = datetime.now(MADRID).date().isoformat()
    cur.execute(
        "SELECT route_short_name, COUNT(*) FROM renfe_gtfs_trips "
        "WHERE feed='alta_velocidad' AND trip_id LIKE %s GROUP BY route_short_name",
        ("%" + today,),
    )
    return {r[0]: int(r[1]) for r in cur.fetchall() if r[0]}


def main():
    rows = trains()
    now = datetime.now(MADRID)
    gen = now.isoformat(timespec="seconds")
    scheduled = scheduled_today()
    expected = {"AVE", "AVLO", "AVANT", "EUROMED", "ALVIA", "Intercity"}
    missing = sorted(expected - set(scheduled))
    services = sorted({r["service"] for r in rows if r["service"] and r["service"] != "s/d"})
    data = {
        "generated_at": gen,
        "window_min": WINDOW_MIN,
        "source": "Renfe GTFS-RT vía NearMe; identidad y corredores del GTFS estático",
        "disclaimer": "Solo Renfe AVE/LD. No incluye Iryo ni Ouigo. No es la posición del tren ni una confirmación oficial.",
        "scheduled_today": scheduled,
        "missing_scheduled": missing,
        "services": services,
        "trains": rows,
    }
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    data_js = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    services_html = "".join(f'<option value="{escape(s)}">{escape(s)}</option>' for s in services)
    if missing:
        note = f'<p class="warn"><b>Hoy el GTFS estático no programa: {escape(", ".join(missing))}.</b> No aparecen porque no hay circulaciones de referencia para hoy; no es un fallo de captura.</p>'
    else:
        note = ""
    json_ld = json.dumps({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Trenes Renfe AVE y larga distancia con retraso",
        "description": "Trenes Renfe AV/LD con retraso reportado en los últimos 30 minutos.",
        "url": URL, "dateModified": gen,
        "creator": {"@type": "Person", "name": "Miguel Castillo"},
        "isAccessibleForFree": True,
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": "https://radar.viajeinteligencia.com/datos/retrasos-renfe-trenes.json"}],
    }, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trenes Renfe AVE y larga distancia con retraso</title>
<meta name="description" content="Trenes Renfe AVE y larga distancia con retraso reportado ahora: servicio, número, origen, destino, última estación y estado. Solo Renfe; no incluye Iryo ni Ouigo.">
<link rel="canonical" href="{URL}">
<meta property="og:title" content="Trenes Renfe AVE/LD con retraso">
<meta property="og:description" content="Servicio, tren, origen, destino, última estación y retraso. Solo Renfe; no es una confirmación oficial.">
<meta property="og:type" content="website">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="https://radar.viajeinteligencia.com/retrasos-renfe-og.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json_ld}</script>
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--amber:#f59e0b;--paper:#fffaf5}}
*{{box-sizing:border-box}} body{{margin:0;background:#fafafa;color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.6}}
.wrap{{max-width:1050px;margin:0 auto;padding:24px 16px 56px}} a{{color:#c2410c}}
.top{{font-size:.85rem;margin-bottom:14px}} h1{{font-size:1.8rem;line-height:1.2;margin:.1em 0}} .lead{{font-size:1rem;color:#334155;max-width:850px}}
.meta{{font-size:.82rem;color:var(--muted)}} .controls{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:16px 0}}
select{{font:inherit;font-size:.88rem;padding:8px;border:1px solid var(--line);border-radius:8px;background:#fff}} .refresh{{font-size:.8rem;color:var(--muted)}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}} .stat{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:11px;text-align:center}} .stat b{{display:block;font-size:1.35rem;color:#b45309}} .stat span{{font-size:.75rem;color:var(--muted)}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:17px;margin:18px 0}} h2{{font-size:1.13rem;margin:0 0 8px;border-bottom:2px solid #fde68a;padding-bottom:5px}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}} th,td{{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}} th{{font-size:.74rem;color:var(--muted);position:sticky;top:0;background:#fff}} .delay{{font-weight:800;white-space:nowrap}} .red{{color:#dc2626}} .orange{{color:#c2410c}} .muted{{color:var(--muted);font-size:.82rem}}
.warn{{background:#fff7ed;border-left:4px solid #b45309;padding:10px 14px;border-radius:7px;font-size:.9rem}}
.foot{{border-top:1px solid var(--line);margin-top:28px;padding-top:18px;font-size:.85rem;color:#475569}} .foot a{{display:inline-block;margin:2px 7px 2px 0}} .kofi{{display:inline-flex;align-items:center;gap:7px;font-weight:700;color:#fff!important;background:#13C3A5;border-radius:7px;padding:9px 14px;text-decoration:none;margin-top:10px}}
@media(max-width:700px){{.stats{{grid-template-columns:1fr 1fr}}table{{font-size:.78rem}}th,td{{padding:6px}}}}
</style></head>
<body><main class="wrap">
<p class="top"><a href="/">← radar</a> · <a href="/retrasos-renfe-hoy.html">retrasos hoy</a> · <a href="/retrasos-renfe-mapa.html">mapa</a> · <a href="/retrasos-renfe-estaciones.html">estaciones</a></p>
<h1>Trenes Renfe AVE y larga distancia con retraso</h1>
<p class="lead">Trenes <b>Renfe AVE y larga distancia</b> con retraso reportado en los últimos <b>30 minutos</b>. La identidad y el corredor proceden del GTFS estático; el retraso, del GTFS-RT. No es la posición del tren.</p>
<p class="meta">Actualizado: <b id="updated">{now.strftime('%d/%m/%Y %H:%M')} Europe/Madrid</b> · datos GTFS-RT de Renfe vía NearMe · no es una web oficial.</p>
{note}
<div class="controls"><label>Servicio <select id="service"><option value="all">Todos</option>{services_html}</select></label><span class="refresh" id="refresh">Se actualiza cada 15 min.</span></div>
<div class="stats"><div class="stat"><b id="count">{len(rows)}</b><span>trenes en esta vista</span></div><div class="stat"><b id="max">+{max((r['delay_min'] for r in rows), default=0)} min</b><span>retraso máximo</span></div><div class="stat"><b>{len(rows)}</b><span>observaciones actuales</span></div></div>
<div class="card"><h2>Trenes con retraso</h2><table><thead><tr><th>Servicio</th><th>Tren</th><th>Origen → destino</th><th>Última estación</th><th>Retraso</th><th>Estado</th></tr></thead><tbody id="body"></tbody></table><p class="muted">Un tren puede tener varias paradas afectadas; aquí se muestra una vez, con su retraso máximo y la última estación observada.</p></div>
<div class="warn"><b>Límites.</b> Solo se muestran trenes Renfe que aparecen en el feed en los últimos 30 minutos. Un tren sin actualización no significa que vaya puntual. No se incluyen Iryo ni Ouigo. No se confirma la causa ni se mide la puntualidad oficial.</div>
<div class="card"><h2>Datos y método</h2><p>Fuente: <a href="https://data.renfe.com/" target="_blank" rel="noopener">Renfe GTFS-RT</a>, capturado por NearMe. Identidad, número, origen y destino desde el GTFS estático oficial. Sin datos manuales.</p><p><a href="/datos/retrasos-renfe-trenes.json">Descargar JSON</a> · <a href="/retrasos-renfe-mapa.html">Mapa de estaciones</a> · <a href="/retrasos-renfe-hoy.html">Estado completo</a></p></div>
<footer class="foot"><b>Ecosistema ViajeInteligencia</b><br><a href="https://www.viajeinteligencia.com">Principal</a><a href="https://municipal.viajeinteligencia.com">Municipal</a><a href="https://nearme.viajeinteligencia.com">NearMe</a><a href="https://country.viajeinteligencia.com">País a País</a><a href="https://vivienda.pruebapublica.com">Vivienda</a><a href="https://analisis.pruebapublica.com">Análisis</a><a href="/estado.html">Estado de fuentes</a><br><a class="kofi" href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer">☕ Invítame a un café</a><p class="muted">Proyecto personal, sin rastreo ni cuentas. Los servidores los paga su autor.</p></footer>
</main>
<script>
const DATA={data_js}; let state={{service:'all'}};
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function render(){{
 const list=DATA.filter(x=>state.service==='all'||x.service===state.service);
 document.getElementById('body').innerHTML=list.map(x=>'<tr><td><b>'+esc(x.service)+'</b></td><td>'+esc(x.number)+'</td><td>'+esc(x.origin)+' → '+esc(x.dest)+'</td><td>'+esc(x.station)+'</td><td class="delay '+(x.delay_min>=60?'red':x.delay_min>=30?'orange':'')+'">+'+x.delay_min+' min</td><td>'+esc(x.status)+'</td></tr>').join('')||'<tr><td colspan="6">Sin trenes con retraso en esta vista.</td></tr>';
 document.getElementById('count').textContent=list.length;
 document.getElementById('max').textContent='+'+Math.max(0,...list.map(x=>x.delay_min))+' min';
}}
document.getElementById('service').onchange=e=>{{state.service=e.target.value;render();}};
async function refresh(){{try{{const r=await fetch('/datos/retrasos-renfe-trenes.json?x='+Date.now(),{{cache:'no-store'}});if(!r.ok)throw Error(r.status);const d=await r.json();if(Array.isArray(d.trains)){{DATA.splice(0,DATA.length,...d.trains);const t=new Date(d.generated_at).toLocaleString('es-ES',{{dateStyle:'short',timeStyle:'short'}});document.getElementById('updated').textContent='Actualizado: '+t+' Europe/Madrid';render();}}}}catch(e){{document.getElementById('refresh').textContent='No se pudo refrescar; se mantiene la última captura.';}}}}
render(); setInterval(refresh,15*60*1000);
</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"OK {OUT} · {len(rows)} trenes · {len(services)} servicios · missing {missing}")


if __name__ == "__main__":
    main()
