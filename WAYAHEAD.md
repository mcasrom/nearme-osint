# WAYAHEAD — NearMe OSINT (GeoPulse / GeoRisk Live)

**Objetivo**: Motor de OSINT geográfico en tiempo real — "¿Qué está pasando a mi alrededor ahora mismo?"
**Live**: https://nearme.viajeinteligencia.com
**GitHub**: https://github.com/mcasrom/nearme-osint
**Server**: `deploy@178.105.80.193` — PM2 `nearme-api` — Puerto 8100 — Nginx + SSL

---

## ✅ Hitos completados

### Sprint 0 — MVP (Jul 2026)
- [x] PostgreSQL + PostGIS
- [x] FastAPI backend + nginx proxy + SSL Let's Encrypt
- [x] Frontend Leaflet: búsqueda texto (Nominatim), clic en mapa, GPS
- [x] Cron `*/15 * * * *` + PM2

### Sprint 1 — Fuentes reales (AEMET + USGS)
- [x] AEMET: observaciones 10.600 estaciones, alertas temp/viento/lluvia
- [x] USGS: terremotos M2.5+ globales (GeoJSON)
- [x] Copernicus/GWIS: intentado, endpoints 404

### Sprint 2 — IntelHub bridge
- [x] Bridge a SQLite Intelligence Hub (24 fuentes, 9 países)
- [x] Scoring: ACTIVE_FIRE_SIGNALS, FALSE_POSITIVES, NOISE_WORDS
- [x] Extracción ubicación de 50+ ciudades españolas

### Sprint 3 — Deploy producción
- [x] rsync + deploy.sh + setup-server.sh
- [x] Nginx proxy + Let's Encrypt wildcard
- [x] PM2 proceso nearme-api

### Sprint 4 — Frontend rewrite
- [x] Búsqueda por texto vía Nominatim geocoding
- [x] Clic en mapa para fijar ubicación
- [x] Botón GPS como secundario (VPN issue)

### Sprint 5 — RENFE (trenes)
- [x] GTFS-RT protobuf (cercanías + AV/LD)
- [x] CSV estaciones para geolocalización (1.070 estaciones, 82% match)
- [x] 120+ retrasos detectados por pipeline

### Sprint 6 — REE (electricidad)
- [x] API `apidatos.ree.es` demanda-tiempo-real
- [x] Detección demanda >38GW (warning) / >42GW (alert)
- [x] ~9 eventos por pipeline

### Sprint 7 — MITECO calidad del aire
- [x] CSV ICA horario: `ica.miteco.es/datos/ica-ultima-hora.csv`
- [x] 620+ estaciones, 249 con ICA ≥ Regular
- [x] Índices: Buena/Regular/Desfavorable/Muy desfavorable

### Sprint 8 — Frontend visual v0.2 (28 Jul 2026)
- [x] Colores por tipo de evento (fire=rojo, air=verde, train=purple, etc.)
- [x] Leaflet.markerCluster para agrupar marcadores
- [x] Loading spinner animado
- [x] Leyenda visual de tipos activos
- [x] Stats por tipo con color y emoji

### Sprint 9 — NASA FIRMS (público, sin MAP_KEY) + DGT DATEX II (28 Jul 2026)
- [x] FIRMS: CSVs públicos de MODIS + VIIRS (sin necesidad de MAP_KEY)
- [x] 2.018 incendios activos en España por pipeline
- [x] DGT: DATEX II v3.6 desde `nap.dgt.es` (free, sin auth)
- [x] 1.242 incidencias de tráfico: cortes, obras, accidentes, retenciones
- [x] Geolocalización por coordenadas reales + provincia + municipio
- [x] Frontend actualizado con fuentes DGT y NASA FIRMS

### Sprint 10 — Puntos de calor + emojis por nivel emergencia (28 Jul 2026)
- [x] Marcadores de fuego: tamaño y color según FRP (gradiente amarillo→rojo→granate)
- [x] Emoji de nivel emergencia en sidebar: 🚨 critical, ⚠️ alert, ❗ warning, ℹ️ info
- [x] Badge de nivel (CRITICAL/ALERT/WARNING) en cada evento del listado
- [x] Mapa de calor (Leaflet.heat) toggle para incendios FIRMS
- [x] Marcadores críticos/alert con pulso animado
- [x] Contador de alertas activas en stats
- [x] Versión frontend v0.3

### Sprint 11 — OpenAQ v3 (29 Jul 2026)
- [x] Registrada cuenta OpenAQ con news@viajeinteligencia.com, verificada email

- [x] Colector v3: X-API-Key header, 6 parámetros (pm25, pm10, o3, no2, co, so2), 3 páginas c/u
- [x] ~980 eventos calidad aire / pipeline, ~77 alertas/warnings
- [x] Añadido OPENAQ_API_KEY a .env
- [x] Desplegado en producción

### Sprint 12 — Fix visibilidad incendios en mapa (29 Jul 2026)
- [x] Diagnosticado: frontend solo cargaba 300 eventos totales, FIRMS (~2.000 incendios) no entraba
- [x] Límite dinámico: 500/1000/2000 según radio de búsqueda (antes: 300 fijo)
- [x] Default API endpoint subido de 100→500, max 5000
- [x] ~446 incendios visibles en radio 200km desde Madrid (antes: 5)

### Sprint 17 — Alertas personalizadas + registro (28 Jul 2026)
- [x] "Avísame si hay incendios a <15 km" — alertas por tipo, radio y nivel
- [x] Sistema de registro/login de usuarios (JWT + PostgreSQL)
- [x] Alertas persisten en servidor asociadas a cada usuario
- [x] Modal de configuración con toggle y borrado (vía API autenticada)
- [x] Browser Notification API
- [x] Badge con contador de coincidencias en botón Alertas
- [x] Detección de eventos coincidentes en cada carga
- [x] Barra de auth en sidebar (login/registro/logout)
- [x] v0.4 → v0.5

### Sprint 18 — Seguridad, observabilidad y operaciones (28 Jul 2026)
- [x] Connection pooling con `psycopg2.pool.ThreadedConnectionPool` en db.py
- [x] Módulo `src/logging.py` con logging JSON estructurado
- [x] Eliminado `verify=False` en MITECO ICA collector
- [x] `.env` limpio sin credenciales reales + `.env.example` con placeholders

### Sprint 19 — Refactoring y configuración (28 Jul 2026)
- [x] `src/config.py` — constantes centralizadas (umbrales, URLs, timeouts, etc.)
- [x] Consolidar USGS duplicado — `src/collectors/ign/` eliminado, lógica integrada en `dgt/EarthquakesCollector`
- [x] Paralelizar colectores con `ThreadPoolExecutor` en `run.py`
- [x] Migrar a `httpx.AsyncClient` — `collect()` async en todos los colectores, `asyncio.gather()` en runner
- [x] Reemplazar PBKDF2 por bcrypt via `passlib` en auth de `server.py`
- [x] Módulo `src/metrics.py` — PipelineMetrics registra latencia y éxito por colector
- [x] Endpoint `/api/metrics` expone resumen de ejecuciones recientes

### Sprint 20 — PWA y responsividad (28 Jul 2026)
- [x] `frontend/manifest.json` — metadata PWA (name, icons, display standalone, theme color)
- [x] `frontend/sw.js` — service worker con cache offline (estrategia network-first para API, cache-first para assets estáticos)
- [x] Meta tags PWA en `index.html` (`manifest`, `apple-mobile-web-app-*`, `theme-color`, `viewport`)
- [x] Registro de service worker en JS
- [x] CSSResponsive — layouts columna en `<768px`, sidebar overlay en móvil, botones/tipografías adaptativos
- [x] Auto-refresh del mapa cada 5 minutos con toggle manual + countdown

### Sprint 21 — POI cercanos (28 Jul 2026)
- [x] Al hacer clic en el mapa o pulsar "📍 Cerca", busca POI mediante Overpass API (gratuita, OSM)
- [x] Categorías: hospital, clínica, farmacia, gasolinera, punto de recarga, policía, bomberos, refugio
- [x] Resultados mostrados en panel lateral + marcadores en el mapa
- [x] Distancia calculada con Haversine, ordenados por cercanía, top 5 por categoría

### Sprint 22 — POI en backend proxy + caché + estabilidad (28 Jul 2026)
- [x] Proxy Overpass en backend (`/api/poi`) — evita CORS/bloqueos red cliente
- [x] POI auto-trigger al hacer clic en el mapa (antes solo con botón "📍 Cerca")
- [x] Panel POI movido al inicio de la sidebar para visibilidad inmediata
- [x] Marcadores en verde, radio 5 km, query Overpass única
- [x] Caché en backend (2 min por ubicación) + mirror fallback Overpass
- [x] AbortController en frontend para clicks rápidos
- [x] Fix bcrypt 5.0.0 incompatible con passlib (downgrade a 4.0.1)
- [x] Fix dependencias faltantes: pyjwt, httpx, passlib, requests, gtfs-realtime-bindings
- [x] Fix crash loop PM2 (puerto 8100 ocupado por proceso zombie)
- [x] Versión frontend v0.8


