#!/usr/bin/env python3
"""Auditoría read-only de los feeds JSON de Renfe AV/LD/MD."""
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn  # noqa: E402

UA = "Mozilla/5.0 (compatible; NearMeAudit/1.0)"
URLS = {
    "trip_updates": "https://gtfsrt.renfe.com/trip_updates_LD.json",
    "vehicles": "https://gtfsrt.renfe.com/vehicle_positions_LD.json",
}
OUT = Path("/home/deploy/nearme-osint/data/audit_renfe_ld.json")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read())


def stamp(value):
    try:
        return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
    except Exception:
        return None


def date_of(trip_id):
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", trip_id or "")
    return m.group(1) if m else None


def audit_trips(data):
    entities = data.get("entity") or []
    trips = {}
    stop_updates = 0
    delays = 0
    missing_delay = 0
    relationships = Counter()
    missing_stop = 0
    for entity in entities:
        tu = entity.get("tripUpdate") or {}
        trip = tu.get("trip") or {}
        trip_id = trip.get("tripId")
        if not trip_id:
            continue
        stus = tu.get("stopTimeUpdate") or []
        trips[trip_id] = {"trip_id": trip_id, "route_id": trip.get("routeId"), "stops": len(stus)}
        stop_updates += len(stus)
        for stu in stus:
            rel = stu.get("scheduleRelationship")
            relationships[str(rel)] += 1
            if not stu.get("stopId"):
                missing_stop += 1
            evt = stu.get("arrival") or stu.get("departure") or {}
            if evt.get("delay") is None:
                missing_delay += 1
            else:
                delays += 1
    return {
        "header_timestamp": stamp((data.get("header") or {}).get("timestamp")),
        "header_age_min": round((datetime.now(timezone.utc) - datetime.fromtimestamp(int((data.get("header") or {}).get("timestamp") or 0), timezone.utc)).total_seconds() / 60, 1) if (data.get("header") or {}).get("timestamp") else None,
        "entities": len(entities),
        "trips": len(trips),
        "stop_updates": stop_updates,
        "delays": delays,
        "missing_delay": missing_delay,
        "missing_stop_id": missing_stop,
        "relationships": dict(relationships),
        "service_dates": dict(Counter(date_of(t) for t in trips)),
        "trip_rows": list(trips.values()),
    }


def audit_vehicles(data):
    entities = data.get("entity") or []
    vehicles = []
    missing_pos = 0
    missing_trip = 0
    for entity in entities:
        v = entity.get("vehicle") or {}
        trip = v.get("trip") or {}
        pos = v.get("position") or {}
        trip_id = trip.get("tripId")
        lat, lon = pos.get("latitude"), pos.get("longitude")
        if not trip_id:
            missing_trip += 1
        if lat is None or lon is None:
            missing_pos += 1
        vehicles.append({
            "trip_id": trip_id, "route_id": trip.get("routeId"), "lat": lat, "lon": lon,
            "timestamp": stamp(v.get("timestamp") or pos.get("timestamp")),
            "bearing": pos.get("bearing"), "speed": pos.get("speed"),
        })
    return {
        "header_timestamp": stamp((data.get("header") or {}).get("timestamp")),
        "header_age_min": round((datetime.now(timezone.utc) - datetime.fromtimestamp(int((data.get("header") or {}).get("timestamp") or 0), timezone.utc)).total_seconds() / 60, 1) if (data.get("header") or {}).get("timestamp") else None,
        "entities": len(entities),
        "vehicles": len(vehicles),
        "missing_trip_id": missing_trip,
        "missing_position": missing_pos,
        "service_dates": dict(Counter(date_of(v["trip_id"]) for v in vehicles)),
        "vehicle_rows": vehicles,
    }


def static_refs(trip_ids, stop_ids):
    cur = get_conn().cursor()
    trips = {}
    for i in range(0, len(trip_ids), 500):
        chunk = list(trip_ids)[i:i + 500]
        cur.execute("SELECT trip_id, route_short_name, origin_name, dest_name FROM renfe_gtfs_trips WHERE feed='alta_velocidad' AND trip_id = ANY(%s)", (chunk,))
        for tid, service, origin, dest in cur.fetchall():
            trips[tid] = {"service": service, "origin": origin, "dest": dest}
    stops = set()
    for i in range(0, len(stop_ids), 500):
        chunk = list(stop_ids)[i:i + 500]
        cur.execute("SELECT stop_id FROM renfe_gtfs_stops WHERE feed='alta_velocidad' AND stop_id = ANY(%s)", (chunk,))
        stops.update(r[0] for r in cur.fetchall())
    return trips, stops


def main():
    status_t, trip_data = fetch(URLS["trip_updates"])
    status_v, vehicle_data = fetch(URLS["vehicles"])
    trips = audit_trips(trip_data)
    vehicles = audit_vehicles(vehicle_data)
    trip_ids = {x["trip_id"] for x in trips["trip_rows"]}
    vehicle_trip_ids = {x["trip_id"] for x in vehicles["vehicle_rows"] if x["trip_id"]}
    stop_ids = set()
    for row in trips["trip_rows"]:
        tu = next((e.get("tripUpdate") for e in trip_data.get("entity", []) if (e.get("tripUpdate") or {}).get("trip", {}).get("tripId") == row["trip_id"]), None)
        if not tu:
            continue
        for stu in tu.get("stopTimeUpdate") or []:
            if stu.get("stopId"):
                stop_ids.add(stu["stopId"])
    static_trips, static_stops = static_refs(trip_ids | vehicle_trip_ids, stop_ids)
    matched = trip_ids & set(static_trips)
    matched_vehicles = vehicle_trip_ids & set(static_trips)
    services = Counter(static_trips[t]["service"] or "s/d" for t in matched)
    for row in trips["trip_rows"]:
        ref = static_trips.get(row["trip_id"]) or {}
        row["service"] = ref.get("service")
        row["origin"] = ref.get("origin")
        row["dest"] = ref.get("dest")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "trip_updates": {"url": URLS["trip_updates"], "status": status_t},
            "vehicles": {"url": URLS["vehicles"], "status": status_v},
        },
        "trip_updates": {k: v for k, v in trips.items() if k != "trip_rows"},
        "vehicles": {k: v for k, v in vehicles.items() if k != "vehicle_rows"},
        "coverage": {
            "trip_updates_trips": len(trip_ids),
            "static_trips_matched": len(matched),
            "static_trip_pct": round(len(matched) * 100 / len(trip_ids), 1) if trip_ids else 0,
            "vehicle_trips": len(vehicle_trip_ids),
            "vehicle_trips_matched": len(matched_vehicles),
            "vehicle_trip_pct": round(len(matched_vehicles) * 100 / len(vehicle_trip_ids), 1) if vehicle_trip_ids else 0,
            "stop_ids": len(stop_ids),
            "static_stops_matched": len(stop_ids & static_stops),
            "stop_pct": round(len(stop_ids & static_stops) * 100 / len(stop_ids), 1) if stop_ids else 0,
        },
        "services": dict(services),
        "unmatched_trip_examples": sorted(trip_ids - set(static_trips))[:15],
        "unmatched_vehicle_examples": sorted(vehicle_trip_ids - set(static_trips))[:15],
        "vehicles_without_trip_match": len(vehicle_trip_ids - set(static_trips)),
        "trip_rows": trips["trip_rows"],
        "vehicle_rows": vehicles["vehicle_rows"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("sources", "coverage", "services")}, ensure_ascii=False, indent=2))
    print(f"informe: {OUT}")


if __name__ == "__main__":
    main()
