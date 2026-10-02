#!/usr/bin/env python3
"""gen_sismos.py — página estática de sismos del radar (/var/www/radar/sismos.html).

Lista + mapa Leaflet de los sismos recientes (IGN + USGS) desde la tabla `events`.
Deep-link: /sismos.html#<source_id> centra el mapa, resalta y hace scroll al evento
(lo usan los posts de Mastodon/Bluesky).

Uso: PYTHONPATH=. venv/bin/python scripts/gen_sismos.py [--out RUTA] [--dias 30]
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn  # noqa: E402


def _mag(subtype, title):
    if subtype and subtype.startswith("mag_"):
        try:
            return float(subtype[4:])
        except ValueError:
            pass
    m = re.search(r"M(-?\d+(?:\.\d+)?)", title or "")
    return float(m.group(1)) if m else None


def _depth(desc):
    m = re.search(r"Profundidad:\s*([\d.,]+)", desc or "")
    return m.group(1) if m else "?"


def _hora(desc, created):
    m = re.search(r"Hora:\s*([\d-]+ [\d:]+)\s*UTC", desc or "")
    if m:
        return m.group(1)
    return created.strftime("%Y-%m-%d %H:%M:%S") if created else ""


def _place(title):
    return re.sub(r"^Terremoto\s+M[\d.]+\s*(\([^)]*\))?\s*[—-]\s*", "", title or "").strip()


def cargar(dias):
    cur = get_conn().cursor()
    cur.execute(
        "SELECT source, source_id, subtype, title, description, lat, lon, created_at "
        "FROM events WHERE event_type='earthquake' AND status='active' "
        "AND created_at > now() - (%s || ' days')::interval", (str(dias),))
    out = []
    for source, sid, subtype, title, desc, lat, lon, created in cur.fetchall():
        mag = _mag(subtype, title)
        if mag is None or lat is None:
            continue
        out.append({"id": sid, "mag": mag, "place": _place(title), "lat": lat, "lon": lon,
                    "depth": _depth(desc), "hora": _hora(desc, created),
                    "fuente": "IGN" if source == "ign" else "USGS",
                    "es": source in ("ign", "usgs_es")})
    out.sort(key=lambda x: x["hora"], reverse=True)
    return out


def nivel(m):
    return "alert" if m >= 5 else "warn" if m >= 3 else "info"


def render(evs, dias):
    from datetime import timedelta
    ahora = datetime.now(timezone.utc)
    d1 = [e for e in evs if e["hora"] and e["hora"][:10] >= (ahora - timedelta(days=1)).strftime("%Y-%m-%d")]
    d7 = [e for e in evs if e["hora"] and e["hora"][:10] >= (ahora - timedelta(days=7)).strftime("%Y-%m-%d")]
    mx = max((e["mag"] for e in d7), default=0)
    filas = "".join(
        f'<div class="ev {nivel(e["mag"])}" id="{html.escape(e["id"])}">'
        f'<div class="t"><span>M{e["mag"]:g} · {html.escape(e["place"])}</span>'
        f'<span class="lvl {nivel(e["mag"])}">{e["fuente"]}</span></div>'
        f'<div class="d">{e["lat"]:.2f} / {e["lon"]:.2f} · prof. {html.escape(str(e["depth"]))} km · '
        f'{html.escape(e["hora"])} UTC</div></div>'
        for e in evs[:400])
    data_js = json.dumps([{k: e[k] for k in ("id", "mag", "lat", "lon", "place", "fuente", "hora")}
                          for e in evs], ensure_ascii=False)
    return TEMPLATE.replace("__DATA__", data_js).replace("__FILAS__", filas) \
                   .replace("__N24__", str(len(d1))).replace("__N7__", str(len(d7))) \
                   .replace("__NMAX__", f"{mx:g}").replace("__TOT__", str(len(evs))) \
                   .replace("__DIAS__", str(dias))


TEMPLATE = r"""<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sismos en España y el mundo · Radar de Emergencias</title>
<meta name="description" content="Sismos recientes en España (IGN) y en el mundo (USGS), en vivo: magnitud, profundidad y epicentro. Radar de emergencias, datos oficiales.">
<meta name="robots" content="index, follow"><link rel="canonical" href="https://radar.viajeinteligencia.com/sismos.html">
<meta property="og:type" content="website"><meta property="og:title" content="Sismos recientes · Radar de Emergencias">
<meta property="og:description" content="Últimos sismos en España (IGN) y el mundo (USGS): magnitud, profundidad y epicentro.">
<meta property="og:image" content="https://radar.viajeinteligencia.com/og.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{--bg:#0B0F17;--panel:#121826;--panel2:#171F30;--line:#232B3D;--text:#E7EBF3;--dim:#8993A8;--faint:#576076;--amber:#FFB454;--red:#F87171;--green:#34D399;}
*{box-sizing:border-box;margin:0;padding:0}body{background:var(--bg);color:var(--text);font-family:-apple-system,system-ui,sans-serif}
.top{display:flex;align-items:center;gap:14px;padding:14px 20px;background:#0d1322;border-bottom:1px solid var(--line);flex-wrap:wrap}
.brand{font-family:ui-monospace,monospace;font-size:14px;font-weight:600}.brand a{color:var(--text);text-decoration:none}.brand .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--red);box-shadow:0 0 8px var(--red)}
.top .r{margin-left:auto;font-size:12px}.top .r a{color:var(--amber);text-decoration:none}
.stats{display:flex;gap:8px;padding:10px 20px;background:#0d1322;border-bottom:1px solid var(--line);flex-wrap:wrap}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 12px;font-size:12px;color:var(--dim)}
.stat b{color:var(--text);font-size:14px}.stat.alert{border-color:var(--amber)}
.layout{display:grid;grid-template-columns:1fr 360px;height:calc(100vh - 104px)}
@media(max-width:820px){.layout{grid-template-columns:1fr;grid-template-rows:55vh auto;height:auto}}
#map{height:100%;min-height:340px;background:#0a0e17}
#feed{background:var(--panel);border-left:1px solid var(--line);overflow-y:auto;padding:12px}
@media(max-width:820px){#feed{border-left:none;border-top:1px solid var(--line);max-height:45vh}}
.ev{background:var(--panel2);border:1px solid var(--line);border-left:3px solid var(--dim);border-radius:8px;padding:9px 11px;margin-bottom:8px;font-size:12.5px;scroll-margin-top:12px}
.ev.alert{border-left-color:var(--red)}.ev.warn{border-left-color:var(--amber)}.ev.info{border-left-color:var(--green)}
.ev.hl{outline:2px solid var(--amber);background:#20293c}
.ev .t{font-weight:700;display:flex;justify-content:space-between;gap:8px}
.ev .lvl{font-size:10px;font-weight:700;text-transform:uppercase;color:var(--faint)}
.ev .lvl.alert{color:var(--red)}.ev .lvl.warn{color:var(--amber)}.ev .lvl.info{color:var(--green)}
.ev .d{color:var(--dim);font-size:11.5px;margin-top:3px}
footer{padding:10px 20px;background:#0d1322;border-top:1px solid var(--line);font-family:ui-monospace,monospace;font-size:10.5px;color:var(--faint);display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px}
footer a{color:var(--amber);text-decoration:none}.osm-dark .leaflet-tile{filter:invert(1) hue-rotate(180deg) brightness(.8) contrast(1.1) saturate(.5)}
</style></head><body>
<div class="top"><div class="brand"><span class="dot"></span> Sismos · <a href="/">Radar de Emergencias</a></div>
<div class="r">Últimos __DIAS__ días · <a href="/">← volver al radar</a></div></div>
<div class="stats">
<span class="stat">Últimas 24 h: <b>__N24__</b></span>
<span class="stat">Últimos 7 días: <b>__N7__</b></span>
<span class="stat alert">Mayor (7 d): <b>M__NMAX__</b></span>
<span class="stat">Total mostrado: <b>__TOT__</b></span>
<span class="stat">Fuente: <b>IGN · USGS</b></span>
</div>
<div class="layout">
<div id="map"></div>
<div id="feed">__FILAS__</div>
</div>
<footer><span>Datos: IGN (sismología) · USGS. Solo se muestran hechos con fuente.</span>
<span>NearMe OSINT · <a href="https://nearme.viajeinteligencia.com">mapa completo →</a></span></footer>
<script>
var DATA = __DATA__;
var map = L.map('map').setView([40.0, -3.0], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,subdomains:'abc',className:'osm-dark',attribution:'© OpenStreetMap'}).addTo(map);
function col(m){return m>=5?'#F87171':m>=3?'#FFB454':'#34D399';}
DATA.forEach(function(e){if(e.lat==null||e.lon==null)return;
  var c=L.circleMarker([e.lat,e.lon],{radius:Math.max(4,Math.min(18,2+e.mag*1.8)),color:col(e.mag),weight:1.5,fillColor:col(e.mag),fillOpacity:.35});
  c.bindPopup('<b>M'+e.mag+'</b> '+e.place+'<br>'+e.hora+' UTC · '+e.fuente);
  c.evId=e.id; c.addTo(map);});
var hash=decodeURIComponent((location.hash||'').slice(1));
if(hash){var el=document.getElementById(hash);var e=DATA.find(function(x){return x.id===hash;});
  if(el){el.classList.add('hl');el.scrollIntoView({block:'center'});}
  if(e&&e.lat!=null){map.setView([e.lat,e.lon],9);}}
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/var/www/radar/sismos.html")
    ap.add_argument("--dias", type=int, default=30)
    a = ap.parse_args()
    evs = cargar(a.dias)
    Path(a.out).write_text(render(evs, a.dias), encoding="utf-8")
    print(f"[sismos] {len(evs)} eventos → {a.out}")


if __name__ == "__main__":
    main()
