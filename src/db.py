import json
import os
from pathlib import Path
import psycopg2
import psycopg2.extras
import psycopg2.pool
from datetime import datetime, timedelta, timezone
from typing import Optional
from src.logging import get_logger
from src.models import Event
from src.config import DEFAULT_TTL_HOURS, DEFAULT_TTL_FALLBACK_HOURS, EVENT_STATUS_ACTIVE, EVENT_STATUS_RESOLVED, EVENT_STATUS_UPDATED, SOURCE_CONFIDENCE

logger = get_logger("src.db")

DISASTER_TYPES = {"fire", "flood", "earthquake", "storm", "wind", "snow", "heatwave"}
EMERGENCY_LEVELS = {"alert", "critical"}

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
        CREATE TABLE IF NOT EXISTS daily_stats (
            stat_date DATE NOT NULL,
            source TEXT NOT NULL,
            metric TEXT NOT NULL,
            value DOUBLE PRECISION,
            PRIMARY KEY(stat_date, source, metric)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(stat_date)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_history (
            id BIGSERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            event_type TEXT NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            level TEXT,
            status TEXT,
            title TEXT,
            snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event_history_event ON event_history(event_id, snapshot_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event_history_time ON event_history(snapshot_at)")
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            endpoint TEXT UNIQUE NOT NULL,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ps_user ON push_subscriptions(user_id)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS push_sent (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            alert_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            level TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT 'push',
            sent_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='push_sent' AND column_name='channel'
            ) THEN
                ALTER TABLE push_sent ADD COLUMN channel TEXT NOT NULL DEFAULT 'push';
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'push_sent_user_id_alert_id_event_id_level_key'
            ) THEN
                ALTER TABLE push_sent DROP CONSTRAINT push_sent_user_id_alert_id_event_id_level_key;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'push_sent_dedup_key'
            ) THEN
                ALTER TABLE push_sent ADD CONSTRAINT push_sent_dedup_key
                    UNIQUE (user_id, alert_id, event_id, level, channel);
            END IF;
        END
        $$;
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_psent_sent ON push_sent(sent_at)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_links (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tglinks_user ON telegram_links(user_id)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            chat_id BIGINT UNIQUE NOT NULL,
            tg_username TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (user_id)
        )
    """)
    # Capa de CCAA + directorio de recursos de emergencia (panel de emergencia)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spain_ccaa (
            cod_ccaa TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            geom GEOMETRY(MultiPolygon, 4326) NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ccaa_geom ON spain_ccaa USING GIST(geom)")
    _ensure_ccaa_layer(cur)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS emergency_resources (
            id SERIAL PRIMARY KEY,
            ccaa_code TEXT NOT NULL REFERENCES spain_ccaa(cod_ccaa) ON DELETE CASCADE,
            resource_type TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            url TEXT DEFAULT '',
            active BOOLEAN DEFAULT true,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_er_ccaa ON emergency_resources(ccaa_code)")
    _seed_emergency_resources(cur)

    conn.commit()
    cur.close()
    release_conn(conn)
    logger.info("Base de datos inicializada")


def _ensure_ccaa_layer(cur):
    """Carga los límites de CCAA desde assets/spain-ccaa.geojson si la tabla está vacía."""
    cur.execute("SELECT count(*) FROM spain_ccaa")
    if cur.fetchone()[0] > 0:
        return
    path = Path(__file__).resolve().parent.parent / "assets" / "spain-ccaa.geojson"
    if not path.exists():
        logger.warning("[ccaa] geojson no encontrado: %s", path)
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("[ccaa] error leyendo geojson: %s", e)
        return
    n = 0
    for f in data.get("features", []):
        props = f.get("properties", {})
        code = str(props.get("cod_ccaa") or "").strip()
        name = str(props.get("noml_ccaa") or props.get("name") or code).strip()
        if not code or not f.get("geometry"):
            continue
        cur.execute(
            "INSERT INTO spain_ccaa (cod_ccaa, name, geom) VALUES (%s, %s, "
            "ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)) "
            "ON CONFLICT (cod_ccaa) DO UPDATE SET name = EXCLUDED.name, geom = EXCLUDED.geom",
            (code, name, json.dumps(f["geometry"])))
        n += 1
    logger.info("[ccaa] capa de CCAA cargada (%d features)", n)


def _seed_emergency_resources(cur):
    """Siembra el directorio de recursos (Cruz Roja + Protección Civil) por CCAA con datos oficiales reales."""
    cur.execute("SELECT count(*) FROM emergency_resources")
    if cur.fetchone()[0] > 0:
        return
    cur.execute("SELECT cod_ccaa FROM spain_ccaa")
    ccaas = [r[0] for r in cur.fetchall()]
    rows = [
        ("cruz_roja", "Cruz Roja", "900 22 11 22", "https://www.cruzroja.es/"),
        ("proteccion_civil", "Protección Civil", "112", "https://www.proteccioncivil.es/"),
    ]
    for code in ccaas:
        for rtype, rname, phone, url in rows:
            cur.execute(
                "INSERT INTO emergency_resources (ccaa_code, resource_type, name, phone, url) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (code, rtype, rname, phone, url))
    logger.info("[ccaa] recursos de emergencia sembrados (%d CCAA x %d)", len(ccaas), len(rows))


def get_ccaa_for_point(lat: float, lon: float) -> Optional[dict]:
    """Devuelve {code, name} de la CCAA que contiene el punto, o None."""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT cod_ccaa AS code, name FROM spain_ccaa "
            "WHERE ST_Within(ST_SetSRID(ST_MakePoint(%s, %s), 4326), geom) LIMIT 1",
            (lon, lat))
        r = cur.fetchone()
        cur.close()
        return dict(r) if r else None
    finally:
        release_conn(conn)


def get_event_resources(event_id: int) -> Optional[dict]:
    """Recursos de emergencia para un evento que cualifica (alert/critical + tipo desastre)."""
    ev = get_event_by_id(event_id)
    if not ev:
        return None
    result = {"qualified": False, "phone_112": "112", "ccaa": None, "resources": []}
    if ev.get("level") not in EMERGENCY_LEVELS or ev.get("event_type") not in DISASTER_TYPES:
        return result
    if ev.get("lat") is None or ev.get("lon") is None:
        return result
    ccaa = get_ccaa_for_point(ev["lat"], ev["lon"])
    if not ccaa:
        return result
    result["qualified"] = True
    result["ccaa"] = ccaa
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT resource_type, name, phone, url FROM emergency_resources "
            "WHERE ccaa_code = %s AND active ORDER BY resource_type", (ccaa["code"],))
        result["resources"] = list(cur.fetchall())
        cur.close()
    finally:
        release_conn(conn)
    return result


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
            expires_at = EXCLUDED.expires_at
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
            cur.execute(
                "SELECT id, level, status, lat, lon, title FROM events WHERE source=%s AND source_id=%s",
                (event.source, event.source_id))
            existing = cur.fetchone()
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
                    expires_at = EXCLUDED.expires_at
                RETURNING id
            """, row)
            event_id = cur.fetchone()[0]
            changed = existing is None or (
                existing[1] != event.level or existing[2] != event.status
                or abs(existing[3] - event.lat) > 1e-6 or abs(existing[4] - event.lon) > 1e-6
                or existing[5] != event.title
            )
            if changed:
                cur.execute(
                    "INSERT INTO event_history (event_id, source, event_type, lat, lon, level, status, title) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (event_id, event.source, event.event_type, event.lat, event.lon,
                     event.level, event.status, event.title))
            saved += 1
        except Exception as e:
            logger.warning("Error guardando evento batch: %s", e)
    conn.commit()
    cur.close()
    release_conn(conn)
    return saved


