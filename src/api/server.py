from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pathlib import Path

app = FastAPI(title="NearMe OSINT API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


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
    min_level: Optional[str] = Query(None, description="Nivel minimo (info/warning/alert/critical)"),
    limit: int = Query(100, description="Limite de resultados"),
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


@app.get("/")
def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"error": "Frontend not found"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
