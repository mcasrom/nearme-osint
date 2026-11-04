#!/usr/bin/env python3
"""Sitemap y llms.txt para Raíles (idempotente)."""
from pathlib import Path
ROOT=Path("/var/www/radar")
PAGES=[
 ("railes.html","2026-11-04","weekly","0.9"),
 ("railes-cifras.html","2026-11-04","monthly","0.8"),
 ("railes-fuentes.html","2026-11-04","monthly","0.7"),
]
smap=ROOT/"sitemap.xml"
s=smap.read_text(encoding="utf-8") if smap.exists() else '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>'
for path,lastmod,freq,prio in PAGES:
    loc=f"https://radar.viajeinteligencia.com/{path}"
    if f"<loc>{loc}</loc>" not in s:
        s=s.replace("</urlset>", f'  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{freq}</changefreq><priority>{prio}</priority></url>\n</urlset>')
smap.write_text(s,encoding="utf-8")
llms='''# El Observatorio Ciudadano del Ferrocarril — Raíles

> Capa de datos abiertos sobre alta velocidad: mapa de corredores, cifras UIC/Eurostat y fuentes. Sin cookies, sin cuentas.

## Páginas
- https://radar.viajeinteligencia.com/railes.html — mapa esquemático de corredores y estaciones.
- https://radar.viajeinteligencia.com/railes-cifras.html — km de AV, pasajeros-km y ferrocarril total.
- https://radar.viajeinteligencia.com/railes-fuentes.html — fuentes, frecuencia, método, límites y contacto.

## Datos
- https://radar.viajeinteligencia.com/datos/railes-cifras.json — cifras UIC/Eurostat.
- https://radar.viajeinteligencia.com/retrasos-renfe-mapa.html — retrasos operativos de Renfe.
- https://radar.viajeinteligencia.com/datos/retrasos-renfe-mapa.json — JSON de retrasos.

## Límites
- No hay media de pasajeros por corredor.
- No hay accidentes/incidentes mensuales por km.
- No se incluyen Iryo ni Ouigo en el mapa de retrasos.
- Las cifras de AV son anuales; no son tiempo real.
'''
(ROOT/"llms.txt").write_text(llms,encoding="utf-8")
print("seo ok",len(s),"urls",len(PAGES))