def get_event_history(event_id: int, limit: int = 200):
    """Snapshots de un evento a lo largo del tiempo (para track patterns)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT snapshot_at, level, status, lat, lon, title FROM event_history "
        "WHERE event_id=%s ORDER BY snapshot_at ASC LIMIT %s",
        (event_id, limit))
    rows = cur.fetchall()
    cur.close()
    release_conn(conn)
    return [
        {"ts": r[0].isoformat(), "level": r[1], "status": r[2],
         "lat": r[3], "lon": r[4], "title": r[5]}
        for r in rows
    ]


def get_timeline_counts(start: str, end: str, step_hours: int = 6):
    """Nº de eventos activos por ventana de tiempo (playback)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        WITH buckets AS (
            SELECT generate_series(%s::timestamptz, %s::timestamptz,
                                   make_interval(hours => %s)) AS ts
        )
        SELECT to_char(b.ts, 'YYYY-MM-DD"T"HH24:MI') AS bucket,
               COUNT(ev.id) AS active
        FROM buckets b
        LEFT JOIN LATERAL (
            SELECT e.id FROM events e
            WHERE e.created_at <= b.ts
              AND (e.expires_at IS NULL OR e.expires_at > b.ts)
        ) ev ON TRUE
        GROUP BY b.ts
        ORDER BY b.ts
    """, (start, end, step_hours))
    rows = cur.fetchall()
    cur.close()
    release_conn(conn)
    return [{"bucket": r[0], "active": r[1]} for r in rows]


def cleanup_history_retention(days: int = 365) -> dict:
    """Política de rotación: borra historial y eventos resueltos antiguos (>days)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM event_history WHERE snapshot_at < %s", (cutoff,))
    h_del = cur.rowcount
    cur.execute("DELETE FROM events WHERE status=%s AND updated_at < %s",
                (EVENT_STATUS_RESOLVED, cutoff))
    e_del = cur.rowcount
    conn.commit()
    cur.close()
    release_conn(conn)
    logger.info("[retention] limpieza %s dias: %s historial, %s eventos resueltos borrados",
                days, h_del, e_del)
    return {"history_deleted": h_del, "events_deleted": e_del}