---

## 📊 Pipeline actual (~6.000+ eventos/15min)
```
OpenAQ:       ~  980  calidad del aire (6 parámetros, v3 API)
NASA FIRMS:   ~2.018  incendios satélite España (MODIS+VIIRS)
DGT:          ~1.242  incidencias tráfico red estatal (DATEX II)
RENFE:         ~  749  retrasos tren geolocalizados (GTFS-RT)
MITECO:        ~  523  calidad del aire ICA (620 estaciones)
AEMET:         ~  330  weather continuo + alertas (10.600 estaciones)
IGN:           ~  227  sismología España (red 24/7, GeoJSON IGN)
UV:             ~   52  índice UV máx (52 capitales + Ceuta/Melilla)
Playas:        ~   37  bandera, oleaje, temp agua, medusas (Euskadi+Bizkaia)
IntelHub:      ~   30  incendios RSS (24 fuentes)
REE:           ~   21  demanda eléctrica alta
Energía:         ~   2  demanda Real + precio PVPC hora actual (ESIOS)
USGS:           ~    1  terremotos M2.5+ España (raros)
──────────────────────────────
TOTAL:        ~6.000+
```

---

### Sprint 23 — Bugfixes críticos (30 Jul 2026)
- [x] AEMET: `_fetch_observaciones()` sin `await` en llamada a `_aemet_get_data()` → nunca recolectaba datos meteorológicos
- [x] OpenAQ: faltaba `import asyncio` → `NameError` en `asyncio.gather()`
- [x] ProtecciónCivil: `requests.get()` bloqueante dentro de método async + `requests` no importado → `NameError`
- [x] RENFE: `requests.get()` en `_load_stations()` sin import → `NameError`
- [x] db.py `_event_to_row`: cuando `expires_at` es `None`, asignaba `datetime.now()` en vez de `now + TTL` → eventos sin expiración caducaban inmediatamente
- [x] server.py: `try/except` silencioso en `init_db()` ocultaba errores de inicialización de BD
- [x] MITECO: validación duplicada `indice < 3` (código muerto)
- [x] deploy.sh actualizado: rsync + PM2 restart con código local (incluye botón Ko-fi + sprints 22-23)

### Sprint 24 — Iconos emoji en mapa + mejoras (30 Jul 2026)
- [x] Reemplazo de `L.circleMarker` por `L.divIcon` con emoji del tipo de evento
- [x] Incendios: unificados al mismo sistema `L.divIcon` con tamaño y color según FRP
- [x] Tamaño de icono variable por severidad (critical=34px, alert=30px, warning/info=28px)
- [x] Pulso CSS glow en iconos critical/alert
- [x] Tooltip `title` en cada icono mostrando tipo y severidad
- [x] Cluster personalizado: emoji del tipo dominante + contador + color según nivel máximo de severidad
- [x] Cluster con badge de nivel crítico si contiene eventos critical/alert

### Sprint 25 — Onboarding, documentación y UI alertas (30 Jul 2026)
- [x] Onboarding ampliado a 5 pasos: explicación de iconos, bordes de severidad y sistema de alertas
- [x] Sidebar: nueva sección "Cómo leer el mapa" con leyenda completa de iconos, colores y pulsos
- [x] Sidebar: sección "Fuentes de datos y metodología" con tabla de 11 fuentes, TTL y ciclo de vida
- [x] Botón Alertas con pulso inicial si el usuario no lo ha explorado
- [x] Pedir permiso de notificación al crear la primera alerta
- [x] Ejemplos de uso en el modal de alertas
- [x] Añadidos tipos de evento faltantes a ICONS (port_incident, water_cut, telecom, etc.)
- [x] WAYAHEAD.md: añadida sección de Metodología

### Sprint 26 — Monitoreo, autochequeo y freshness (30 Jul 2026)
- [x] Tabla `collector_runs` con persistencia en PostgreSQL (cada ejecución del pipeline se guarda)
- [x] `PipelineMetrics.record_run()` escribe a DB además de in-memory
- [x] `/health` enriquecido: DB check, pipeline stats, último run
- [x] `/api/status` → estado por colector (último run, éxito, latencia, stats 24h)
- [x] `/api/status/runs` → últimas 50 ejecuciones
- [x] `/api/nearby` ahora incluye `server_ts` (timestamp del servidor)
- [x] `frontend/admin.html` → dashboard con cards, tabla de colectores, últimas ejecuciones
- [x] `#update-time` usa `server_ts` en vez de `Date()` local
- [x] Freshness badge en cada tarjeta de evento (🟢<30min, 🟠<2h, 🔴≥2h)
- [x] Sidebar: columna "Estado" con semáforo 🟢🟡🔴 por fuente, actualizado cada 60s
- [x] Stale banner: alerta cuando una fuente no se actualiza en >2x su intervalo
- [x] SW excluye `/api/nearby`, `/api/status`, `/admin` de cache PWA

### Sprint 27 — APIs en modo información continua (30 Jul 2026)
- [x] AEMET_API_KEY puesta en producción
- [x] OPENAQ_API_KEY puesta en producción
- [x] AEMET: ahora emite evento `weather` por estación con nivel info (muestra T, viento, lluvia siempre)
- [x] AEMET: cuando se superan umbrales, sube a warning/alert y emite subtipo específico (heatwave, wind, storm)
- [x] OpenAQ: ya emitía info siempre, solo faltaba API key — ahora activo
- [x] `weather` añadido a EVENT_TYPES, ICONS, TYPE_COLORS (🌡️ azul info, naranja/rojo alerta)
- [x] Metodología AEMET actualizada: no solo alertas, sino informe meteorológico continuo

### Sprint 28 — Health indicator del sistema (30 Jul 2026)
- [x] Barra de salud en sidebar (justo bajo el header) con indicador 🟢/🟡/🔴
- [x] Muestra estado general: Saludable / Degradado / Crítico / Caído
- [x] Contador de fuentes activas (ej: "Saludable (9/11 fuentes)")
- [x] Porcentaje de fuentes operativas con color según umbral (≥80% verde, ≥50% naranja, <50% rojo)
- [x] Se actualiza automáticamente cada 60s con el mismo ciclo de `refreshSourceStatus`

### Sprint 29 — Privacidad y transparencia para lanzamiento público (30 Jul 2026)
- [x] Nueva sección "Privacidad y datos" en sidebar con disclosure de datos recogidos
- [x] Explicación del sistema de alertas en el modal: "como funciona" (guardado en servidor, comparación local en navegador, contador + notificación)
- [x] Política clara: no compartir datos, no analytics, no tracking, sin cookies, sin IPs, sin geolocalización de usuario
- [x] Email de contacto para solicitar baja de cuenta

### Sprint 30 — Compartir en redes sociales (30 Jul 2026)
- [x] Botón 📤 en header (junto al toggle oscuro) con popup de plataformas
- [x] Texto dinámico: "🔥 N eventos activos cerca de lat, lon — NearMe OSINT"
- [x] Soporte Web Share API nativa en móvil (navigator.share)
- [x] Fallback con enlaces directos: 𝕏, WhatsApp, Telegram, Bluesky, Mastodon
- [x] Versión v0.9

### Sprint 31 — Contador de visitas + protección admin (30 Jul 2026)
- [x] Tabla `page_views` con solo `id SERIAL` + `viewed_at` — sin IP, sin user-agent, sin datos personales
- [x] `POST /api/visit` llamado una vez por carga de página desde `init()`
- [x] `GET /api/stats` → `{total_views, today_views, yesterday_views}`
- [x] Card "Visitas totales" en `/admin`
- [x] Limpieza automática de registros >60 días
- [x] `/admin` protegido con password vía `ADMIN_PASSWORD` en `.env` (sessionStorage, caduca al cerrar navegador)
- [x] Default en código = `CHANGE_ME_IN_PRODUCTION` — forzar cambio en producción
- [x] Fix: nginx proxy `/admin` al backend (no servirlo como estático)
- [x] Fix: `load_dotenv(override=True)` para que `.env` tenga prioridad sobre el entorno del proceso

### Sprint 32 — Preparación Product Hunt (30 Jul 2026)
- [x] OG meta tags actualizadas a inglés (title, description, twitter)
- [x] OG image (`og-image.svg`) con subtítulo en inglés: "Wildfires · Traffic · Weather · Earthquakes · Air Quality · Trains"
- [x] `manifest.json` descripción en inglés, categorías actualizadas
- [x] Meta description de la página en inglés
- [x] Logo SVG rediseñado a 240x240 (radar + data dots, escalable)

