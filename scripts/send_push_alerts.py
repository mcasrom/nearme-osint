#!/usr/bin/env python3
"""send_push_alerts.py — Envia Web Push cuando un evento coincide con las alertas
de un usuario (ancladas a sus ubicaciones guardadas). Dedup via push_sent.
Cron: */5 * * * * cd /home/deploy/nearme-osint && venv/bin/python scripts/send_push_alerts.py >> logs/push.log 2>&1
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(os.path.join(Path(__file__).parent.parent, ".env"), override=True)

from pywebpush import webpush, WebPushException

from src.db import (
    get_push_users,
    get_user_alerts,
    get_user_locations,
    get_push_subscriptions,
    get_events_nearby,
    push_sent_exists,
    mark_push_sent,
    delete_push_subscription,
    prune_push_sent,
)

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:nearme@viajeinteligencia.com")

EMOJIS = {
    "fire": "🔥", "traffic": "🚧", "weather": "🌡️", "air": "🌫️", "earthquake": "🌍",
    "train": "🚆", "uv": "☀️", "energy": "⚡", "wind": "💨", "rain": "🌧️", "heatwave": "🔥",
    "flood": "🌊", "beach": "🏖️", "water": "💧", "storm": "⛈️", "port": "⚓", "telecom": "📡",
}

LEVEL_ORDER = {"info": 1, "warning": 2, "alert": 3, "critical": 4}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def send_push(sub, payload):
    webpush(
        subscription_info={"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
        data=json.dumps(payload),
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims={"sub": VAPID_SUBJECT},
        timeout=10,
    )


def main():
    if not VAPID_PRIVATE_KEY:
        print(f"[{now_iso()}] [SKIP] VAPID_PRIVATE_KEY no configurada")
        return

    user_ids = get_push_users()
    total_sent = 0
    for user_id in user_ids:
        alerts = [a for a in get_user_alerts(user_id) if a["enabled"]]
        locations = get_user_locations(user_id)
        subs = get_push_subscriptions(user_id)
        if not alerts or not locations or not subs:
            continue

        pending = []  # (location_name, n, titles)
        for loc in locations:
            for alert in alerts:
                try:
                    events = get_events_nearby(
                        loc["lat"], loc["lon"],
                        radius_km=alert["radius_km"],
                        event_type=alert["event_type"] if alert["event_type"] != "all" else None,
                        min_level=alert["min_level"],
                        limit=200,
                    )
                except Exception:
                    continue
                for e in events:
                    key = (user_id, alert["id"], e["id"], e["level"])
                    if not push_sent_exists(*key):
                        pending.append((key, loc, e))

        if not pending:
            continue

        # agrupar por (alert, location) para un unico push por zona
        grouped = {}
        for key, loc, e in pending:
            gkey = (key[1], loc["id"])
            grouped.setdefault(gkey, []).append((key, e))

        sent_any = False
        for (alert_id, loc_id), items in grouped.items():
            loc = next(l for l in locations if l["id"] == loc_id)
            items.sort(key=lambda x: LEVEL_ORDER.get(x[1]["level"], 0), reverse=True)
            n = len(items)
            first = [f"{EMOJIS.get(e['event_type'], '📍')} {e['title'][:60]}" for _, e in items[:3]]
            body = ", ".join(first)
            if n > 3:
                body += f" (+{n - 3} mas)"
            payload = {
                "title": f"🔔 {n} evento{'s' if n != 1 else ''} cerca de {loc['name']}",
                "body": body,
                "url": "/",
            }
            for sub in subs:
                try:
                    send_push(sub, payload)
                    sent_any = True
                except WebPushException as exc:
                    code = getattr(exc.response, "status_code", None) if exc.response else None
                    if code in (404, 410):
                        print(f"[{now_iso()}] [DROP] suscripcion caducada user={user_id}")
                        delete_push_subscription(user_id, sub["endpoint"])
                    elif code == 429:
                        print(f"[{now_iso()}] [RATE] user={user_id} (429), se detiene")
                        break
                    else:
                        print(f"[{now_iso()}] [ERR] push user={user_id} code={code}: {exc}")
                except Exception as exc:
                    print(f"[{now_iso()}] [ERR] push user={user_id}: {exc}")

        if sent_any:
            for key, _, _ in pending:
                mark_push_sent(*key)
            total_sent += 1
            print(f"[{now_iso()}] [SEND] user={user_id} grupos={len(grouped)}")

    pruned = prune_push_sent(48)
    print(f"[{now_iso()}] [OK] users={len(user_ids)} push_groups={total_sent} pruned={pruned}")


if __name__ == "__main__":
    main()
