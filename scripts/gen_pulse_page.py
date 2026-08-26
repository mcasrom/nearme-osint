#!/usr/bin/env python3
"""gen_pulse_page.py — página editorial estática «El pulso de España».

Gráfico 1: mapa de calor CCAA x día (intensidad de eventos del ecosistema NearMe).
Gráfico 2: índice de estrés sistémico (nº de fuentes distintas activas al día +
           diversidad media por CCAA).
Datos: tabla zone_metrics generada por compute_zone_metrics.py (cron 23:40).
SVG inline sin JS, metodología visible.

Salida: /var/www/radar/pulso-espana.html
Uso: PYTHONPATH=. venv/bin/python scripts/gen_pulse_page.py [--out RUTA]
"""
import sys
from datetime import date
from pathlib import Path

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn  # noqa: E402

OUT_DEFAULT = Path("/var/www/radar/pulso-espana.html")

NOMBRES = {
    "01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Baleares",
    "05": "Canarias", "06": "Cantabria", "07": "Castilla y León", "08": "Castilla-La Mancha",
    "09": "Cataluña", "10": "C. Valenciana", "11": "Extremadura", "12": "Galicia",
    "13": "Madrid", "14": "Murcia", "15": "Navarra", "16": "País Vasco",
    "17": "La Rioja", "18": "Ceuta", "19": "Melilla",
}


def cargar():
    cur = get_conn().cursor()
    cur.execute(
        "SELECT zone_id, stat_date, events_total, "
        "COALESCE(events_warning,0)+COALESCE(events_alert,0)+COALESCE(events_critical,0) "
        "FROM zone_metrics WHERE scope='ccaa' AND source='ALL'"
    )
    matriz = {}  # {(cod, fecha): (total, severos)}
    for cod, d, tot, sev in cur.fetchall():
        if cod in NOMBRES:
            matriz[(cod, d.isoformat())] = (tot, sev)
    cur.execute(
        "SELECT stat_date, count(DISTINCT source), round(avg(diversity)::numeric,2) "
        "FROM zone_metrics WHERE scope='ccaa' AND source<>'ALL' AND events_total>0 "
        "GROUP BY stat_date ORDER BY stat_date"
    )
    estres = [(d.isoformat(), int(n), float(avg)) for d, n, avg in cur.fetchall()]
    return matriz, estres


def color(v, vmax):
    """blanco->ambar->rojo según sqrt(v/vmax)."""
    t = (v / vmax) ** 0.5 if vmax else 0.0
    stops = [(255, 247, 237), (253, 186, 116), (234, 88, 12), (153, 27, 27)]
    seg = min(int(t * 3), 2)
    f = t * 3 - seg
    c = tuple(round(stops[seg][i] + (stops[seg + 1][i] - stops[seg][i]) * f) for i in range(3))
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def svg_heatmap(matriz, fechas, cods_orden):
    cw, ch, pad_l, pad_t = 26, 21, 150, 14
    W = pad_l + len(fechas) * cw + 60
    H = pad_t + len(cods_orden) * ch + 46
    vmax = max((v[0] for v in matriz.values()), default=1)
    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font-family:system-ui">'
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    for j, f in enumerate(fechas):
        if j % 5 == 0 or j == len(fechas) - 1:
            dd = f[8:10] + "/" + f[5:7]
            out.append(f'<text x="{pad_l + j * cw + cw // 2}" y="{H - 26}" font-size="9" '
                       f'text-anchor="middle" fill="#888">{dd}</text>')
    for i, cod in enumerate(cods_orden):
        y = pad_t + i * ch
        nombre = NOMBRES[cod]
        total_fila = sum(matriz.get((cod, f), (0, 0))[0] for f in fechas)
        out.append(f'<text x="{pad_l - 6}" y="{y + ch // 2 + 4}" font-size="10.5" text-anchor="end" '
                   f'fill="#333">{nombre}</text>')
        out.append(f'<text x="{pad_l - 6}" y="{y + ch // 2 + 4}" font-size="9" text-anchor="end" fill="#aaa" '
                   f'dx="-{max(4, 6 * len(nombre))}">{total_fila}</text>')
        for j, f in enumerate(fechas):
            tot, sev = matriz.get((cod, f), (0, 0))
            x = pad_l + j * cw
            out.append(f'<rect x="{x}" y="{y}" width="{cw - 2}" height="{ch - 2}" rx="3" '
                       f'fill="{color(tot, vmax)}">'
                       f'<title>{NOMBRES[cod]} · {f}: {tot} eventos ({sev} severos)</title></rect>')
    out.append(f'<text x="{pad_l}" y="{H - 8}" font-size="9.5" fill="#777">'
               f'intensidad = nº eventos asignados a la comunidad ese día (escala raíz)</text></svg>')
    return "".join(out)


