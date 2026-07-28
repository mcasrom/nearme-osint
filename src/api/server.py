from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(title="NearMe OSINT API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    from src.db import init_db
    try:
        init_db()
    except Exception:
        pass


@app.get("/health")
def health():
    return {"status": "ok", "service": "NearMe OSINT", "version": "0.1"}


@app.get("/api/nearby")
def nearby(
    lat: float = Query(40.42, description="Latitud"),
    lon: float = Query(-3.70, description="Longitud"),
    radius: float = Query(25, description="Radio en km"),
    event_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    min_level: Optional[str] = Query(None, description="Nivel mínimo (info/warning/alert/critical)"),
    limit: int = Query(100, description="Límite de resultados"),
):
    from src.db import get_events_nearby
    events = get_events_nearby(lat, lon, radius, limit, event_type, min_level)
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius,
        "total": len(events),
        "events": events,
    }


@app.get("/api/summary")
def summary(
    lat: float = Query(40.42, description="Latitud"),
    lon: float = Query(-3.70, description="Longitud"),
    radius: float = Query(25, description="Radio en km"),
):
    from src.db import get_events_summary
    s = get_events_summary(lat, lon, radius)
    return {"lat": lat, "lon": lon, "radius_km": radius, **s}


@app.get("/api/types")
def event_types():
    from src.models import EVENT_TYPES
    return EVENT_TYPES
