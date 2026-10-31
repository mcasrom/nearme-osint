#!/usr/bin/env python3
"""Carga el GTFS estático de Renfe en las tablas de referencia de NearMe."""
import argparse
import csv
import io
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import psycopg2.extras

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn, release_conn  # noqa: E402

URLS = {
    "cercanias": "https://ssl.renfe.com/ftransit/Fichero_CER_FOMENTO/fomento_transit.zip",
    "alta_velocidad": "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip",
}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
SCHEMA = """
CREATE TABLE IF NOT EXISTS renfe_gtfs_stops (
    feed TEXT NOT NULL,
    stop_id TEXT NOT NULL,
    stop_name TEXT,
    stop_lat DOUBLE PRECISION,
    stop_lon DOUBLE PRECISION,
    PRIMARY KEY (feed, stop_id)
);
CREATE TABLE IF NOT EXISTS renfe_gtfs_trips (
    feed TEXT NOT NULL,
    trip_id TEXT NOT NULL,
    route_id TEXT,
    route_short_name TEXT,
    route_long_name TEXT,
    origin_stop_id TEXT,
    origin_name TEXT,
    dest_stop_id TEXT,
    dest_name TEXT,
    PRIMARY KEY (feed, trip_id)
);
CREATE TABLE IF NOT EXISTS renfe_gtfs_meta (
    feed TEXT PRIMARY KEY,
    updated_at TIMESTAMPTZ NOT NULL,
    source_url TEXT NOT NULL,
    n_stops INTEGER NOT NULL,
    n_trips INTEGER NOT NULL
);
"""


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def rows(zf, name):
    with zf.open(name) as fh:
        reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
        for row in reader:
            yield {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def parse_gtfs(data, feed):
    zf = zipfile.ZipFile(io.BytesIO(data))
    stops = {}
    for row in rows(zf, "stops.txt"):
        stop_id = row.get("stop_id") or ""
        if not stop_id:
            continue
        try:
            lat = float(row.get("stop_lat") or 0)
            lon = float(row.get("stop_lon") or 0)
        except ValueError:
            lat = lon = None
        stops[stop_id] = (row.get("stop_name") or stop_id, lat, lon)

    routes = {}
    for row in rows(zf, "routes.txt"):
        rid = row.get("route_id") or ""
        if rid:
            short = re.sub(r"\s+", " ", row.get("route_short_name") or "").strip()
            long = re.sub(r"\s+", " ", row.get("route_long_name") or "").strip()
            routes[rid] = (short, long)

    first = {}
    last = {}
    for row in rows(zf, "stop_times.txt"):
        trip_id = row.get("trip_id") or ""
        stop_id = row.get("stop_id") or ""
        try:
            seq = int(float(row.get("stop_sequence") or 0))
        except ValueError:
            continue
        if not trip_id or not stop_id:
            continue
        prev = first.get(trip_id)
        if prev is None or seq < prev[0]:
            first[trip_id] = (seq, stop_id)
        prev = last.get(trip_id)
        if prev is None or seq > prev[0]:
            last[trip_id] = (seq, stop_id)

    trips = []
    for row in rows(zf, "trips.txt"):
        trip_id = row.get("trip_id") or ""
        if not trip_id:
            continue
        route_id = row.get("route_id") or ""
        short, long = routes.get(route_id, ("", ""))
        oid = first.get(trip_id, (0, ""))[1]
        did = last.get(trip_id, (0, ""))[1]
        trips.append((
            feed, trip_id, route_id, short, long,
            oid, stops.get(oid, ("",))[0],
            did, stops.get(did, ("",))[0],
        ))
    return stops, trips


def apply(feed, source_url, stops, trips):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(SCHEMA)
        cur.execute("DELETE FROM renfe_gtfs_stops WHERE feed=%s", (feed,))
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO renfe_gtfs_stops (feed, stop_id, stop_name, stop_lat, stop_lon) VALUES %s",
            [(feed, sid, name, lat, lon) for sid, (name, lat, lon) in stops.items()],
            page_size=500,
        )
        cur.execute("DELETE FROM renfe_gtfs_trips WHERE feed=%s", (feed,))
        if trips:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO renfe_gtfs_trips "
                "(feed, trip_id, route_id, route_short_name, route_long_name, "
                " origin_stop_id, origin_name, dest_stop_id, dest_name) VALUES %s",
                trips,
                page_size=500,
            )
        cur.execute(
            "INSERT INTO renfe_gtfs_meta (feed, updated_at, source_url, n_stops, n_trips) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (feed) DO UPDATE SET updated_at=EXCLUDED.updated_at, "
            "source_url=EXCLUDED.source_url, n_stops=EXCLUDED.n_stops, n_trips=EXCLUDED.n_trips",
            (feed, datetime.now(timezone.utc), source_url, len(stops), len(trips)),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_conn(conn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", choices=sorted(URLS), action="append")
    args = ap.parse_args()
    feeds = args.feed or sorted(URLS)
    for feed in feeds:
        data = download(URLS[feed])
        stops, trips = parse_gtfs(data, feed)
        apply(feed, URLS[feed], stops, trips)
        print(f"{feed}: {len(stops)} paradas · {len(trips)} viajes")


if __name__ == "__main__":
    main()