**Borrador primer comentario maker para PH:**
> Hey PH! I'm a solo dev in Spain — built NearMe because I was tired of checking 5 different apps to know if there's a wildfire, a train delay, or a weather alert near me. It pulls from NASA FIRMS, USGS, AEMET, DGT, RENFE and more, normalizes everything into one event schema (severity levels, TTL expiry, freshness badges), and renders it as a PWA you can install offline. Built with async Python collectors → PostGIS → FastAPI → Leaflet, with a TTL-based event lifecycle that auto-expires stale data. Currently Spain-only because that's where the open data APIs I integrated live — but the pipeline is source-agnostic, so adding another country is mostly "write a new collector." Open source, feedback and contributions welcome.

### Sprint 33 — Lanzamiento Product Hunt (31 Jul 2026)
- [x] Publicado en Product Hunt (hunting ~09:01 Madrid / 00:01 PDT)
- [x] Análisis de logs nginx post-lanzamiento: 23 visitas reales de 14 IPs, 5 con `?ref=producthunt`, bots Googlebot/Applebot
- [x] Análisis del propio tráfico con **GoAccess** sobre logs nginx filtrados (NearMe + `/api/` + `/admin`)
- [x] Reporte en `/analytics/` (basic auth) regenerado cada 10 min vía cron (`scripts/gen-analytics.sh`)
- [x] `analytics/` excluido del rsync de deploy

### Sprint 34 — Bugfix `/api/status/runs` (31 Jul 2026)
- [x] Endpoint leía `PipelineMetrics` en memoria, pero el pipeline corre en proceso cron separado → siempre vacío
- [x] Fix: `get_collector_runs(n)` en `src/db.py` lee `collector_runs` de PostgreSQL (1.329 runs)
- [x] `/api/status/runs` sirve ahora desde DB (verificado con curl)
- [x] Datos reales: USGS 19.5s, OpenAQ 14.0s, DGT 2.1s, AEMET 1.3s... por ejecución

### Sprint 35 — Nuevas fuentes demandadas por usuarios (31 Jul 2026)
- [x] Estudio de viabilidad: UV ✅, Terremotos IGN ✅, Energía ✅; descartados SAIH caudales, polen Palinocam, estado del mar (sin API JSON unificada)
- [x] **IGN Sismología** (`src/collectors/ign`): GeoJSON `terremotos.js` (var dias3/10/30), red nacional 24/7, ~227 terremotos España (15 min)
- [x] **Índice UV** (`src/collectors/uv`): Open-Meteo `uv_index_max` para 52 capitales + Ceuta/Melilla, escala OMS (60 min)
- [x] **Energía** (`src/collectors/energy`): demanda REE tiempo real (serie "Real") + precio PVPC vía ESIOS `archives/70` (15 min)
- [x] Config en `src/config.py`, registro en `run.py`, `event_type=energy` en `EVENT_TYPES`
- [x] Frontend: TYPE_COLORS/ICONS/typeOrder/SOURCE_INTERVALS + tabla de fuentes 12→15 + narrativa actualizada

## 📖 Metodología

### Arquitectura
```
[14 colectores async] → [Pipeline (asyncio.gather)] → [PostgreSQL+PostGIS] → [FastAPI] → [Frontend Leaflet]
```
Cada colector implementa `BaseCollector` con método `async collect()` que devuelve `list[Event]`. El pipeline ejecuta todos en paralelo cada ciclo (cron `*/15 * * * *`).

### Ciclo de vida de un evento
1. **Creación**: el colector obtiene datos de la fuente → `save_events_batch()` hace upsert por `(source, source_id)`
2. **Actualización**: en cada ciclo, si el evento sigue en la fuente, se actualiza su `expires_at` y `updated_at`
3. **Resolución automática**: si el evento deja de aparecer en la fuente, `resolve_events()` lo marca como `status=resolved`
4. **Expiración por TTL**: si la fuente no marca fin pero el evento supera su TTL (incendios=24h, tráfico=12h, etc.), `clean_expired()` lo elimina
5. **Expiración explícita**: si la fuente proporciona `end_time` (ej: DGT overallEndTime), se usa como `expires_at`

### Sistema de niveles
| Nivel | Color | Criterio |
|-------|-------|----------|
| info | azul | Evento informativo, sin riesgo |
| warning | amarillo | Precaución (ej: ICA≥3, temperatura≥35°C) |
| alert | naranja | Peligro (ej: FRP≥100MW, terremoto M≥5) |
| critical | rojo | Emergencia (severidad DGT "highest") |

### Freshness y stale detection
Cada evento lleva un badge de frescura basado en su `updated_at`:
- 🟢 `< 30 min` — recién actualizado
- 🟠 `30 min – 2 h` — desactualizándose
- 🔴 `> 2 h` — obsoleto

Por fuente, el sidebar muestra un semáforo que se actualiza cada 60s desde `/api/status`:
- 🟢 última ejecución ok y en plazo
- 🟡 última ejecución con error
- 🔴 sin datos en >2x el intervalo de la fuente

Si una fuente lleva >2 ciclos sin actualizar, aparece un banner de alerta en la sidebar.

### Fuentes de datos
| Fuente | Protocolo | Autenticación | Cobertura | Actualización |
|--------|-----------|---------------|-----------|---------------|
| NASA FIRMS | CSV público | Sin clave | España (MODIS+VIIRS) | 15 min |
| DGT DATEX II | XML v3.6 | Sin clave | Red estatal España | 5 min |
| AEMET | REST API | API Key JWT | España (10.600 estaciones, meteo continuo + alertas) | 15 min |
| RENFE | GTFS-RT (Protobuf) | Sin clave | Cercanías + AV/LD | 15 min |
| MITECO ICA | CSV horario | Sin clave | 620 estaciones España | 30 min |
| OpenAQ v3 | REST API | API Key | España (6 parámetros) | 30 min |
| USGS | GeoJSON | Sin clave | Global M2.5+ / España M1.5+ | 15 min |
| Protección Civil | CAP XML (AEMET) | API Key JWT | España | 30 min |
| REE | REST API | Sin clave | Peninsular | 15 min |
| IntelHub | RSS/HTML | Sin clave | 24 fuentes, 9 países | 10 min |
| Playas Euskadi | GeoJSON | Sin clave | País Vasco | 60 min |
| IGN Sismología | GeoJSON (`terremotos.js`) | Sin clave | España (red 24/7) | 15 min |
| Open-Meteo UV | REST API | Sin clave | 52 capitales + Ceuta/Melilla | 60 min |
| ESIOS (REE) | REST API | Sin clave | Península (precio PVPC) | 15 min |

### Monitoreo y autochequeo
El sistema cuenta con un subsistema de monitoreo basado en la tabla `collector_runs`:

- **Persistencia**: cada ejecución de colector se registra en PostgreSQL con collector, timestamp, éxito, latencia y número de eventos
- **Pipeline in-memory**: `PipelineMetrics` mantiene un buffer en memoria para consultas rápidas (últimas N ejecuciones)
- **Endpoints**:
  - `/health` — estado de BD, pipeline stats, último run
  - `/api/status` — último estado por colector + estadísticas 24h
  - `/api/status/runs?n=50` — últimas ejecuciones
  - `/api/metrics` — resumen agregado (compatible con herramientas externas)
- **Admin dashboard**: `/admin` — página HTML standalone con cards de resumen, tabla de colectores y últimas ejecuciones, auto-refresh cada 10s
- **Server timestamp**: `/api/nearby` devuelve `server_ts` para sincronización cliente-servidor

### PWA
- Service worker con estrategia network-first para `/api/*`, cache-first para assets estáticos
- `/api/nearby`, `/api/status` y `/admin` excluidos de cache (siempre fresh)
- Auto-refresh cada 5 minutos con indicador visual
- Offline: muestra datos cacheados con banner "📡 Sin conexión"

### Geolocalización
- **Precisa**: FIRMS (coordenadas satélite), DGT (coordenadas del incidente), AEMET (estaciones fijas)
- **Aproximada**: IntelHub (extracción por regex de provincia/ciudad), RENFE (estación origen)
- **Por defecto**: si no hay coordenadas, se usa el centro de la provincia o se descarta el evento

## 🔜 Próximos sprints

---

## 🐛 Bugs conocidos
- [x] ~~Eventos IntelHub nunca expiraban por `expires_at = EXCLUDED.expires_at` en upsert de db.py — cada refresh (10 min) recalculaba `now + TTL`, perpetuando eventos viejos~~ **(fix: `expires_at = events.expires_at` + expires_at basado en `published` del artículo)**
- [ ] ~20% paradas RENFE sin geolocalización (stop_id no encontrado en CSV estaciones)
- [ ] Coordenadas incendios RSS aproximadas (por provincia), no geoposicionamiento real

---

