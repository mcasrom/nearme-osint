# Changelog — NearMe OSINT

Agregador de datos publicos geolocalizados en tiempo real, de codigo abierto.
De mas reciente a mas antiguo. Detalles tecnicos: [WAYAHEAD.md](WAYAHEAD.md).

## v0.11 — 1 Ago 2026 (sprint 37i)

- **Web Push real**: notificaciones push del navegador con la app cerrada. Suscripcion con claves VAPID, tablas `push_subscriptions`/`push_sent` (dedup por alerta+evento+nivel), endpoint `/api/push/*` protegido con JWT y cron cada 5 min (`scripts/send_push_alerts.py`) que envia cuando un evento coincide con tus alertas ancladas a ubicaciones guardadas.
- **Interfaz**: el modal de alertas explica que recibiras avisos aunque cierres la app (se comprueba cada 5 min); aviso toast al activar push.

## v0.10 — 1 Ago 2026 (sprints 37f-37h)

- **Visualizaciones de alto valor**: heatmap multi-fuente (peso por severidad y frescura), confidence score por evento (fiabilidad de fuente × frescura, badge "✓ NN%") y ranking de municipios + tendencias 24h en el panel.
- **i18n ES/EN**: toggle de idioma en el panel lateral (Español / English), persistente entre visitas.
- **Onboarding visual**: carrusel de 4 pasos con capturas de pantalla (explora el mapa, lee los iconos, filtra y localiza, instala y activa alertas), con i18n ES/EN.
- **Nuevas fuentes**: IGN sismología, indice UV (Open-Meteo) y energia (demanda REE + precio PVPC ESIOS). Total: 15 fuentes.
- **Revisión Product Hunt**: meta og/twitter en ingles con stack tecnico (Python/FastAPI, PostgreSQL+PostGIS, Leaflet); copy sin "proximamente"/"pronto" y aclarado que las alertas usan notificacion del navegador (no Web Push); nota SLA con i18n.
- **Contacto**: email de contacto pasa a `nearme@viajeinteligencia.com`.
- **Admin**: badge de Estado con deteccion de stale en el dashboard.
- **Fix datos obsoletos**: eventos con `expires_at` nulo se autocorrigen; feed DGT actualizado a DATEX II v3.7.
- **Operaciones**: healthcheck cada 5 min, fix del conflicto PM2/systemd en /admin, `/admin` sin cache del navegador.

## v0.9 — 30 Jul 2026 (sprints 29-32)

- **Privacidad y transparencia**: seccion de disclosure de datos, sin analytics/tracking/cookies, email para baja de cuenta.
- **Compartir en redes**: boton con Web Share API nativa + X, WhatsApp, Telegram, Bluesky, Mastodon.
- **Contador de visitas**: tabla sin IP ni user-agent, card en /admin.
- **Proteccion /admin** con password via `ADMIN_PASSWORD`.
- **Preparacion Product Hunt**: logo SVG 240x240, og-image en ingles, manifest bilingue, lanzamiento publicado (31 Jul).

## v0.8 — 30 Jul 2026 (sprints 23-28)

- **Bugfixes criticos** de colectores (AEMET, OpenAQ, Proteccion Civil, RENFE, db.py, MITECO).
- **Iconos emoji en mapa** con tamano/color por severidad, clusters con emoji dominante y badge de nivel critico, pulso en critical/alert.
- **Onboarding ampliado** a 5 pasos + secciones "Como leer el mapa" y "Fuentes de datos y metodologia".
- **Monitoreo**: tabla `collector_runs` persistente, /health enriquecido, /api/status, dashboard /admin, freshness badges (🟢<30min 🟠<2h 🔴≥2h), stale banner, semaforo por fuente.
- **Meteorologia continua**: AEMET emite evento `weather` por estacion (no solo alertas); OpenAQ activo con API key.
- **Health indicator**: barra de salud en la sidebar (Saludable / Degradado / Critico / Caido).
- **POI cercanos** (Overpass API): hospitales, farmacias, gasolineras, policia, bomberos... con proxy + cache en backend.

## v0.5 → v0.7 — 28 Jul 2026 (sprints 17-22)

- **Alertas personalizadas + registro**: alertas por tipo/radio/nivel, JWT + PostgreSQL, Browser Notification API, modal de configuracion, badge de coincidencias.
- **Seguridad y operaciones**: connection pooling, logging JSON, `.env.example`, bcrypt.
- **Refactor**: config centralizada, colectores paralelos (ThreadPoolExecutor) y async (httpx), /api/metrics.
- **PWA**: manifest, service worker con cache offline, instalable, auto-refresh del mapa cada 5 min, diseno responsive.

## v0.2 → v0.4 — 28-29 Jul 2026 (sprints 0-12)

- **MVP**: PostgreSQL+PostGIS, FastAPI + nginx + SSL, frontend Leaflet (busqueda texto, clic en mapa, GPS), cron cada 15 min.
- **Fuentes integradas**: AEMET (meteo + alertas), USGS (terremotos), IntelHub bridge (24 fuentes, 9 paises), RENFE (GTFS-RT), REE (demanda electrica), MITECO (calidad del aire), NASA FIRMS (incendios, sin key), DGT DATEX II (trafico), OpenAQ v3 (aire, 6 parametros).
- **Frontend visual**: colores por tipo, markerCluster, spinner, leyenda, mapa de calor para incendios, contador de alertas, limite dinamico de eventos por radio.

---
NearMe OSINT — software libre, sin SLA garantizado. Apoyo: [ko-fi.com/m_castillo](https://ko-fi.com/m_castillo)
