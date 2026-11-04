#!/usr/bin/env python3
"""Genera /var/www/radar/railes-cifras.html desde datos Eurostat."""
from __future__ import annotations
import json
from pathlib import Path
DATA = Path("/var/www/radar/datos/railes-cifras.json")
OUT = Path("/var/www/radar/railes-cifras.html")
LABEL = {"ES":"España","FR":"Francia","DE":"Alemania","IT":"Italia","EU27_2020":"UE-27"}
COLOR = {"ES":"#ff5a1f","FR":"#3ddc97","DE":"#8ec5ff","IT":"#f2c94c","EU27_2020":"#bb6bd9"}
def bar_rows(d, key, suffix):
    vals=[c for c in d["countries"] if c.get(key) is not None]
    mx=max((c[key] for c in vals), default=1) or 1
    out=[]
    for c in vals:
        pct=round(100*c[key]/mx,1)
        out.append(f'<div class="barrow"><span>{LABEL.get(c["code"],c["code"])}</span><div class="bar"><i style="width:{pct}%;background:{COLOR.get(c["code"],"#ff5a1f")}"></i></div><b>{c[key]:.1f}{suffix}</b></div>')
    return "".join(out)
def main():
    d=json.loads(DATA.read_text(encoding="utf-8"))
    es=next((c for c in d["countries"] if c["code"]=="ES"), {})
    html=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cifras · Raíles</title><meta name="description" content="Viajeros y pasajeros-km de ferrocarril en España, Francia, Alemania, Italia y UE-27. Datos Eurostat 2023; alta velocidad, inversión, mantenimiento y seguridad pendientes de fuente.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/railes-cifras.html"><meta property="og:title" content="Cifras · Raíles"><meta property="og:description" content="Ferrocarril total 2023: España frente a Europa. Sin alta velocidad desagregada todavía."><meta property="og:type" content="website"><meta property="og:url" content="https://radar.viajeinteligencia.com/railes-cifras.html"><meta property="og:image" content="https://radar.viajeinteligencia.com/retrasos-renfe-og.png"><meta name="twitter:card" content="summary_large_image">
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--paper:#fffaf5}}
*{{box-sizing:border-box}}body{{margin:0;background:#fafafa;color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.55}}.wrap{{max-width:980px;margin:auto;padding:24px 16px 56px}}a{{color:#c2410c}}.top{{font-size:.85rem;margin-bottom:14px}}h1{{font-size:2rem;margin:.1em 0}}.lead{{max-width:780px;color:#334155}}.meta{{font-size:.82rem;color:var(--muted)}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}}.kpi{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px}}.kpi b{{display:block;font-size:1.6rem;color:#b45309}}.kpi span{{font-size:.75rem;color:var(--muted)}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:17px;margin:18px 0}}h2{{font-size:1.15rem;margin:0 0 8px;border-bottom:2px solid #fde68a;padding-bottom:5px}}.card p,.card li{{font-size:.9rem;color:#334155}}.muted{{color:var(--muted);font-size:.82rem}}
.barrow{{display:grid;grid-template-columns:100px 1fr 75px;gap:9px;align-items:center;margin:9px 0;font-size:.85rem}}.barrow span{{color:#334155}}.bar{{height:14px;background:#f1f5f9;border-radius:99px;overflow:hidden}}.bar i{{display:block;height:100%;border-radius:99px}}.barrow b{{text-align:right;font-variant-numeric:tabular-nums}}
.warn{{background:#fff7ed;border-left:4px solid #b45309;padding:10px 14px;border-radius:7px;font-size:.9rem}}.pending{{border-left:4px solid #94a3b8}}.pending h2{{border-bottom-color:#cbd5e1}}
@media(max-width:600px){{.kpis{{grid-template-columns:1fr}}.barrow{{grid-template-columns:80px 1fr 70px}}}}
</style></head><body><main class="wrap">
<p class="top"><a href="/">← radar</a> · <a href="/railes.html">raíles</a> · <a href="/retrasos-renfe-mapa.html">retrasos en vivo</a></p>
<h1>Cifras · Raíles</h1>
<p class="lead">Demanda ferroviaria total en España frente a Francia, Alemania, Italia y la UE-27. <b>Eurostat no desglosa alta velocidad</b>: estos datos son de ferrocarril total, no de AVE.</p>
<p class="meta">Año {d["year"]} · fuente: <a href="{d["source_url"]}" target="_blank" rel="noopener">{d["source"]}</a> · datos abiertos Eurostat.</p>
<div class="kpis"><div class="kpi"><b>{es.get("pax_m",0):.1f} M</b><span>viajeros España</span></div><div class="kpi"><b>{es.get("pkm_bn",0):.1f} mil M</b><span>pasajeros-km España</span></div><div class="kpi"><b>{d["year"]}</b><span>último año Eurostat cargado</span></div></div>
<div class="warn"><b>No es alta velocidad.</b> Eurostat publica ferrocarril total. Para AVE/AV hacen falta OFE/ADIF/UIC. No se presenta el total como si fuera alta velocidad.</div>
<div class="card"><h2>Viajeros por país <span class="muted">millones · 2023</span></h2>{bar_rows(d,"pax_m"," M")}<p class="muted">Viajeros transportados; no son usuarios únicos. La UE-27 no tiene dato de viajeros en esta consulta.</p></div>
<div class="card"><h2>Pasajeros-km <span class="muted">miles de millones · 2023</span></h2>{bar_rows(d,"pkm_bn"," mil M")}<p class="muted">Pasajeros-km: demanda ponderada por distancia. No es lo mismo que viajeros.</p></div>
<div class="card pending"><h2>Alta velocidad: pendiente de fuente</h2><p>Kilómetros de red, viajeros y pasajeros-km <b>solo de alta velocidad</b> no están en <code>RAIL_PA_TOTAL</code>. Fuentes a integrar: Observatorio del Ferrocarril, ADIF/ADIF AV y UIC. Hasta entonces: sin dato.</p><p class="muted">No se estima repartiendo el total ferroviario.</p></div>
<div class="card pending"><h2>Inversión y mantenimiento: pendiente</h2><p>Inversión ejecutada y gasto de mantenimiento son anuales y agregados. Fuentes: ADIF/ADIF AV, MITMA y PGE. No hay desglose público limpio por corredor.</p><p class="muted">No se publica €/km ni €/pasajero-km hasta validar denominador y año.</p></div>
<div class="card pending"><h2>Seguridad: pendiente</h2><p>Accidentes e incidentes comparables: ERA (indicadores comunes de seguridad) y CIAF en España. Publicación anual y con retraso; el accidente de Urda de 2026 no está consolidado.</p><p class="muted">No se mezclan retrasos GTFS-RT con accidentes.</p></div>
<div class="card"><h2>Qué se puede afirmar hoy</h2><ul><li>España movió <b>{es.get("pax_m",0):.1f} millones</b> de viajeros ferroviarios en 2023.</li><li>La demanda española fue <b>{es.get("pkm_bn",0):.1f} mil millones de pasajeros-km</b>.</li><li>Alemania y Francia tienen más demanda total; la comparación de alta velocidad aún no está disponible.</li></ul><p class="muted">Datos: <a href="/datos/railes-cifras.json">JSON</a> · fuente original Eurostat.</p></div>
<footer class="muted">Proyecto personal · sin cookies · AGPL-3.0 · <a href="https://github.com/mcasrom/nearme-osint">código</a></footer>
</main></body></html>'''
    OUT.write_text(html,encoding="utf-8"); print("cifras ok",OUT,len(html))
if __name__=="__main__": main()
