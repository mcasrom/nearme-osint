import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from passlib.hash import bcrypt
from typing import Optional
from pathlib import Path

app = FastAPI(title="NearMe OSINT API", version="0.2")
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
JWT_SECRET = os.environ.get("JWT_SECRET", "nearme_dev_secret_change_in_prod_2026")
JWT_ALGO = "HS256"
JWT_EXPIRY_HOURS = 72

# ----- Anti-fraud -----
_rate_limiter = defaultdict(list)  # ip -> [timestamps]
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
RATE_LIMIT_MAX = 5  # max registrations per window


def _clean_rate_limiter():
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    for ip in list(_rate_limiter.keys()):
        _rate_limiter[ip] = [t for t in _rate_limiter[ip] if t > cutoff]
        if not _rate_limiter[ip]:
            del _rate_limiter[ip]


def check_rate_limit(ip: str):
    _clean_rate_limiter()
    if len(_rate_limiter.get(ip, [])) >= RATE_LIMIT_MAX:
        wait = int(RATE_LIMIT_WINDOW - (time.time() - _rate_limiter[ip][0]))
        raise HTTPException(status_code=429, detail=f"Demasiados registros. Intenta en {wait // 60} minutos")


def record_attempt(ip: str):
    _rate_limiter[ip].append(time.time())


BLACKLIST_PATTERNS = [
    r'http[s]?://', r'www\.', r'\.com', r'\.xyz', r'\.top',
    r'[0-9]{8,}',  # 8+ digits (phone numbers)
]

HONEYPOT_FIELDS = {'website', 'url', 'hp_field'}


# ----- Auth helpers -----

def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def check_password(password: str, stored: str) -> bool:
    return bcrypt.verify(password, stored)


def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = int(payload["sub"])
        from src.db import get_user_by_id
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")


# ----- Request/Response models -----

class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    email: str = ""
    website: str = ""
    url: str = ""
    hp_field: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


class AlertBody(BaseModel):
    event_type: str = "all"
    radius_km: float = 15
    min_level: str = "warning"
    enabled: bool = True


class AlertUpdate(BaseModel):
    event_type: Optional[str] = None
    radius_km: Optional[float] = None
    min_level: Optional[str] = None
    enabled: Optional[bool] = None


@app.on_event("startup")
def startup():
    from src.db import init_db
    try:
        init_db()
    except Exception:
        pass


@app.get("/health")
def health():
    return {"status": "ok", "service": "NearMe OSINT", "version": "0.2"}


