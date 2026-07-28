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
| AEMET | ✅ | ~180 alertas meteorológicas (temp/viento/lluvia) | `opendata.aemet.es` |
| USGS | ✅ | ~30 terremotos M2.5+ (24h) | `earthquake.usgs.gov` |
| RENFE | ✅ | ~120 retrasos cercanías + AV/LD, geolocalizados | `gtfsrt.renfe.com` + estaciones CSV |
| REE | ✅ | ~9 eventos demanda eléctrica | `apidatos.ree.es` |
| MITECO | ✅ | ~250 estaciones calidad aire (ICA horario) | `ica.miteco.es` |
| IntelHub | ✅ | ~30 incendios RSS (24 fuentes) | SQLite local |
| Protección Civil | ✅ | Avisos meteorológicos AEMET (CAP XML) | `opendata.aemet.es/avisos_cap` |
| NASA FIRMS | ⏳ | Requiere Earthdata API key | — |
| DGT | ❌ | API bloqueada (timeout/403) | — |
| AENA | ❌ | Deniega acceso datos puntualidad | — |

### Pipeline actual (28 Jul 2026, 624 eventos)
```
AEMET:       ~183  (heatwave/wind/storm)
USGS:         ~30  (terremotos)
RENFE:       ~123  (retrasos tren, geolocalizados)
REE:           ~9  (demanda eléctrica)
MITECO:      ~249  (calidad del aire, ICA ≥ Regular)
IntelHub:     ~30  (incendios RSS)
──────────────────────────────
TOTAL:       ~624
```

### Desplegado en Producción (28 Jul 2026)
- [x] RENFE retrasos tren — geolocalizados con CSV estaciones (1070 estaciones)
- [x] REE demanda eléctrica alta
- [x] MITECO calidad del aire — 249 estaciones con ICA
- [x] Contacto mailto:news@viajeinteligencia.com en About

---

## 🔧 Técnico pendiente
- [ ] Colores por tipo de evento en mapa
- [ ] Agrupar marcadores (Leaflet.markercluster)
- [ ] Indicador de carga/error cuando la API no responde
- [ ] Botones de radio muestran cuál está activo

## 🐛 Bugs conocidos
- [ ] ~20% paradas RENFE sin geolocalización (stop_id no encontrado en CSV)
- [ ] Coordenadas incendios RSS aproximadas (por provincia)

## 🚀 Fase 2
- [ ] NASA FIRMS (Earthdata key)
- [ ] DGT (incidentes viales, endpoint alternativo)
- [ ] Playas (Bizkaia/Euskadi open data)
- [ ] Alertas personalizadas push

## 🔑 Credenciales (en .env, gitignored)
- `AEMET_API_KEY`: JWT (exp ~Dic 2026)
- `DB_*`: PostgreSQL nearme/nearme_pass_2026
- `NASA_FIRMS_KEY`: Pendiente

## 📁 Estructura
```
nearme-osint/
├── run.py                    # Pipeline orchestrator (11 colectores)
├── src/
│   ├── api/server.py         # FastAPI
│   ├── db.py                 # PostgreSQL/PostGIS
│   ├── models.py             # Event dataclass + EVENT_TYPES
│   └── collectors/
│       ├── aemet/            # Meteorología real
│       ├── dgt/              # USGS terremotos + FIRMS
│       ├── renfe/            # Retrasos tren (GTFS-RT + CSV estaciones)
│       ├── ree/              # Demanda eléctrica
│       ├── miteco/           # Calidad del aire (ICA)
│       ├── proteccion_civil/ # Avisos meteorológicos
│       └── intelhub_bridge.py
├── frontend/                 # Leaflet + vanilla JS
└── .env                      # Credenciales (gitignored)
```