## ❌ Fuentes no accesibles
| Fuente | Motivo |
|--------|--------|
| AENA | Deniega acceso a datos de puntualidad (interés comercial) |
| Copernicus/GWIS | Endpoints devuelven 404 |
| OpenAQ | ~~Requiere API key~~ **(resuelto Sprint 11, ~980 eventos/pipe)** |
| Murcia COPLA | XML timeout desde Hetzner (red interna 112) |
| Galicia MeteoGalicia | API playas funciona pero falta lista pública de IDs |
| AEMET Playas | API funciona pero CSV de IDs (Playas_codigos.csv) devuelve 400 |
| Valencia estado mar | Solo HTML, sin API pública |
| Andalucía Oceanaria | Sin API pública |

---

## 🔑 Credenciales (en .env, gitignored)
- `.env.example` incluido con placeholders — nunca subir credenciales reales
- `AEMET_API_KEY`: JWT (exp ~Dic 2026) — configurar en servidor
- `DB_*`: PostgreSQL nearme / cambiar `DB_PASSWORD` en producción
- `JWT_SECRET`: HMAC para tokens de usuario — cambiar en producción

---

## 📁 Estructura
```
nearme-osint/
├── run.py                     # Pipeline orchestrator (14 colectores)
├── src/
│   ├── api/server.py          # FastAPI (frontend + API)
│   ├── db.py                  # PostgreSQL/PostGIS con connection pooling
│   ├── logging.py             # JSON logging module
│   ├── models.py              # Event dataclass + EVENT_TYPES
│   └── collectors/
│       ├── aemet/             # Meteorología (observaciones)
│       ├── dgt/               # DGT tráfico DATEX II + USGS terremotos + NASA FIRMS
│       ├── renfe/             # Retrasos tren (GTFS-RT + CSV)
│       ├── ree/               # Demanda eléctrica
│       ├── miteco/            # Calidad del aire (ICA)
│       ├── openaq/            # Calidad del aire (fallback)
│       ├── copernicus/        # Incendios (no funciona)
│       ├── proteccion_civil/  # Avisos meteorológicos
│       ├── intelhub_bridge.py # Incendios RSS
│       ├── playas/            # Estado playas Euskadi
│       ├── embalses/          # Nivel embalses (MITECO SAIH)
│       ├── ign/               # Sismología IGN (red 24/7)
│       ├── uv/                # Índice UV (Open-Meteo)
│       └── energy/            # Demanda REE + precio PVPC (ESIOS)
├── frontend/                  # Leaflet + MarkerCluster + vanilla JS
├── deploy.sh                  # rsync + PM2
├── setup-server.sh            # Provisioning servidor
├── WAYAHEAD.md                # Este archivo
├── requirements.txt           # Dependencias Python
├── .env.example               # Template de credenciales (gitignored)
└── .env                       # Credenciales reales (gitignored)
```

---

## ⏳ Pendiente Ko-fi
- [ ] Crear 2 tiers de membresía mensual (€3 Colaborador, €10 Mecenas)
- [ ] Subir meta de €20 → €50 con desglose (electricidad + dominio + APIs)
- [ ] Usar feed de Ko-fi para anunciar deploys nuevos
- [ ] Widget en frontend muestre barra de progreso de la meta
- [ ] Separar CTA por proyecto en el About de Ko-fi

### Sprint 36 — README público (31 Jul 2026)
- [x] README.md completo en español: demo CTA, 15 fuentes, ciclo de vida, severidad, stack, API, setup local, contribución, privacidad, roadmap, Ko-fi
- [x] Commiteado y pusheado a origin/main (e0ad3e8). Deploy sigue por rsync.
- [ ] NOTA: el servidor local no tiene acceso SSH a nearme-osint (solo intelligence-hub vía git@github.com-ikm) — los push se hacen desde el desktop vía clone HTTPS.

### Sprint 37 — Ideas de crecimiento gratuitas (análisis externo, 31 Jul 2026)
Fuente: outreach de Viberank (cold email con fin comercial → NO pagar sponsorship $4.99, ofrece "security audits" = red flag). Ideas verificadas y aplicables gratis:

- [x] **Anonymous-first UX** (mapa+GPS sin login ya; alertas usables sin login, pulse en boton Alertas para todos): mostrar el mapa con geolocalización sin login; diferir auth solo a guardar ubicación o crear alerta (PRIORIDAD ALTA)
- [x] **Guest mode** (ubicaciones y alertas en localStorage `nearme_guest_locations`/`nearme_guest_alerts`, auto-migracion a cloud en login/registro via `migrateGuestData`, toast feedback, note visual en modal y barra): ubicaciones guardadas en localStorage que auto-migran a cloud al registrarse (PRIORIDAD ALTA)
- [ ] Onboarding 30s con coachmarks: radio, filtros, leyenda severidad, freshness badge
- [ ] Permalinks por evento para compartir (viralidad orgánica)
- [ ] Web Push value-first: "Recibe alertas críticas en tu zona" en vez del diálogo crudo del navegador
- [ ] Roadmap geográfico en la UI: "Próximamente: Portugal, sur de Francia" (anticipación, gratis)
- [ ] Sacar la tabla de fuentes del modal de ayuda a la landing (mejor trust signal del producto)
- [ ] Transparencia de monetización visible (Ko-fi / "sostenido por la comunidad")
- [ ] Añadir `charset=utf-8` al content-type en nginx (el HTML ya es UTF-8 correcto; solo elimina ambigüedad para crawlers)

NOTAS de verificación:
- El "bug crítico de encoding" (mojibake â/ðŸ”) del análisis es FALSO POSITIVO de su crawler: el HTML servido tiene UTF-8 correcto (62 emojis reales, 0 bytes corruptos, meta charset línea 5).
- UX decision: registro/login debe pasar a segundo plano (guest-first), solo requerido al persistir ubicaciones/alertas.

### Sprint 37e — Research mercado: visualizaciones de alto valor usuario (1 Ago 2026)
- Busqueda web (mapas de incidentes en tiempo real, dashboards geo, 2026): features mas demandadas = heatmap de hotspots, score de riesgo por zona, timeline/playback historico, confidence/fiabilidad de eventos, Safe Zones + push, ranking/tendencias por region, rutas afectadas (DGT/RENFE), embed/API publica, export CSV/PDF.
- Decision del usuario: implementar **1) Heatmap**, **4) Confidence/fiabilidad** y **7) Ranking/tendencias** (mayor retorno por esfuerzo con la infra existente). Los demas (score de riesgo por zona, timeline playback, safe zones + web push, rutas afectadas, embed, export) quedan en backlog.

## Sprint 37g — i18n ES/EN + review feedback + badge Estado stale (1 Ago 2026)
- **Review (4 comentarios)**: 1) Ko-fi duplicado (elmapayelcodigo vs m_castillo) -> UNIFICADO a m_castillo (`afec486`). 2) Columna "Estado" del admin "solo —": FALSO POSITIVO (verificado en vivo: las 15 fuentes muestran Ok, refresh 10s) -> mejora opcional aplicada: badge Ok/Stale/Error con stale detection. 3) Sin hreflang/EN: quick win aplicado -> toggle ES/EN. 4) Atribución a "El Mapa y El Código" (proyecto blog ajeno): CORREGIDO, autor = mcasrom con link al perfil.
- **i18n ES/EN quick win** (`1d3b4c7`): diccionario I18N + toggle en el sidebar (persistente, nearme_lang), traduce tagline, buscador, login, boton calor, health y seccion Sobre. data-i18n en elementos + literales dinamicos (Mapa de calor/Desactivar/Iniciar sesion/Ubicaciones guardadas/Cargando eventos). applyLang re-renderiza updateAuthUI tras guardar el lang.
- **sw.js CACHE_NAME -> nearme-v3**: los clientes PWA con cacheFirst servian HTML viejo (por eso el usuario seguia viendo "El Mapa y El Código"); el bump fuerza descartar la cache y ver las versiones nuevas (recargar 1-2 veces).
- **Badge Estado con stale detection** (admin.html): badge Ok/Stale/Error; interval por nombre mostrado (antes el map usaba claves minúsculas que nunca casaban -> siempre 60); Stale = last_success && edad > 2x interval. Verificado con Playwright inyectando DGT con 30 min (interval 5) -> muestra Stale.
- Commits: `afec486`, `1d3b4c7`.

## Sprint 37h — Cierre review Product Hunt + CHANGELOG + onboarding visual + Telegram (1 Ago 2026)
- **Review PH (6 comentarios "mejorable")**: 3 aplicados ya en 37g (ko-fi unificado, autor mcasrom, i18n) y ahora los 3 restantes:
  1) **Meta og/twitter/description**: anade "open-source" + stack (Python/FastAPI, PostgreSQL+PostGIS, Leaflet) como hook tecnico (commit `4138a0a`).
  2) **Copy sin promesas falsas**: quitados "proximamente" (alertas email) y "pronto" (notificaciones real-time); suavizado "alertas push" de la PWA — NO hay Web Push real (verificado: sin pushManager/VAPID), solo notificaciones de navegador.
  3) **Nota SLA** con i18n ES/EN: "Codigo abierto en GitHub. Sin SLA garantizado: proyecto personal/educativo, puede haber interrupciones."
