# WAYAHEAD — NearMe OSINT

## 🐛 Bugs conocidos
- [ ] Las coordenadas de incendios desde RSS son aproximadas (por provincia). No hay geoposicionamiento real.
- [ ] El mapa carga los eventos pero el zoom inicial puede no mostrarlos todos (usar fitBounds)
- [ ] Sin indicador de carga/error cuando la API no responde
- [ ] Los botones de radio (50/200/500 km) no muestran cuál está activo

## 🔧 Técnico pendiente
- [ ] Añadir fitBounds() para que el mapa ajuste zoom automático a todos los eventos
- [ ] Agrupar marcadores (Leaflet.markercluster) cuando hay muchos
- [ ] Cachear respuesta API en el frontend (evitar recarga completa al cambiar radio)
- [ ] Poner indicador visual de fuente: color por tipo de evento (rojo=incendio, naranja=terremoto, etc.)

## 🔑 APIs gratuitas pendientes (si merece la pena)
- [ ] OpenAQ → calidad del aire (openaq.org, key gratuita)
- [ ] NASA FIRMS → incendios satélite (firms.modaps.eosdis.nasa.gov, requiere Earthdata login)
- [ ] AEMET → alertas meteorológicas reales (key ya obtenida, falta integrar endpoint correcto)

## 🚀 Fase 2 (cuando toque)
- [ ] Alertas personalizadas: "avísame si hay incendios a <15 km"
- [ ] Histórico: qué eventos han pasado en esta zona en las últimas 24h
- [ ] RSS local por municipio/provincia
- [ ] Eventos de transporte: RENFE, AENA (si tienen APIs abiertas)

## ✅ Lo que funciona ahora (sin tocar)
- Intelligence Hub: 24 fuentes, 9 países, pipeline 151s, LLM cache
- NearMe: mapa, API, PostgreSQL+PostGIS, SSL, cron cada 15min
- Incendios desde RSS del Hub
- Terremotos USGS
- AEMET conectada (alertas mock mientras no haya avisos reales)
