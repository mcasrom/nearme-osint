#!/usr/bin/env python3
"""gen_enjambre_granada.py — página editorial: enjambre sísmico de Granada.

Muestra la evolución del enjambre activo desde el 14 de agosto de 2026:
- Timeline día a día (barras eventos + línea magnitud máxima)
- Heatmap por municipio (barras apiladas)
- Comparación con enjambre Santa Fe 2021
Datos: tabla events (source=ign) con fecha derivada de expires_at-48h.
SVG inline sin JS, footer ecosistema+Ko-fi.

Salida: /var/www/radar/enjambre-granada.html
Uso: PYTHONPATH=. venv/bin/python scripts/gen_enjambre_granada.py [--out RUTA]
"""
import re, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn  # noqa: E402

OUT_DEFAULT = Path("/var/www/radar/enjambre-granada.html")

# Municipios del enjambre de Granada — centroides aproximados para referencia
MUNICIPIOS = {
    "ALHENDÍN": "Alhendín", "LA ZUBIA": "La Zubia", "GÓJAR": "Gójar",
    "OGÍJARES": "Ogíjares", "OTURA": "Otura", "ARMILLA": "Armilla",
    "LAS GABIAS": "Las Gabias", "CHURRIANA DE LA VEGA": "Churriana d.Vega",
    "VÍZNAR": "Víznar", "ALFACAR": "Alfacar", "PULIANAS": "Pulianas",
    "MARACENA": "Maracena", "AGONÍA": "Agonía", "CAMBIJAR": "Cambijar",
    "CUEVAS DE VELASCO": "Cuevas", "VEGAS DEL GENIL": "Vegas del Genil",
}

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


def extract_municipality(title):
    """Extrae municipio del título IGN: 'Terremoto M2.0 — SE ALHENDÍN.GR'"""
    m = re.search(r"—\s+\w+\s+(.+?)\.GR", title)
    if m:
        name = m.group(1).strip().upper()
        return MUNICIPIOS.get(name, name.title())
    return "Otro"


def extract_mag(title):
    """Extrae magnitud del título: 'Terremoto M3.7 (Mw)'"""
    m = re.search(r"M(\d+\.?\d*)", title)
    return float(m.group(1)) if m else 0.0


def cargar():
    """Carga eventos IGN en zona Granada desde el 14/Ago."""
    cur = get_conn().cursor()
    cur.execute("""
        SELECT title, expires_at - interval '48 hours' as event_time, lat, lon
        FROM events WHERE source='ign'
        AND lat BETWEEN 36.8 AND 37.4 AND lon BETWEEN -3.8 AND -3.0
        AND expires_at >= '2026-08-14'
        ORDER BY event_time
    """)
    events = []
    for title, etime, lat, lon in cur.fetchall():
        mag = extract_mag(title)
        mun = extract_municipality(title)
        events.append({
            "date": etime.date().isoformat() if etime else "unknown",
            "mag": mag, "mun": mun, "lat": lat, "lon": lon
        })
    return events


