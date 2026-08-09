import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).parent.parent.parent, ".env"), override=True)

import httpx
import jwt
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from passlib.hash import bcrypt
from typing import Optional

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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CHANGE_ME_IN_PRODUCTION")

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


class PushSubscribeBody(BaseModel):
    endpoint: str = Field(min_length=10)
    p256dh: str = Field(min_length=10)
    auth: str = Field(min_length=5)


class PushUnsubscribeBody(BaseModel):
    endpoint: str = Field(min_length=10)


@app.on_event("startup")
def startup():
    from src.db import init_db
    from src.logging import get_logger
    _log = get_logger("src.api.server")
    try:
        init_db()
    except Exception as e:
        _log.error("Error inicializando BD: %s", e)


@app.get("/health")
def health():
    from src.db import get_conn, release_conn
    db_ok = False
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        release_conn(conn)
        db_ok = True
    except Exception:
        db_ok = False

    from src.metrics import PipelineMetrics
    metrics = PipelineMetrics.get()
    summary = metrics.summary()
    last = metrics.last_n(1)

    if summary.get("total_runs", 0) == 0 and db_ok:
        from src.db import get_collector_status
        db_status = get_collector_status()
        total = sum(c.get("runs_24h", 0) for c in db_status)
        ok = sum(c.get("successes_24h", 0) for c in db_status)
        total_events = sum(c.get("events_24h", 0) for c in db_status)
        last_run_ts = max((c["last_run"] for c in db_status if c.get("last_run")), default=None)
        return {
            "status": "ok",
            "service": "NearMe OSINT",
            "version": "0.9",
            "database": "connected",
            "pipeline_total_runs": total,
            "pipeline_success_rate": round(ok / total * 100, 1) if total > 0 else 0,
            "total_events_24h": total_events,
            "last_collector_run": last_run_ts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "service": "NearMe OSINT",
        "version": "0.9",
        "database": "connected" if db_ok else "error",
        "pipeline_total_runs": summary.get("total_runs", 0),
        "pipeline_success_rate": summary.get("success_rate", 0),
        "total_events_24h": summary.get("total_events", 0),
        "last_collector_run": last[0] if last else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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
        "server_ts": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/ccaa-stats")
def ccaa_stats():
    """Eventos críticos/alert por CCAA (spatial join con spain_ccaa).
    Para colorear el mapa territorial del Radar de Emergencias."""
    from src.db import get_conn, release_conn
    import psycopg2.extras
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT c.name AS ccaa,
                   COUNT(*) FILTER (WHERE e.level = 'critical') AS critical,
                   COUNT(*) FILTER (WHERE e.level = 'alert') AS alert,
                   COUNT(*) AS total
            FROM events e
            JOIN spain_ccaa c ON ST_Contains(c.geom, e.geom)
            WHERE e.expires_at > NOW()
              AND e.status != 'resolved'
              AND e.level IN ('critical','alert','warning')
            GROUP BY c.name
            ORDER BY total DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return {"ccaa": rows, "generated": datetime.now(timezone.utc).isoformat()}
    finally:
        release_conn(conn)


@app.get("/api/event/{event_id}")
def event_by_id(event_id: int):
    from src.db import get_event_by_id
    ev = get_event_by_id(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evento no encontrado o expirado")
    return ev


@app.get("/api/event/{event_id}/resources")
def event_resources(event_id: int):
    from src.db import get_event_resources
    data = get_event_resources(event_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Evento no encontrado o expirado")
    return data


@app.get("/api/event/{event_id}/history")
def event_history(event_id: int, limit: int = Query(200, ge=1, le=1000)):
    from src.db import get_event_history
    return {"event_id": event_id, "points": get_event_history(event_id, limit)}


@app.get("/api/timeline")
def timeline(
    start: str = Query(..., description="ISO inicio (UTC)"),
    end: str = Query(..., description="ISO fin (UTC)"),
    step_hours: int = Query(6, ge=1, le=48),
):
    from src.db import get_timeline_counts
    try:
        data = get_timeline_counts(start, end, step_hours)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fechas invalidas: {e}")
    return {"start": start, "end": end, "step_hours": step_hours, "points": data}


@app.get("/api/summary")
def summary(
    lat: float = Query(40.42, description="Latitud"),
    lon: float = Query(-3.70, description="Longitud"),
    radius: float = Query(25, description="Radio en km"),
):
    from src.db import get_events_summary
    s = get_events_summary(lat, lon, radius)
    return {"lat": lat, "lon": lon, "radius_km": radius, **s}


@app.get("/api/rankings")
def rankings(
    lat: float = Query(40.42, description="Latitud"),
    lon: float = Query(-3.70, description="Longitud"),
    radius: float = Query(25, description="Radio en km"),
    limit: int = Query(8, ge=1, le=20),
):
    from src.db import get_rankings, get_trends
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius,
        "top": get_rankings(lat, lon, radius, limit),
        "trends": get_trends(),
    }


@app.get("/api/stats/trends")
def stats_trends(days: int = Query(60, ge=1, le=365)):
    """Estadísticas diarias por fuente (tabla daily_stats, pre-agregada por cron 23:00)."""
    from src.db import get_conn, release_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT stat_date, source, metric, value FROM daily_stats "
            "WHERE stat_date >= CURRENT_DATE - %s::int ORDER BY stat_date",
            (days,))
        rows = cur.fetchall()
    finally:
        release_conn(conn)
    out = {}
    for r in rows:
        sd = r[0]
        d = sd.isoformat() if hasattr(sd, "isoformat") else str(sd)
        out.setdefault(r[1], {}).setdefault(r[2], []).append({"date": d, "value": r[3]})
    return {"days": days, "stats": out}


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


# ----- Web Push endpoints -----

@app.get("/api/push/vapid-key")
def vapid_public_key():
    pub = os.environ.get("VAPID_PUBLIC_KEY", "")
    if not pub:
        raise HTTPException(status_code=500, detail="VAPID no configurado")
    return {"public_key": pub}


@app.post("/api/push/subscribe")
def push_subscribe(body: PushSubscribeBody, user: dict = Depends(get_current_user)):
    from src.db import save_push_subscription
    sub = save_push_subscription(user["id"], body.endpoint, body.p256dh, body.auth)
    return {"ok": True, "id": sub["id"]}


@app.post("/api/push/unsubscribe")
def push_unsubscribe(body: PushUnsubscribeBody, user: dict = Depends(get_current_user)):
    from src.db import delete_push_subscription
    return {"ok": delete_push_subscription(user["id"], body.endpoint)}


# ----- Telegram alerts endpoints -----

TELEGRAM_BOT_USERNAME = "nearme_status_bot"


@app.get("/api/telegram/bot")
def telegram_bot_info():
    return {"username": TELEGRAM_BOT_USERNAME, "handle": "@" + TELEGRAM_BOT_USERNAME, "url": "https://t.me/" + TELEGRAM_BOT_USERNAME}


@app.get("/api/telegram/status")
def telegram_status(user: dict = Depends(get_current_user)):
    from src.db import get_telegram_subscription
    sub = get_telegram_subscription(user["id"])
    if not sub:
        return {"linked": False, "tg_username": None}
    return {"linked": True, "tg_username": sub["tg_username"] or None}


@app.post("/api/telegram/link")
def telegram_link(user: dict = Depends(get_current_user)):
    from src.db import create_telegram_link
    code = create_telegram_link(user["id"])
    return {"code": code, "bot": TELEGRAM_BOT_USERNAME, "expires_min": 10}


@app.post("/api/telegram/unlink")
def telegram_unlink(user: dict = Depends(get_current_user)):
    from src.db import delete_telegram_subscription
    return {"ok": delete_telegram_subscription(user["id"])}


class LocationBody(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    lat: float
    lon: float


# ----- Saved Locations endpoints -----

@app.get("/api/locations")
def list_locations(user: dict = Depends(get_current_user)):
    from src.db import get_user_locations
    return {"locations": get_user_locations(user["id"])}


@app.post("/api/locations")
def create_location(body: LocationBody, user: dict = Depends(get_current_user)):
    from src.db import create_location
    loc = create_location(user["id"], body.name, body.lat, body.lon)
    return loc


@app.delete("/api/locations/{location_id}")
def delete_location(location_id: int, user: dict = Depends(get_current_user)):
    from src.db import delete_location
    if not delete_location(location_id, user["id"]):
        raise HTTPException(status_code=404, detail="Ubicacion no encontrada")
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


@app.get("/api/status")
def collector_status():
    from src.db import get_collector_status
    return {"collectors": get_collector_status()}


@app.get("/api/status/pipeline")
def pipeline_status():
    from src.db import get_last_pipeline_run
    return get_last_pipeline_run() or {"timestamp": None, "collectors": 0, "successful": 0, "total_events": 0}


@app.get("/api/status/runs")
def collector_runs(n: int = 50):
    from src.db import get_collector_runs
    return {"runs": get_collector_runs(n)}


@app.get("/api/metrics")
def metrics():
    from src.metrics import PipelineMetrics
    summary = PipelineMetrics.get().summary()
    if summary.get("total_runs", 0) > 0:
        return summary
    from src.db import get_collector_status
    db_status = get_collector_status()
    if not db_status:
        return summary
    total = sum(c.get("runs_24h", 0) for c in db_status)
    ok = sum(c.get("successes_24h", 0) for c in db_status)
    total_events = sum(c.get("events_24h", 0) for c in db_status)
    total_latency = sum(c.get("last_latency", 0) for c in db_status if c.get("last_latency"))
    by_collector = {}
    for c in db_status:
        by_collector[c["collector"]] = {
            "runs": c.get("runs_24h", 0),
            "successes": c.get("successes_24h", 0),
            "total_events": c.get("events_24h", 0),
            "total_latency": c.get("last_latency", 0),
        }
    return {
        "total_runs": total,
        "success_rate": round(ok / total * 100, 1) if total > 0 else 0,
        "total_events": total_events,
        "total_latency_s": round(total_latency, 2),
        "by_collector": by_collector,
        "source": "db",
    }


@app.get("/admin")
def serve_admin():
    admin = FRONTEND_DIR / "admin.html"
    if admin.exists():
        return FileResponse(str(admin))
    return {"error": "Admin page not found"}


@app.post("/api/admin/check")
def admin_check(body: dict):
    return {"ok": body.get("password", "") == ADMIN_PASSWORD}


@app.get("/")
def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"error": "Frontend not found"}


@app.get("/firms")
def serve_firms():
    firms = FRONTEND_DIR / "firms.html"
    if firms.exists():
        return FileResponse(str(firms))
    return {"error": "Page not found"}


@app.get("/calidad-aire")
def serve_calidad_aire():
    page = FRONTEND_DIR / "calidad-aire.html"
    if page.exists():
        return FileResponse(str(page))
    return {"error": "Page not found"}


@app.get("/robots.txt")
def serve_robots():
    robots = FRONTEND_DIR / "robots.txt"
    if robots.exists():
        return FileResponse(str(robots), media_type="text/plain")
    return {"error": "Not found"}


@app.get("/sitemap.xml")
def serve_sitemap():
    sitemap = FRONTEND_DIR / "sitemap.xml"
    if sitemap.exists():
        return FileResponse(str(sitemap), media_type="application/xml")
    return {"error": "Not found"}


INDEXNOW_KEY = "133a9cae0b643b77df12b5282f23fba9"


@app.get("/indexnow.key")
def serve_indexnow_key():
    return Response(content=INDEXNOW_KEY, media_type="text/plain")


@app.post("/api/visit")
def record_visit():
    from src.db import record_page_view
    try:
        record_page_view()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/stats")
def page_stats():
    from src.db import get_page_views
    try:
        return get_page_views()
    except Exception as e:
        return {"total_views": 0, "today_views": 0, "yesterday_views": 0, "error": str(e)}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
