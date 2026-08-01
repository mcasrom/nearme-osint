#!/usr/bin/env python3
"""Asigna expires_at a eventos activos con expires_at NULL y limpia los expirados.

expires_at = updated_at + TTL(event_type). Un evento que lleva sin confirmarse
mas tiempo que su TTL queda expirado y es eliminado por clean_expired().
"""
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/deploy/nearme-osint")

from src.config import DEFAULT_TTL_HOURS, DEFAULT_TTL_FALLBACK_HOURS
from src.db import get_conn, clean_expired


def main() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, event_type, updated_at FROM events "
        "WHERE status = 'active' AND expires_at IS NULL"
    )
    rows = cur.fetchall()
    updated = 0
    for event_id, event_type, updated_at in rows:
        ttl_hours = DEFAULT_TTL_HOURS.get(event_type, DEFAULT_TTL_FALLBACK_HOURS)
        base = updated_at or datetime.now(timezone.utc)
        expires = base + timedelta(hours=ttl_hours)
        cur.execute("UPDATE events SET expires_at = %s WHERE id = %s", (expires, event_id))
        updated += 1
    conn.commit()
    cur.close()
    deleted = clean_expired()
    print(f"Backfill: {updated} eventos con expires_at NULL asignados")
    print(f"Expiración inmediata aplicada a {deleted} eventos obsoletos")


if __name__ == "__main__":
    main()