def get_event_by_id(event_id: int) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, source, source_id, event_type, subtype, lat, lon, radius_m,
               level, title, description, country, region, municipality,
               status, created_at, updated_at, expires_at
        FROM events
        WHERE id = %s
          AND status != %s
          AND (expires_at > NOW() OR (expires_at IS NULL AND updated_at > NOW() - INTERVAL '2 hours'))
    """, (event_id, EVENT_STATUS_RESOLVED))
    row = cur.fetchone()
    cur.close()
    release_conn(conn)
    if not row:
        return None
    d = dict(row)
    d["status"] = d.get("status", EVENT_STATUS_ACTIVE)
    d["distance_km"] = 0.0
    d["confidence"] = event_confidence(d.get("source", ""), d.get("updated_at"))
    for k in ("created_at", "updated_at", "expires_at"):
        if d.get(k):
            d[k] = d[k].isoformat()
    return d


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
    conditions.append("(expires_at > NOW() OR (expires_at IS NULL AND updated_at > NOW() - INTERVAL '2 hours'))")
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
        d["confidence"] = event_confidence(d.get("source", ""), d.get("updated_at"))
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



def event_confidence(source: str, updated_at) -> int:
    """Score 0-100: fiabilidad de la fuente x frescura."""
    base = SOURCE_CONFIDENCE.get(source, 60)
    if not updated_at:
        return base
    age = datetime.now(timezone.utc) - updated_at
    hours = age.total_seconds() / 3600
    if hours < 0.5:
        fresh = 1.0
    elif hours < 2:
        fresh = 0.9
    elif hours < 6:
        fresh = 0.75
    elif hours < 12:
        fresh = 0.55
    else:
        fresh = 0.35
    return max(10, min(99, round(base * fresh)))




def get_rankings(lat: float, lon: float, radius_km: float = 25, limit: int = 8) -> list[dict]:
    """Top zonas (municipio) por nº de eventos activos en el radio."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT municipality AS name, region, COUNT(*) AS count,
               MAX(CASE level WHEN 'critical' THEN 4 WHEN 'alert' THEN 3 WHEN 'warning' THEN 2 ELSE 1 END) AS max_lvl
        FROM events
        WHERE status != %s
          AND (expires_at > NOW() OR (expires_at IS NULL AND updated_at > NOW() - INTERVAL '2 hours'))
          AND municipality IS NOT NULL AND municipality != ''
          AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
        GROUP BY municipality, region
        ORDER BY count DESC
        LIMIT %s
    """, (EVENT_STATUS_RESOLVED, lon, lat, radius_km * 1000, limit))
    rows = cur.fetchall()
    cur.close()
    release_conn(conn)
    lvl_names = {4: "critical", 3: "alert", 2: "warning", 1: "info"}
    return [{"name": r["name"], "region": r["region"], "count": r["count"],
             "max_level": lvl_names.get(r["max_lvl"], "info")} for r in rows]


def get_trends(hours: int = 24, bucket_hours: int = 2) -> dict:
    """Serie temporal (bucket_hours) de eventos creados + hoy vs ayer (Europe/Madrid)."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT to_char(date_trunc('hour', created_at), 'HH24:00') AS label, COUNT(*) AS count
        FROM events
        WHERE created_at >= NOW() - INTERVAL '%s hours'
        GROUP BY 1
        ORDER BY 1
    """, (hours,))
    raw = cur.fetchall()
    cur.execute("""
        SELECT
          COUNT(*) FILTER (WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'Europe/Madrid')::timestamptz) AS hoy,
          COUNT(*) FILTER (WHERE created_at < date_trunc('day', NOW() AT TIME ZONE 'Europe/Madrid')::timestamptz
                           AND created_at >= (date_trunc('day', NOW() AT TIME ZONE 'Europe/Madrid') - INTERVAL '1 day')::timestamptz) AS ayer
        FROM events
        WHERE created_at >= NOW() - INTERVAL '2 days'
    """)
    day = cur.fetchone()
    cur.close()
    release_conn(conn)
    series = []
    for r in raw:
        try:
            h = int(r["label"].split(":")[0])
            series.append({"label": r["label"], "count": r["count"], "idx": h})
        except (ValueError, IndexError):
            continue
    return {"bucket_hours": bucket_hours, "series": series,
            "hoy": day["hoy"] or 0, "ayer": day["ayer"] or 0}
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


# ---------- Web Push ----------

def save_push_subscription(user_id: int, endpoint: str, p256dh: str, auth: str) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (endpoint) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            p256dh = EXCLUDED.p256dh,
            auth = EXCLUDED.auth
        RETURNING id, user_id, endpoint, created_at
    """, (user_id, endpoint, p256dh, auth))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    release_conn(conn)
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def delete_push_subscription(user_id: int, endpoint: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM push_subscriptions WHERE user_id = %s AND endpoint = %s", (user_id, endpoint))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    release_conn(conn)
    return deleted


def get_push_subscriptions(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, user_id, endpoint, p256dh, auth, created_at FROM push_subscriptions WHERE user_id = %s",
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


def get_push_users() -> list[int]:
    """Usuarios con alertas activas (candidatos a push)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT user_id FROM alerts WHERE enabled = true")
    rows = [r[0] for r in cur.fetchall()]
    cur.close()
    release_conn(conn)
    return rows


def push_sent_exists(user_id: int, alert_id: int, event_id: int, level: str, channel: str = "push") -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM push_sent WHERE user_id = %s AND alert_id = %s AND event_id = %s AND level = %s AND channel = %s",
        (user_id, alert_id, event_id, level, channel)
    )
    found = cur.fetchone() is not None
    cur.close()
    release_conn(conn)
    return found


def get_sent_keys(user_id: int, channel: str = "push") -> set:
    """Claves (alert_id, event_id, level) ya notificadas por un canal."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT alert_id, event_id, level FROM push_sent WHERE user_id = %s AND channel = %s",
        (user_id, channel)
    )
    rows = {(r[0], r[1], r[2]) for r in cur.fetchall()}
    cur.close()
    release_conn(conn)
    return rows


def mark_push_sent(user_id: int, alert_id: int, event_id: int, level: str, channel: str = "push") -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO push_sent (user_id, alert_id, event_id, level, channel) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (user_id, alert_id, event_id, level, channel)
    )
    conn.commit()
    cur.close()
    release_conn(conn)