def svg_timeline(daily):
    """Barras eventos/día (azul) + línea magnitud máxima (rojo) con doble eje Y."""
    dates = sorted(daily.keys())
    n = len(dates)
    if n < 3:
        return "<p>(datos insuficientes)</p>"
    # Layout: left axis (events), right axis (magnitude)
    pad_l, pad_r, pad_top, pad_bot = 52, 52, 40, 48
    W = max(720, n * 36 + pad_l + pad_r)
    H = 320
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_top - pad_bot

    y1_max = max(d["count"] for d in daily.values())
    y2_max = max(d["max_mag"] for d in daily.values()) + 0.3

    bar_w = max(10, plot_w // n - 5)

    def X(i): return pad_l + i * (plot_w / n) + bar_w / 2
    def Y1(v): return pad_top + plot_h - (v / (y1_max + 0.5)) * plot_h
    def Y2(v): return pad_top + plot_h - (v / y2_max) * plot_h

    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font-family:system-ui">',
           f'<defs><linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0%" stop-color="#3b82f6" stop-opacity=".9"/>'
           f'<stop offset="100%" stop-color="#1d4ed8" stop-opacity=".75"/>'
           f'</linearGradient></defs>',
           f'<rect width="{W}" height="{H}" fill="var(--card,#fff)"/>']

    # --- Left axis: events count (blue) ---
    steps1 = min(5, y1_max + 1)
    step1 = max(1, round((y1_max + 1) / steps1))
    for g in range(0, y1_max + step1, step1):
        yy = Y1(g)
        out.append(f'<line x1="{pad_l}" y1="{yy}" x2="{W - pad_r}" y2="{yy}" stroke="#e5e7eb" stroke-dasharray="4,3"/>')
        out.append(f'<text x="{pad_l - 8}" y="{yy + 3}" font-size="10" text-anchor="end" fill="#3b82f6" font-weight="600">{g}</text>')
    # left axis label
    out.append(f'<text x="12" y="{pad_top + plot_h / 2}" font-size="10" fill="#3b82f6" font-weight="600" '
               f'transform="rotate(-90,12,{pad_top + plot_h / 2})" text-anchor="middle">eventos/día</text>')
    # left axis line
    out.append(f'<line x1="{pad_l}" y1="{pad_top}" x2="{pad_l}" y2="{pad_top + plot_h}" stroke="#3b82f6" stroke-width="1.5" opacity=".4"/>')

    # --- Right axis: magnitude (red) ---
    steps2 = 5
    step2 = round(y2_max / steps2, 1)
    for gi in range(steps2 + 1):
        g = round(gi * step2, 1)
        yy = Y2(g)
        out.append(f'<text x="{W - pad_r + 8}" y="{yy + 3}" font-size="10" text-anchor="start" fill="#dc2626" font-weight="600">M{g:.1f}</text>')
    # right axis line
    out.append(f'<line x1="{W - pad_r}" y1="{pad_top}" x2="{W - pad_r}" y2="{pad_top + plot_h}" stroke="#dc2626" stroke-width="1.5" opacity=".4"/>')
    # right axis label
    out.append(f'<text x="{W - 8}" y="{pad_top + plot_h / 2}" font-size="10" fill="#dc2626" font-weight="600" '
               f'transform="rotate(90,{W - 8},{pad_top + plot_h / 2})" text-anchor="middle">magnitud máx</text>')

    # --- Bars (blue gradient) ---
    mag_pts = []
    for i, d in enumerate(dates):
        x = X(i)
        v = daily[d]["count"]
        yy = Y1(v)
        out.append(f'<rect x="{x - bar_w / 2}" y="{yy}" width="{bar_w}" height="{pad_top + plot_h - yy}" rx="3" '
                   f'fill="url(#barGrad)">'
                   f'<title>{d}: {v} terremotos, máx M{daily[d]["max_mag"]:.1f}</title></rect>')
        # value on top of bar
        if v > 0:
            out.append(f'<text x="{x}" y="{yy - 4}" font-size="9" text-anchor="middle" fill="#3b82f6" font-weight="600">{v}</text>')
        mag_pts.append(f"{x:.1f},{Y2(daily[d]['max_mag']):.1f}")

    # --- Magnitude line (red, thick) ---
    out.append(f'<polyline points="{" ".join(mag_pts)}" fill="none" stroke="#dc2626" stroke-width="2.5" '
               f'stroke-linecap="round" stroke-linejoin="round"/>')
    # dots on magnitude line
    for i, d in enumerate(dates):
        x = X(i)
        my = Y2(daily[d]["max_mag"])
        out.append(f'<circle cx="{x:.1f}" cy="{my:.1f}" r="3.5" fill="#dc2626" stroke="#fff" stroke-width="1.5">'
                   f'<title>M{daily[d]["max_mag"]:.1f} · {d}</title></circle>')

    # --- X labels ---
    for i, d in enumerate(dates):
        if i % 2 == 0 or i == n - 1:
            out.append(f'<text x="{X(i)}" y="{H - 18}" font-size="9.5" text-anchor="middle" fill="#6b7280">'
                       f'{d[8:10]}/{d[5:7]}</text>')
    # x-axis label
    out.append(f'<text x="{pad_l + plot_w / 2}" y="{H - 4}" font-size="9" text-anchor="middle" fill="#9ca3af">fecha</text>')

    # --- Legend ---
    lx = pad_l + 6
    ly = 12
    out.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" rx="3" fill="url(#barGrad)"/>')
    out.append(f'<text x="{lx + 18}" y="{ly + 11}" font-size="10.5" fill="#3b82f6" font-weight="600">eventos/día</text>')
    out.append(f'<line x1="{lx + 110}" y1="{ly + 7}" x2="{lx + 132}" y2="{ly + 7}" stroke="#dc2626" stroke-width="2.5"/>')
    out.append(f'<circle cx="{lx + 121}" cy="{ly + 7}" r="3" fill="#dc2626"/>')
    out.append(f'<text x="{lx + 138}" y="{ly + 11}" font-size="10.5" fill="#dc2626" font-weight="600">magnitud máx</text>')

    out.append(f'</svg>')
    return "".join(out)


def svg_municipios(mun_data):
    """Heatmap horizontal: municipios × días, color = intensidad."""
    munis = sorted(mun_data.keys(), key=lambda m: -sum(mun_data[m].values()))
    dates = sorted(set(d for m in mun_data for d in mun_data[m]))
    n_dates = len(dates)
    if n_dates < 3 or not munis:
        return "<p>(datos insuficientes)</p>"
    cw, ch, pad_l = 24, 18, 130
    W = pad_l + n_dates * cw + 40
    H = 30 + len(munis) * ch + 30
    vmax = max(v for m in mun_data for v in mun_data[m].values())

    def cv(v):
        t = (v / vmax) ** 0.5 if vmax else 0
        r = round(234 + (153 - 234) * t)
        g = round(88 + (27 - 88) * t)
        b = round(12 + (27 - 12) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font-family:system-ui">',
           f'<rect width="{W}" height="{H}" fill="#fff"/>']
    for j, d in enumerate(dates):
        if j % 3 == 0 or j == n_dates - 1:
            out.append(f'<text x="{pad_l + j * cw + cw//2}" y="{H-8}" font-size="8" text-anchor="middle" fill="#888">'
                       f'{d[8:10]}/{d[5:7]}</text>')
    for i, mun in enumerate(munis):
        y = 28 + i * ch
        total = sum(mun_data[mun].values())
        out.append(f'<text x="{pad_l - 6}" y="{y + ch//2 + 3}" font-size="10" text-anchor="end" fill="#333">{mun}</text>')
        out.append(f'<text x="{pad_l - 6}" y="{y + ch//2 + 3}" font-size="8" text-anchor="end" fill="#aaa" '
                   f'dx="-{max(4, 5*len(mun))}">{total}</text>')
        for j, d in enumerate(dates):
            v = mun_data[mun].get(d, 0)
            if v > 0:
                out.append(f'<rect x="{pad_l + j*cw}" y="{y}" width="{cw-2}" height="{ch-2}" rx="2" '
                           f'fill="{cv(v)}"><title>{mun} · {d}: {v}</title></rect>')
    out.append(f'<text x="{pad_l}" y="{H-22}" font-size="9" fill="#888">'
               f'15 municipalities · color = intensity (sqrt scale)</text></svg>')
    return "".join(out)


def svg_santa_fe():
    """Comparación simplificada con enjambre Santa Fe 2021 (datos públicos prensa)."""
    W, H, pad = 700, 200, 50
    # Datos aproximados de prensa: ~3.000+ eventos en 3 meses, picos M4.6, M5.0
    sf_monthly = [("Sep 2021", 180), ("Oct 2021", 650), ("Nov 2021", 920),
                  ("Dic 2021", 580), ("Ene 2022", 420), ("Feb 2022", 250)]
    gr_monthly = [(" Ago 2026", 295)]  # nuestro dato actual
    all_m = sf_monthly + gr_monthly
    ymax = max(v for _, v in all_m) + 50
    bar_w = 50
    gap = 30
    total_w = len(all_m) * (bar_w + gap) + pad * 2
    W = max(W, total_w)

    def X(i): return pad + i * (bar_w + gap)
    def Y(v): return H - 35 - (v / ymax) * (H - 60)

    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font-family:system-ui">',
           f'<rect width="{W}" height="{H}" fill="#fff"/>']
    for i, (label, val) in enumerate(all_m):
        x = X(i)
        color = "#dc2626" if "2026" in label else "#94a3b8"
        out.append(f'<rect x="{x}" y="{Y(val)}" width="{bar_w}" height="{H-35-Y(val)}" rx="3" fill="{color}">'
                   f'<title>{label}: {val} eventos</title></rect>')
        out.append(f'<text x="{x+bar_w//2}" y="{Y(val)-6}" font-size="10" text-anchor="middle" fill="{color}">{val}</text>')
        out.append(f'<text x="{x+bar_w//2}" y="{H-14}" font-size="8.5" text-anchor="middle" fill="#666">{label.strip()}</text>')
    out.append(f'<text x="{pad}" y="18" font-size="10" fill="#94a3b8">■ Santa Fe 2021 (3 meses, ~3.000+ eventos)</text>'
               f'<text x="{pad+260}" y="18" font-size="10" fill="#dc2626">■ Granada 2026 ({"mes actual"})</text>'
               f'</svg>')
    return "".join(out)


