#!/usr/bin/env python3
"""gen_retrasos_renfe.py — página editorial: retrasos RENFE en vivo hoy.

Estado del día en curso de la red ferroviaria española a partir de los retrasos
detectados por NearMe (GTFS-RT oficial de RENFE, feeds cercanías + larga
distancia/AVE). Formato tipo enjambre-granada: KPIs + SVG inline, sin JS.

- KPIs: retrasos totales hoy, AVE/larga distancia vs cercanías, retraso medio,
  estación con más incidencias, franja horaria pico.
- Gráfico: evolución horaria del día (barras por hora).
- Dona "Hoy por gravedad": retrasos de hoy por bandas contiguas (10-14, 15-29,
  30-44, 45-59, >=60) separados por cercanías y larga distancia/AVE.
- Resumen semanal: donas acumuladas desde `renfe_daily` (últimos 7 días o todos
  los disponibles). Al ser un histórico que arranca cuando se despliega el
  acumulador, el primer resumen completo de 7 días estará tras una semana.
- Top: estaciones con más retrasos acumulados hoy.

Datos: tabla events (source=renfe) del día en curso + renfe_daily (agregados diarios).
Salida: /var/www/radar/retrasos-renfe-hoy.html
Uso: PYTHONPATH=. venv/bin/python scripts/gen_retrasos_renfe.py [--out RUTA]
"""
import math
import re
import sys
from datetime import date, datetime, timedelta
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
    # El feed llega con bytes latin-1 interpretados como ISO-8859-2
    # (GRÀCIA -> GRŔCIA, VALÈNCIA -> VALČNCIA, IRUÑA -> IRUŃA). Se revierte.
    try:
        s = s.encode("iso-8859-2").decode("iso-8859-1")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()  # 'Madrid-Puerta De Atocha'


def cargar():
    """Carga retrasos RENFE del día en curso (un evento por tren×parada)."""
    cur = get_conn().cursor()
    cur.execute("""
        SELECT title, subtype, level, lat, lon, created_at, description
        FROM events
        WHERE source='renfe' AND event_type='train_delay'
          AND created_at >= date_trunc('day', now())
        ORDER BY created_at
    """)
    rows = cur.fetchall()
    eventos = []
    for title, subtype, level, lat, lon, created_at, desc in rows:
        m = re.search(r": \+(\d+)min \((.*)\)", title or "")
        if not m:
            continue
        delay = int(m.group(1))
        est = fix_estacion(m.group(2))
        tm = re.search(r"Trip: (\S+)", desc or "")
        trip = tm.group(1) if tm else None
        hora = created_at.hour if created_at else 0
        eventos.append({
            "tipo": subtype or "desconocido", "est": est, "delay": delay,
            "hora": hora, "lat": lat, "lon": lon, "level": level, "trip": trip,
        })
    return eventos


def cargar_semanal(dias=7):
    """Agregados diarios acumulados (renfe_daily): últimos `dias` días.

    Devuelve (por_tipo, dias_disp) donde por_tipo = {subtipo: {banda: n}}
    y dias_disp = nº de fechas distintas presentes en la ventana.
    Si la tabla no existe aún (primer día antes del primer snapshot) -> (None, 0).
    """
    try:
        cur = get_conn().cursor()
        cur.execute("""
            SELECT subtipo, banda, SUM(n)
            FROM renfe_daily_trenes
            WHERE fecha >= date_trunc('day', now()) - (interval '1 day' * %s)
            GROUP BY subtipo, banda
        """, (dias,))
        filas = cur.fetchall()
    except Exception:
        return None, 0
    por_tipo = defaultdict(lambda: defaultdict(int))
    fechas = set()
    try:
        cur.execute("""
            SELECT DISTINCT fecha FROM renfe_daily_trenes
            WHERE fecha >= date_trunc('day', now()) - (interval '1 day' * %s)
        """, (dias,))
        fechas = {r[0] for r in cur.fetchall()}
    except Exception:
        pass
    for subtipo, banda, n in filas:
        if n:
            por_tipo[subtipo or "desconocido"][banda] += n
    return dict(por_tipo), len(fechas)


# ----- bandas del pie (contiguas/excluyentes) -----
PIE_ORDER = ["10-14", "15-29", "30-44", "45-59", ">=60"]
PIE_COLORS = {
    "10-14": "#22c55e",   # verde: leve
    "15-29": "#f59e0b",   # ámbar
    "30-44": "#f97316",   # naranja
    "45-59": "#ea580c",   # naranja oscuro
    ">=60":  "#dc2626",   # rojo: grave
}
PIE_LABEL = {
    "10-14": "10–14 min",
    "15-29": "15–29 min",
    "30-44": "30–44 min",
    "45-59": "45–59 min",
    ">=60":  "≥ 60 min",
}