- **Email de contacto** (`a5de9c9`): creado `nearme@viajeinteligencia.com` y sustituido `news@` en index.html (Contacto + Control), README y setup-server.sh. En intelligence-hub (`ca94987`): template de briefings + deploy script. Históricos output/*.html sin tocar.
- **CHANGELOG publico** (`2a163c1`): `CHANGELOG.md` en raiz (historia v0.2->v0.10) con symlink `frontend/CHANGELOG.md` servido en `/CHANGELOG.md`; link "Cambios/Changelog" (i18n) en Sobre tras Codigo; version frontend -> v0.10 (1 Ago 2026); sw -> nearme-v5.
- **Onboarding visual 4 pasos** (`5db0788`): showOnboarding pasa de texto a carrusel con capturas de `frontend/ph/` (01-map-general, 06-event-clusters, 03-poi-filters, 04-mobile-pwa), navegacion prev/next + dots, "Empezar" en ultimo paso y "Saltar"; textos con i18n ES/EN (claves ob_*) renderizados desde I18N[currentLang()]; se conserva localStorage nearme_onboarding; sw -> nearme-v6. Verificado con Playwright.
- **Telegram healthcheck** (`c285b7b`, `90c026e`): bot `@nearme_status_bot` (TOKEN + chat_id 47652516 en .env gitignored). healthcheck.sh alerta por Telegram SOLO en cambio de estado up->down (dedup) + aviso [RECOVERED]; estado en logs/healthcheck.state. Fixes en test: telegram_send dentro de 'if !' (un fallo de curl abortaba el script bajo set -e y rompia el dedup) y CDIR robusto via `git rev-parse --show-toplevel` (independiente de la ruta de invocacion). Verificado end-to-end con Telegram real.
- Commits: `4138a0a`, `a5de9c9`, `2a163c1`, `5db0788`, `c285b7b`, `90c026e`.

## Sprint 37i — Web Push real (1 Ago 2026)
- **Contexto**: en 37h se aclaró que las alertas eran SOLO notificación de navegador (sin Web Push). Este sprint añade **Web Push real** (pushManager + VAPID + service worker): avisos aunque la app esté cerrada.
- **Backend**: claves VAPID en `.env` (gitignored, round-trip ECDSA verificado). `src/db.py`: tablas `push_subscriptions` (endpoint UNIQUE, p256dh, auth) y `push_sent` (UNIQUE user_id,alert_id,event_id,level; dedup) + `save/delete/get_push_subscription`, `get_push_users` (usuarios con alertas activas), `push_sent_exists/mark_push_sent/prune_push_sent`. `src/api/server.py`: `GET /api/push/vapid-key`, `POST /api/push/subscribe`, `POST /api/push/unsubscribe`, todos con JWT (401 sin auth). `scripts/send_push_alerts.py` (cron `*/5`): agrupa por (alerta, ubicación), 1 push/zona, dedup vía push_sent, limpia suscripciones 404/410.
- **Frontend** (sw -> `nearme-v7`): `sw.js` handlers `push` (showNotification con icono `/icon-256.png`) y `notificationclick` (focus/navigate). `index.html`: helpers `urlBase64ToUint8Array` + `setupPushSubscription()` llamado tras login/registro (`doAuth`), al cargar con sesión (`checkAuth`) y al crear una alerta (tras otorgar permiso); toast "Push activado"; modal de alertas explica que recibirás avisos con la app cerrada (cada 5 min). Sin prompt intrusivo: solo si permiso ya concedido o al crear alerta.
- **Verificación**: Playwright headless valida registro→login→suscripción simulada→`/api/push/subscribe`→Postgres; luego envío REAL con claves EC válidas: `[SEND] user=17 grupos=1`, payload cifrado `aes128gcm` (437 B), cabecera VAPID con JWT ES256/P-256 **firma verificada**, `sub=mailto:nearme@viajeinteligencia.com`, TTL 0. El handshake real navegador→FCM no es testeable en headless (limitación del navegador, API estándar).
- **Ops**: `pywebpush` añadido a `requirements.txt`; `init_db()` ejecutado en Postgres (tablas push creadas); cron instalado: `*/5 * * * * cd /home/deploy/nearme-osint && venv/bin/python scripts/send_push_alerts.py >> logs/push.log 2>&1`; CHANGELOG v0.11. Residuo `nearme.db` (sqlite 0 B) sacado del repo.
- Commit: `0e744ea`.

## Research 37j — Features demandadas y tendencias en RRSS para mapas OSINT de incidencias (web 2026)
Ronda de investigacion sobre lo que piden los usuarios y hacia donde va la categoria "mapas de incidencias/OSINT en tiempo real". Senales de Reddit (r/OSINT), Product Hunt, prensa (Xataka, Cinco Dias, Infobae) y competidores open-source con traccion en 2026.

### Competidores / senales del mercado (2026)
- **OSIRIS** (osirislive.app, open-source): capas multi-dominio (aviation, maritime, CCTV, seismic, fire, weather, space, cyber, conflict) con toggle independiente; renderizado GPU/WebGL (60fps con miles de entidades); carga lazy por viewport (-75% peticiones); recon toolkit (DNS, WHOIS, SSL, CVE); 25+ streams de noticias en el mapa; atajos de teclado; self-hostable y sin API keys en lo basico.
- **ShadowBroker** (open-source, Next.js+FastAPI): 15+ fuentes en un mapa oscuro unificado (ADS-B, AIS, satelites, USGS, ACLED, CCTV, spoofing GPS, geopolitica). Cobertura en prensa espanola 2026 (Ecosistema Startup, Descubre.ai, AdminSistemas). "Desplegar sin codigo" como argumento.
- **Map Alerts** (iOS/Android, mapalerts.org): canales publicos de **Telegram geolocalizados en un mapa** ("Telegram on a map"). Nicho: analistas OSINT, defensa civil, trafico y clima. TENDENCIA CLAVE: Telegram/WhatsApp como canal de distribucion de avisos, no solo push del navegador.
- **Real-Time Alert** (app de seguridad): reportes comunitarios geolocalizados (activos 3h, notifican a <300 ft); **AI-verified** para reducir falsos positivos; confidence score 0-100 (a estrenar otono 2026); safe zones (hasta 6); "Mark Me Safe" (avisa a 10 contactos en 1 tap); safety analytics por barrio (0-100); export PDF/CSV; ruta "Navigate Safely". Lema: "Built for real threats, not false alarms".
- **Radarix / SituationRoom / MonitorTheSituation**: crisis maps en vivo (aeronaves, barcos, NOTAMs, ciber, cortes de internet, video en directo).
- **Felt** (GIS cloud): Felt AI + MCP server, export GeoJSON/GeoPackage/GeoTIFF, embed de mapas, Field App movil.
- **Caso espanol ciudadano**: la prensa generalista engancha mucho con "mapa DGT en vivo" (Xataka 17-jul, Cinco Dias 13-jul, Infobae con borrascas) y AEMET. Uso que pide el publico: "mira tu ruta antes de salir" y avisos por carretera concreta.

### Demandas explicitas de usuarios (r/OSINT 2025-26 + informes 2026)
1. **Verificacion y ruido**: distinguir contenido real vs AI-generado; reducir falsos positivos; confidence score (valida nuestro `event_confidence` de 37f).
2. **Correlacion entre plataformas** y supervivencia de datos historicos (anti-scraping, borrados, retencion) -> archivado/historial/playback.
3. **Sobrecarga de informacion** -> filtros, IA asistida, resumenes.
4. **Canales sociales**: Telegram/WhatsApp bots como canal de avisos; comunidades (Reddit) como motor de adopcion.
5. **Capas multi-dominio** activables y rendimiento con miles de markers (GPU/lazy).
6. **Open-source + self-hostable** como diferenciador de confianza.

### Backlog propuesto para NearMe (priorizado)
Corto plazo / alta demanda (quick wins con la infra actual):
- [x] **Alertas por Telegram al usuario** (sprint 37k): `@nearme_status_bot` + `/nearme CODIGO` vincula el chat del usuario; cuando una alerta coincide, el bot le escribe (reutiliza el healthcheck). Complementa el Web Push con el canal mas demandado.
- [ ] **Reportes ciudadanos** (crowdsourcing): reportar incidencia geolocalizada (foto opcional), ventana activa ~3h, capa separada con su propia fuente; diferenciador "AI-verified" si se anade confianza.
- [ ] **Rutas afectadas / alerta en ruta**: linea entre ubicaciones guardadas + radio; avisar si un evento corta la ruta (PostGIS lo soporta). Matchea el uso espanol "mira tu ruta antes de salir" (DGT).
- [ ] **Export CSV / PDF / GeoJSON** de la lista de eventos de una zona.
- [ ] **Widget embed + URLs compartibles** (iframe) — demanda de Felt/PH y util para prensa.
Medio plazo:
- [ ] **Timeline/playback** (backlog 37e): "historial hasta 1 ano" y "track patterns" son demandas explicitas.
- [ ] **Score de riesgo por zona** (37e) — Real-Time Alert lo monetiza como safety analytics.
- [ ] **Quiet hours / dedup configurable** y radio/ventana temporal por alerta.
- [ ] **Capas extra opcionales**: CCTV publico, sismico en vivo (ya tenemos IGN), streams de video.
Largo plazo / estrategico:
- [ ] Resumen IA por zona/incidencia (verificacion asistida), archivo historico, colaboracion/comentarios.
- **Nota de posicionamiento**: la categoria valora "open-source + self-hostable + verified/no-false-alarms + Telegram". NearMe ya tiene 15 fuentes + confidence + Web Push; el gap mas visible vs competencia es Telegram y reportes ciudadanos.

## Sprint 37k — Alertas por Telegram al usuario (1 Ago 2026)
- **Contexto**: la research 37j senalaba Telegram/WhatsApp como el canal de distribucion de avisos mas demandado (Map Alerts: "Telegram on a map"). Reutilizamos `@nearme_status_bot` (que ya usaba el healthcheck) para avisar al usuario.
- **Backend**: `src/db.py` — migracion de `push_sent` anadiendo `channel` ('push'|'telegram') con dedup UNIQUE (user_id, alert_id, event_id, level, channel); tablas `telegram_links` (codigo 8 chars A-Z0-9, valido 10 min, un solo uso, borra links previos del usuario) y `telegram_subscriptions` (chat_id UNIQUE + UNIQUE user_id); funciones create/consume/save/get/delete (save hace delete+insert: Postgres no permite doble ON CONFLICT). `init_db()` idempotente, ejecutado. `src/api/server.py`: `GET /api/telegram/bot`, `GET /api/telegram/status`, `POST /api/telegram/link`, `POST /api/telegram/unlink` (JWT).
- **Bot** (`scripts/telegram_bot.py`, PM2 `telegram-bot`): long-polling con getUpdates (offset persistido en `logs/telegram_bot.offset`, 409->reset a -1), comandos `/start`, `/help`, `/nearme <CODIGO>`, `/unlink`; `process_update` aislado para tests; robusto a errores de red (RequestException -> sleep, no muere). No colisiona con el healthcheck (solo usa sendMessage, nunca getUpdates).
- **Envio** (`scripts/send_push_alerts.py`, cron `*/5`): ahora envia Web Push + Telegram en una pasada; dedup por canal via `get_sent_keys(user_id, channel)` y `mark_push_sent(channel)`; mensajes HTML con emojis agrupados por (alerta, ubicacion); stats `push_grupos`/`tg_grupos`; maneja 403/400 de Telegram sin crashear.
- **Frontend**: bloque "Alertas por Telegram" en el modal de alertas (solo logueado): estado enlazado/desenlazado, boton generar codigo (instrucciones `/nearme CODIGO` + handle del bot), boton desvincular; i18n ES/EN.
- **Verificacion E2E (Playwright headless)**: registro->modal->generar codigo->consumo via `process_update` (chat real del admin)->recarga->"Enlazado a mcasrom"->desvincular->vuelve el boton. Envio real de alerta a Telegram verificado (`tg_grupos=1`, mensaje recibido en el chat 47652516). Datos de test limpiados (usuarios tgtest*/uitest*).
- **Ops**: proceso PM2 `telegram-bot` arrancado y guardado (`pm2 save`); CHANGELOG v0.12.

## Ops 37m — Telegram IPv4 + monitor de latencia (1 Ago 2026)
- **Problema**: 4 timeouts del bot contra api.telegram.org (14:58-15:07 UTC). Diagnostico: DNS resuelve IPv6 (`2001:67c:4e8:f004::9`), ruta IPv6 inestable, `requests` la intenta primero -> 24.25 s (agota timeout 30). curl (v4+v6) iba bien; forzar IPv4 -> 0.23 s.
- **Fix**: `urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET` al inicio de `telegram_bot.py` y `send_push_alerts.py`. Bot reiniciado (getMe 0.10 s).
- **Monitor**: `scripts/check_telegram_api.py` (3 peticiones, log a `logs/telegram_api.log`) + cron `*/5`. Salud inicial: OK avg_ttfb=0.21s.
- Commit: `19bc6a9`.

## Fix 37l — RENFE alta velocidad: filtrar retrasos por fecha de servicio (1 Ago 2026)
- **Problema**: avisos "vivos" pero con dato de ayer (usuario: "¿está actualizado? parece del hace días"). El feed `trip_updates_LD.pb` de RENFE sirve trip_updates de la fecha de servicio anterior (observado 14:40 UTC: 173 de 250 con fecha 07-31; 37 con retraso >5 min, p.ej. `Trip: 0514022026-07-31` +30 min en CUENCA-FERNANDO ZÓBEL). El colector ingería todo retraso >=10 min sin mirar la fecha -> re-creaba/reactualizaba retrasos de trenes de ayer cada ciclo 15 min (updated_at reciente -> confianza 94% enganosa).
- **Fix** (`src/collectors/renfe/__init__.py`): en el feed LD se extrae la fecha de servicio del trip_id (sufijo `YYYY-MM-DD`) y se descartan los que no correspondan a hoy (Europe/Madrid). Cercanias no lleva fecha en el trip_id (intacto). Verificado contra feed live: 18 retrasos LD y 0 con fecha != hoy.
- **Limpieza BD**: 39 eventos renfe alta_velocidad con fecha != hoy marcados `expired` (quedan 21 activos de hoy).
- Commit: `18a4a29`.

## Fix 37n — Sismo Murcia: validación, radio de alerta y confirmación envío Telegram (2 Ago 2026)
- **Contexto**: el usuario reportó un sismo en Murcia (M3.9 NW LIBRILLA.MU) que "no veía" en la app y del que "no saltaba" alerta en Telegram.
- **Validación (sin cambios de código)**: el evento sí estaba y se veía (BD id 1180634, creado 10:15 UTC, sismo 09:59:28 UTC del 02-08; IGN lo revisó de M4.1→M3.9). No visible para el usuario por pestaña sin recargar / filtros / radio del mapa — no era un bug.
- **Causa raíz de la alerta no enviada**: la alerta del usuario (id 3) tenía `radius_km=15` y el sismo estaba a ~23,4 km de su ubicación guardada (Murcia 37.9348,-1.1131). El matcher hace `get_events_nearby(loc, radius)` → no entraba; `push.log` mostraba `push_grupos=0 tg_grupos=0` (el pipeline iba bien, simplemente no había coincidencia). Radio subido a **30 km** (`UPDATE alerts SET radius_km=30 WHERE id=3`).
- **Confirmación de envío**: tras subir el radio, el ciclo manual de `send_push_alerts.py` envió el aviso por push y Telegram (`tg_grupos=1`); `push_sent` registra `(user 3, alert 3, event 1180634, warning, telegram)` + 4 eventos DGT. El aviso de Telegram llegó **agrupado en un único mensaje "5 eventos cerca de..."** (terremoto + 4 incidencias DGT) — fácil de pasar por alto.
- **Revisión IGN en caliente**: IGN revisa magnitudes y ubicación; el mismo `source_id` (`ign_es2026paacq`) se re-colecta y **se actualiza in-place** (M3.9 NW LIBRILLA → M4.1 SE PLIEGO.MU, coordenadas movidas, updated_at 11:15 UTC). Comportamiento normal de la fuente, el upsert por (source, source_id) lo maneja.
- **Canal Telegram sano**: verificado con sendMessage directo al chat 47652516 (200 OK, message_id 25). Los "Read timed out" del bot en getUpdates son ruido del long-polling (timeout HTTP 30 s = timeout del long-poll) y no afectan al envío de alertas (sendMessage).

## Sprint 37f — Implementados: Heatmap multi-fuente, Confidence, Ranking/Tendencias (1 Ago 2026)
- **Heatmap multi-fuente**: ya no solo incendios. Peso = severidad (critical 1.0 / alert 0.75 / warning 0.5 / info 0.25) x frescura (decay por antiguedad de updated_at); fuegos nasa_firms siguen usando FRP. Usa los eventos ya cargados (allEvents), fallback a fetch de /api/nearby.
- **Confidence score (0-100)**: `event_confidence()` en db.py = fiabilidad base de la fuente (SOURCE_CONFIDENCE en config.py: dgt/renfe/aemet/ign 92-95, satelites 85-90, intelhub 60) x factor de frescura de updated_at. Expuesto en /api/nearby como campo `confidence` por evento; badge "✓ NN%" en las cards del sidebar y en los popups de los marcadores.
- **Ranking/Tendencias**: nuevo endpoint `GET /api/rankings?lat&lon&radius&limit` -> `top` (top municipios por nº de incidencias activas en el radio, con nivel max) + `trends` (serie 24h de eventos creados + hoy vs ayer en Europe/Madrid). Panel en el sidebar con barras de top zonas y tendencias; se refresca con loadRankings() tras cada loadEvents().
- Verificado con Playwright headless: 0 errores de consola, 414 eventos con confidence, heatmap renderizado (canvas), panel de rankings visible (Madrid 19, Getafe 4, ...).
- Commits: `0c1dfd9` (push a origin/main desde 3066082).


### Sprint 37d — Fix datos obsoletos / feed DGT (1 Ago 2026)
- **Problema reportado**: incidencias DGT del 28JUL (vehicleObstruction RM-C19, A-30 Ulea, etc.) visibles dias despues. Innumerables eventos obsoletos.
- **Causa raiz 1 (datos eternos)**: 4.761 eventos activos con `expires_at NULL` (dgt 2905, miteco 1450, aemet 406), todos sin actualizar >24h. La consulta `(expires_at IS NULL OR expires_at > NOW())` los mostraba para siempre. El upsert usaba `expires_at = events.expires_at` (mantenia el NULL original) e ignoraba el TTL calculado.
  - **Fix**: `src/db.py` upsert -> `expires_at = EXCLUDED.expires_at` (2 sitios: `save_event`, `save_events_batch`); consulta endurecida -> `(expires_at > NOW() OR (expires_at IS NULL AND updated_at > NOW() - INTERVAL '2 hours'))`. Nuevo `scripts/backfill_expiry.py` que asigna `expires_at = updated_at + TTL(event_type)` a los NULLs y limpia expirados. Ejecutado: 4.761 asignados, 4.941 borrados.
- **Causa raiz 2 (DGT sin datos actuales)**: el feed `datex2_v36.xml` devuelve HTTP 301 hacia `datex2_v37.xml` y el colector NO seguia redirects (httpx sin `follow_redirects`) -> 0 incidencias desde hacia dias, los eventos viejos quedaban huérfanos.
  - **Fix**: `src/config.py` y `src/collectors/dgt/__init__.py` -> URL v37 + `follow_redirects=True`. El parser v36 es compatible con v37 (mismos prefijos sit/com/loc/lse). Verificado: 726 incidencias parseadas (203 vehicleObstruction), 662 activas en DB con created_at de HOY.
- **Verificado**: `/api/nearby` Murcia -> 42 dgt actuales (0 viejos), evento RM-C19 eliminado, 0 NULLs activos globales. Ley aplicada: ningun evento sin expiracion puede vivir mas que su TTL desde su ultima confirmacion.

## OPERACIONES — Infraestructura (31 Jul 2026)
- **Fuente de verdad unica**: GitHub `mcasrom/nearme-osint`. El servidor `deploy@178.105.80.193` edita el working tree (= produccion, nginx sirve desde `frontend/`), y ahora puede **pushear directo** con la deploy key write `~/.ssh/nearme-deploy-key` (host alias `github.com-nearme`).
- Flujo: editar en el servidor → `git add -A && git commit && git push origin main`. El historial git del servidor fue reconciliado con origin (commit `c3139c8`); sin clones de desktop ni patches.
- `deploy.sh` del repo es para despliegue desde el desktop (push + rsync); con el flujo servidor-directo ya no es necesario salvo para provisionar una maquina nueva.
- Cron del servidor: `*/15` run.py (colectores), `*/10` gen-analytics.sh. `analytics/` es runtime y esta en `.gitignore`.
- Otros repos con deploy keys write en este servidor: `intelligence-hub` (alias `github.com-ih`, key `~/.ssh/ih-deploy-key`). La vieja `github-data-removal` esta muerta (Permission denied); `ikm-deploy-key` sigue como read-only de `mcasrom/ikm`.

### Sprint 37b — Healthcheck NearMe (31 Jul 2026)
- [x] **Healthcheck propio**: `/health` ya existia y es completo (db + pipeline + events 24h + last_collector_run). Nuevo `scripts/healthcheck.sh` que valida status=ok, database=connected y freshness <45 min; alerta por Telegram (condicional a `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` en `.env`); cron `*/5` con log en `logs/healthcheck.log` (ignorado por git).
- [ ] Opcional: monitor externo **UptimeRobot** (free, checks 5 min) apuntando a `https://nearme.viajeinteligencia.com/health` — requiere crear cuenta, no lo hice.
- NOTA: el mail de Uptiqr (uptiqr.com) era cold outreach; su dato "11-feed" es incorrecto (somos 15 fuentes). Rechazado el vendor, adoptada la idea gratis.