def main():
    events = cargar()
    if not events:
        print("sin datos IGN Granada"); sys.exit(1)

    # Timeline
    daily = defaultdict(lambda: {"count": 0, "max_mag": 0.0})
    for e in events:
        d = e["date"]
        daily[d]["count"] += 1
        daily[d]["max_mag"] = max(daily[d]["max_mag"], e["mag"])

    # Municipios
    mun_data = defaultdict(lambda: defaultdict(int))
    for e in events:
        mun_data[e["mun"]][e["date"]] += 1

    total = len(events)
    munis_count = len(mun_data)
    top_muni = max(mun_data.keys(), key=lambda m: sum(mun_data[m].values()))
    top_count = sum(mun_data[top_muni].values())
    dates = sorted(daily.keys())
    peak_day = max(daily.keys(), key=lambda d: daily[d]["count"])
    peak_mag = max(events, key=lambda e: e["mag"])

    hoy = date.today().strftime("%d/%m/%Y")
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Enjambre sísmico de Granada · evolución día a día</title>
<meta name="description" content="Evolución cronológica del enjambre sísmico activo en la Vega de Granada desde el 14 de agosto de 2026. Datos IGN oficiales, actualizado periódicamente.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/enjambre-granada.html"></head>
<body style="font-family:system-ui,-apple-system,sans-serif;margin:0;background:#fafafa;color:#222">
<main style="max-width:900px;margin:0 auto;padding:20px 16px 48px">
<p style="font-size:.85rem"><a href="/" style="color:#c2410c">← radar</a> · <a href="/pulso-espana.html" style="color:#c2410c">💓 pulso</a> · <a href="/incendios-meteorologia.html" style="color:#c2410c">🔥 incendios</a></p>
<h1 style="font-size:1.55rem;margin:.2em 0">Enjambre sísmico de Granada</h1>
<p>Desde el <strong>14 de agosto de 2026</strong>, la Vega de Granada experimenta un enjambre sísmico activo
con epicentro en los municipios del entorno: Alhendín, La Zubia, Gójar, Ogíjares y Otura.
Este mapa muestra la evolución día a día con datos oficiales del IGN.</p>

