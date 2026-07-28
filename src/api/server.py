import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
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


# ----- Auth helpers -----

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"


def check_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) != 2:
        return False
    salt, expected = parts
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return h == expected


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


# ----- Auth endpoints -----

@app.post("/api/auth/register")
def register(body: RegisterBody):
    from src.db import create_user
    pw_hash = hash_password(body.password)
    user = create_user(body.username.strip(), pw_hash, body.email.strip())
    if not user:
        raise HTTPException(status_code=409, detail="El nombre de usuario ya existe")
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


@app.get("/")
def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"error": "Frontend not found"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
