# WAYAHEAD — NearMe OSINT (GeoPulse / GeoRisk Live)

**Objetivo**: Motor de OSINT geográfico en tiempo real que responde "¿Qué está pasando a mi alrededor ahora mismo?"
**Live**: https://nearme.viajeinteligencia.com
**GitHub**: https://github.com/mcasrom/nearme-osint

---

## ✅ Hitos completados

### Fase 0 — MVP (Jul 2026)
- [x] PostgreSQL + PostGIS en Hetzner (`deploy@178.105.80.193`)
- [x] FastAPI backend en puerto 8100, nginx proxy + SSL Let's Encrypt
- [x] Frontend Leaflet con búsqueda por texto (Nominatim), clic en mapa, GPS
- [x] Cron cada 15 min: `*/15 * * * * cd /home/deploy/nearme-osint && venv/bin/python run.py`
- [x] PM2 para gestionar proceso API

### Fase 1 — Fuentes de datos reales
| Fuente | Estado | Datos | Endpoint |
|--------|--------|-------|----------|
| AEMET | ✅ | ~180 alertas (temp/viento/lluvia) de ~10K estaciones | `opendata.aemet.es` (observations) |
| USGS | ✅ | ~30 terremotos M2.5+ (24h) | `earthquake.usgs.gov` GeoJSON |
| NASA FIRMS | ⏳ | Requiere Earthdata API key | `firms.modaps.eosdis.nasa.gov` |
| IntelHub bridge | ✅ | ~20 incendios desde RSS (24 fuentes, 9 países) | SQLite local |
| RENFE | ✅ | ~120 retrasos (cercanías + AV/LD) | `gtfsrt.renfe.com` (GTFS-RT protobuf) |
| REE | ✅ | ~9 eventos de demanda eléctrica alta | `apidatos.ree.es` (demanda-tiempo-real) |
| DGT | ❌ | API bloqueada (timeout/403) | `infocar.dgt.es` (SPA, no API pública) |
| AENA | ❌ | Deniega acceso a datos de puntualidad | — |
| Protección Civil | ✅ | Alertas meteorológicas AEMET (CAP XML) | `opendata.aemet.es/avisos_cap` |
| OpenAQ | ✅ | 10 ciudades españolas | `api.openaq.org` |
| Copernicus/GWIS | ❌ | Endpoints 404 | — |

### Pipeline actual (28 Jul 2026)
```
AEMET:      ~183 eventos (heatwave/wind/storm alerts)
USGS:        30 terremotos
RENFE:      ~120 retrasos de tren
REE:          9 eventos de demanda eléctrica
IntelHub:    ~20 incendios RSS
────────────────────────────
TOTAL:      ~370 eventos/pipeline
```

---

## 🔧 Técnico pendiente
- [ ] Añadir fitBounds() para zoom automático
- [ ] Agrupar marcadores (Leaflet.markercluster)
- [ ] Cachear respuesta API en frontend
- [ ] Colores por tipo de evento (rojo=incendio, naranja=terremoto, etc.)
- [ ] Indicador de carga/error cuando la API no responde
- [ ] Botones de radio muestran cuál está activo

## 🐛 Bugs conocidos
- [ ] Coordenadas incendios RSS aproximadas (por provincia), no geoposicionamiento real
- [ ] Zoom inicial puede no mostrar todos los eventos
- [ ] Frontend: no hay indicador visual de "procesando..."

## 🚀 Fase 2
- [ ] **NASA FIRMS**: Obtener Earthdata API key para incendios satelitales
- [ ] **DGT**: Buscar endpoint alternativo o scraping para incidentes viales
- [ ] Alertas personalizadas: "avísame si hay incendios a <15 km"
- [ ] Histórico: eventos en zona en últimas 24h
- [ ] RSS local por municipio/provincia

## 🔑 Credenciales (en .env, gitignored)
- `AEMET_API_KEY`: JWT (exp ~Dic 2026)
- `DB_*`: PostgreSQL nearme/nearme_pass_2026
- `NASA_FIRMS_KEY`: Pendiente

## 📁 Estructura
```
nearme-osint/
├── run.py              # Pipeline orchestrator
├── src/
│   ├── api/server.py   # FastAPI (frontend + API)
│   ├── db.py           # PostgreSQL/PostGIS
│   ├── models.py       # Event dataclass + EVENT_TYPES
│   └── collectors/     # Módulos de recolección
│       ├── aemet/      # Meteorología real
│       ├── dgt/        # USGS terremotos + FIRMS incendios
│       ├── renfe/      # Retrasos tren (GTFS-RT)
│       ├── ree/        # Demanda eléctrica
│       ├── openaq/     # Calidad del aire
│       ├── copernicus/ # Incendios (no funciona)
│       ├── ign/        # Terremotos (duplicado)
│       ├── proteccion_civil/ # Avisos meteorológicos
│       └── intelhub_bridge.py # Incendios RSS
├── frontend/           # Leaflet + vanilla JS
├── deploy.sh          # rsync + PM2
└── .env               # Credenciales (gitignored)
```