### Sprint 37c — Fix Quirks Mode /admin + conflicto de procesos (31 Jul 2026)
- **Problema**: warning "Quirks Mode" en `/admin` (nearme.viajeinteligencia.com). Causa raíz: la API se gestionaba DUPLICADA — unit systemd `nearme-osint-api.service` (uvicorn `127.0.0.1:8100`) Y app PM2 `nearme-api` (uvicorn `0.0.0.0:8100`) peleándose por el puerto 8100 (PM2 acumulaba 20k+ reinicios). Las respuestas eran inconsistentes (a veces 405/JSON, a veces HTML), de ahi el warning del navegador.
- **Fix**: deshabilitado/parado el unit systemd (`systemctl disable nearme-osint-api`); PM2 es el gestor estandar del servidor (13 apps). App PM2 `nearme-api` (id 39) re-registrada correctamente con el python del venv: `/home/deploy/nearme-osint/venv/bin/python3 -m uvicorn src.api.server:app --host 127.0.0.1 --port 8100` (cwd `/home/deploy/nearme-osint`). IMPORTANTE: si se usa `python3 venv/bin/uvicorn` directo, PM2 lo lanza con el python del SISTEMA y falla `ModuleNotFoundError: dotenv` → siempre `venv/bin/python3 -m uvicorn`.
- **Gestionar NearMe**: `pm2 restart nearme-api` / `pm2 logs nearme-api` / `pm2 save`. PUERTO 8100 NO expuesto en firewall (solo nginx proxya via 443).
- **Epilogo (mismo dia)**: el usuario segua viendo "Quirks Mode" en /admin con el servidor sano — era CACHE DEL NAVEGADOR de un 502 viejo (HTML sin doctype). Fix en nginx: `location /admin` anade `Cache-Control: no-store, no-cache, must-revalidate` + `Pragma: no-cache`. Verificado con Chromium headless: GET /admin = 200, `<!DOCTYPE html>`, panel renderiza. /admin se sirve con `text/html; charset=utf-8` (charset ya cubierto para el backend).

