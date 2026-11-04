#!/usr/bin/env python3
"""Genera /var/www/radar/railes-cifras.html desde datos Eurostat."""
from __future__ import annotations
import json
from pathlib import Path
CSS = '.site-head{position:sticky;top:0;z-index:1000;background:#fff;border-bottom:1px solid #e2e8f0}.headwrap{max-width:1100px;margin:auto;display:flex;align-items:center;gap:12px;padding:10px 16px;flex-wrap:wrap}.brand{font-weight:800;font-size:1.25rem;color:#172033;text-decoration:none;display:flex;align-items:center;gap:7px}.brand .mark{display:inline-block;width:10px;height:24px;border-radius:3px;background:#ff5a1f}.tag{font-size:.78rem;color:#64748b}.site-head nav{display:flex;gap:12px;margin-left:auto;flex-wrap:wrap}.site-head nav a{font-size:.86rem;color:#334155;text-decoration:none}.site-head nav a:hover{color:#c2410c}.site-foot{background:#fff;border-top:1px solid #e2e8f0;margin-top:28px;padding:20px 16px}.footwrap{max-width:1100px;margin:auto;font-size:.85rem;color:#475569}.footwrap p{margin:4px 0}.footlinks{display:flex;gap:12px;flex-wrap:wrap}.footlinks a{color:#c2410c;text-decoration:none}.kofi{display:inline-flex;align-items:center;gap:6px;background:#13C3A5;color:#fff!important;border-radius:7px;padding:8px 12px;text-decoration:none;font-weight:700}.fine{color:#94a3b8;font-size:.78rem}@media(max-width:600px){.tag{display:none}.site-head nav{gap:10px}.site-head nav a{font-size:.8rem}}'
DATA = Path("/var/www/radar/datos/railes-cifras.json")
OUT = Path("/var/www/radar/railes-cifras.html")
LABEL = {"ES":"España","FR":"Francia","DE":"Alemania","IT":"Italia","EU27_2020":"UE-27","EUROPE":"Europa","WORLD":"Mundo"}
COLOR = {"ES":"#ff5a1f","FR":"#3ddc97","DE":"#8ec5ff","IT":"#f2c94c","EU27_2020":"#bb6bd9"}
def bar_rows(d, key, suffix):
    vals=[c for c in d["countries"] if c.get(key) is not None]
    mx=max((c[key] for c in vals), default=1) or 1
    out=[]
    for c in vals:
        pct=round(100*c[key]/mx,1)
        out.append(f'<div class="barrow"><span>{LABEL.get(c["code"],c["code"])}</span><div class="bar"><i style="width:{pct}%;background:{COLOR.get(c["code"],"#ff5a1f")}"></i></div><b>{c[key]:.1f}{suffix}</b></div>')
    return "".join(out)
def bar_pairs(items, suffix):
    mx=max(items.values(), default=1) or 1
    out=[]
    for code,val in items.items():
        pct=round(100*val/mx,1)
        out.append(f'<div class="barrow"><span>{LABEL.get(code,code)}</span><div class="bar"><i style="width:{pct}%;background:{COLOR.get(code,"#ff5a1f")}"></i></div><b>{val:.1f}{suffix}</b></div>')
    return "".join(out)