def prune_push_sent(hours: int = 48) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM push_sent WHERE sent_at < NOW() - INTERVAL '%s hours'", (hours,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    release_conn(conn)
    return deleted


# ---------- Telegram alerts ----------

def create_telegram_link(user_id: int) -> str:
    """Genera un codigo de enlace de un solo uso (10 min) para vincular Telegram."""
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(alphabet) for _ in range(8))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM telegram_links WHERE user_id = %s AND used = false", (user_id,))
    cur.execute(
        "INSERT INTO telegram_links (user_id, code, expires_at) VALUES (%s, %s, NOW() + INTERVAL '10 minutes')",
        (user_id, code)
    )
    conn.commit()
    cur.close()
    release_conn(conn)
    return code


def consume_telegram_link(code: str) -> int | None:
    """Marca el codigo como usado y devuelve el user_id asociado (o None)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id FROM telegram_links WHERE code = %s AND used = false AND expires_at > NOW()",
        (code.strip().upper(),)
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        release_conn(conn)
        return None
    user_id = row[0]
    cur.execute("UPDATE telegram_links SET used = true WHERE code = %s", (code.strip().upper(),))
    conn.commit()
    cur.close()
    release_conn(conn)
    return user_id


def save_telegram_subscription(user_id: int, chat_id: int, tg_username: str = "") -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("DELETE FROM telegram_subscriptions WHERE chat_id = %s", (chat_id,))
    cur.execute("DELETE FROM telegram_subscriptions WHERE user_id = %s", (user_id,))
    cur.execute("""
        INSERT INTO telegram_subscriptions (user_id, chat_id, tg_username)
        VALUES (%s, %s, %s)
        RETURNING id, user_id, chat_id, tg_username, created_at
    """, (user_id, chat_id, tg_username))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    release_conn(conn)
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def get_telegram_subscription(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, user_id, chat_id, tg_username, created_at FROM telegram_subscriptions WHERE user_id = %s",
        (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    release_conn(conn)
    if not row:
        return None
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def get_telegram_chat(user_id: int) -> int | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM telegram_subscriptions WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    release_conn(conn)
    return row[0] if row else None


def delete_telegram_subscription(user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM telegram_subscriptions WHERE user_id = %s", (user_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    release_conn(conn)
    return deleted


def delete_telegram_subscription_by_chat(chat_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM telegram_subscriptions WHERE chat_id = %s", (chat_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    release_conn(conn)
    return deleted