<div style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0">
<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">📅 {dates[0]} → {dates[-1]}</span>
<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">📍 {total} terremotos registrados</span>
<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">🏆 municipio más afectado: {top_muni} ({top_count})</span>
<span style="background:#fef2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">⚡ pico: {peak_day} · M{peak_mag["mag"]:.1f}</span>
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Evolución diaria</h3>
<p style="font-size:.9rem;color:#555;margin-top:0">Barras: número de eventos detectados por día. Línea roja: magnitud máxima del día.</p>
{svg_timeline(daily)}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Municipios más afectados</h3>
{svg_municipios(mun_data)}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Comparación: ¿cómo se compara con Santa Fe 2021?</h3>
<p style="font-size:.9rem;color:#555;margin-top:0">El enjambre de Santa Fe (2021) acumuló más de 3.000 terremotos en 3 meses.
El de la Vega de Granada ya lleva {total} en {(date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days + 1} días.</p>
{svg_santa_fe()}
</div>

<div style="font-size:.85rem;color:#555;line-height:1.6;border-top:1px solid #ddd;padding-top:14px;margin-top:18px">
<strong>Metodología.</strong> Fuente: Instituto Geográfico Nacional (IGN), catálogo de terremotos próximos.
La ventana incluye terremotos con epicentro en un bounding box de la Vega de Granada
(36.8°–37.4°N, 3.0°–3.8°O). Magnitudes en escala local (mbLg) o moment magnitude (Mw) cuando disponible.
La fecha del terremoto se deriva de <code>expires_at − 48h</code> (ventana de expiración del colector NearMe).
Comparación Santa Fe 2021: datos de prensa (Ideal, Granada Hoy, El País), no catálogo IGN directo.
<strong>Sin interpretación de riesgo futuro.</strong> Esta página muestra lo que ya ocurrió.
Actualizado: {hoy}.
</div>
{FOOTER}
</main></body></html>"""
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else OUT_DEFAULT
    out.write_text(html)
    print(f"OK {out} ({len(html)//1024} KB) · {total} eventos · {munis_count} municipios")


if __name__ == "__main__":
    main()