def main():
    d=json.loads(DATA.read_text(encoding="utf-8"))
    es=next((c for c in d["countries"] if c["code"]=="ES"), {})
    hs=d.get("hs",{})
    hs_km=hs.get("lines_km",{})
    hs_pkm=hs.get("traffic_pkm_bn",{})
    hs_share=round(100*hs_km.get("ES",0)/hs_km.get("WORLD",1),1) if hs_km.get("WORLD") else 0
    html=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cifras · Raíles</title><meta name="description" content="Red y demanda de alta velocidad en España frente a Europa y el mundo; viajeros ferroviarios totales Eurostat. Inversión, mantenimiento y seguridad, separados y con fuente.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/railes-cifras.html"><meta property="og:title" content="Cifras · Raíles"><meta property="og:description" content="Alta velocidad: km y pasajeros-km UIC; ferrocarril total Eurostat. Sin cifras inventadas."><meta property="og:type" content="website"><meta property="og:url" content="https://radar.viajeinteligencia.com/railes-cifras.html"><meta property="og:image" content="https://radar.viajeinteligencia.com/retrasos-renfe-og.png"><meta name="twitter:card" content="summary_large_image">
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--paper:#fffaf5}}
*{{box-sizing:border-box}}body{{margin:0;background:#fafafa;color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.55}}.wrap{{max-width:980px;margin:auto;padding:24px 16px 56px}}a{{color:#c2410c}}.top{{font-size:.85rem;margin-bottom:14px}}h1{{font-size:2rem;margin:.1em 0}}.lead{{max-width:780px;color:#334155}}.meta{{font-size:.82rem;color:var(--muted)}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}}.kpi{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px}}.kpi b{{display:block;font-size:1.6rem;color:#b45309}}.kpi span{{font-size:.75rem;color:var(--muted)}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:17px;margin:18px 0}}h2{{font-size:1.15rem;margin:0 0 8px;border-bottom:2px solid #fde68a;padding-bottom:5px}}.card p,.card li{{font-size:.9rem;color:#334155}}.muted{{color:var(--muted);font-size:.82rem}}
.barrow{{display:grid;grid-template-columns:100px 1fr 75px;gap:9px;align-items:center;margin:9px 0;font-size:.85rem}}.barrow span{{color:#334155}}.bar{{height:14px;background:#f1f5f9;border-radius:99px;overflow:hidden}}.bar i{{display:block;height:100%;border-radius:99px}}.barrow b{{text-align:right;font-variant-numeric:tabular-nums}}
.warn{{background:#fff7ed;border-left:4px solid #b45309;padding:10px 14px;border-radius:7px;font-size:.9rem}}.pending{{border-left:4px solid #94a3b8}}.pending h2{{border-bottom-color:#cbd5e1}}
@media(max-width:600px){{.kpis{{grid-template-columns:1fr}}.barrow{{grid-template-columns:80px 1fr 70px}}}}
</style></head><body><main class="wrap">
<header class="site-head"><div class="headwrap"><a class="brand" href="/railes.html"><span class="mark"></span>Raíles</a><span class="tag">Alta velocidad · datos abiertos</span><nav><a href="/railes.html">Mapa</a><a href="/railes-cifras.html">Cifras</a><a href="/railes-fuentes.html">Fuentes</a><a href="/retrasos-renfe-mapa.html">Retrasos</a><a href="/">Radar</a></nav></div></header>
<h1>Cifras · Raíles</h1>
<p class="lead">Alta velocidad española frente a Europa y el mundo: kilómetros de red y pasajeros-km. El bloque de ferrocarril total se mantiene separado porque Eurostat no desglosa AVE.</p>
<p class="meta">Red: UIC, estado a {hs.get("network_state","—")} · Demanda AV: {hs.get("traffic_year","—")} · Total ferroviario: Eurostat {d["year"]}.</p>
<div class="kpis"><div class="kpi"><b>{hs_km.get("ES",0):,.0f} km</b><span>alta velocidad en servicio · España</span></div><div class="kpi"><b>{hs_pkm.get("ES",0):.1f} mil M</b><span>pasajeros-km de AV · 2023</span></div><div class="kpi"><b>{hs_share:.1f} %</b><span>de la red AV mundial</span></div></div>
<div class="warn"><b>Dos bases distintas, no mezcladas.</b> UIC mide <b>alta velocidad</b> (red y pasajeros-km). Eurostat mide <b>ferrocarril total</b>. No se presenta el total como si fuera AVE.</div>
<div class="card"><h2>Red de alta velocidad <span class="muted">km en servicio · 2024</span></h2>{bar_pairs(hs_km," km")}<p class="muted">UIC High-Speed Atlas 2025. España: <b>{hs_km.get("ES",0):,.0f} km</b>; Europa: <b>{hs_km.get("EUROPE",0):,.0f} km</b>; mundo: <b>{hs_km.get("WORLD",0):,.0f} km</b>. Es red en servicio, no kilómetros de vía.</p></div>
<div class="card"><h2>Demanda de alta velocidad <span class="muted">pasajeros-km · miles de millones · 2023</span></h2>{bar_pairs(hs_pkm," mil M")}<p class="muted">UIC, tráfico de alta velocidad. No hay dato de viajeros únicos; no se estima.</p></div>
<div class="card"><h2>Viajeros por país <span class="muted">millones · 2023</span></h2>{bar_rows(d,"pax_m"," M")}<p class="muted">Viajeros transportados; no son usuarios únicos. La UE-27 no tiene dato de viajeros en esta consulta.</p></div>
<div class="card"><h2>Pasajeros-km <span class="muted">miles de millones · 2023</span></h2>{bar_rows(d,"pkm_bn"," mil M")}<p class="muted">Pasajeros-km: demanda ponderada por distancia. No es lo mismo que viajeros.</p></div>
<div class="card"><h2>Qué falta en alta velocidad</h2><p>La red y la demanda ya están. Faltan <b>viajeros únicos</b> (no existen como serie), <b>inversión y mantenimiento por corredor</b> y <b>seguridad desagregada</b>. No se estiman.</p><p class="muted">Fuente UIC: <a href="{hs.get("source_url","")}" target="_blank" rel="noopener">{hs.get("source","UIC")}</a>.</p></div>
<div class="card pending"><h2>Inversión y mantenimiento: pendiente</h2><p>Inversión ejecutada y gasto de mantenimiento son anuales y agregados. Fuentes: ADIF/ADIF AV, MITMA y PGE. No hay desglose público limpio por corredor.</p><p class="muted">No se publica €/km ni €/pasajero-km hasta validar denominador y año.</p></div>
<div class="card pending"><h2>Seguridad: pendiente</h2><p>Accidentes e incidentes comparables: ERA (indicadores comunes de seguridad) y CIAF en España. Publicación anual y con retraso; el accidente de Urda de 2026 no está consolidado.</p><p class="muted">No se mezclan retrasos GTFS-RT con accidentes.</p></div>
<div class="card"><h2>Qué se puede afirmar hoy</h2><ul><li>España tiene <b>{hs_km.get("ES",0):,.0f} km</b> de alta velocidad en servicio.</li><li>La AV española movió <b>{hs_pkm.get("ES",0):.1f} mil millones de pasajeros-km</b> en 2023.</li><li>España representa el <b>{hs_share:.1f} %</b> de la red AV mundial; Francia y Alemania tienen más demanda de AV.</li><li>El ferrocarril total español movió <b>{es.get("pax_m",0):.1f} millones</b> de viajeros en 2023.</li></ul><p class="muted">Datos: <a href="/datos/railes-cifras.json">JSON</a> · fuente original Eurostat.</p></div>
<footer class="site-foot"><div class="footwrap"><p><strong>Raíles</strong> · alta velocidad española, eje a eje. Datos abiertos, sin cookies.</p><p class="footlinks"><a href="/railes.html">Mapa</a><a href="/railes-cifras.html">Cifras</a><a href="/railes-fuentes.html">Fuentes</a><a href="/retrasos-renfe-mapa.html">Retrasos Renfe</a><a href="/">Radar</a><a href="https://github.com/mcasrom/nearme-osint">Código</a></p><p><a class="kofi" href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer">☕ Invítame a un café</a></p><p class="fine">Raíles v1.0 · AGPL-3.0 · Sin rastreo ni cuentas · Proyecto personal</p></div></footer>
</main></body></html>'''
    html = html.replace("</style>", CSS + "</style>")
    OUT.write_text(html,encoding="utf-8"); print("cifras ok",OUT,len(html))
if __name__=="__main__": main()
