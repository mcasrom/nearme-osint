#!/usr/bin/env python3
"""gen_nivel_embalses.py — Página de nivel de los embalses de España.

HTML estático + SVG inline (patrón enjambre-granada.html), con:
- KPI cards con color según estado
- Donut del nivel medio nacional
- Barras por cuenca con gradiente
- Ranking más llenos / más vacíos
- Lluvia reciente AEMET por cuenca

Salida: /var/www/radar/nivel-embalses.html  (NO toca nada existente)
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/deploy/nearme-osint")
OUT_DEFAULT = Path("/var/www/radar/nivel-embalses.html")

EMBALSES_API = "https://estadoembalses.es/api/embalses?limit=500"
AEMET_BASE = "https://opendata.aemet.es/opendata/api"
UA = "Mozilla/5.0 (radar.viajeinteligencia.com embalses page)"

PROV_CUENCA = None  # se rellena desde embalses


def aemet_key():
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("AEMET_API_KEY"):
                return line.split("=", 1)[1].strip()
    return ""


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=30).read()
    return json.loads(raw.decode("utf-8", "ignore"))


def fetch_embalses():
    data = get_json(EMBALSES_API, {"User-Agent": UA})
    return data.get("data", []) if isinstance(data, dict) else data


def fetch_lluvia():
    key = aemet_key()
    if not key:
        return []
    try:
        d = get_json(f"{AEMET_BASE}/observacion/convencional/todas", {"api_key": key})
        if not d.get("datos"):
            return []
        return get_json(d["datos"], {"api_key": key})
    except Exception:
        return []


def color_pct(pct):
    if pct is None:
        return "#94a3b8", "#cbd5e1"
    if pct >= 70:
        return "#16a34a", "#bbf7d0"
    if pct >= 50:
        return "#0891b2", "#a5f3fc"
    if pct >= 40:
        return "#eab308", "#fef08a"
    if pct >= 20:
        return "#f97316", "#fed7aa"
    return "#dc2626", "#fecaca"


def kpi_card(label, value, sub, bg):
    return (f'<div style="flex:1 1 160px;background:{bg};border-radius:12px;padding:14px 16px;'
            f'box-shadow:0 1px 3px rgba(0,0,0,.06)">'
            f'<div style="font-size:.75rem;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:.04em">{label}</div>'
            f'<div style="font-size:1.7rem;font-weight:800;color:#0f172a;line-height:1.2">{value}</div>'
            f'<div style="font-size:.8rem;color:#64748b">{sub}</div></div>')


def svg_donut(pct, label):
    """Donut del nivel medio nacional."""
    pct = pct or 0
    r = 70
    c = 2 * 3.1415926 * r
    frac = pct / 100
    col, _ = color_pct(pct)
    return f'''<svg viewBox="0 0 200 200" style="width:180px;height:auto;font-family:system-ui">
<defs><linearGradient id="donutGrad" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="{col}"/><stop offset="100%" stop-color="#7c3aed"/>
</linearGradient></defs>
<circle cx="100" cy="100" r="{r}" fill="none" stroke="#e2e8f0" stroke-width="22"/>
<circle cx="100" cy="100" r="{r}" fill="none" stroke="url(#donutGrad)" stroke-width="22"
  stroke-linecap="round" stroke-dasharray="{frac*c:.1f} {c:.1f}" transform="rotate(-90 100 100)"/>
<text x="100" y="94" font-size="34" font-weight="800" text-anchor="middle" fill="#0f172a">{pct:.1f}%</text>
<text x="100" y="118" font-size="11" fill="#64748b" text-anchor="middle">{label}</text>
</svg>'''


def svg_cuencas(cuencas):
    """Barras horizontales por cuenca con gradiente por estado."""
    if not cuencas:
        return "<p>Sin datos de cuencas.</p>"
    top = sorted(cuencas.items(), key=lambda kv: kv[1]["pct"], reverse=True)[:14]
    H = 30 + len(top) * 28
    pad_l = 160
    maxw = 430
    parts = [f'<svg viewBox="0 0 700 {H}" style="width:100%;height:auto;font-family:system-ui">']
    for i, (name, d) in enumerate(top):
        y = 30 + i * 28
        w = max(6, int((d["pct"] / 100) * maxw))
        col, _ = color_pct(d["pct"])
        parts.append(f'<text x="{pad_l-8}" y="{y+15}" font-size="11" text-anchor="end" fill="#334155" font-weight="600">{name[:24]}</text>')
        parts.append(f'<rect x="{pad_l}" y="{y+3}" width="{maxw}" height="16" rx="4" fill="#f1f5f9"/>')
        parts.append(f'<rect x="{pad_l}" y="{y+3}" width="{w}" height="16" rx="4" fill="{col}"/>')
        parts.append(f'<text x="{pad_l+w+8}" y="{y+16}" font-size="10.5" fill="#475569">{d["pct"]:.0f}% · {d["n"]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_ranking(rows, empty=False):
    """Ranking embalses con barras de progreso."""
    if not rows:
        return "<p>Sin datos.</p>"
    H = 36 + len(rows) * 28
    parts = [f'<svg viewBox="0 0 700 {H}" style="width:100%;height:auto;font-family:system-ui">']
    for i, r in enumerate(rows):
        pct = r.get("porcentaje") or 0
        y = 36 + i * 28
        w = max(6, int((pct / 100) * 400))
        col, _ = color_pct(pct)
        nombre = r["nombre"][:30]
        prov = (r.get("provincia") or "")[:14]
        parts.append(f'<text x="330" y="{y+15}" font-size="11" text-anchor="end" fill="#334155" font-weight="600">{nombre}</text>')
        parts.append(f'<text x="338" y="{y+13}" font-size="9" fill="#94a3b8">{prov}</text>')
        parts.append(f'<rect x="338" y="{y+3}" width="300" height="15" rx="4" fill="#f1f5f9"/>')
        parts.append(f'<rect x="338" y="{y+3}" width="{w}" height="15" rx="4" fill="{col}"/>')
        parts.append(f'<text x="646" y="{y+16}" font-size="10.5" fill="#0f172a" font-weight="700">{pct:.1f}%</text>')
        if r.get("volumen_hm3") and r.get("capacidad_hm3"):
            parts.append(f'<text x="646" y="{y+27}" font-size="8.5" fill="#94a3b8">{r["volumen_hm3"]:.0f}/{r["capacidad_hm3"]:.0f} hm³</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_lluvia(lluvia_by_cuenca):
    if not lluvia_by_cuenca:
        return "<p>Datos de lluvia no disponibles en esta actualización.</p>"
    top = sorted(lluvia_by_cuenca.items(), key=lambda kv: kv[1], reverse=True)[:14]
    maxmm = max(v for _, v in top) or 1
    H = 30 + len(top) * 28
    parts = [f'<svg viewBox="0 0 700 {H}" style="width:100%;height:auto;font-family:system-ui">']
    parts.append('<defs><linearGradient id="rainGrad" x1="0" y1="0" x2="1" y2="0">'
                 '<stop offset="0%" stop-color="#2563eb"/><stop offset="100%" stop-color="#38bdf8"/>'
                 '</linearGradient></defs>')
    for i, (name, mm) in enumerate(top):
        y = 30 + i * 28
        w = max(6, int((mm / maxmm) * 430))
        parts.append(f'<text x="152" y="{y+15}" font-size="11" text-anchor="end" fill="#334155" font-weight="600">{name[:24]}</text>')
        parts.append(f'<rect x="160" y="{y+3}" width="{w}" height="16" rx="4" fill="url(#rainGrad)"/>')
        parts.append(f'<text x="{160+w+8}" y="{y+16}" font-size="10.5" fill="#1d4ed8" font-weight="700">{mm:.1f} mm</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_dots(emb):
    """Distribución clara de embalses por estado: barras por categoría con recuento
    y porcentaje, en vez de un heatmap confuso de cientos de recuadros."""
    con = [e for e in emb if e.get("porcentaje") is not None]
    if not con:
        return "<p>Sin datos.</p>"
    cat = {"Llenos (≥70%)": (70, "#16a34a"),
           "Buenos (50-70%)": (50, "#0891b2"),
           "Medios (40-50%)": (40, "#eab308"),
           "Bajos (20-40%)": (20, "#f97316"),
           "Críticos (<20%)": (0, "#dc2626")}
    counts = []
    for name, (thr, col) in cat.items():
        n = sum(1 for e in con if e["porcentaje"] >= thr if thr > 0 or e["porcentaje"] < 20)
        if thr == 0:
            n = sum(1 for e in con if e["porcentaje"] < 20)
        counts.append((name, n, col))
    total = len(con)
    H = 40 + len(counts) * 34
    maxw = 340
    parts = [f'<svg viewBox="0 0 700 {H}" style="width:100%;height:auto;font-family:system-ui">']
    for i, (name, n, col) in enumerate(counts):
        y = 40 + i * 34
        w = max(8, int((n / total) * maxw))
        pct = (n / total) * 100
        parts.append(f'<text x="168" y="{y+15}" font-size="11.5" text-anchor="end" fill="#334155" font-weight="600">{name}</text>')
        parts.append(f'<rect x="176" y="{y+3}" width="{maxw}" height="20" rx="5" fill="#f1f5f9"/>')
        parts.append(f'<rect x="176" y="{y+3}" width="{w}" height="20" rx="5" fill="{col}"/>')
        parts.append(f'<text x="{176+w+10}" y="{y+18}" font-size="12" fill="#0f172a" font-weight="800">{n}</text>')
        parts.append(f'<text x="{176+w+38}" y="{y+18}" font-size="10.5" fill="#64748b">{pct:.0f}%</text>')
    parts.append(f'<text x="176" y="{H-6}" font-size="9.5" fill="#64748b">Total: {total} embalses con nivel conocido</text>')
    parts.append("</svg>")
    return "".join(parts)


def main():
    emb = fetch_embalses()
    if not emb:
        print("sin datos embalses")
        sys.exit(1)

    con = [e for e in emb if e.get("porcentaje") is not None]
    n, n_con = len(emb), len(con)
    pct_medio = sum(e["porcentaje"] for e in con) / n_con if n_con else 0
    alerta = [e for e in con if e["porcentaje"] < 40]
    critico = [e for e in con if e["porcentaje"] < 20]
    cap_total = sum(e.get("capacidad_hm3") or 0 for e in emb)
    vol_total = sum(e.get("volumen_hm3") or 0 for e in emb)

    cuencas = {}
    for e in emb:
        c = (e.get("cuenca") or "Desconocida").replace("_", " ").title()
        cuencas.setdefault(c, {"n": 0, "sum": 0, "cnt": 0})
        cuencas[c]["n"] += 1
        if e.get("porcentaje") is not None:
            cuencas[c]["sum"] += e["porcentaje"]
            cuencas[c]["cnt"] += 1
    for c in cuencas:
        cuencas[c]["pct"] = cuencas[c]["sum"] / cuencas[c]["cnt"] if cuencas[c]["cnt"] else 0

    top_full = sorted(con, key=lambda e: e["porcentaje"], reverse=True)[:8]
    top_empty = sorted(con, key=lambda e: e["porcentaje"])[:8]

    # lluvia
    estaciones = fetch_lluvia()
    # mapeo por coordenadas: asignar cada estación a la cuenca del embalse más cercano
    emb_geo = [(e.get("lat"), e.get("lng"), (e.get("cuenca") or "Desconocida").replace("_", " ").title())
               for e in emb if e.get("lat") is not None and e.get("lng") is not None]

    def cuenca_cercana(lat, lon):
        best, best_d = None, 1e18
        for elat, elon, cname in emb_geo:
            d = (elat - lat) ** 2 + (elon - lon) ** 2
            if d < best_d:
                best_d, best = d, cname
        return best or "Otras"

    lluvia = {}
    for s in estaciones:
        lat, lon = s.get("lat"), s.get("lon")
        prec = s.get("prec")
        if prec is None or lat is None or lon is None:
            continue
        try:
            mm = float(prec)
        except (TypeError, ValueError):
            continue
        cu = cuenca_cercana(lat, lon)
        lluvia.setdefault(cu, []).append(mm)
    lluvia_by_cuenca = {c: sum(v) / len(v) for c, v in lluvia.items() if v}

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    # KPIs con color
    pct_col, pct_bg = color_pct(pct_medio)
    cards = "".join([
        kpi_card("Embalses", f"{n}", "monitorizados", "#eff6ff"),
        kpi_card("Nivel medio", f"{pct_medio:.1f}%", "capacidad", pct_bg),
        kpi_card("Alerta", f"{len(alerta)}", "<40%", "#fef2f2"),
        kpi_card("Críticos", f"{len(critico)}", "<20%", "#fee2e2"),
        kpi_card("Volumen", f"{vol_total/1000:.1f} km³", f"{cap_total/1000:.1f} km³ total", "#f0fdf4"),
        kpi_card("Actualizado", now[:16], "UTC", "#fafaf9"),
    ])

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nivel de los embalses de España · evolución y lluvia</title>
<meta name="description" content="Nivel actual de los embalses de España: porcentaje de llenado, volumen, capacidad, estado por cuenca y lluvia reciente (AEMET). Actualizado periódicamente.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/nivel-embalses.html">
<style>
:root{{color-scheme:light}}
body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f8fafc;color:#0f172a}}
main{{max-width:960px;margin:0 auto;padding:20px 16px 56px}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin:18px 0;box-shadow:0 1px 2px rgba(15,23,42,.04)}}
.card h3{{margin-top:0;font-size:1.05rem}}
.caption{{font-size:.85rem;color:#64748b;margin:.2rem 0 0}}
.kpis{{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}}
a{{color:#c2410c}}
.leyenda{{display:flex;gap:14px;flex-wrap:wrap;font-size:.78rem;color:#475569;margin-top:10px}}
.leyenda span{{display:inline-flex;align-items:center;gap:5px}}
.dot{{width:11px;height:11px;border-radius:3px;display:inline-block}}
</style></head>
<body>
<main>
<p style="font-size:.85rem"><a href="/">← radar</a> · <a href="/enjambre-granada.html">🌍 enjambre</a> · <a href="/pulso-espana.html">💓 pulso</a> · <a href="/incendios-meteorologia.html">🔥 incendios</a></p>
<h1 style="font-size:1.6rem;margin:.2em 0">Nivel de los embalses de España</h1>
<p style="color:#475569">Estado actual del agua almacenada en los embalses españoles:
porcentaje de llenado, volumen, situación por cuenca y precipitación reciente.
Fuentes: <strong>MITECO/SAIH</strong> (estadoembalses.es) y <strong>AEMET</strong> (observaciones en vivo).</p>

<div class="kpis">{cards}</div>

<div class="card">
  <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center">
    <div>{svg_donut(pct_medio, "nivel medio nacional")}</div>
    <div style="flex:1;min-width:240px">
      <h3 style="margin-top:0">Distribución de embalses por estado</h3>
      <p class="caption">Cuántos embalses están en cada franja de llenado, con su porcentaje del total.</p>
      {svg_dots(emb)}
    </div>
  </div>
</div>

<div class="card">
  <h3>Nivel medio por cuenca hidrográfica</h3>
  <p class="caption">Porcentaje medio de llenado por cuenca (nº de embalses con dato).</p>
  {svg_cuencas(cuencas)}
</div>

<div class="card">
  <div style="display:flex;gap:24px;flex-wrap:wrap">
    <div style="flex:1;min-width:280px"><h3>Embalses más llenos</h3>{svg_ranking(top_full)}</div>
    <div style="flex:1;min-width:280px"><h3>Embalses más vacíos</h3>{svg_ranking(top_empty)}</div>
  </div>
</div>

<div class="card">
  <h3>Lluvia reciente por cuenca (AEMET)</h3>
  <p class="caption">Precipitación media de las estaciones AEMET asociadas a cada cuenca (última observación disponible).</p>
  {svg_lluvia(lluvia_by_cuenca)}
</div>

<p style="font-size:.82rem;color:#64748b;margin-top:28px">
<strong>Metodología.</strong> Embalses: estadoembalses.es (MITECO/SAIH), API pública, ~500 embalses.
Lluvia: AEMET OpenData, observaciones convencionales en vivo. Página regenerada automáticamente
(cron 6h), igual que el resto del radar. El nivel de un embalse puede no renovarse a diario en la
fuente. Las categorías de color son informativas y NO constituyen alertas oficiales de la CHS.</p>

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

    OUT_DEFAULT.write_text(html, encoding="utf-8")
    print(f"OK: {OUT_DEFAULT} — {n} embalses, nivel medio {pct_medio:.1f}%, alerta {len(alerta)}, "
          f"críticos {len(critico)}, {len(lluvia_by_cuenca)} cuencas con lluvia")


if __name__ == "__main__":
    main()
