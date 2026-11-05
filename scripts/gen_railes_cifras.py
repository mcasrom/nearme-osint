#!/usr/bin/env python3
"""Genera /var/www/radar/railes-cifras.html desde datos Eurostat."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import quote
try:
    from gen_railes_info import THEME_CSS, THEME_JS
except Exception:
    THEME_CSS=""; THEME_JS=""
DATA = Path("/var/www/radar/datos/railes-cifras.json")
OUT = Path("/var/www/radar/railes-cifras.html")
LABEL = {"ES":"España","FR":"Francia","DE":"Alemania","IT":"Italia","EU27_2020":"UE-27","EUROPE":"Europa","WORLD":"Mundo"}
COLOR = {"ES":"#ff5a1f","FR":"#3ddc97","DE":"#8ec5ff","IT":"#f2c94c","EU27_2020":"#bb6bd9"}
def bar_rows(d, key, suffix):
    vals=[c for c in d["countries"] if c.get(key) is not None and c["code"] not in {"EU27_2020","EUROPE","WORLD"}]
    mx=max((c[key] for c in vals), default=1) or 1
    out=[]
    for c in vals:
        pct=round(100*c[key]/mx,1)
        out.append(f'<div class="barrow"><span>{LABEL.get(c["code"],c["code"])}</span><div class="bar"><i style="width:{pct}%;background:{COLOR.get(c["code"],"#ff5a1f")}"></i></div><b>{c[key]:.1f}{suffix}</b></div>')
    return "".join(out)
def bar_pairs(items, suffix):
    items={k:v for k,v in items.items() if k not in {"EU27_2020","EUROPE","WORLD"}}
    mx=max(items.values(), default=1) or 1
    out=[]
    for code,val in items.items():
        pct=round(100*val/mx,1)
        out.append(f'<div class="barrow"><span>{LABEL.get(code,code)}</span><div class="bar"><i style="width:{pct}%;background:{COLOR.get(code,"#ff5a1f")}"></i></div><b>{val:.1f}{suffix}</b></div>')
    return "".join(out)

def indexed(series, years, base="2019"):
    out={}
    for code,vals in series.items():
        by=dict(zip(years,vals)); b=by.get(base)
        out[code]=[None if v is None or not b else round(100*v/b,1) for v in vals]
    return out

def svg_line(years, series, y_min, y_max, ticks, title, unit, fmt="{:.0f}", height=340):
    W=720; H=height; L=46; R=14; T=16; B=34; pw=W-L-R; ph=H-T-B
    ys=[int(y) for y in years]; xmin,xmax=min(ys),max(ys)
    def x(y): return L+(int(y)-xmin)/(xmax-xmin)*pw if xmax> xmin else L+pw/2
    def yv(v): return T+(y_max-v)/(y_max-y_min)*ph
    g=[]
    for t in ticks:
        yy=yv(t); g.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{W-R}" y2="{yy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        g.append(f'<text x="{L-8}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="#64748b">{fmt.format(t)}</text>')
    xlabels=[xmin]+[y for y in [2013,2016,2019,2022] if xmin<y<xmax]+[xmax]
    for yy in xlabels:
        if yy in ys:
            g.append(f'<line x1="{x(yy):.1f}" y1="{T}" x2="{x(yy):.1f}" y2="{H-B}" stroke="#f1f5f9" stroke-width="1"/>')
            g.append(f'<text x="{x(yy):.1f}" y="{H-12}" text-anchor="middle" font-size="11" fill="#64748b">{yy}</text>')
    for code, vals in series.items():
        pts=[]
        for yr,v in zip(years,vals):
            if v is not None: pts.append((x(yr),yv(v)))
        if not pts: continue
        g.append('<polyline fill="none" stroke="%s" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" points="%s"/>'%(COLOR.get(code,"#64748b")," ".join(f"{a:.1f},{b:.1f}" for a,b in pts)))
        a,b=pts[-1]; g.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3.6" fill="{COLOR.get(code,"#64748b")}" stroke="#fff" stroke-width="1.5"/>')
    legend=" ".join(f'<span><i style="background:{COLOR.get(c,"#64748b")}"></i>{LABEL.get(c,c)}</span>' for c in series)
    return f'<figure class="chart"><svg viewBox="0 0 {W} {H}" role="img" aria-label="{title}"><text x="{L}" y="11" font-size="11" fill="#64748b">{unit}</text>{"".join(g)}</svg><figcaption>{title}<span class="legend">{legend}</span></figcaption></figure>'

def svg_scatter(ctx):
    W=720;H=380;L=48;R=20;T=18;B=42;pw=W-L-R;ph=H-T-B
    xmin,xmax=0,95; ymin,ymax=0,27
    def X(v): return L+v/xmax*pw
    def Y(v): return T+(ymax-v)/ymax*ph
    g=[]
    for t in [0,20,40,60,80]:
        xx=X(t); g.append(f'<line x1="{xx:.1f}" y1="{T}" x2="{xx:.1f}" y2="{H-B}" stroke="#f1f5f9"/><text x="{xx:.1f}" y="{H-22}" text-anchor="middle" font-size="11" fill="#64748b">{t}</text>')
    for t in [0,5,10,15,20,25]:
        yy=Y(t); g.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{W-R}" y2="{yy:.1f}" stroke="#f1f5f9"/><text x="{L-7}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="#64748b">{t}</text>')
    g.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="#94a3b8"/><line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="#94a3b8"/>')
    for code,xv in ctx["hs_km_per_million_inhabitants"].items():
        yv=ctx["hs_pkm_per_network_km_m"][code]; xx,yy=X(xv),Y(yv)
        g.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="7" fill="{COLOR.get(code,"#64748b")}" stroke="#fff" stroke-width="2"><title>{LABEL.get(code,code)}: {xv:.1f} km/M hab.; {yv:.1f} M pkm/km</title></circle>')
        g.append(f'<text x="{xx+10:.1f}" y="{yy+4:.1f}" font-size="12" font-weight="700" fill="#334155">{LABEL.get(code,code)}</text>')
    g.append(f'<text x="{L+.5*(W-L-R):.1f}" y="{H-5}" text-anchor="middle" font-size="11" fill="#64748b">km de AV por millón de habitantes →</text>')
    g.append(f'<text x="12" y="{T+.5*(H-T-B):.1f}" transform="rotate(-90 12 {T+.5*(H-T-B):.1f})" text-anchor="middle" font-size="11" fill="#64748b">pkm de AV por km de red (millones) →</text>')
    return f'<figure class="chart"><svg viewBox="0 0 {W} {H}" role="img" aria-label="Dotación y uso de la alta velocidad">{"".join(g)}</svg><figcaption>Dotación y uso · 2024/2023. Cada punto es un país; no es un índice ni un ranking.</figcaption></figure>'

def main():
    d=json.loads(DATA.read_text(encoding="utf-8"))
    es=next((c for c in d["countries"] if c["code"]=="ES"), {})
    hs=d.get("hs",{})
    hs_km=hs.get("lines_km",{})
    hs_pkm=hs.get("traffic_pkm_bn",{})
    ctx=d.get("context",{})
    dens=ctx.get("hs_density_per_1000_km2",{})
    perhab=ctx.get("hs_km_per_million_inhabitants",{})
    sf=d.get("safety",{})
    sf_years=sf.get("years",[])
    sf_i=sf_years.index(2024) if 2024 in sf_years else -1
    sf_rate={g:vals[sf_i] for g,vals in sf.get("rate_per_million_train_km",{}).items()}
    sf_acc={g:vals[sf_i] for g,vals in sf.get("accidents",{}).items()}
    sf_km={g:vals[sf_i] for g,vals in sf.get("train_km_m",{}).items()}
    intensity=ctx.get("hs_pkm_per_network_km_m",{})
    percap=ctx.get("hs_pkm_per_capita",{})
    series=d.get("series",{})
    syears=series.get("years",[])
    idx=indexed(series.get("pkm_bn",{}),syears,"2019")
    trend_svg=svg_line(syears,idx,35,140,[40,60,80,100,120,140],"Demanda de ferrocarril total · índice 2019 = 100","índice")
    safety_svg=svg_line(sf.get("years",[]),sf.get("rate_per_million_train_km",{}),0,1.0,[0,0.2,0.4,0.6,0.8,1.0],"Accidentes significativos por millón de tren-km · 2006–2024","tasa anual",fmt="{:.1f}")
    scatter_svg=svg_scatter(ctx)
    jsonld=json.dumps({"@context":"https://schema.org","@type":"Dataset","name":"Cifras de alta velocidad y seguridad ferroviaria en España, Francia, Alemania e Italia","description":"Red de alta velocidad UIC 2024, densidad territorial, km por millón de habitantes, intensidad de uso, pasajeros-km UIC 2023, ferrocarril total Eurostat 2013-2024 y accidentes significativos por millón de tren-km ERA 2006-2024. Solo países comparables; sin totales agregados.","url":"https://radar.viajeinteligencia.com/railes-cifras.html","creator":{"@type":"Person","name":"Miguel Castillo","url":"https://viajeinteligencia.com"},"isAccessibleForFree":True,"inLanguage":"es","dateModified":"2026-11-04","keywords":"alta velocidad, AVE, densidad ferroviaria, km por habitante, pasajeros-km, UIC, Eurostat, ERA","spatialCoverage":["España","Francia","Alemania","Italia"],"temporalCoverage":"2006/2024","variableMeasured":["km de alta velocidad en servicio","densidad de red por 1.000 km²","km de alta velocidad por millón de habitantes","pasajeros-km de alta velocidad","intensidad de uso por km de red","pasajeros-km de ferrocarril total","serie temporal 2013-2024","accidentes significativos por millón de tren-km"],"distribution":{"@type":"DataDownload","encodingFormat":"application/json","contentUrl":"https://radar.viajeinteligencia.com/datos/railes-cifras.json"},"citation":["https://uic.org/activities/high-speed-data-and-atlas","https://doi.org/10.2908/RAIL_PA_TOTAL","https://data.worldbank.org/indicator/SP.POP.TOTL","https://www.era.europa.eu/domains/accident-incident/common-safety-indicators-csis"]},ensure_ascii=False)
    breadcrumb=json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Radar","item":"https://radar.viajeinteligencia.com/"},{"@type":"ListItem","position":2,"name":"Raíles","item":"https://radar.viajeinteligencia.com/railes.html"},{"@type":"ListItem","position":3,"name":"Cifras","item":"https://radar.viajeinteligencia.com/railes-cifras.html"}]},ensure_ascii=False)
    share_url="https://radar.viajeinteligencia.com/railes-cifras.html"
    share_text="Alta velocidad: 3.993 km en España; 7,9 km/1.000 km²; 82,6 km por millón de habitantes; 3,8 M pkm por km de red. Sin totales agregados."
    share_enc=quote(share_text+" "+share_url)
    html=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cifras · Raíles</title><meta name="description" content="Red, densidad y demanda de alta velocidad en España, Francia, Alemania e Italia; series 2013-2024, intensidad de uso y seguridad ERA 2006-2024. Sin totales agregados."><meta name="robots" content="index,follow,max-image-preview:large"><meta name="author" content="Miguel Castillo"><meta name="theme-color" content="#101827"><meta name="keywords" content="alta velocidad, AVE, España, densidad ferroviaria, km por habitante, pasajeros-km, UIC, Eurostat, ERA, seguridad ferroviaria">
<link rel="canonical" href="https://radar.viajeinteligencia.com/railes-cifras.html"><meta property="og:title" content="Cifras · Raíles"><meta property="og:description" content="Alta velocidad: km, densidad, km por habitante, intensidad de uso, series y seguridad. Solo países comparables; sin totales agregados ni cifras inventadas."><meta property="og:type" content="website"><meta property="og:url" content="https://radar.viajeinteligencia.com/railes-cifras.html"><meta property="og:site_name" content="El Observatorio Ciudadano del Ferrocarril"><meta property="og:locale" content="es_ES"><meta property="og:image" content="https://radar.viajeinteligencia.com/railes-cifras-og.png"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Raíles: 3.993 km de alta velocidad en España; 7,9 km por 1.000 km²; 82,6 km por millón de habitantes; 3,8 millones de pkm por km de red; 0,27 accidentes por millón de tren-km."><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Cifras · Raíles"><meta name="twitter:description" content="Red, densidad, demanda y seguridad de la alta velocidad. Sin totales agregados."><meta name="twitter:image" content="https://radar.viajeinteligencia.com/railes-cifras-og.png"><meta name="twitter:image:alt" content="Tarjeta de cifras de Raíles">
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--paper:#fffaf5}}
*{{box-sizing:border-box}}body{{margin:0;background:#fafafa;color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.55}}.wrap{{max-width:1100px;margin:auto;padding:24px 16px 56px}}a{{color:#c2410c}}.top{{font-size:.85rem;margin-bottom:14px}}h1{{font-size:2rem;margin:.1em 0}}.lead{{max-width:780px;color:#334155}}.meta{{font-size:.82rem;color:var(--muted)}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}}.kpi{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px}}.kpi b{{display:block;font-size:1.6rem;color:#b45309}}.kpi span{{font-size:.75rem;color:var(--muted)}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:17px;margin:18px 0}}h2{{font-size:1.15rem;margin:0 0 8px;border-bottom:2px solid #fde68a;padding-bottom:5px}}.card p,.card li{{font-size:.9rem;color:#334155}}.muted{{color:var(--muted);font-size:.82rem}}
.barrow{{display:grid;grid-template-columns:100px minmax(60px,1fr) 126px;gap:8px;align-items:center;margin:9px 0;font-size:.85rem}}.barrow span{{color:#334155;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.bar{{height:14px;background:#f1f5f9;border-radius:99px;overflow:hidden;min-width:0}}.bar i{{display:block;height:100%;border-radius:99px}}.barrow b{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:.82rem}}
.warn{{background:#fff7ed;border-left:4px solid #b45309;padding:10px 14px;border-radius:7px;font-size:.9rem}}.card[id]{{scroll-margin-top:72px}}.funnel{{border:1px solid #fed7aa;background:linear-gradient(180deg,#fff7ed,#fff)}}.steps{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:12px 0 6px;padding:0;list-style:none;counter-reset:step}}.steps li{{counter-increment:step}}.steps a{{display:block;height:100%;text-decoration:none;border:1px solid var(--line);border-radius:9px;padding:10px;background:#fff;color:var(--ink)}}.steps a:before{{content:counter(step);display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:#ff5a1f;color:#fff;font-size:.75rem;font-weight:800;margin-bottom:6px}}.steps b{{display:block;font-size:.86rem}}.steps small{{display:block;color:var(--muted);font-size:.72rem;margin-top:2px}}.chart{{margin:10px 0 4px}}.chart svg{{width:100%;height:auto;display:block}}.chart figcaption{{font-size:.78rem;color:var(--muted);margin-top:4px}}.chart .legend{{display:flex;gap:10px;flex-wrap:wrap;margin-top:5px}}.chart .legend span{{display:inline-flex;align-items:center;gap:4px}}.chart .legend i{{width:9px;height:9px;border-radius:2px;display:inline-block}}.pending{{border-left:4px solid #94a3b8}}.pending h2{{border-bottom-color:#cbd5e1}}
@media(max-width:600px){{.kpis{{grid-template-columns:1fr}}.barrow{{grid-template-columns:76px minmax(40px,1fr) 116px;gap:6px;font-size:.8rem}}.barrow b{{font-size:.76rem}}.steps{{grid-template-columns:1fr 1fr}}.steps a{{padding:8px}}.steps b{{font-size:.8rem}}}}
.site-head{{position:sticky;top:0;z-index:1000;background:#fff;border-bottom:1px solid #e2e8f0}}.headwrap{{max-width:1100px;margin:auto;display:flex;align-items:center;gap:12px;padding:10px 16px;flex-wrap:wrap}}.brand{{font-weight:800;font-size:1.25rem;color:#172033;text-decoration:none;display:flex;align-items:center;gap:7px}}.brandtext{{max-width:520px;line-height:1.1}}.brand .mark{{display:inline-block;width:10px;height:24px;border-radius:3px;background:#ff5a1f}}.tag{{font-size:.78rem;color:#64748b}}.site-head nav{{display:flex;gap:12px;margin-left:auto;flex-wrap:wrap}}.site-head nav a{{font-size:.86rem;color:#334155;text-decoration:none}}.site-head nav a:hover{{color:#c2410c}}.site-foot{{background:#fff;border-top:1px solid #e2e8f0;margin-top:28px;padding:20px 16px}}.footwrap{{max-width:1100px;margin:auto;font-size:.85rem;color:#475569}}.footwrap p{{margin:4px 0}}.footlinks{{display:flex;gap:12px;flex-wrap:wrap}}.footlinks a{{color:#c2410c;text-decoration:none}}.kofi{{display:inline-flex;align-items:center;gap:6px;background:#13C3A5;color:#fff!important;border-radius:7px;padding:8px 12px;text-decoration:none;font-weight:700}}.fine{{color:#94a3b8;font-size:.78rem}}@media(max-width:600px){{.tag{{display:none}}.site-head nav{{gap:10px}}.site-head nav a{{font-size:.8rem}}}}</style><script type="application/ld+json">{jsonld}</script><script type="application/ld+json">{breadcrumb}</script></head><body><main class="wrap">
<header class="site-head"><div class="headwrap"><a class="brand" href="/railes.html"><span class="mark"></span><span class="brandtext">El Observatorio Ciudadano del Ferrocarril</span></a><span class="tag">Raíles · alta velocidad</span><nav><a href="/railes.html">Mapa</a><a href="/railes-cifras.html">Cifras</a><a href="/railes-inversiones.html">Inversiones</a><a href="/railes-fuentes.html">Fuentes</a><a href="/railes-about.html">About</a><a href="/retrasos-renfe-mapa.html">Retrasos</a><a href="/">Radar</a></nav><button class="themebtn" id="railes-theme" type="button" onclick="toggleRailesTheme()" aria-label="Cambiar tema">☾ Oscuro</button></div></header>
<h1>Cifras · Raíles</h1>
<p class="lead">Alta velocidad española frente a otros países: kilómetros de red, densidad y pasajeros-km. Solo países comparables; sin totales agregados. El ferrocarril total se mantiene separado porque Eurostat no desglosa AVE.</p>
<p class="meta">Actualizado: 4-nov-2026 · revisión automática mensual (día 5, 06:20 UTC) · Red: UIC, estado a {hs.get("network_state","—")} · Demanda AV: {hs.get("traffic_year","—")} · Contexto: Banco Mundial {ctx.get("year","—")} · Total ferroviario: Eurostat {d["year"]}.</p>
<div class="kpis"><div class="kpi"><b>{hs_km.get("ES",0):,.0f} km</b><span>alta velocidad en servicio · España</span></div><div class="kpi"><b>{hs_pkm.get("ES",0):.1f} mil M</b><span>pasajeros-km de AV · 2023</span></div><div class="kpi"><b>{dens.get("ES",0):.1f}</b><span>km de AV por 1.000 km²</span></div></div>
<div class="warn"><b>Dos bases distintas, no mezcladas.</b> UIC mide <b>alta velocidad</b> (red y pasajeros-km). Eurostat mide <b>ferrocarril total</b>. No se presenta el total como si fuera AVE.<br><br><b>Sin totales agregados.</b> No se suman kilómetros de países: no sirve para comparar redes. Se compara la red, su <b>densidad por superficie</b>, su <b>longitud por habitante</b> y su <b>intensidad de uso</b>, con población y área del Banco Mundial.</div>
<div class="card funnel" id="empieza"><h2>Empieza por aquí <span class="muted">5 pasos, 2 minutos</span></h2><p>El orden importa: primero la red, después cómo se reparte y cuánto se usa, y al final la evolución y la seguridad. Cada paso enlaza al gráfico y a su fuente.</p><ol class="steps"><li><a href="#red"><b>Cuánta red</b><small>3.993 km de AV</small></a></li><li><a href="#densidad"><b>Densidad y habitantes</b><small>7,9 km/1.000 km²</small></a></li><li><a href="#uso"><b>Intensidad de uso</b><small>3,8 M pkm/km</small></a></li><li><a href="#evolucion"><b>Evolución</b><small>índice 2019 = 100</small></a></li><li><a href="#seguridad"><b>Seguridad</b><small>0,27 acc./M tren-km</small></a></li></ol><p class="muted">Si solo quieres una conclusión, salta a <a href="#afirmar">“Qué se puede afirmar”</a>. Si buscas lo que no hay, ve a <a href="#limites">“Qué falta”</a>.</p></div>
<div class="card" id="red"><h2>Red de alta velocidad <span class="muted">km en servicio · 2024</span></h2>{bar_pairs(hs_km," km")}<p class="muted">Solo países comparables. UIC High-Speed Atlas 2025. Es red en servicio, no kilómetros de vía. No se publican totales agregados.</p></div>
<div class="card" id="densidad"><h2>Densidad de red <span class="muted">km de alta velocidad por 1.000 km² · 2024</span></h2>{bar_pairs(dens," km/1.000 km²")}<p class="muted">Red UIC 2024 dividida por la superficie total del país (Banco Mundial, 2023). Mide presencia territorial, no calidad ni uso. No se usa la media de km por país.</p></div>
<div class="card" id="habitante"><h2>Red por habitante <span class="muted">km de alta velocidad por millón de habitantes · 2024</span></h2>{bar_pairs(perhab," km/M hab.")}<p class="muted">Red UIC 2024 dividida por la población de 2023 (Banco Mundial). Es una ratio descriptiva; no mide demanda ni accesibilidad real.</p></div>
<div class="card" id="demanda"><h2>Demanda de alta velocidad <span class="muted">pasajeros-km · miles de millones · 2023</span></h2>{bar_pairs(hs_pkm," mil M")}<p class="muted">Solo países comparables. UIC, tráfico de alta velocidad. No se compara con totales mundiales ni se calculan medias por país. No hay dato de viajeros únicos; no se estima.</p></div>
<div class="card" id="uso"><h2>Intensidad de uso <span class="muted">millones de pasajeros-km de AV por km de red · 2023/2024</span></h2>{bar_pairs(intensity," M pkm/km")}<p class="muted">Pasajeros-km UIC 2023 divididos por km de red UIC 2024. Es una ratio descriptiva de uso por km, no eficiencia ni rentabilidad. La mezcla temporal es de un año y se declara.</p></div>
<div class="card" id="dotacion"><h2>Dotación y uso <span class="muted">cada punto es un país · 2023/2024</span></h2>{scatter_svg}<p class="muted">Eje X: km de AV por millón de habitantes. Eje Y: millones de pkm de AV por km de red. España aparece con mucha dotación y baja intensidad; con cuatro puntos es <b>exploratorio</b>, no un índice ni una conclusión causal.</p></div>
<div class="card" id="viajeros"><h2>Viajeros por país <span class="muted">millones · 2024</span></h2>{bar_rows(d,"pax_m"," M")}<p class="muted">Viajeros transportados; no son usuarios únicos. Eurostat 2024; la UE-27 no se compara como si fuera un país.</p></div>
<div class="card" id="pkm"><h2>Pasajeros-km <span class="muted">miles de millones · 2024</span></h2>{bar_rows(d,"pkm_bn"," mil M")}<p class="muted">Solo países. Pasajeros-km: demanda ponderada por distancia; no es lo mismo que viajeros. Eurostat 2024; la UE-27 no se usa como si fuera un país.</p></div>
<div class="card pending"><h2>Desglose Cercanías / Media Distancia / Larga Distancia: pendiente</h2><p>Eurostat publica el total y no lo desglosa; no se deriva ni se estima. Fuente necesaria: OFE, Renfe o INE, con tabla anual verificable. Cercanías y AVE no son el mismo producto ni la misma demanda.</p><p class="muted">Si no hay tabla descargable, la página seguirá mostrando solo el total.</p></div>
<div class="card" id="evolucion"><h2>Evolución del ferrocarril total <span class="muted">pasajeros-km · índice 2019 = 100 · 2013–2024</span></h2>{trend_svg}<p class="muted">Eurostat. El índice elimina la diferencia de escala entre países; no es alta velocidad. 2020 refleja la caída de la pandemia. España 2024: <b>132</b>; Francia <b>115</b>; Alemania <b>109</b>; Italia <b>99</b>.</p></div>
<div class="card" id="seguridad"><h2>Seguridad <span class="muted">accidentes significativos por millón de tren-km · 2024</span></h2>{bar_pairs(sf_rate," / M tren-km")}<p>España: <b>{sf_acc.get("ES",0)} accidentes significativos</b> y <b>{sf_km.get("ES",0):.1f} millones de tren-km</b>; tasa <b>{sf_rate.get("ES",0):.2f}</b>. Francia {sf_rate.get("FR",0):.2f}, Alemania {sf_rate.get("DE",0):.2f} e Italia {sf_rate.get("IT",0):.2f}. Es una tasa anual agregada, no una serie mensual ni por corredor.</p><p class="muted">Fuente: <a href="{sf.get("source_url","")}" target="_blank" rel="noopener">ERA · Common Safety Indicators 2006-2024</a>, tablas de accidentes y tren-km; última actualización 14-ene-2026. El accidente de Urda de 2026 no está consolidado y no se usa como dato anual. No se mezclan retrasos GTFS-RT con accidentes.</p></div>
<div class="card" id="seguridad-serie"><h2>Seguridad en el tiempo <span class="muted">accidentes significativos por millón de tren-km · 2006–2024</span></h2>{safety_svg}<p class="muted">Misma fuente y denominador. La subida española de 2020 coincide con menos tren-km por la pandemia, no con más accidentes: 51 accidentes en 2020 frente a 49 en 2019. No se interpreta un año aislado como tendencia.</p></div>
<div class="card" id="limites"><h2>Qué falta en alta velocidad</h2><p>La red, la demanda, la intensidad, la serie temporal y la tasa anual de seguridad ya están. Faltan <b>viajeros únicos</b> (no existen como serie), <b>inversión y mantenimiento por corredor</b>, <b>desglose Cercanías/MD/LD</b> y <b>seguridad mensual o por corredor</b>. No se estiman.</p><p class="muted">Fuente UIC: <a href="{hs.get("source_url","")}" target="_blank" rel="noopener">{hs.get("source","UIC")}</a>.</p></div>
<div class="card"><h2>Macroinversiones ferroviarias <span class="muted">registro parcial</span></h2><p>He empezado un registro de proyectos concretos con fuente oficial: Corredor Mediterráneo, Corredor Atlántico, cercanías, estaciones e integraciones urbanas. <strong>No es el total del sistema</strong> y los importes no se suman.</p><p class="muted">Faltan la serie anual de inversión ejecutada y el mantenimiento por corredor; siguen pendientes.</p><p><a class="btn" href="/railes-inversiones.html">Ver el registro de macroinversiones →</a></p></div>
<div class="card pending"><h2>Seguridad por corredor: pendiente</h2><p>La tasa anual ya está publicada; no hay accidentes comparables por corredor ni serie mensual. CIAF/ERA publican con retraso y el accidente de Urda de 2026 no está consolidado.</p><p class="muted">No se mezclan retrasos GTFS-RT con accidentes.</p></div>
<div class="card"><h2>Compartir</h2><p><a href="https://twitter.com/intent/tweet?text={quote(share_text)}&url={quote(share_url)}" target="_blank" rel="noopener">X</a> · <a href="https://mastodon.social/share?text={share_enc}" target="_blank" rel="noopener">Mastodon</a> · <a href="https://bsky.app/intent/compose?text={share_enc}" target="_blank" rel="noopener">Bluesky</a> · <a href="https://wa.me/?text={share_enc}" target="_blank" rel="noopener">WhatsApp</a></p><p class="muted">Comparte la página, no una captura: así se ven las fuentes y los límites.</p></div>
<div class="card" id="afirmar"><h2>Qué se puede afirmar hoy</h2><ul><li>España tiene <b>{hs_km.get("ES",0):,.0f} km</b> de alta velocidad en servicio.</li><li>La AV española movió <b>{hs_pkm.get("ES",0):.1f} mil millones de pasajeros-km</b> en 2023.</li><li>España tiene la mayor red de los cuatro países y la mayor densidad: <b>{dens.get("ES",0):.1f} km por 1.000 km²</b> y <b>{perhab.get("ES",0):.1f} km por millón de habitantes</b>.</li><li>El ferrocarril total español movió <b>{es.get("pax_m",0):.1f} millones</b> de viajeros y <b>{es.get("pkm_bn",0):.1f} mil M pkm</b> en 2024.</li><li>La demanda total española está en <b>132</b> sobre 2019; Francia 115, Alemania 109 e Italia 99.</li><li>La AV española mueve <b>{intensity.get("ES",0):.1f} M pkm por km de red</b>, frente a 21–24 en Francia, Alemania e Italia; es intensidad de uso, no eficiencia.</li><li>La tasa de accidentes significativos fue <b>{sf_rate.get("ES",0):.2f} por millón de tren-km</b> en 2024 (ERA).</li></ul><p class="muted">Datos: <a href="/datos/railes-cifras.json">JSON</a> · fuentes: UIC, Eurostat, Banco Mundial y ERA.</p></div>
<footer class="site-foot"><div class="footwrap"><p><strong>Raíles</strong> · alta velocidad española, eje a eje. Datos abiertos, sin cookies.</p><p class="footlinks"><a href="/railes.html">Mapa</a><a href="/railes-cifras.html">Cifras</a><a href="/railes-inversiones.html">Inversiones</a><a href="/railes-fuentes.html">Fuentes</a><a href="/railes-about.html">About</a><a href="/retrasos-renfe-mapa.html">Retrasos Renfe</a><a href="/">Radar</a><a href="https://github.com/mcasrom/nearme-osint">Código</a></p><p><strong>Ecosistema:</strong> <a href="https://www.viajeinteligencia.com">ViajeInteligencia</a> · <a href="https://www.pruebapublica.com">Prueba Pública</a> · <a href="https://fimi.viajeinteligencia.com">FIMI</a> · <a href="https://analisis.pruebapublica.com">Análisis</a> · <a href="/railes-about.html#ecosistema">Todos los proyectos</a></p><p><a class="kofi" href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer">☕ Invítame a un café</a></p><p class="fine">Raíles v1.0 · AGPL-3.0 · Sin rastreo ni cuentas · Proyecto personal</p></div></footer>
</main>{THEME_JS}</body></html>'''
    OUT.write_text(html,encoding="utf-8"); print("cifras ok",OUT,len(html))
if __name__=="__main__": main()
