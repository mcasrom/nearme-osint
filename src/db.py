import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from typing import Optional
from src.models import Event

DB_CONFIG = {
    "dbname": "nearme_osint",
    "user": "nearme",
    "password": "nearme_pass_2026",
    "host": "localhost",
    "port": 5432,
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
                      limit: int = 100, event_type: Optional[str] = None,
                      min_level: Optional[str] = None) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    conditions = ["expires_at IS NULL OR expires_at > NOW()"]
    params = []
    if event_type:
        conditions.append("event_type = %s")
        params.append(event_type)
    if min_level:
        levels = {"info": 1, "warning": 2, "alert": 3, "critical": 4}
        min_lvl = levels.get(min_level, 1)
        conditions.append(f"CASE level WHEN 'critical' THEN 4 WHEN 'alert' THEN 3 WHEN 'warning' THEN 2 ELSE 1 END >= %s")
        params.append(min_lvl)
    where = " AND ".join(conditions) if conditions else "TRUE"
    params.extend([lon, lat, radius_km * 1000, lon, lat, limit])
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
