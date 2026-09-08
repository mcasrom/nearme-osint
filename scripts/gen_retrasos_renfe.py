#!/usr/bin/env python3
"""gen_retrasos_renfe.py — página editorial: retrasos RENFE en vivo hoy.

Estado del día en curso de la red ferroviaria española a partir de los retrasos
detectados por NearMe (GTFS-RT oficial de RENFE, feeds cercanías + larga
distancia/AVE). Formato tipo enjambre-granada: KPIs + SVG inline, sin JS.

- KPIs: retrasos totales hoy, AVE/larga distancia vs cercanías, retraso medio,
  estación con más incidencias, franja horaria pico.
- Gráfico: evolución horaria del día (barras por hora).
- Top: estaciones con más retrasos acumulados hoy.

Datos: tabla events (source=renfe) del día en curso.
Salida: /var/www/radar/retrasos-renfe-hoy.html
Uso: PYTHONPATH=. venv/bin/python scripts/gen_retrasos_renfe.py [--out RUTA]
"""
import re
import sys
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn  # noqa: E402

OUT_DEFAULT = Path("/var/www/radar/retrasos-renfe-hoy.html")

# Corrección de acentos por codificación del feed (la estación llega latin-1
# interpretada como utf-8: GRÀCIA -> GRŔCIA, IRUÑA -> IRUŃA, etc.)
_FIX_ACC = {
    "Ŕ": "À", "Á": "Á", "É": "É", "Í": "Í", "Ó": "Ó", "Ú": "Ú",
    "Ń": "Ñ", "Ü": "Ü", "Ç": "Ç",
}


def fix_estacion(s):
    if not s:
        return s
    s = re.sub(r"[ŔÁÉÍÓÚŃÜÇ]", lambda m: _FIX_ACC.get(m.group(0), m.group(0)), s)
    # mojibake doble: À como Ã€ etc no esperado aqui; baste lo anterior
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()  # 'Madrid-Puerta De Atocha'


def cargar():
    """Carga retrasos RENFE del día en curso."""
    cur = get_conn().cursor()
    cur.execute("""
        SELECT title, subtype, level, lat, lon, created_at
        FROM events
        WHERE source='renfe' AND event_type='train_delay'
          AND created_at >= date_trunc('day', now())
        ORDER BY created_at
    """)
    rows = cur.fetchall()
    eventos = []
    for title, subtype, level, lat, lon, created_at in rows:
        m = re.search(r": \+(\d+)min \((.*)\)", title or "")
        if not m:
            continue
        delay = int(m.group(1))
        est = fix_estacion(m.group(2))
        hora = created_at.hour if created_at else 0
        eventos.append({
            "tipo": subtype or "desconocido", "est": est, "delay": delay,
            "hora": hora, "lat": lat, "lon": lon, "level": level,
        })
    return eventos


# Severidad: rangos contiguos/excluyentes (un retraso cae en una sola banda).
# El feed ya captura desde >=10 min. Orden de apilado (de abajo a arriba).
SEV_ORDER = ["10-15", "15-30", "30-60", ">60"]
SEV_COLORS = {
    "10-15": "#22c55e",   # verde: retraso leve
    "15-30": "#f59e0b",   # ámbar: retraso moderado
    "30-60": "#f97316",   # naranja: retraso alto
    ">60":   "#dc2626",   # rojo: retraso grave
}
SEV_LABEL = {
    "10-15": "10–15 min",
    "15-30": "15–30 min",
    "30-60": "30–60 min",
    ">60": "> 60 min",
}


def sev_of(delay):
    """Banda de severidad contigua para un retraso en minutos."""
    if delay >= 60:
        return ">60"
    if delay >= 30:
        return "30-60"
    if delay >= 15:
        return "15-30"
    return "10-15"