def banda_pie(delay):
    """Banda contigua para la dona (>=10 min capturados por el feed)."""
    if delay >= 60:
        return ">=60"
    if delay >= 45:
        return "45-59"
    if delay >= 30:
        return "30-44"
    if delay >= 15:
        return "15-29"
    return "10-14"


def svg_dona(por_banda, titulo, subtotal_txt, vistos=None):
    """Dona SVG inline (sin librería): círculo base + arcos stroked.

    Cada banda es un <circle> con stroke-dasharray proporcional a su fracción.
    El centro muestra el total como <text> en dos líneas.
    """
    total = sum(por_banda.values())
    if total <= 0:
        # Distinguir "no hay datos" de "hay trenes pero ninguno >=10 min".
        # Con el feed funcionando, un 0 aqui NO es ausencia de informacion.
        if vistos:
            return (f'<p style="font-size:.9rem;color:#888">(sin retrasos de 10 min o mas; '
                    f'{vistos} trenes vistos en el feed)</p>')
        return f'<p style="font-size:.9rem;color:#888">(sin datos en {titulo})</p>'
    CX, CY, R, SW = 105, 105, 78, 46
    C = 2 * math.pi * R
    gap = 3.0
    out = [
        f'<svg viewBox="0 0 {CX*2} {CY*2}" style="width:230px;height:230px;display:block;margin:0 auto;font-family:system-ui">',
        f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="#f1f5f9" stroke-width="{SW}"/>',
    ]
    acum = 0.0
    for banda in PIE_ORDER:
        n = por_banda.get(banda, 0)
        if n <= 0:
            continue
        frac = n / total
        dash = max(0.0, frac * C - gap)
        offset = -acum * C
        out.append(
            f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="{PIE_COLORS[banda]}" '
            f'stroke-width="{SW}" stroke-dasharray="{dash:.2f} {C - dash:.2f}" '
            f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 {CX} {CY})">'
            f'<title>{n} retrasos · {PIE_LABEL[banda]}</title></circle>'
        )
        acum += frac
    out.append(f'<text x="{CX}" y="{CY-4}" text-anchor="middle" font-size="26" font-weight="800" fill="#0f172a">{total}</text>')
    out.append(f'<text x="{CX}" y="{CY+16}" text-anchor="middle" font-size="10" fill="#64748b">{subtotal_txt}</text>')
    out.append('</svg>')
    # leyenda HTML (bajo la dona)
    chips = []
    for banda in PIE_ORDER:
        n = por_banda.get(banda, 0)
        pct = (n / total * 100) if total else 0
        chips.append(
            f'<span style="display:inline-flex;align-items:center;gap:6px;background:#f2f2f2;'
            f'border-radius:8px;padding:4px 9px;font-size:.82rem;margin:2px">'
            f'<span style="width:10px;height:10px;border-radius:2px;background:{PIE_COLORS[banda]}"></span>'
            f'{PIE_LABEL[banda]}: {n} ({pct:.0f}%)</span>'
        )
    leyenda = f'<div style="text-align:center;margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;justify-content:center">{chr(10).join(chips)}</div>'
    return "".join(out) + leyenda


