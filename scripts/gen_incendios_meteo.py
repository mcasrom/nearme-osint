#!/usr/bin/env python3
"""gen_incendios_meteo.py — página editorial estática: incendios × meteorología (opción B).

Cruza detecciones FIRMS de NearMe (zone_metrics) con meteo diaria real
(Open-Meteo forecast past_days, sin retardo de reanálisis) por CCAA y día.
Claves por código INE de CCAA (estable; los nombres en BD están truncados).
SVG inline sin dependencias JS.

Salida: /var/www/radar/incendios-meteorologia.html
Uso: python3 scripts/gen_incendios_meteo.py [--out RUTA]
"""
import json, math, sys, time
from datetime import date, timedelta
from pathlib import Path
import urllib.request

BASE = Path.home() / "nearme-osint"
CACHE = BASE / "data" / "meteo_cache.json"
OUT_DEFAULT = Path("/var/www/radar/incendios-meteorologia.html")
WINDOW_DAYS = 30

# capital aproximada por código INE de CCAA -> lat,lon
CAPITALES = {
    "01": (37.39, -5.99), "02": (41.65, -0.89), "03": (43.36, -5.86),
    "04": (39.57, 2.65), "05": (28.12, -15.44), "06": (43.46, -3.81),
    "07": (41.65, -4.72), "08": (39.86, -4.03),
    "09": (41.39, 2.17), "10": (39.47, -0.38),
    "11": (38.92, -6.34), "12": (42.88, -8.54),
    "13": (40.42, -3.70), "14": (37.99, -1.13),
    "15": (42.82, -1.64), "16": (42.85, -2.67),
    "17": (42.47, -2.45), "18": (35.89, -5.32), "19": (35.29, -2.95),
}
NOMBRES = {
    "01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Baleares",
    "05": "Canarias", "06": "Cantabria", "07": "Castilla y León", "08": "Castilla-La Mancha",
    "09": "Cataluña", "10": "C. Valenciana", "11": "Extremadura", "12": "Galicia",
    "13": "Madrid", "14": "Murcia", "15": "Navarra", "16": "País Vasco",
    "17": "La Rioja", "18": "Ceuta", "19": "Melilla",
}

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 nearme-analytics"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def meteo(d0, d1):
    """{cod_ccaa: {fecha_iso: (tmax, wmax)}} con caché 12h."""
    if CACHE.exists():
        try:
            j = json.load(open(CACHE))
            if j.get("d0") == d0.isoformat() and j.get("d1") == d1.isoformat() \
               and time.time() - j.get("ts", 0) < 12 * 3600:
                return j["data"]
        except Exception:
            pass
    data = {}
    for cod, (lat, lon) in CAPITALES.items():
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&daily=temperature_2m_max,wind_speed_10m_max&timezone=Europe%2FMadrid"
               f"&past_days={WINDOW_DAYS + 2}")
        try:
            daily = fetch(url).get("daily", {})
            data[cod] = {f: (daily["temperature_2m_max"][i], daily["wind_speed_10m_max"][i])
                         for i, f in enumerate(daily.get("time", []))}
        except Exception as e:
            print(f"  aviso meteo {cod}: {str(e)[:60]}", flush=True)
        time.sleep(1.1)          # cortesía con la API gratuita
    CACHE.write_text(json.dumps({"d0": d0.isoformat(), "d1": d1.isoformat(), "ts": time.time(), "data": data}))
    return data

def pearson(xs, ys):
    n = len(xs)
    if n < 3: return None
    mx, my = sum(xs)/n, sum(ys)/n
    sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x-mx)**2 for x in xs)); sy = math.sqrt(sum((y-my)**2 for y in ys))
    return sxy/(sx*sy) if sx*sy else None

def svg_scatter(pts, xlabel, ylabel, W=760, H=430, color="#e05520"):
    if len(pts) < 3: return "<p>(sin datos suficientes)</p>"
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1 = min(xs), max(xs); y1 = max(max(ys), 1)
    pad = 46
    def X(v): return pad + (v-x0)/(x1-x0+1e-9)*(W-pad-18)
    def Y(v): return H-30-(v/y1)*(H-56)
    grid = "".join(f'<line x1="{pad}" y1="{Y(t):.1f}" x2="{W-14}" y2="{Y(t):.1f}" stroke="#eee"/>'
                   f'<text x="6" y="{Y(t)+4:.1f}" font-size="11" fill="#888">{t:g}</text>'
                   for t in [y1*i/4 for i in range(5)])
    dots = "".join(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{s:.1f}" fill="{color}" fill-opacity="0.55"/>'
                   for x, y, s in pts)
    n = len(pts); mx = sum(xs)/n; my = sum(ys)/n
    b = sum((x-mx)*(y-my) for x, y in zip(xs, ys))/max(sum((x-mx)**2 for x in xs), 1e-9)
    a = my-b*mx
    trend = (f'<line x1="{X(x0):.1f}" y1="{Y(a+b*x0):.1f}" x2="{X(x1):.1f}" y2="{Y(a+b*x1):.1f}" '
             f'stroke="#333" stroke-dasharray="5 4" stroke-width="1.5"/>')
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img">{grid}'
            f'<line x1="{pad}" y1="{H-30}" x2="{W-14}" y2="{H-30}" stroke="#999"/>'
            f'<line x1="{pad}" y1="16" x2="{pad}" y2="{H-30}" stroke="#999"/>'
            f'<text x="{W/2}" y="{H-8}" text-anchor="middle" font-size="12" fill="#555">{xlabel}</text>'
            f'<text x="14" y="{H/2}" transform="rotate(-90 14 {H/2})" text-anchor="middle" font-size="12" fill="#555">{ylabel}</text>'
            f'{dots}{trend}</svg>')