def svg_horas(por_hora):
    """Barras apiladas por hora: retrasos por banda de severidad (10-15, 15-30,
    30-60, >60 min). Cada segmento suma el total de la hora."""
    horas = sorted(por_hora.keys())
    if not horas:
        return "<p>(sin datos todavía hoy)</p>"
    pad_l, pad_b, pad_t = 46, 34, 26
    W = max(620, len(horas) * 52 + pad_l + 20)
    H = 320
    plot_w = W - pad_l - 20
    plot_h = H - pad_t - pad_b
    ymax = max(sum(por_hora[h].values()) for h in horas)
    step = max(1, round(ymax / 5))

    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font-family:system-ui">',
           f'<rect width="{W}" height="{H}" fill="#fff"/>']
    # leyenda (arriba, dentro del SVG): un chip por banda
    lx = pad_l
    out.append(f'<text x="{lx}" y="14" font-size="10" fill="#94a3b8" font-weight="600">Retrasos por hora según gravedad</text>')
    for sev in SEV_ORDER:
        txt = f'{SEV_LABEL[sev]}'
        out.append(f'<rect x="{lx}" y="18" width="10" height="10" rx="2" fill="{SEV_COLORS[sev]}"/>')
        lx += 14
        out.append(f'<text x="{lx}" y="27" font-size="9.5" fill="#64748b">{txt}</text>')
        lx += 7.4 * len(txt) + 14
    for g in range(0, ymax + step, step):
        yy = pad_t + plot_h - (g / ymax) * plot_h
        out.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{W-20}" y2="{yy:.1f}" stroke="#f1f5f9"/>')
        out.append(f'<text x="{pad_l-8}" y="{yy+3:.1f}" font-size="10" text-anchor="end" fill="#475569" font-weight="600">{g}</text>')
    bw = min(40, plot_w / len(horas) - 4)
    for i, h in enumerate(horas):
        buckets = por_hora[h]
        total = sum(buckets.values())
        x = pad_l + i * (plot_w / len(horas)) + (plot_w / len(horas) - bw) / 2
        # apilar de abajo (leve) hacia arriba (grave)
        y_cursor = pad_t + plot_h
        tip = f"{h}:00 — {total} retrasos"
        for sev in SEV_ORDER:
            v = buckets.get(sev, 0)
            if v <= 0:
                continue
            hpx = (v / ymax) * plot_h
            y_top = y_cursor - hpx
            tip += f" · {SEV_LABEL[sev]}: {v}"
            out.append(f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bw:.1f}" height="{hpx:.1f}" '
                       f'fill="{SEV_COLORS[sev]}">'
                       f'<title>{h}:00 — {v} retrasos de {SEV_LABEL[sev]}</title></rect>')
            y_cursor = y_top
        out.append(f'<text x="{x+bw/2:.1f}" y="{y_cursor-4:.1f}" font-size="9.5" text-anchor="middle" '
                   f'fill="#475569" font-weight="700">{total}</text>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{H-8}" font-size="9" text-anchor="middle" fill="#6b7280">{h}:00</text>')
    out.append(f'</svg>')
    return "".join(out)


def svg_top(est_data, max_bars=12):
    """Barras horizontales: estaciones con más retrasos hoy."""
    top = sorted(est_data.items(), key=lambda kv: -kv[1])[:max_bars]
    if not top:
        return "<p>(sin datos)</p>"
    vmax = top[0][1]
    row_h, pad_l = 22, 190
    W = 860
    H = 30 + len(top) * row_h
    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font-family:system-ui">',
           f'<rect width="{W}" height="{H}" fill="#fff"/>']
    for i, (est, n) in enumerate(top):
        y = 20 + i * row_h
        bw = max(6, (n / vmax) * (W - pad_l - 90))
        out.append(f'<text x="{pad_l-8}" y="{y+14}" font-size="10" text-anchor="end" fill="#333">{est[:34]}</text>')
        out.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="16" rx="3" fill="#b91c1c">'
                   f'<title>{est}: {n} retrasos</title></rect>')
        out.append(f'<text x="{pad_l+bw+6:.1f}" y="{y+13}" font-size="9.5" fill="#dc2626" font-weight="700">{n}</text>')
    out.append(f'</svg>')
    return "".join(out)