@app.get("/api/nearby")
def nearby(
    lat: float = Query(40.42, description="Latitud"),
    lon: float = Query(-3.70, description="Longitud"),
    radius: float = Query(25, description="Radio en km"),
    event_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    min_level: Optional[str] = Query(None, description="Nivel minimo (info/warning/alert/critical)"),
    limit: int = Query(500, description="Limite de resultados"),
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


_poi_cache: dict[str, tuple[float, list]] = {}

CATEGORIES = {
    "hospital": "Hospital",
    "clinic": "Clínica",
    "pharmacy": "Farmacia",
    "fuel": "Gasolinera",
    "charging_station": "Punto recarga",
    "police": "Policía",
    "fire_station": "Bomberos",
    "shelter": "Refugio",
}


@app.get("/api/poi")
def poi(
    lat: float = Query(40.42),
    lon: float = Query(-3.70),
    radius: int = Query(5000, description="Radio en metros"),
):
    cache_key = f"{lat:.1f},{lon:.1f},{radius}"
    cached = _poi_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < 120:
        return cached[1]

    types = list(CATEGORIES.keys())
    lat_s = f"{lat:.4f}"
    lon_s = f"{lon:.4f}"
    query = (
        '[out:json][timeout:25];('
        + "".join(f'node["amenity"="{t}"](around:{radius},{lat_s},{lon_s});' for t in types)
        + ");out body;"
    )
    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    data = None
    for url in mirrors:
        try:
            resp = httpx.get(
                url,
                params={"data": query},
                headers={"Accept": "application/json", "User-Agent": "NearMeOSINT/1.0"},
                timeout=25,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception:
            continue
    if data is None:
        raise HTTPException(status_code=502, detail="Overpass API no disponible (rate limit o timeout). Intenta de nuevo en unos segundos.")

    by_type: dict[str, list[dict]] = {}
    for el in data.get("elements", []):
        t = el.get("tags", {}).get("amenity", "other")
        name = el.get("tags", {}).get("name") or el.get("tags", {}).get("name:es") or CATEGORIES.get(t, t)
        by_type.setdefault(t, []).append({
            "name": name,
            "lat": el["lat"],
            "lon": el["lon"],
            "distance": _haversine(lat, lon, el["lat"], el["lon"]),
        })

    results = []
    for t, items in by_type.items():
        items.sort(key=lambda x: x["distance"])
        results.append({"label": CATEGORIES.get(t, t), "items": items[:5]})
    results.sort(key=lambda r: r["items"][0]["distance"] if r["items"] else 999999)

    payload = {"results": results}
    _poi_cache[cache_key] = (time.time(), payload)
    if len(_poi_cache) > 100:
        old_keys = [k for k, v in _poi_cache.items() if time.time() - v[0] > 300]
        for k in old_keys:
            del _poi_cache[k]
    return payload


def _haversine(lat1, lon1, lat2, lon2):
    import math
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


# ----- Auth endpoints -----

@app.post("/api/auth/register")
def register(body: RegisterBody, request: Request):
    # Honeypot: if any hidden field was filled, reject silently
    if body.website or body.url or body.hp_field:
        raise HTTPException(status_code=400, detail="Registro invalido")

    # Rate limit by IP (respect X-Forwarded-For behind nginx proxy)
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    check_rate_limit(ip)

    # Username blacklist
    import re
    for pat in BLACKLIST_PATTERNS:
        if re.search(pat, body.username.lower()):
            raise HTTPException(status_code=400, detail="Nombre de usuario no valido")

    from src.db import create_user
    pw_hash = hash_password(body.password)
    user = create_user(body.username.strip(), pw_hash, body.email.strip())
    if not user:
        raise HTTPException(status_code=409, detail="El nombre de usuario ya existe")

    record_attempt(ip)
    token = create_token(user["id"], user["username"])
    return {"user": user, "token": token}


@app.post("/api/auth/login")
def login(body: LoginBody):
    from src.db import get_user_by_username
    user = get_user_by_username(body.username.strip())
    if not user or not check_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    token = create_token(user["id"], user["username"])
    return {
        "user": {"id": user["id"], "username": user["username"], "email": user.get("email", ""), "created_at": str(user.get("created_at", ""))},
        "token": token,
    }


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user


# ----- Alerts endpoints -----

@app.get("/api/alerts")
def list_alerts(user: dict = Depends(get_current_user)):
    from src.db import get_user_alerts
    return {"alerts": get_user_alerts(user["id"])}


@app.post("/api/alerts")
def create_alert(body: AlertBody, user: dict = Depends(get_current_user)):
    from src.db import create_alert
    alert = create_alert(user["id"], body.event_type, body.radius_km, body.min_level, body.enabled)
    return alert


@app.put("/api/alerts/{alert_id}")
def update_alert(alert_id: int, body: AlertUpdate, user: dict = Depends(get_current_user)):
    from src.db import update_alert
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    alert = update_alert(alert_id, user["id"], **kwargs)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alert


@app.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int, user: dict = Depends(get_current_user)):
    from src.db import delete_alert
    if not delete_alert(alert_id, user["id"]):
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"ok": True}


class RatingBody(BaseModel):
    rating: int = Field(ge=1, le=3)


# ----- Rating endpoints -----

@app.post("/api/rating")
def submit_rating(body: RatingBody, request: Request):
    from src.db import save_rating
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")
    ua = request.headers.get("User-Agent", "")
    ref = request.headers.get("Referer", "")
    result = save_rating(body.rating, ip, ua, ref)
    return {"ok": True, "rating": result}


@app.get("/api/ratings")
def ratings_summary():
    from src.db import get_ratings_summary
    return get_ratings_summary()


@app.get("/api/metrics")
def metrics():
    from src.metrics import PipelineMetrics
    return PipelineMetrics.get().summary()


@app.get("/")
def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"error": "Frontend not found"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