# Severidad para el gráfico horario (bandas del feed, se mantiene)
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
    total_eventos = len(eventos)
    delays = [e["delay"] for e in eventos]

    # Agregación por TREN (un tren = un trip_id): interesa el retraso MÁXIMO del
    # tren, no cada parada. Los eventos son tren×parada; aquí se colapsan a tren.
    max_trip = {}          # (tipo, trip) -> retraso máx
    for e in eventos:
        k = (e["tipo"], e["trip"] or "_?")
        if e["delay"] > max_trip.get(k, 0):
            max_trip[k] = e["delay"]
    trenes_tipo = defaultdict(int)
    for (tipo, _t) in max_trip:
        trenes_tipo[tipo] += 1
    trenes_total = sum(trenes_tipo.values())

    por_tipo = defaultdict(int)                        # eventos (tren×parada)
    por_hora = defaultdict(lambda: defaultdict(int))   # hora -> {severidad: n}
    pie_hoy = defaultdict(lambda: defaultdict(int))    # subtipo -> {banda: n} (TRENES)
    est_n = defaultdict(int)
    for e in eventos:
        por_tipo[e["tipo"]] += 1
        por_hora[e["hora"]][sev_of(e["delay"])] += 1
        est_n[e["est"]] += 1
    for (tipo, _t), d in max_trip.items():
        pie_hoy[tipo][banda_pie(d)] += 1   # dona por TREN (banda del retraso máximo)

    av = trenes_tipo.get("alta_velocidad", 0)          # trenes
    cer = trenes_tipo.get("cercanias", 0)
    av_ev = por_tipo.get("alta_velocidad", 0)          # incidencias (tren×parada)
    cer_ev = por_tipo.get("cercanias", 0)
    media_tren = (sum(max_trip.values()) / len(max_trip)) if max_trip else 0
    media = (sum(delays) / len(delays)) if delays else 0
    pico_hora = max(por_hora, key=lambda h: sum(por_hora[h].values()))
    top_est = max(est_n, key=lambda s: est_n[s])
    hoy = date.today().strftime("%d/%m/%Y")
    ahora = datetime.now().strftime("%H:%M")

    # Denominador: trenes vistos en el feed hoy (con o sin retraso) → % afectado.
    try:
        from src.db import count_trips_seen
        den = count_trips_seen(date.today()) or {}
    except Exception:
        den = {}
    den_cer = den.get("cercanias", 0)
    den_av = den.get("alta_velocidad", 0)

    def _pct(n, d):
        # Denominador incompleto (arranca a mitad de día): evita un % engañoso >100%.
        if not d or n > d:
            return "s/d"
        return f"{round(n * 100 / d)}%"

    # Dona "Hoy por gravedad": una por tipo (si hay datos del tipo)
    dona_cerc = svg_dona(pie_hoy.get("cercanias", {}), "cercanías",
                         f"{cer} trenes · {cer_ev} incidencias", vistos=den_cer)
    dona_av = svg_dona(pie_hoy.get("alta_velocidad", {}), "larga distancia/AVE",
                       f"{av} trenes · {av_ev} incidencias", vistos=den_av)
    donas_hoy_html = (
        f'<div style="display:flex;flex-wrap:wrap;gap:16px;justify-content:space-around">'
        f'<div style="flex:1 1 280px;min-width:260px"><h4 style="margin:.2em 0 .2em;font-size:.95rem;text-align:center">Cercanías</h4>{dona_cerc}</div>'
        f'<div style="flex:1 1 280px;min-width:260px"><h4 style="margin:.2em 0 .2em;font-size:.95rem;text-align:center">Larga distancia / AVE</h4>{dona_av}</div>'
        f'</div>'
    )

    # Resumen semanal desde renfe_daily (acumulador)
    semanal, dias_disp = cargar_semanal(7)
    if semanal:
        dona_sem_cer = svg_dona(semanal.get("cercanias", {}), "cercanías", f"{sum(semanal.get('cercanias', {}).values())} trenes en {dias_disp} días")
        dona_sem_av = svg_dona(semanal.get("alta_velocidad", {}), "larga distancia/AVE", f"{sum(semanal.get('alta_velocidad', {}).values())} trenes en {dias_disp} días")
        sem_html = (
            f'<p style="font-size:.9rem;color:#555;margin-top:0"><b>Trenes</b> acumulados por día (cada tren en la franja de su retraso máximo) '
            f'en los últimos 7 días ({dias_disp} día(s) registrados). El acumulador arranca el día de su activación, así que el primer '
            f'resumen completo de 7 días estará disponible en torno a la próxima semana.</p>'
            f'<div style="display:flex;flex-wrap:wrap;gap:16px;justify-content:space-around">'
            f'<div style="flex:1 1 280px;min-width:260px"><h4 style="margin:.2em 0 .2em;font-size:.95rem;text-align:center">Cercanías</h4>{dona_sem_cer}</div>'
            f'<div style="flex:1 1 280px;min-width:260px"><h4 style="margin:.2em 0 .2em;font-size:.95rem;text-align:center">Larga distancia / AVE</h4>{dona_sem_av}</div>'
            f'</div>'
        )
    else:
        sem_html = ('<p style="font-size:.9rem;color:#888">Este bloque se activa cuando el acumulador diario registre datos '
                    '(primera carga al cierre de hoy; resumen completo de 7 días en una semana).</p>')

    # pildoras KPI
    kpis = (
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">📅 {hoy} · {ahora}</span>'
        f'<span style="background:#fef2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">🚆 <b>{trenes_total}</b> trenes con retraso ≥10 min hoy</span>'
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">📊 {total_eventos} incidencias por parada</span>'
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">⚡ media +{media_tren:.0f} min por tren</span>'
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">🏆 estación con más: {top_est} ({est_n[top_est]})</span>'
        f'<span style="background:#f2f2f2;border-radius:8px;padding:8px 14px;font-size:.95rem">🕐 pico: {pico_hora}:00</span>'
    )

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retrasos del tren en España hoy · RENFE en vivo</title>
<meta name="description" content="Retrasos de trenes en España hoy: {trenes_total} trenes afectados ({total_eventos} incidencias por parada) en tiempo real (AVE/larga distancia y cercanías), media de +{media_tren:.0f} min por tren. Datos GTFS-RT oficiales de RENFE vía NearMe.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/retrasos-renfe-hoy.html"><meta property="og:type" content="website">
<meta property="og:title" content="Retrasos del tren en España hoy · {trenes_total} trenes afectados">
<meta property="og:description" content="{trenes_total} trenes con retraso ≥10 min hoy ({total_eventos} incidencias por parada) en la red (AVE + cercanías), media +{media_tren:.0f} min. Estación con más: {top_est}. Datos oficiales RENFE en tiempo real.">
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
en el feed oficial de RENFE (GTFS-RT). Se muestran <strong>trenes con retraso significativo (≥10 minutos)</strong>
en <strong>AVE/larga distancia</strong> y <strong>cercanías</strong>. Un mismo tren puede generar varias
<em>incidencias</em> (una por parada); el titular cuenta <strong>trenes</strong>, no incidencias.</p>

