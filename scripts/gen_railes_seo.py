#!/usr/bin/env python3
"""Sitemap y llms.txt para Raíles (idempotente)."""
from pathlib import Path
ROOT=Path("/var/www/radar")
PAGES=[
 ("railes.html","2026-11-04","weekly","0.9"),
 ("railes-cifras.html","2026-11-04","monthly","0.8"),
 ("railes-fuentes.html","2026-11-04","monthly","0.7"),
 ("railes-about.html","2026-11-04","monthly","0.6"),
]
smap=ROOT/"sitemap.xml"
s=smap.read_text(encoding="utf-8") if smap.exists() else '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>'
for path,lastmod,freq,prio in PAGES:
    loc=f"https://radar.viajeinteligencia.com/{path}"
    if f"<loc>{loc}</loc>" not in s:
        s=s.replace("</urlset>", f'  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{freq}</changefreq><priority>{prio}</priority></url>\n</urlset>')
smap.write_text(s,encoding="utf-8")
llms='''# El Observatorio Ciudadano del Ferrocarril — Raíles

> Capa de datos abiertos sobre alta velocidad: mapa de corredores, cifras UIC/Eurostat/ERA y fuentes. Sin cookies, sin cuentas y sin totales agregados.

## Páginas
- https://radar.viajeinteligencia.com/railes.html — mapa esquemático de corredores y estaciones.
- https://radar.viajeinteligencia.com/railes-cifras.html — km de AV, densidad, km por habitante, intensidad de uso, serie 2013–2024 del ferrocarril total y seguridad ERA 2006–2024.
- https://radar.viajeinteligencia.com/railes-fuentes.html — fuentes, frecuencia, método, límites y contacto.
- https://radar.viajeinteligencia.com/railes-about.html — qué es Raíles, qué no hace y ecosistema (viajeinteligencia.com / pruebapublica.com).

## Datos
- https://radar.viajeinteligencia.com/datos/railes-cifras.json — cifras UIC/Eurostat/ERA, series y contexto Banco Mundial.
- https://radar.viajeinteligencia.com/retrasos-renfe-mapa.html — retrasos operativos de Renfe.
- https://radar.viajeinteligencia.com/datos/retrasos-renfe-mapa.json — JSON de retrasos.

## Ecosistema
- https://www.viajeinteligencia.com — landing e índice.
- https://www.pruebapublica.com — landing e índice.
- Raíles about: https://radar.viajeinteligencia.com/railes-about.html#ecosistema

## Límites
- No hay totales agregados de países ni medias de km por país.
- No hay desglose Cercanías/Media Distancia/Larga Distancia; solo el total Eurostat.
- No hay media de pasajeros por corredor.
- No hay accidentes/incidentes mensuales ni por corredor; sí serie anual ERA 2006–2024.
- No se incluyen Iryo ni Ouigo en el mapa de retrasos.
- Las cifras de AV son anuales; no son tiempo real. La serie total llega a 2024; 2025 no se usa por provisional.
- Comprobación automática mensual (día 5, 06:20 UTC); solo regenera, avisa por Telegram y purga si cambia el hash de los datos.
'''
(ROOT/"llms.txt").write_text(llms,encoding="utf-8")
print("seo ok",len(s),"urls",len(PAGES))
