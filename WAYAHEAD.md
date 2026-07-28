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

---

## 📊 Pipeline actual (624 eventos/15min)
```
AEMET:       ~183  heatwave/wind/storm (10.600 estaciones)
MITECO:      ~249  calidad del aire ICA ≥ Regular (620 estaciones)
RENFE:       ~123  retrasos tren geolocalizados (GTFS-RT)
USGS:         ~30  terremotos M2.5+ globales
IntelHub:     ~30  incendios RSS (24 fuentes)
REE:           ~9  demanda eléctrica alta
──────────────────────────────
TOTAL:       ~624
```

---

## 🔜 Próximos sprints

### Sprint 13 — NASA FIRMS (incendios satélite)
- [ ] Registrarse en Earthdata (`urs.earthdata.nasa.gov`)
- [ ] Obtener MAP_KEY para FIRMS API
- [ ] Collector: `firms.modaps.eosdis.nasa.gov/api/area/csv/`
- [ ] Fire alert/warning por FRP y brillo

### Sprint 14 — DGT (carreteras)
- [ ] Investigar endpoint alternativo (SPA de infocar.dgt.es no tiene API pública)
- [ ] Opción: scraping de `etraffic.dgt.es` o RSS DGT
- [ ] Cortes de carretera + obras en tiempo real

### Sprint 15 — Playas (estacional)
- [ ] Bizkaia: bandera, oleaje, temp agua, medusas (JSON open data)
- [ ] Euskadi: estado sanitario playas (GeoJSON)
- [ ] Valencia: estado mar diario
- [ ] Solo temporada jun-sep

### Sprint 16 — UX mejorada
- [ ] Botones radio muestran cuál está activo
- [ ] Filtros por tipo de evento en sidebar
- [ ] Popup expandido con más detalles
- [ ] Modo oscuro / claro toggle

### Sprint 17 — Alertas personalizadas
- [ ] "Avísame si hay incendios a <15 km"
- [ ] Push notifications vía Service Worker
- [ ] Persistencia en localStorage

---

## 🐛 Bugs conocidos
- [ ] ~20% paradas RENFE sin geolocalización (stop_id no encontrado en CSV estaciones)
- [ ] Coordenadas incendios RSS aproximadas (por provincia), no geoposicionamiento real

---

## ❌ Fuentes no accesibles
| Fuente | Motivo |
|--------|--------|
| DGT | API bloqueada (timeout/403), SPA sin API pública |
| AENA | Deniega acceso a datos de puntualidad (interés comercial) |
| Copernicus/GWIS | Endpoints devuelven 404 |
| OpenAQ | Requiere API key gratuita (pendiente registrar) |

---

## 🔑 Credenciales (en .env, gitignored)
- `AEMET_API_KEY`: JWT (exp ~Dic 2026)
- `DB_*`: PostgreSQL nearme / nearme_pass_2026
- `NASA_FIRMS_KEY`: **Pendiente** (Sprint 13)

---

## 📁 Estructura
```
nearme-osint/
├── run.py                     # Pipeline orchestrator (11 colectores)
├── src/
│   ├── api/server.py          # FastAPI (frontend + API)
│   ├── db.py                  # PostgreSQL/PostGIS
│   ├── models.py              # Event dataclass + EVENT_TYPES
│   └── collectors/
│       ├── aemet/             # Meteorología (observaciones)
│       ├── dgt/               # USGS terremotos + NASA FIRMS
│       ├── renfe/             # Retrasos tren (GTFS-RT + CSV)
│       ├── ree/               # Demanda eléctrica
│       ├── miteco/            # Calidad del aire (ICA)
│       ├── openaq/            # Calidad del aire (fallback)
│       ├── copernicus/        # Incendios (no funciona)
│       ├── ign/               # Terremotos (duplicado)
│       ├── proteccion_civil/  # Avisos meteorológicos
│       └── intelhub_bridge.py # Incendios RSS
├── frontend/                  # Leaflet + MarkerCluster + vanilla JS
├── deploy.sh                  # rsync + PM2
├── setup-server.sh            # Provisioning servidor
├── WAYAHEAD.md                # Este archivo
├── requirements.txt           # Dependencias Python
└── .env                       # Credenciales (gitignored)
```