## Sprint 38 — Respuesta a la valoración pública: permalinks, Web Push value-first y prueba social (4 Ago 2026)
- **Contexto**: valoración externa de la app con 5 puntos "mejorables". Verificado que 3 ya estaban resueltos en `0a5548d` (enlace privacidad NO roto, i18n ES/EN, onboarding visual). Se implementaron las opciones recomendadas de mayor prioridad × valor.
- **Permalink por evento** (`?e=<id>`): endpoint `GET /api/event/{event_id}` (db.py `get_event_by_id`, 404 si no existe/expirado). Frontend: `eventPermalink()`, `copyEventLink()` (clipboard + fallback), `shareEvent()` comparte el permalink, boton "🔗 Copiar enlace" y 📤 en el modal de detalle (handlers enlazados en JS, sin inline frágil), `showEventDetail` refactorizado a `showEventDetailObj(e)`, `openEventFromPermalink()` al final de `init()`. Verificado E2E Playwright: overlay abre, 0 errores de consola.
- **Web Push value-first**: `requestNotifPermValueFirst()` + `showNotifValuePrompt()` — pre-prompt con 3 pasos y microcopy en valor antes del dialogo nativo; se pide permiso al pulsar "Activar". Aplicado al crear alerta y a la barra de permiso del modal. i18n ES/EN (nv_*). Verificado E2E (prompt muestra, enable cierra y llama callback).
- **Prueba social en la UI**: strip `#metricsStrip` bajo la barra de salud: "📊 N eventos en 24h · ✓ X% éxito · 🕐 última actualización hace X" (de `/api/metrics` + `/api/status`), i18n ES/EN, refresco cada 60 s junto a `refreshSourceStatus`.
- **URL `?lang=en|es`**: `currentLang()` respeta el parámetro (para el lanzamiento de PH).
- **Caché de imágenes en nginx**: `location ~* \.(png|...)$` con `expires 1h` + `Cache-Control: public, max-age=3600` (og-image revalidable por crawlers). Verificado en producción.
- **Hero GIF** en README: `frontend/nearme-preview.gif` (2.5 MB, 400x212, 5 capturas — sin panel admin—, ~10 s loop, Ken Burns sutil, 128 colores). GitHub NO anima WebP en README (verificado), por eso GIF.
- **Deploy**: commits `8993984` (A/B/C/D) y posterior (permalinks + value-first). sw -> `nearme-v8`. Los 3 entornos sincronizados (laptop, GitHub, server vía rsync).
- Nota: el `git HEAD` del server queda desactualizado tras rsync (modelo deploy.sh); el código desplegado es el correcto (gif/endpoint verificados en vivo).