def svg_estres(estres):
    W, H, pad = 800, 280, 46
    n = len(estres)
    y1f, y1d = max(e[1] for e in estres), 5.0
    def X(i): return pad + i * (W - pad - 20) / max(n - 1, 1)
    def Y1(v): return H - 34 - v / (y1f + 1) * (H - 74)
    def Y2(v): return H - 34 - v / y1d * (H - 74)
    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font-family:system-ui">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    for gv in range(0, int(y1f) + 2, max(1, (y1f + 1) // 4)):
        out.append(f'<line x1="{pad}" y1="{Y1(gv)}" x2="{W - 20}" y2="{Y1(gv)}" stroke="#eee"/>'
                   f'<text x="{pad - 6}" y="{Y1(gv) + 3}" font-size="9" text-anchor="end" fill="#999">{gv}</text>')
    p1 = " ".join(f"{X(i):.1f},{Y1(e[1]):.1f}" for i, e in enumerate(estres))
    p2 = " ".join(f"{X(i):.1f},{Y2(e[2]):.1f}" for i, e in enumerate(estres))
    out.append(f'<polyline points="{p1}" fill="none" stroke="#e05520" stroke-width="2"/>')
    out.append(f'<polyline points="{p2}" fill="none" stroke="#2563eb" stroke-width="2" stroke-dasharray="5,4"/>')
    pico = max(estres, key=lambda e: e[1])
    ip = estres.index(pico)
    out.append(f'<circle cx="{X(ip)}" cy="{Y1(pico[1])}" r="4" fill="#e05520"/>'
               f'<text x="{X(ip)}" y="{Y1(pico[1]) - 10}" font-size="10" text-anchor="middle" fill="#c2410c">'
               f'pico: {pico[1]} fuentes ({pico[0][8:10]}/{pico[0][5:7]})</text>')
    for i, e in enumerate(estres):
        if i % 5 == 0 or i == n - 1:
            out.append(f'<text x="{X(i)}" y="{H - 16}" font-size="9" text-anchor="middle" fill="#888">'
                       f'{e[0][8:10]}/{e[0][5:7]}</text>')
    out.append(f'<text x="{pad}" y="18" font-size="11" fill="#e05520">— fuentes distintas activas en España</text>'
               f'<text x="{pad + 250}" y="18" font-size="11" fill="#2563eb">-- diversidad media por CCAA</text>'
               f'</svg>')
    return "".join(out)


def main():
    matriz, estres = cargar()
    if not matriz:
        print("sin datos zone_metrics"); sys.exit(1)
    fechas = sorted({k[1] for k in matriz})
    cods = sorted({k[0] for k in matriz}, key=lambda c: -sum(v[0] for k, v in matriz.items() if k[0] == c))
    tot_global = sum(v[0] for v in matriz.values())
    top_ccaa = NOMBRES[cods[0]]
    pico = max(estres, key=lambda e: e[1])
    hoy = date.today().strftime("%d/%m/%Y")
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>El pulso de España · estrés territorial medido día a día</title>
<meta name="description" content="Mapa de calor de la actividad de emergencias y avisos por comunidad autónoma y día, más el índice de estrés sistémico: cuántas fuentes de datos distintas alarman a la vez. Datos propios NearMe.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/pulso-espana.html"></head>
<body style="font-family:system-ui,-apple-system,sans-serif;margin:0;background:#fafafa;color:#222">
<main style="max-width:900px;margin:0 auto;padding:20px 16px 48px">
<p style="font-size:.85rem"><a href="/" style="color:#c2410c">← radar</a> · <a href="/incendios-meteorologia.html" style="color:#c2410c">incendios × meteorología</a></p>
<h1 style="font-size:1.55rem;margin:.2em 0">El pulso de España</h1>
<p>Cada día el ecosistema NearMe captura miles de señales: incendios (NASA FIRMS), tráfico (DGT),
avisos meteorológicos (AEMET), calidad del aire (MITECO/OpenAQ), ferroviarias (Renfe), energía (REE),
embalses y sismicidad (IGN). Esta página las agrega por comunidad y día.</p>
<div class="kpi" style="display:inline-block;background:#f2f2f2;border-radius:8px;padding:8px 14px;margin:4px 6px 4px 0;font-size:.95rem">📅 ventana: {fechas[0][8:10]}/{fechas[0][5:7]} → {fechas[-1][8:10]}/{fechas[-1][5:7]}</div>
<div class="kpi" style="display:inline-block;background:#f2f2f2;border-radius:8px;padding:8px 14px;margin:4px 6px 4px 0;font-size:.95rem">📍 {tot_global:,} eventos asignados</div>
<div class="kpi" style="display:inline-block;background:#f2f2f2;border-radius:8px;padding:8px 14px;margin:4px 6px 4px 0;font-size:.95rem">🏆 comunidad más activa: {top_ccaa}</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Mapa de calor: intensidad por comunidad y día</h3>
{svg_heatmap(matriz, fechas, cods)}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Índice de estrés sistémico</h3>
<p style="font-size:.92rem;color:#444;margin-top:0">¿Cuántos <em>sistemas distintos</em> alarman el mismo día?
Cuando fuego, calor, aire y energía coinciden, hablamos de crisis compuesta. Pico de la ventana:
<strong>{pico[1]} fuentes simultáneas</strong> el {pico[0][8:10]}/{pico[0][5:7]}.</p>
{svg_estres(estres)}
</div>

<div class="met" style="font-size:.85rem;color:#555;line-height:1.5;border-top:1px solid #ddd;padding-top:12px">
<strong>Metodología honesta.</strong> Fuente: tabla <code>zone_metrics</code> del proyecto nearme-osint
(agregado diario automático sobre eventos geolocalizados y asignados a CCAA mediante polígonos oficiales).
La ingesta histórica es irregular (las fuentes se incorporaron escalonadamente desde el 28/07/2026), por lo que
los primeros días sobrerrepresentan arranques masivos. Los volúmenes dominados por DGT reflejan densidad de
carreteras vigiladas, no necesariamente mayor peligrosidad. Sin relación causal implícita: descripción,
no diagnóstico. Actualizado: {hoy}.
</div>
</main></body></html>"""
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else OUT_DEFAULT
    out.write_text(html)
    print(f"OK {out} ({len(html)//1024} KB) · {len(fechas)} días · {tot_global:,} eventos")


if __name__ == "__main__":
    main()
