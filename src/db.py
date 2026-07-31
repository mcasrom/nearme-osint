import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
from datetime import datetime, timedelta, timezone
from typing import Optional
from src.logging import get_logger
from src.models import Event
from src.config import DEFAULT_TTL_HOURS, DEFAULT_TTL_FALLBACK_HOURS, EVENT_STATUS_ACTIVE, EVENT_STATUS_RESOLVED, EVENT_STATUS_UPDATED

logger = get_logger("src.db")

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "nearme_osint"),
    "user": os.environ.get("DB_USER", "nearme"),
    "password": os.environ.get("DB_PASSWORD", "nearme_pass_2026"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
}

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        from src.config import POOL_MINCONN, POOL_MAXCONN
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=POOL_MINCONN,
            maxconn=POOL_MAXCONN,
            **DB_CONFIG,
        )
    return _pool


def get_conn():
    pool = get_pool()
    conn = pool.getconn()
    conn.autocommit = False
    return conn


def release_conn(conn):
    conn.rollback()
    pool = get_pool()
    pool.putconn(conn)


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

    # Migration: add status column if missing (runs before index creation)
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='events' AND column_name='status'
            ) THEN
                ALTER TABLE events ADD COLUMN status TEXT DEFAULT 'active';
            END IF;
        END
        $$;
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id SERIAL PRIMARY KEY,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 3),
            ip TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            page_url TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS saved_locations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_locations_user ON saved_locations(user_id)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS page_views (
            id SERIAL PRIMARY KEY,
            viewed_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_page_views_date ON page_views(viewed_at)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS collector_runs (
            id SERIAL PRIMARY KEY,
            collector TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            latency_s DOUBLE PRECISION NOT NULL,
            events INT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cr_collector ON collector_runs(collector)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cr_ts ON collector_runs(timestamp)")
    conn.commit()
    cur.close()
    release_conn(conn)
    logger.info("Base de datos inicializada")


def _event_to_row(event: Event) -> tuple:
    expires_at = event.expires_at
    if not expires_at:
        ttl_hours = DEFAULT_TTL_HOURS.get(event.event_type, DEFAULT_TTL_FALLBACK_HOURS)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    return (
        event.source, event.source_id, event.event_type, event.subtype,
        event.lat, event.lon, event.radius_m, event.level,
        event.title, event.description, event.country, event.region, event.municipality,
        EVENT_STATUS_ACTIVE,
        psycopg2.extras.Json(event.raw_json) if event.raw_json else None,
        event.lon, event.lat,
        now, event.updated_at, expires_at
    )


def save_event(event: Event) -> int:
    conn = get_conn()
    cur = conn.cursor()
    row = _event_to_row(event)
    cur.execute("""
        INSERT INTO events (source, source_id, event_type, subtype, lat, lon, radius_m,
                            level, title, description, country, region, municipality,
                            status, raw_json, geom, created_at, updated_at, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
        ON CONFLICT (source, source_id)
        DO UPDATE SET
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            radius_m = EXCLUDED.radius_m,
            level = EXCLUDED.level,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            raw_json = EXCLUDED.raw_json,
            geom = EXCLUDED.geom,
            created_at = events.created_at,
            updated_at = NOW(),
            expires_at = events.expires_at
    """, row)
    event_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    release_conn(conn)
    return event_id


def save_events_batch(events: list[Event]) -> int:
    """Batch upsert multiple events in a single connection/transaction."""
    if not events:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    saved = 0
    for event in events:
        try:
            row = _event_to_row(event)
            cur.execute("""
                INSERT INTO events (source, source_id, event_type, subtype, lat, lon, radius_m,
                                    level, title, description, country, region, municipality,
                                    status, raw_json, geom, created_at, updated_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
                ON CONFLICT (source, source_id)
                DO UPDATE SET
                    lat = EXCLUDED.lat,
                    lon = EXCLUDED.lon,
                    radius_m = EXCLUDED.radius_m,
                    level = EXCLUDED.level,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    raw_json = EXCLUDED.raw_json,
                    geom = EXCLUDED.geom,
                    created_at = events.created_at,
                    updated_at = NOW(),
                    expires_at = events.expires_at
            """, row)
            saved += 1
        except Exception as e:
            logger.warning("Error guardando evento batch: %s", e)
    conn.commit()
    cur.close()
    release_conn(conn)
    return saved


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
    conditions.append("status != %s")
    cond_params.append(EVENT_STATUS_RESOLVED)
    where = " AND ".join(conditions)
    params = [lon, lat] + cond_params + [lon, lat, radius_km * 1000, limit]
    cur.execute(f"""
        SELECT id, source, source_id, event_type, subtype, lat, lon, radius_m,
               level, title, description, country, region, municipality,
               status, created_at, updated_at, expires_at,
               ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as distance_m
        FROM events
        WHERE {where}
          AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
        ORDER BY status ASC, distance_m ASC, level DESC, created_at DESC
        LIMIT %s
    """, params)
    rows = cur.fetchall()
    cur.close()
    release_conn(conn)
    result = []
    for r in rows:
        d = dict(r)
        d["distance_km"] = round(d.pop("distance_m", 0) / 1000, 1) if d.get("distance_m") else 0
        d["status"] = d.get("status", EVENT_STATUS_ACTIVE)
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


def resolve_events(source: str, active_ids: set[str]) -> int:
    """Mark events from source not in active_ids as resolved."""
    if not active_ids:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE events
        SET status = %s, updated_at = NOW()
        WHERE source = %s
          AND source_id != ALL(%s)
          AND status = %s
    """, (EVENT_STATUS_RESOLVED, source, list(active_ids), EVENT_STATUS_ACTIVE))
    resolved = cur.rowcount
    conn.commit()
    cur.close()
    release_conn(conn)
    return resolved


def resolve_all_before(source: str, cutoff: str) -> int:
    """Mark events from source last updated before cutoff as resolved."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE events
        SET status = %s, updated_at = NOW()
        WHERE source = %s
          AND updated_at < %s::timestamptz
          AND status = %s
    """, (EVENT_STATUS_RESOLVED, source, cutoff, EVENT_STATUS_ACTIVE))
    resolved = cur.rowcount
    conn.commit()
    cur.close()
    release_conn(conn)
    return resolved


# ----- Collector Runs -----

def save_collector_run(collector: str, success: bool, latency_s: float, events: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO collector_runs (collector, success, latency_s, events) VALUES (%s, %s, %s, %s)",
        (collector, success, round(latency_s, 3), events)
    )
    conn.commit()
    cur.close()
    release_conn(conn)


def get_collector_status() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        WITH latest AS (
            SELECT DISTINCT ON (collector) collector, success, latency_s, events, timestamp
            FROM collector_runs
            ORDER BY collector, timestamp DESC
        ),
        stats AS (
            SELECT collector,
                   COUNT(*) AS total_runs,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successes,
                   SUM(events) AS total_events,
                   MAX(timestamp) AS last_ts
            FROM collector_runs
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY collector
        )
        SELECT l.collector, l.success AS last_success, l.latency_s AS last_latency,
               l.events AS last_events, l.timestamp AS last_run,
               COALESCE(s.total_runs, 0) AS runs_24h,
               COALESCE(s.successes, 0) AS successes_24h,
               COALESCE(s.total_events, 0) AS events_24h
        FROM latest l
        LEFT JOIN stats s ON l.collector = s.collector
        ORDER BY l.collector
    """)
    rows = cur.fetchall()
    cur.close()
    release_conn(conn)
    return [dict(r) for r in rows]


def get_collector_runs(n: int = 50) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT collector, success, latency_s, events, timestamp
        FROM collector_runs
        ORDER BY timestamp DESC, id DESC
        LIMIT %s
    """, (n,))
    rows = cur.fetchall()
    cur.close()
    release_conn(conn)
    return [dict(r) for r in rows]


def get_last_pipeline_run() -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT timestamp, COUNT(*) AS collectors,
               SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successful,
               SUM(events) AS total_events
        FROM collector_runs
        WHERE timestamp > (SELECT MAX(timestamp) - INTERVAL '5 minutes' FROM collector_runs)
        GROUP BY timestamp
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    release_conn(conn)
    return dict(row) if row else None


# ----- Expired cleanup -----

def clean_expired():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE expires_at IS NOT NULL AND expires_at < NOW()")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    release_conn(conn)
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
        release_conn(conn)


def get_user_by_username(username: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, email, password_hash, created_at FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    release_conn(conn)
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, email, created_at FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    release_conn(conn)
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
    release_conn(conn)
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
    release_conn(conn)
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
    release_conn(conn)
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
    release_conn(conn)
    return deleted


# ----- Ratings -----

def save_rating(rating: int, ip: str = "", user_agent: str = "", page_url: str = "") -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO ratings (rating, ip, user_agent, page_url) VALUES (%s, %s, %s, %s) RETURNING id, rating, created_at",
        (rating, ip, user_agent, page_url)
    )
    row = dict(cur.fetchone())
    conn.commit()
    cur.close()
    release_conn(conn)
    if row.get("created_at"):
        row["created_at"] = row["created_at"].isoformat()
    return row


def get_ratings_summary() -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT rating, COUNT(*) as count FROM ratings GROUP BY rating ORDER BY rating")
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) as total FROM ratings")
    total = cur.fetchone()["total"]
    cur.close()
    release_conn(conn)
    dist = {1: 0, 2: 0, 3: 0}
    for r in rows:
        dist[r["rating"]] = r["count"]
    return {"total": total, "distribution": dist, "positive_pct": round(dist.get(3, 0) / max(total, 1) * 100, 1)}


# ----- Saved Locations -----

def create_location(user_id: int, name: str, lat: float, lon: float) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO saved_locations (user_id, name, lat, lon) VALUES (%s, %s, %s, %s) RETURNING id, user_id, name, lat, lon, created_at",
        (user_id, name.strip(), lat, lon)
    )
    row = dict(cur.fetchone())
    conn.commit()
    cur.close()
    release_conn(conn)
    if row.get("created_at"):
        row["created_at"] = row["created_at"].isoformat()
    return row


def get_user_locations(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, user_id, name, lat, lon, created_at FROM saved_locations WHERE user_id = %s ORDER BY created_at ASC",
        (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    release_conn(conn)
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return result


def update_location(location_id: int, user_id: int, name: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "UPDATE saved_locations SET name = %s WHERE id = %s AND user_id = %s RETURNING id, user_id, name, lat, lon, created_at",
        (name.strip(), location_id, user_id)
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    release_conn(conn)
    if row:
        d = dict(row)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        return d
    return None


def delete_location(location_id: int, user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM saved_locations WHERE id = %s AND user_id = %s", (location_id, user_id))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    release_conn(conn)
    return deleted


def record_page_view():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO page_views DEFAULT VALUES")
    conn.commit()
    cur.close()
    release_conn(conn)
    try:
        conn2 = get_conn()
        cur2 = conn2.cursor()
        cur2.execute("DELETE FROM page_views WHERE viewed_at < NOW() - INTERVAL '60 days'")
        conn2.commit()
        cur2.close()
        release_conn(conn2)
    except:
        pass


def get_page_views() -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) as total FROM page_views")
    total = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) as today FROM page_views WHERE viewed_at >= CURRENT_DATE")
    today = cur.fetchone()["today"]
    cur.execute("SELECT COUNT(*) as yesterday FROM page_views WHERE viewed_at >= CURRENT_DATE - INTERVAL '1 day' AND viewed_at < CURRENT_DATE")
    yesterday = cur.fetchone()["yesterday"]
    cur.close()
    release_conn(conn)
    return {"total_views": total, "today_views": today, "yesterday_views": yesterday}