FOOTER = """
<footer style="border-top:1px solid #e5e5e5;margin-top:28px;padding-top:18px;text-align:center">
  <div style="font-size:.85rem;color:#666;line-height:1.9">
    <b>Ecosistema ViajeInteligencia</b><br>
    <a href="https://www.viajeinteligencia.com" style="color:#c2410c">Principal</a> ·
    <a href="https://municipal.viajeinteligencia.com" style="color:#c2410c">Municipal</a> ·
    <a href="https://nearme.viajeinteligencia.com" style="color:#c2410c">NearMe</a> ·
    <a href="https://country.viajeinteligencia.com" style="color:#c2410c">País a País</a> ·
    <a href="https://radar.viajeinteligencia.com/estado.html" style="color:#c2410c">Estado de fuentes</a>
  </div>
  <a href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer"
     style="display:inline-flex;align-items:center;gap:8px;font-weight:700;font-size:13.5px;color:#fff;background:#13C3A5;border-radius:7px;padding:11px 18px;margin-top:14px;text-decoration:none">☕ Invítame a un café</a>
  <p style="font-size:.78rem;color:#888;margin:10px 0 0">Proyecto personal, sin rastreo ni cuentas. Los servidores los paga su autor.</p>
</footer>
"""


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()

    eventos = cargar()
    if not eventos:
        print("sin datos RENFE hoy"); sys.exit(1)

    total = len(eventos)
    delays = [e["delay"] for e in eventos]
    por_tipo = defaultdict(int)
    por_hora = defaultdict(lambda: defaultdict(int))  # hora -> {severidad: n}
    est_n = defaultdict(int)
    est_delay = defaultdict(int)
    for e in eventos:
        por_tipo[e["tipo"]] += 1
        por_hora[e["hora"]][sev_of(e["delay"])] += 1
        est_n[e["est"]] += 1
        est_delay[e["est"]] += e["delay"]

    tipo_txt = {k: (v, k) for k, v in por_tipo.items()}
    av = por_tipo.get("alta_velocidad", 0)
    cer = por_tipo.get("cercanias", 0)
    media = sum(delays) / len(delays)
    pico_hora = max(por_hora, key=lambda h: sum(por_hora[h].values()))
    top_est = max(est_n, key=lambda s: est_n[s])
    hoy = date.today().strftime("%d/%m/%Y")
    ahora = datetime.now().strftime("%H:%M")

    # pildoras KPI
    kpis = (
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">📅 {hoy} · {ahora}</span>'
        f'<span style="background:#fef2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">🚆 {total} retrasos detectados hoy</span>'
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">⚡ media +{media:.0f} min</span>'
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">🏆 estación con más: {top_est} ({est_n[top_est]})</span>'
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">🕐 pico: {pico_hora}:00</span>'
    )

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retrasos del tren en España hoy · RENFE en vivo</title>
<meta name="description" content="Retrasos de trenes en España hoy: {total} incidencias detectadas en tiempo real (AVE/larga distancia y cercanías), media de +{media:.0f} min, estaciones con más retrasos. Datos GTFS-RT oficiales de RENFE vía NearMe.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/retrasos-renfe-hoy.html"><meta property="og:type" content="website">
<meta property="og:title" content="Retrasos del tren en España hoy · {total} incidencias">
<meta property="og:description" content="{total} retrasos detectados hoy en la red (AVE + cercanías), media +{media:.0f} min. Estación con más: {top_est}. Datos oficiales RENFE en tiempo real.">
<meta property="og:locale" content="es_ES">
<meta property="og:url" content="https://radar.viajeinteligencia.com/retrasos-renfe-hoy.html">
<meta property="og:image" content="https://radar.viajeinteligencia.com/retrasos-renfe-og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
</head>
<body style="font-family:system-ui,-apple-system,sans-serif;margin:0;background:#fafafa;color:#222">
<main style="max-width:900px;margin:0 auto;padding:20px 16px 48px">
<p style="font-size:.85rem"><a href="/" style="color:#c2410c">← radar</a> · <a href="/pulso-espana.html" style="color:#c2410c">💓 pulso</a> · <a href="/enjambre-granada.html" style="color:#c2410c">🌋 enjambre</a> · <a href="/nivel-embalses.html" style="color:#c2410c">💧 embalses</a></p>
<h1 style="font-size:1.55rem;margin:.2em 0">Retrasos del tren en España hoy</h1>
<p>Estado del día en curso de la red ferroviaria, a partir de los retrasos que NearMe detecta
en el feed oficial de RENFE (GTFS-RT). Se muestran incidencias de <strong>AVE/larga distancia</strong>
y <strong>cercanías</strong> con retraso significativo (≥10 minutos).</p>

<div style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0">{kpis}</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Evolución del día, hora a hora</h3>
<p style="font-size:.9rem;color:#555;margin-top:0">Barras apiladas: retrasos detectados en cada hora por gravedad (10–15, 15–30, 30–60 y &gt;60 min). AVE/larga distancia {av} · cercanías {cer}.</p>
{svg_horas(por_hora)}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Estaciones con más retrasos hoy</h3>
{svg_top(est_n)}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Cómo se lee esto</h3>
<p style="font-size:.9rem;color:#444;line-height:1.6">Cada punto es un tren que ha registrado un retraso de
<b>10 minutos o más</b> en una parada durante el día. Un mismo tren puede aparecer varias veces si su
retraso se confirma en varias estaciones de su recorrido. <b>Esto es una foto del día, no un histórico</b>:
los datos se recogen en tiempo real y no se acumulan de un día para otro. Si un trayecto te interesa
(p. ej. Madrid-Murcia), revisa el mapa de incidencias en <a href="https://nearme.viajeinteligencia.com"
style="color:#c2410c">NearMe</a> para ver la posición de los trenes afectados.</p>
</div>

{FOOTER}
</main>
</body></html>"""

    Path(args.out).write_text(html, encoding="utf-8")
    print(f"OK: {args.out} — {total} retrasos RENFE hoy (AV {av}, cercanías {cer})")


if __name__ == "__main__":
    main()
