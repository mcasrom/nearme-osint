<p align="center">
  <img src="frontend/icon.svg" alt="NearMe OSINT" width="120" />
</p>

<h1 align="center">📍 NearMe OSINT — Mapa de eventos en tiempo real</h1>

<p align="center">
  <em>¿Qué está pasando a mi alrededor ahora mismo?</em>
</p>

<p align="center">
  <a href="https://nearme.viajeinteligencia.com"><img src="https://img.shields.io/badge/DEMO_LIVE-nearme.viajeinteligencia.com-00d4ff?style=for-the-badge" alt="Demo en vivo"></a>
  <a href="https://github.com/mcasrom/nearme-osint"><img src="https://img.shields.io/badge/licencia-MIT-blue?style=for-the-badge" alt="Licencia MIT"></a>
  <a href="#fuentes-de-datos"><img src="https://img.shields.io/badge/fuentes-15%20oficiales%20y%20abiertas-brightgreen?style=for-the-badge" alt="15 fuentes"></a>
  <a href="https://ko-fi.com/elmapayelcodigo"><img src="https://img.shields.io/badge/apoyar-Ko--fi-ff5e5b?style=for-the-badge" alt="Apoyar en Ko-fi"></a>
</p>

<p align="center">
  🔥 Incendios · 🚧 Tráfico · 🌡️ Meteorología · 🌫️ Calidad del aire · 🚆 Trenes · 🏚️ Terremotos · ⚡ Energía · 🏖️ Playas
</p>

---

Un **agregador OSINT geográfico en tiempo real** que une 15 fuentes de datos públicos y oficiales en un solo mapa interactivo con niveles de severidad, mediciones continuas y alertas personalizables. Funciona como una **PWA instalable y offline**.

> 💡 **¿Qué es esto en la práctica?** En vez de revisar cinco apps distintas para saber si hay un incendio cerca, un retraso de tren, una alerta meteorológica o un corte de tráfico, NearMe lo agrupa todo en un flujo único de eventos geolocalizados.

---

## 🚀 Prueba la demo

