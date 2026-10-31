"""Referencias GTFS estáticas de Renfe para las páginas de retrasos."""
from src.db import get_conn, release_conn


def load_refs():
    conn = get_conn()
    cur = conn.cursor()
    stops = {}
    trips = {}
    try:
        cur.execute("SELECT feed, stop_id, stop_name FROM renfe_gtfs_stops")
        for feed, stop_id, stop_name in cur.fetchall():
            stops[(feed, stop_id)] = stop_name
        cur.execute(
            "SELECT feed, trip_id, route_id, route_short_name, route_long_name, "
            "origin_stop_id, origin_name, dest_stop_id, dest_name FROM renfe_gtfs_trips"
        )
        for r in cur.fetchall():
            trips[(r[0], r[1])] = {
                "route_id": r[2],
                "route_short_name": r[3],
                "route_long_name": r[4],
                "origin_stop_id": r[5],
                "origin_name": r[6],
                "dest_stop_id": r[7],
                "dest_name": r[8],
            }
    except Exception:
        conn.rollback()
    finally:
        cur.close()
        release_conn(conn)
    return stops, trips