## Sprint 40 — Panel de recursos de emergencia (5 Ago 2026)

- **Objetivo (opción A, bajo riesgo)**: panel automático con recursos de ayuda cuando un evento activo es alert/critical en tipos desastre (fire, flood, earthquake, storm, wind, snow, heatwave).
- **Capa CCAA**: `assets/spain-ccaa.geojson` (19 features, fuente Click That Hood / INE `cod_ccaa`) cargada en PostGIS (`spain_ccaa`), lookup espacial `ST_Within` por lat/lon del evento (los eventos desastre no tienen `region` pero sí coordenadas).
- **Directorio**: tabla `emergency_resources` sembrada por CCAA con referencias oficiales reales y nacionales: Cruz Roja (900 22 11 22, cruzroja.es) y Protección Civil (112, proteccioncivil.es). 112 fijo en el panel. Los contactos específicos por CCAA quedan pendientes de curado manual (no se inventan datos).
- **Endpoint**: `GET /api/event/{id}/resources` → `{qualified, phone_112, ccaa, resources}`. Fuera de España o evento no cualificado → `qualified:false` y lista vacía (sin error).
- **Frontend**: en el modal de detalle del evento se inserta el panel `🚨 Recursos de emergencia` (112 + Cruz Roja + Protección Civil) cuando cualifica, y botón **"📍 Compartir mi ubicación"** (100% cliente: `navigator.geolocation` + Web Share, fallback WhatsApp `wa.me`; nada se envía al servidor, coherente con zero-tracking).
- **Narrativa**: nota in-place en el panel ("solo alert/critical, verifica siempre con 112") + bullet en "Cómo leer el mapa" (no se tocó el funnel).
- **Visibilidad de incendios alert/critical en el mapa**:
  - critical: anillo rojo pulsante + badge "!" + tamaño ≥40px + borde 3px.
  - alert: badge ⚠ + borde 3px naranja + pulso con halo.
  - clusters con alert/critical: borde 3px + pulso (visible a cualquier zoom).
  - El fondo del círculo sigue siendo calor FRP (independiente del nivel; el nivel va en borde + badge).
- **Fix UX**: el popup del marcador no tenía forma de abrir el modal (el panel solo se veía desde el listado/permalink) → se añadió botón **"🔍 Ver detalle"** en el popup del marcador que abre el modal con el panel.
- **Fix CRÍTICO de despliegue**: el SW de NearMe servía `index.html` con cacheFirst → el navegador nunca veía las versiones nuevas pese a recargar. Ahora: **network-first para la página** + instalación con `cache: "reload"` (SW v17) + nginx `Cache-Control: no-cache` para `/sw.js`. Mismo bug que MigrationFlow, ahora corregido de raíz.
- **Verificado**: lookup Madrid→13, Sevilla→01, Canarias→05, fuera→None; endpoint con incendio alert en Castilla y León (qualified, recursos) y con evento no cualificado (qualified:false); flujo completo headless: marcador → popup → "Ver detalle" → modal con panel visible; 2 cargas con SW activo sirven la app nueva. Ejemplo directo: `https://nearme.viajeinteligencia.com/?e=1921713` o `?lat=41.30&lon=-4.75&radius=100` (zoom) para ver incendios alert pulsando.

## Sprint 39 — Paquete para prensa/analistas: embed widget + export CSV/GeoJSON (4 Ago 2026)
- **Embed widget** (`?embed=1`): oculta sidebar, onboarding, rating widget y tracking de visitas; mapa a pantalla completa del iframe con badge de crédito "NearMe OSINT" (enlazado, top-left). Parámetros `?lat&lon&radius` para que el embed centre una zona concreta (zoom 12, radio 50/200/500 km). Uso típico en prensa: `https://nearme.viajeinteligencia.com/?embed=1&lat=40.42&lon=-3.70&radius=200`. Verificado E2E con Chromium headless: `embed-mode` aplicado, sidebar `display:none`, onboarding no se muestra, `embedCredit` visible, mapa 780x493, params aplicados, modo normal intacto.
- **Export CSV/GeoJSON**: botones "⬇️ CSV" y "⬇️ GeoJSON" en el sidebar que descargan los eventos actuales (respetando filtros activos) — `exportData()`, `exportCSV()` (BOM UTF-8 + escaping RFC 4180), `exportGeoJSON()` (FeatureCollection con lat/lon en [lon,lat]), `downloadBlob()` con revoke de URL. CSV: 16 columnas (id, event_type, subtype, level, title, source, municipality, region, country, lat, lon, distance_km, confidence, created_at, updated_at, expires_at). i18n ES/EN (`export_csv`/`export_geojson`).
- **Charset nginx**: añadido `charset utf-8;` al server block (Content-Type con charset en estáticos y JSON).
- **Monitor local (activo)**: cron `*/5` con `scripts/healthcheck.sh` — verifica `/health` (api=ok, database=connected) y freshness del pipeline (<45 min desde el último collector run). Alerta por Telegram (`@nearme_status_bot`) SOLO en cambio de estado (down/recovery), no cada ejecución. Estado actual `up`, último check `api=ok db=connected pipeline_age=<Xs`. Sin dependencias externas.
- **UptimeRobot (OPCIONAL)**: se deja como canal externo opcional — crear monitor HTTP(S) a `https://nearme.viajeinteligencia.com/health`, intervalo 5 min, alerta email; útil solo si se quiere una status page pública para la landing/README. No automatizable (requiere cuenta externa), por eso el monitor local es el canal primario.
- **Deploy**: sw -> `nearme-v9`, v0.14 en CHANGELOG. Los 3 entornos sincronizados (laptop, GitHub, server vía rsync).

## Fix 41a — Embalses invisibles: expiración 7 días desde recolección (8 Ago 2026)

- **Síntoma reportado**: el embalse de Alarcón (1112 hm³, río Riansares, Cuenca) — un embalse importante — no mostraba icono/porcentaje en el mapa, mientras que embalses menores sí aparecían.
- **Causa raíz (3 niveles)**:
  1. La fuente `estadoembalses.es` NO renueva la `ultima_lectura` de todos los embalses con la misma frecuencia. Alarcón (y Contreras, La Toba en Cuenca, 80+ más) llevaban lectura del 22-Jul-2026.
  2. El colector calculaba `expires_at = ultima_lectura + 6h` → con lectura vieja, `expires_at` quedaba en el pasado.
  3. La consulta `/api/nearby` excluye `expires_at > NOW()` → los 83 embalses con lectura vieja eran **invisibles** pese a estar en la BD (452 con coords, 369 visibles).
- **Fix**: los datos de nivel de embalse son estables durante días y el colector corre cada 30 min (refresca `expires_at` en cada colección), así que se fija **expiración de 7 días desde el momento de recolección** (ya no desde `ultima_lectura`). `EMBALSE_TTL_DAYS = 7`.
- **Resultado verificado**: Alarcón expira el 15-Ago (antes 22-Jul), **0 embalses expirados** (antes 83), **452/452 visibles**, y Alarcón aparece en `/api/nearby` y en producción (mapa).
- **Sin impacto en recursos**: solo cambia la fecha de expiración al insertar; no hay queries ni procesamiento extra.
- **Commit**: `54ba2a2`. Backup: `src/collectors/embalses/__init__.py.bak-20260808`.

## Fix 41b — Embalses: frescura visible (Opción 1) (8 Ago 2026)

- **Objetivo**: superar la expiración de forma automática Y transparente — el dato de nivel de embalse no desaparece del mapa (TTL 7d del Fix 41a) y, además, se indica cuándo se midió.
- **Colector**: la descripción del embalse ahora incluye **"Medición: DD/MM/AAAA HH:MM"** (la `ultima_lectura` real de la fuente). Alarcón: "Medición: 22/07/2026 08:40".
- **Frontend**:
  - **Popup del marcador en el mapa**: ahora muestra `freshnessBadge(updated_at)` (verde <30min, naranja <2h, rojo ≥2h) — misma función ya usada en el listado.
  - **Modal de detalle**: nueva línea "Actualizado: <fecha> + freshnessBadge".
- **Resultado**: el embalse se ve siempre (TTL 7d desde recolección, refrescado cada 30 min por el upsert) y el usuario ve la frescura real de la medición. Sin impacto en recursos (solo texto + badge).
- **Commits**: colector + frontend en `e47eca5`.
