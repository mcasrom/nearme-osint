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
- [x] API key: `74e8929712ebc8825766adb2a5020578679fe923cb87f08cfe3ceb1fdea28255`
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

---

## 📊 Pipeline actual (~5.470 eventos/15min)
```
OpenAQ:       ~  980  calidad del aire (6 parámetros, v3 API)
NASA FIRMS:   ~2.018  incendios satélite España (MODIS+VIIRS)
DGT:          ~1.242  incidencias tráfico red estatal (DATEX II)
RENFE:        ~  749  retrasos tren geolocalizados (GTFS-RT)
MITECO:       ~  523  calidad del aire ICA (620 estaciones)
AEMET:        ~  330  heatwave/wind/storm (10.600 estaciones)
Playas:       ~   37  bandera, oleaje, temp agua, medusas (Euskadi+Bizkaia)
IntelHub:     ~   30  incendios RSS (24 fuentes)
REE:          ~   21  demanda eléctrica alta
USGS:          ~    1  terremotos M2.5+ España (raros)
──────────────────────────────
TOTAL:        ~5.470
```

---

## 🔜 Próximos sprints

### Sprint 18 — ?

---

## 🐛 Bugs conocidos
- [ ] ~20% paradas RENFE sin geolocalización (stop_id no encontrado en CSV estaciones)
- [ ] Coordenadas incendios RSS aproximadas (por provincia), no geoposicionamiento real
- [ ] Colectores bloqueantes (`requests`) en pipeline secuencial — considerar async + ThreadPoolExecutor

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
