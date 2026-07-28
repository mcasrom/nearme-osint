import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from typing import Optional
from src.models import Event

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "nearme_osint"),
    "user": os.environ.get("DB_USER", "nearme"),
    "password": os.environ.get("DB_PASSWORD", "nearme_pass_2026"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
}


def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            subtype TEXT DEFAULT '',
            lat DOUBLE PRECISION NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            radius_m DOUBLE PRECISION DEFAULT 0,
            level TEXT DEFAULT 'info',
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            country TEXT DEFAULT '',
            region TEXT DEFAULT '',
            municipality TEXT DEFAULT '',
            raw_json JSONB,
            geom GEOMETRY(Point, 4326),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ,
            UNIQUE(source, source_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_level ON events(level)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_geom ON events USING GIST(geom)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_expires ON events(expires_at) WHERE expires_at IS NOT NULL")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_type TEXT DEFAULT 'all',
            radius_km DOUBLE PRECISION DEFAULT 15,
            min_level TEXT DEFAULT 'warning',
            enabled BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id)")
    conn.commit()
    cur.close()
    conn.close()
    print("[OK] Base de datos inicializada")


def save_event(event: Event) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO events (source, source_id, event_type, subtype, lat, lon, radius_m,
                            level, title, description, country, region, municipality,
                            raw_json, geom, created_at, updated_at, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
        ON CONFLICT (source, source_id)
        DO UPDATE SET
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            radius_m = EXCLUDED.radius_m,
            level = EXCLUDED.level,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            raw_json = EXCLUDED.raw_json,
            geom = EXCLUDED.geom,
            updated_at = NOW(),
            expires_at = EXCLUDED.expires_at
        RETURNING id
    """, (
        event.source, event.source_id, event.event_type, event.subtype,
        event.lat, event.lon, event.radius_m, event.level,
        event.title, event.description, event.country, event.region, event.municipality,
        psycopg2.extras.Json(event.raw_json) if event.raw_json else None,
        event.lon, event.lat,
        event.created_at, event.updated_at, event.expires_at
    ))
    event_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return event_id


def get_events_nearby(lat: float, lon: float, radius_km: float = 25,
                      limit: int = 500, event_type: Optional[str] = None,
                      min_level: Optional[str] = None) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    conditions = []
    cond_params = []
    if event_type:
        conditions.append("event_type = %s")
        cond_params.append(event_type)
    if min_level:
        levels = {"info": 1, "warning": 2, "alert": 3, "critical": 4}
        min_lvl = levels.get(min_level, 1)
        conditions.append("CASE level WHEN 'critical' THEN 4 WHEN 'alert' THEN 3 WHEN 'warning' THEN 2 ELSE 1 END >= %s")
        cond_params.append(min_lvl)
    conditions.append("(expires_at IS NULL OR expires_at > NOW())")
    where = " AND ".join(conditions)
    params = [lon, lat] + cond_params + [lon, lat, radius_km * 1000, limit]
    cur.execute(f"""
        SELECT id, source, source_id, event_type, subtype, lat, lon, radius_m,
               level, title, description, country, region, municipality,
               created_at, updated_at, expires_at,
               ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as distance_m
        FROM events
        WHERE {where}
          AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
        ORDER BY distance_m ASC, level DESC, created_at DESC
        LIMIT %s
    """, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["distance_km"] = round(d.pop("distance_m", 0) / 1000, 1) if d.get("distance_m") else 0
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        if d.get("updated_at"):
            d["updated_at"] = d["updated_at"].isoformat()
        if d.get("expires_at"):
            d["expires_at"] = d["expires_at"].isoformat()
        result.append(d)
    return result


def get_events_summary(lat: float, lon: float, radius_km: float = 25) -> dict:
    nearby = get_events_nearby(lat, lon, radius_km, limit=500)
    summary = {"total": len(nearby), "by_type": {}, "by_level": {}, "critical": []}
    for ev in nearby:
        t = ev["event_type"]
        lvl = ev["level"]
        summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
        summary["by_level"][lvl] = summary["by_level"].get(lvl, 0) + 1
        if lvl in ("alert", "critical"):
            summary["critical"].append(ev)
    return summary


def clean_expired():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE expires_at IS NOT NULL AND expires_at < NOW()")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


# ----- Users & Auth -----

def create_user(username: str, password_hash: str, email: str = "") -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id, username, email, created_at",
            (username, email or None, password_hash)
        )
        user = dict(cur.fetchone())
        conn.commit()
        return user
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, email, password_hash, created_at FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, email, created_at FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


# ----- Alerts CRUD -----

def create_alert(user_id: int, event_type: str = "all", radius_km: float = 15,
                 min_level: str = "warning", enabled: bool = True) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """INSERT INTO alerts (user_id, event_type, radius_km, min_level, enabled)
           VALUES (%s, %s, %s, %s, %s) RETURNING id, user_id, event_type, radius_km, min_level, enabled, created_at""",
        (user_id, event_type, radius_km, min_level, enabled)
    )
    alert = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    if alert.get("created_at"):
        alert["created_at"] = alert["created_at"].isoformat()
    return alert


def get_user_alerts(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, user_id, event_type, radius_km, min_level, enabled, created_at FROM alerts WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return result


def update_alert(alert_id: int, user_id: int, **kwargs) -> dict | None:
    allowed = {"event_type", "radius_km", "min_level", "enabled"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return None
    sets = ", ".join(f"{k} = %s" for k in updates)
    vals = list(updates.values()) + [alert_id, user_id]
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        f"UPDATE alerts SET {sets} WHERE id = %s AND user_id = %s RETURNING id, user_id, event_type, radius_km, min_level, enabled, created_at",
        vals
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if row:
        d = dict(row)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        return d
    return None


def delete_alert(alert_id: int, user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM alerts WHERE id = %s AND user_id = %s", (alert_id, user_id))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    return deleted
