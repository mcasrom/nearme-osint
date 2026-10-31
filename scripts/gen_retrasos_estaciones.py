#!/usr/bin/env python3
import json,re,unicodedata,html
from pathlib import Path
DATA=Path('/var/www/radar/datos/retrasos-renfe-hoy.json')
OUT=Path('/var/www/radar')
def esc(x): return html.escape(str(x or ''))
def slug(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+','-',s).strip('-')[:70] or 'estacion'
try: d=json.loads(DATA.read_text(encoding='utf-8'))
except Exception as e: print('sin datos',e); raise SystemExit(0)
items=d.get('items',[]); date=d.get('date',''); generated=d.get('generated_at','')
by={}
for e in items:
 by.setdefault(e.get('estacion') or 'Sin estación',[]).append(e)
groups=sorted(by.items(),key=lambda kv:(-len(kv[1]),kv[0]))[:20]
links=[]
for est,evs in groups:
 s=slug(est); f=OUT/f'retrasos-renfe-{s}.html'; n=len(evs)
 rows=''.join(f'<tr><td>{esc(e.get("servicio") or e.get("tipo"))}</td><td>{esc((e.get("origen")+" → "+e.get("destino")) if e.get("origen") and e.get("destino") else (e.get("corredor") or (e.get("ruta") if e.get("ruta") not in (None,".","") else "s/d")))}</td><td>{esc(e.get("trip"))}</td><td><b>+{esc(e.get("retraso_min"))} min</b></td><td>{esc(e.get("created_at"))}</td></tr>' for e in sorted(evs,key=lambda x:-(x.get('retraso_min') or 0))[:50])
 page=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retrasos de Renfe en {esc(est)} hoy</title><meta name="description" content="Retrasos de Renfe en {esc(est)}: {n} incidencias. Datos GTFS-RT y GTFS estático; no es una web oficial."><link rel="canonical" href="https://radar.viajeinteligencia.com/retrasos-renfe-{s}.html"><style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:0 auto;padding:24px 16px;color:#222}}table{{width:100%;border-collapse:collapse;font-size:.9rem}}th,td{{border-bottom:1px solid #e5e5e5;padding:7px;text-align:left}}a{{color:#c2410c}}p.small{{font-size:.85rem;color:#666}}</style></head><body><p><a href="/retrasos-renfe-hoy.html">← Retrasos de Renfe hoy</a> · <a href="/retrasos-renfe-estaciones.html">Estaciones</a></p><h1>Retrasos de Renfe en {esc(est)}</h1><p>{n} incidencias · actualizado {esc(date)} · {esc(generated)}</p><p class="small">Datos GTFS-RT y GTFS estático de Renfe vía NearMe. No es una web oficial. La línea y el corredor proceden del GTFS estático de Renfe cuando están disponibles.</p><table><thead><tr><th>Servicio</th><th>Corredor</th><th>Trip</th><th>Retraso</th><th>Registrado</th></tr></thead><tbody>{rows}</tbody></table></body></html>'''
 f.write_text(page,encoding='utf-8'); links.append(f'<li><a href="/retrasos-renfe-{s}.html">{esc(est)}</a> ({n})</li>')
idx=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Estaciones con retrasos de Renfe hoy</title><meta name="robots" content="index,follow"><link rel="canonical" href="https://radar.viajeinteligencia.com/retrasos-renfe-estaciones.html"><style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:0 auto;padding:24px 16px;color:#222}}li{{margin:5px 0}}a{{color:#c2410c}}</style></head><body><p><a href="/retrasos-renfe-hoy.html">← Retrasos de Renfe hoy</a></p><h1>Estaciones con retrasos de Renfe</h1><p>Actualizado {esc(generated)}. Datos GTFS-RT; no es una web oficial.</p><ul>{''.join(links)}</ul></body></html>'''
(OUT/'retrasos-renfe-estaciones.html').write_text(idx,encoding='utf-8')
# Actualiza el sitemap de radar: quita las fichas antiguas y añade las actuales.
smap = OUT/'sitemap.xml'
if smap.exists():
    txt = smap.read_text(encoding='utf-8')
    txt = re.sub(r'\s*<url><loc>https://radar\.viajeinteligencia\.com/retrasos-renfe-(?:hoy|estaciones|[a-z0-9-]+)\.html</loc>.*?</url>', '', txt, flags=re.S)
    last = (generated or '')[:10]
    entries = [f'<url><loc>https://radar.viajeinteligencia.com/retrasos-renfe-hoy.html</loc><lastmod>{esc(last)}</lastmod><changefreq>hourly</changefreq><priority>0.9</priority></url>',
               f'<url><loc>https://radar.viajeinteligencia.com/retrasos-renfe-mapa.html</loc><lastmod>{esc(last)}</lastmod><changefreq>hourly</changefreq><priority>0.85</priority></url>',
               f'<url><loc>https://radar.viajeinteligencia.com/retrasos-renfe-estaciones.html</loc><lastmod>{esc(last)}</lastmod><changefreq>hourly</changefreq><priority>0.8</priority></url>']
    for est,_ in groups:
        entries.append(f'<url><loc>https://radar.viajeinteligencia.com/retrasos-renfe-{slug(est)}.html</loc><lastmod>{esc(last)}</lastmod><changefreq>daily</changefreq><priority>0.6</priority></url>')
    txt = txt.replace('</urlset>', ''.join(entries) + '</urlset>')
    smap.write_text(txt, encoding='utf-8')

keep={'retrasos-renfe-hoy.html','retrasos-renfe-estaciones.html','retrasos-renfe-mapa.html'}|{f'retrasos-renfe-{slug(est)}.html' for est,_ in groups}
for old in OUT.glob('retrasos-renfe-*.html'):
    if old.name not in keep:
        old.unlink()
print('estaciones',len(groups),'generated',generated)