**[→ Abrir NearMe OSINT en vivo](https://nearme.viajeinteligencia.com)**

- 📍 Busca una ubicación por texto, haz clic en el mapa o usa tu GPS
- 🔥 Explora incendios reales detectados por satélite (NASA FIRMS)
- 🚆 Consulta retrasos de tren (RENFE) e incidencias de tráfico (DGT)
- 🔔 Activa alertas: *"avísame si hay incendios a <15 km"*
- 📱 Instálala como app (PWA con soporte offline)

## ✨ Características

| | |
|---|---|
| 🗺️ **Mapa en tiempo real** | Leaflet + MarkerCluster, iconos por tipo de evento y severidad |
| 🔥 **Incendios por satélite** | NASA FIRMS (MODIS + VIIRS) con mapa de calor y gradiente por potencia (FRP) |
| 🚧 **Tráfico** | DGT DATEX II: cortes, obras, accidentes y retenciones en la red estatal |
| 🚆 **Trenes** | Retrasos RENFE geolocalizados vía GTFS-RT (cercanías + AV/LD) |
| 🌡️ **Meteorología** | AEMET: 10.600 estaciones con informes continuos + alertas |
| 🌫️ **Calidad del aire** | MITECO ICA + OpenAQ (6 parámetros) |
| 🏚️ **Sismología** | IGN (red nacional 24/7) + USGS (global M2.5+) |
| ⚡ **Energía** | Demanda eléctrica REE + precio PVPC (ESIOS) en tiempo real |
| 🏖️ **Playas** | Estado de playas del País Vasco (bandera, oleaje, medusas) |
| ☀️ **Índice UV** | Open-Meteo para 52 capitales + Ceuta/Melilla |
| 🔔 **Alertas personalizadas** | Por tipo, radio y nivel con notificaciones del navegador |
| 📍 **POI cercanos** | Hospitales, farmacias, gasolineras y más (Overpass/OSM) |
| 📤 **Compartir** | Texto dinámico + Web Share API con enlaces a 𝕏, WhatsApp, Telegram, Bluesky y Mastodon |
| 🟢 **Estado del sistema** | Semáforo por fuente, freshness badges y health indicator |
| 📱 **PWA** | Instalable, offline, auto-refresh cada 5 minutos |
| 🔒 **Privacidad** | Sin analytics, sin tracking, sin cookies, sin IPs |

## 📊 Pipeline de datos

```
[15 colectores async] → [Pipeline (asyncio.gather)] → [PostgreSQL + PostGIS] → [FastAPI] → [Frontend Leaflet]
```

Cada ciclo de 15 minutos procesa **~6.000+ eventos**:

| Fuente | Qué aporta | Autenticación | Actualización |
|--------|-----------|---------------|---------------|
| NASA FIRMS | 🔥 Incendios satélite (MODIS+VIIRS) | Sin clave | 15 min |
| DGT | 🚧 Incidencias tráfico (DATEX II) | Sin clave | 5 min |
| AEMET | 🌡️ Meteo continuo + alertas (10.600 est.) | API Key | 15 min |
| RENFE | 🚆 Retrasos tren (GTFS-RT) | Sin clave | 15 min |
| MITECO | 🌫️ Calidad del aire ICA (620 est.) | Sin clave | 30 min |
| OpenAQ | 🌫️ Calidad del aire (6 parámetros, v3) | API Key | 30 min |
| USGS | 🏚️ Terremotos M2.5+ globales | Sin clave | 15 min |
| Protección Civil | ⚠️ Avisos meteorológicos (CAP/AEMET) | API Key | 30 min |
| REE | ⚡ Demanda eléctrica tiempo real | Sin clave | 15 min |
| IntelHub | 📰 Noticias + incendios RSS (24 fuentes, 9 países) | Sin clave | 10 min |
| Playas Euskadi | 🏖️ Bandera, oleaje, temperatura, medusas | Sin clave | 60 min |
| Embalses | 🌊 Nivel de embalses (MITECO SAIH) | Sin clave | 30 min |
| IGN | 🏚️ Sismología española (red 24/7) | Sin clave | 15 min |
| Open-Meteo | ☀️ Índice UV máximo (52 capitales) | Sin clave | 60 min |
| REE + ESIOS | ⚡ Demanda y precio PVPC | Sin clave | 15 min |

### Ciclo de vida de un evento
1. **Creación** — el colector obtiene datos y hace *upsert* por `(source, source_id)`
2. **Actualización** — si el evento sigue en la fuente, se renueva su `expires_at`
3. **Resolución** — si deja de aparecer, `resolve_events()` lo marca como `resolved`
4. **Expiración por TTL** — si no hay fin explícito, se limpia al superar su TTL (incendios 24 h, tráfico 12 h, …)
5. **Expiración explícita** — se respeta el `end_time` de la fuente (p. ej. DGT `overallEndTime`)

### Niveles de severidad
| Nivel | Color | Ejemplo |
|-------|-------|---------|
| `info` | 🔵 Azul | Datos normales (clima, calidad del aire) |
| `warning` | 🟡 Amarillo | Precauciones (ICA ≥ 3, temperatura ≥ 35 °C) |
| `alert` | 🟠 Naranja | Peligro (FRP ≥ 100 MW, terremoto ≥ M5) |
| `critical` | 🔴 Rojo | Emergencia (severidad DGT *highest*) |

### Frescura
Cada evento lleva un badge según su `updated_at`: 🟢 `<30 min` · 🟠 `30 min–2 h` · 🔴 `>2 h`. El sidebar muestra un semáforo por fuente (🟢🟡🔴) actualizado cada 60 s desde `/api/status`.

## 🛠️ Stack

- **Backend**: FastAPI + uvicorn · async Python (httpx, asyncio.gather)
- **Base de datos**: PostgreSQL + PostGIS con *connection pooling* (psycopg2)
- **Pipeline**: cron `*/15 * * * *` + monitoreo persistente en `collector_runs`
- **Frontend**: Leaflet + Leaflet.markerCluster + Leaflet.heat + vanilla JS (PWA con Service Worker)
- **Auth**: JWT + bcrypt (passlib)
- **Infra**: Nginx + SSL Let's Encrypt · PM2 (`nearme-api`) · rsync

## 📁 Estructura del proyecto

```
nearme-osint/
├── run.py                      # Orquestador del pipeline (colectores async)
├── src/
│   ├── api/server.py           # FastAPI (frontend + API + auth)
│   ├── db.py                   # PostgreSQL/PostGIS con connection pooling
│   ├── config.py               # Constantes centralizadas (umbrales, URLs, TTLs)
│   ├── logging.py              # Logging JSON estructurado
│   ├── metrics.py              # PipelineMetrics (latencia y éxito por colector)
│   ├── models.py               # Event dataclass + EVENT_TYPES
│   └── collectors/
│       ├── aemet/              # Meteorología (observaciones + alertas)
│       ├── dgt/                # Tráfico DATEX II + USGS + NASA FIRMS
│       ├── renfe/              # Retrasos tren (GTFS-RT + CSV estaciones)
│       ├── ree/                # Demanda eléctrica
│       ├── miteco/             # Calidad del aire (ICA)
│       ├── openaq/             # Calidad del aire (fallback, 6 parámetros)
│       ├── proteccion_civil/   # Avisos meteorológicos (CAP)
│       ├── intelhub_bridge.py  # Noticias/incendios RSS (IntelHub)
│       ├── playas/             # Estado de playas Euskadi
│       ├── embalses/           # Nivel de embalses (SAIH + MITECO)
│       ├── ign/                # Sismología española (red 24/7)
│       ├── uv/                 # Índice UV (Open-Meteo)
│       ├── energy/             # Demanda REE + precio PVPC (ESIOS)
│       └── copernicus/         # Incendios GWIS (endpoints 404 — deshabilitado)
├── frontend/                   # Leaflet + MarkerCluster + vanilla JS (PWA)
├── analytics/                  # Reporte GoAccess (basic auth)
├── deploy.sh                   # rsync + PM2 restart
├── setup-server.sh             # Provisionamiento del servidor
├── requirements.txt
├── .env.example                # Template de credenciales (gitignored)
└── WAYAHEAD.md                 # Bitácora de desarrollo y sprints
```

## 🔌 API

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/nearby` | Eventos activos (radio, tipos, niveles) |
| `GET /api/status` | Estado por colector (último run, latencia, stats 24 h) |
| `GET /api/status/runs?n=50` | Últimas ejecuciones del pipeline |
| `GET /api/metrics` | Resumen agregado del pipeline |
| `GET /api/poi` | Puntos de interés cercanos (proxy Overpass/OSM, con caché) |
| `GET /api/stats` | Visitas (total, hoy, ayer) |
| `GET /health` | Estado de BD, pipeline y último run |

Panel de operaciones: `/admin` (protegido con `ADMIN_PASSWORD`).

## 🚀 Puesta en marcha local

```bash
git clone git@github.com:mcasrom/nearme-osint.git
cd nearme-osint

# 1. Credenciales (AEMET_API_KEY, OPENAQ_API_KEY, DB_*, JWT_SECRET, ADMIN_PASSWORD)
cp .env.example .env

# 2. PostgreSQL con PostGIS
#    (ver setup-server.sh para el aprovisionamiento completo)

# 3. Instalar dependencias
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 4. Ejecutar el pipeline (recolección → PostGIS)
python run.py

# 5. Arrancar la API
uvicorn src.api.server:app --host 0.0.0.0 --port 8100
```

## 👥 Contribuir

¿Te interesa el OSINT de código abierto o los datos abiertos de España? Todas las contribuciones son bienvenidas:

- 🐛 **Reporta bugs** o sugerencias vía [Issues](https://github.com/mcasrom/nearme-osint/issues)
- 📦 **Añade un colector**: implementa `BaseCollector` con `async collect()` → `list[Event]`, regístralo en `run.py` y añade su config en `src/config.py`
- 🗺️ **Nueva fuente o región**: el pipeline es agnóstico a la fuente; añadir otro país es "escribir un colector nuevo"
- 📄 Revisa `WAYAHEAD.md` para el contexto de desarrollo y sprints

## 🔒 Privacidad

Sin analytics, sin tracking, sin cookies, sin publicidad. Solo se guardan datos mínimos (usuario, email opcional y hash bcrypt) exclusivamente para el sistema de alertas y las ubicaciones favoritas. Sin IPs, sin geolocalización del usuario. [Detalles en la app](https://nearme.viajeinteligencia.com).

## 🧭 Roadmap

- [ ] Alertas por email
- [ ] Soporte multi-región (más países)
- [ ] Más fuentes de datos abiertos
- [ ] App móvil nativa (Android/iOS)
- [ ] API pública documentada para terceros

## ☕ Apoyar el proyecto

Hecho por un desarrollador independiente en España. Si te resulta útil:

- ⭐ Da una estrella al repositorio
- ☕ [Invita un café en Ko-fi](https://ko-fi.com/elmapayelcodigo)
- 📤 Comparte el mapa con quien pueda necesitarlo

**Contacto**: [news@viajeinteligencia.com](mailto:news@viajeinteligencia.com)

## 📄 Licencia

[MIT](https://github.com/mcasrom/nearme-osint/blob/main/LICENSE) — libre de usar, auditar y modificar. Las fuentes de datos conservan sus propias licencias.