def fmt_r(r):
    return f"r={r:+.2f}" if r is not None else "r n/d"

FOOTER = """
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
"""


def main():
    from src.db import get_conn
    cur = get_conn().cursor()
    d1 = date.today(); d0 = d1 - timedelta(days=WINDOW_DAYS)

    cur.execute("""SELECT stat_date, zone_id, events_total FROM zone_metrics
                   WHERE scope='ccaa' AND source='nasa_firms' AND stat_date BETWEEN %s AND %s""",
                (d0, d1))
    fires = cur.fetchall()

    met = meteo(d0, d1)
    fire_map = {(d, cod): nf for d, cod, nf in fires}
    all_days = [d0 + timedelta(days=i) for i in range((d1-d0).days + 1)]
    pts_t, pts_w, rows = [], [], []
    for cod in CAPITALES:
        for d in all_days:
            mday = met.get(cod, {}).get(d.isoformat())
            if not mday or mday[0] is None: continue
            tmax, wmax = mday
            t = tmax if tmax is not None else 0
            w = wmax if wmax is not None else 0
            nf = fire_map.get((d, cod), 0)   # ceros incluidos: días sin fuego
            pts_t.append((t, nf, 3+min(w, 60)/12))
            pts_w.append((w, nf, 3+min(t, 45)/8))
            if nf > 0: rows.append((d, cod, nf, t, w))

    r_t = pearson([p[0] for p in pts_t], [p[1] for p in pts_t])
    r_w = pearson([p[0] for p in pts_w], [p[1] for p in pts_w])
    rows.sort(key=lambda r: -r[2])

    top = "".join(f"<tr><td>{d.strftime('%d/%m')}</td><td>{NOMBRES.get(cod, cod)}</td>"
                  f"<td><b>{nf}</b></td><td>{t:.1f} °C</td><td>{w:.0f} km/h</td></tr>"
                  for d, cod, nf, t, w in rows[:12])
    last_meteo = max((f for v in met.values() for f in v), default="-")

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Incendios × meteorología · NearMe análisis</title>
<meta name="description" content="Relación entre detecciones térmicas de incendios (NASA FIRMS vía NearMe) y temperatura/viento diarios por comunidad autónoma. Metodología explícita.">
<style>
body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#fafafa;color:#222}}
main{{max-width:900px;margin:auto;padding:24px 16px}}
h1{{font-size:1.5rem}} .card{{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0}}
.kpi{{display:inline-block;background:#f2f2f2;border-radius:8px;padding:8px 14px;margin:4px 6px 4px 0;font-size:.95rem}}
table{{border-collapse:collapse;width:100%;font-size:.92rem}} td,th{{padding:6px 8px;border-bottom:1px solid #eee;text-align:left}}
.met{{font-size:.85rem;color:#555;line-height:1.5}} a{{color:#c2410c}}
</style></head><body><main>
<h1>🔥 Incendios × meteorología</h1>
<p>Cada punto es una <b>comunidad autónoma en un día concreto</b>: eje X = temperatura máxima diaria (media en la capital autonómica), eje Y = detecciones térmicas registradas por NearMe (NASA FIRMS). El tamaño refleja el viento.</p>
<div class="kpi">Ventana: {d0.strftime('%d/%m')} – {d1.strftime('%d/%m')} 2026</div>
<div class="kpi">Puntos: {len(pts_t)} CCAA-día</div>
<div class="kpi">Correlación temp: {fmt_r(r_t)}</div>
<div class="kpi">Correlación viento: {fmt_r(r_w)}</div>
<div class="card"><h3>Detecciones vs temperatura máxima</h3>{svg_scatter(pts_t, "T máxima diaria (°C)", "Detecciones FIRMS")}</div>
<div class="card"><h3>Detecciones vs viento máximo</h3>{svg_scatter(pts_w, "Viento máx diario (km/h)", "Detecciones FIRMS", color="#2563eb")}</div>
<div class="card"><h3>Días con más detecciones</h3><table><tr><th>Día</th><th>CCAA</th><th>Detecciones</th><th>T máx</th><th>Viento</th></tr>{top}</table></div>
<div class="card met"><b>Metodología y límites (léelo antes de compartir)</b><br>
· Fuente de fuego: NASA FIRMS (satélites MODIS/VIIRS) tal como la ingiere NearMe OSINT — son <i>detecciones térmicas puntuales</i>, no superficie quemada ni focos confirmados.<br>
· Fuente de meteo: Open-Meteo (modelos), valor diario en la capital autonómica como aproximación territorial; disponible hasta {last_meteo}.<br>
· Correlación NO es causalidad: puede mediar humedad, sequía acumulada o ignición humana, variables no controladas aquí.<br>
· Sesgos conocidos: cobertura satelital variable, nubosidad, y que las CCAA grandes concentran más terreno forestal.<br>
· Datos generados automáticamente el {date.today().strftime('%d/%m/%Y')} · parte del ecosistema <a href="https://nearme.viajeinteligencia.com">NearMe OSINT</a>.</div>
{FOOTER}</main></body></html>"""

    out = Path(sys.argv[sys.argv.index("--out")+1]) if "--out" in sys.argv else OUT_DEFAULT
    out.write_text(html)
    print(f"[FIN] {out} · puntos={len(pts_t)} temp:{fmt_r(r_t)} viento:{fmt_r(r_w)}")

if __name__ == "__main__":
    main()
