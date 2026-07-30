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

## 📊 Pipeline actual (~5.470 eventos/15min)
```
OpenAQ:       ~  980  calidad del aire (6 parámetros, v3 API)
NASA FIRMS:   ~2.018  incendios satélite España (MODIS+VIIRS)
DGT:          ~1.242  incidencias tráfico red estatal (DATEX II)
RENFE:         ~  749  retrasos tren geolocalizados (GTFS-RT)
MITECO:        ~  523  calidad del aire ICA (620 estaciones)
AEMET:         ~  330  weather continuo + alertas (10.600 estaciones)
Playas:        ~   37  bandera, oleaje, temp agua, medusas (Euskadi+Bizkaia)
IntelHub:      ~   30  incendios RSS (24 fuentes)
REE:           ~   21  demanda eléctrica alta
USGS:           ~    1  terremotos M2.5+ España (raros)
──────────────────────────────
TOTAL:        ~5.470
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

## 📖 Metodología

### Arquitectura
```
[11 colectores async] → [Pipeline (asyncio.gather)] → [PostgreSQL+PostGIS] → [FastAPI] → [Frontend Leaflet]
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
├── run.py                     # Pipeline orchestrator (11 colectores)
├── src/
│   ├── api/server.py          # FastAPI (frontend + API)
│   ├── db.py                  # PostgreSQL/PostGIS con connection pooling
│   ├── logging.py             # JSON logging module
│   ├── models.py              # Event dataclass + EVENT_TYPES
│   └── collectors/
│       ├── aemet/             # Meteorología (observaciones)
│   ├── dgt/               # DGT tráfico DATEX II + USGS terremotos + NASA FIRMS
│       ├── renfe/             # Retrasos tren (GTFS-RT + CSV)
│       ├── ree/               # Demanda eléctrica
│       ├── miteco/            # Calidad del aire (ICA)
│       ├── openaq/            # Calidad del aire (fallback)
│       ├── copernicus/        # Incendios (no funciona)
│       ├── proteccion_civil/  # Avisos meteorológicos
│       └── intelhub_bridge.py # Incendios RSS
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