<div style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0">{kpis}</div>
<p style="font-size:.85rem;color:#555;margin:6px 0 0">Cobertura del feed hoy: cercanías <b>{cer}</b>/{den_cer or 's/d'} trenes ({_pct(cer, den_cer)}) · AVE/larga distancia <b>{av}</b>/{den_av or 's/d'} ({_pct(av, den_av)}). Denominador = trenes vistos en el feed (con o sin retraso); se acumula por día y muestra <em>s/d</em> hasta que el día esté completo.</p>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Hoy por gravedad (por tren)</h3>
<p style="font-size:.9rem;color:#555;margin-top:0">Cada tren cuenta una vez, en la franja de su <b>retraso máximo</b> del día, separado por tipo de servicio (cercanías y larga distancia/AVE).</p>
{donas_hoy_html}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Resumen semanal (<small>se acumula</small>)</h3>
{sem_html}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Evolución del día, hora a hora</h3>
<p style="font-size:.9rem;color:#555;margin-top:0">Barras apiladas: <b>incidencias</b> (tren×parada) por hora según gravedad (10–15, 15–30, 30–60 y &gt;60 min). Trenes afectados hoy: AVE/larga distancia {av} · cercanías {cer}.</p>
{svg_horas(por_hora)}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Estaciones con más retrasos hoy</h3>
{svg_top(est_n)}
</div>

<div class="card" style="background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px;margin:18px 0">
<h3 style="margin-top:0">Cómo se lee esto</h3>
<p style="font-size:.9rem;color:#444;line-height:1.6"><b>Titular = trenes</b> con retraso ≥10 min (un tren = un servicio, contado una vez).
Un mismo tren puede generar varias <em>incidencias</em> (una por cada parada con ≥10 min de retraso), que es el segundo KPI.
La <b>cobertura</b> compara los trenes afectados con los trenes vistos en el feed ese día (denominador, orden de magnitud),
no con la puntualidad oficial de RENFE (que mide otra cosa: % por servicio y umbral). <b>Esto es una foto del día</b>: los
eventos caducan (TTL 6 h) y no se acumulan de un día a otro; el <b>resumen semanal</b> sí acumula por día (por tren y franja de
retraso) desde que se activó. Si un trayecto te interesa (p. ej. Madrid-Murcia), revisa el mapa de incidencias en
<a href="https://nearme.viajeinteligencia.com" style="color:#c2410c">NearMe</a> para ver la posición de los trenes afectados.</p>
</div>

{FOOTER}
</main>
</body></html>"""

    Path(args.out).write_text(html, encoding="utf-8")
    print(f"OK: {args.out} — {trenes_total} trenes / {total_eventos} incidencias RENFE hoy "
          f"(AV {av}, cercanías {cer}, semanal {dias_disp} días)")


if __name__ == "__main__":
    main()