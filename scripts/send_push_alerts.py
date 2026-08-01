#!/usr/bin/env python3
"""send_push_alerts.py — Envia alertas (Web Push + Telegram) cuando un evento
coincide con las alertas de un usuario (ancladas a sus ubicaciones guardadas).
Dedup por canal via push_sent (channel='push'|'telegram').
Cron: */5 * * * * cd /home/deploy/nearme-osint && venv/bin/python scripts/send_push_alerts.py >> logs/push.log 2>&1
"""
import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(os.path.join(Path(__file__).parent.parent, ".env"), override=True)

import requests

from pywebpush import webpush, WebPushException

from src.db import (
    get_push_users,
    get_user_alerts,
    get_user_locations,
    get_push_subscriptions,
    get_telegram_chat,
    get_events_nearby,
    get_sent_keys,
    mark_push_sent,
    delete_push_subscription,
    prune_push_sent,
)

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:nearme@viajeinteligencia.com")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_API = "https://api.telegram.org/bot{token}/sendMessage"

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


def send_telegram(chat_id: int, text: str) -> bool:
    if not TG_TOKEN:
        return False
    try:
        r = requests.post(TG_API.format(token=TG_TOKEN), json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        if r.status_code == 403 or r.status_code == 400:
            return False  # chat no disponible / bloqueado
        r.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        print(f"[{now_iso()}] [ERR] telegram chat={chat_id}: {exc}")
        return False


def build_items_text(items, loc_name):
    items.sort(key=lambda x: LEVEL_ORDER.get(x[2]["level"], 0), reverse=True)
    n = len(items)
    lines = [f"{EMOJIS.get(e['event_type'], '📍')} {html.escape(e['title'][:60])}" for _, _, e in items[:3]]
    body = "\n".join(lines)
    if n > 3:
        body += f"\n(+{n - 3} mas)"
    return n, body


def main():
    user_ids = get_push_users()
    total_push = 0
    total_tg = 0
    for user_id in user_ids:
        alerts = [a for a in get_user_alerts(user_id) if a["enabled"]]
        locations = get_user_locations(user_id)
        if not alerts or not locations:
            continue
        subs = get_push_subscriptions(user_id)
        chat_id = get_telegram_chat(user_id)
        if not subs and not chat_id:
            continue

        matches = []  # (loc, alert, event)
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
                    matches.append((loc, alert, e))

        if not matches:
            continue

        grouped = {}
        for loc, alert, e in matches:
            grouped.setdefault((alert["id"], loc["id"]), []).append((loc, alert, e))

        sent_push = get_sent_keys(user_id, "push") if subs else set()
        sent_tg = get_sent_keys(user_id, "telegram") if chat_id else set()
        push_here = 0
        tg_here = 0

        for (alert_id, loc_id), items in grouped.items():
            loc = items[0][0]
            n, body = build_items_text(items, loc["name"])

            if subs:
                push_items = [it for it in items if (alert_id, it[2]["id"], it[2]["level"]) not in sent_push]
                if push_items:
                    pn, pbody = build_items_text(push_items, loc["name"])
                    payload = {
                        "title": f"🔔 {pn} evento{'s' if pn != 1 else ''} cerca de {loc['name']}",
                        "body": pbody.replace("\n", ", "),
                        "url": "/",
                    }
                    ok = False
                    for sub in subs:
                        try:
                            send_push(sub, payload)
                            ok = True
                        except WebPushException as exc:
                            code = getattr(exc.response, "status_code", None) if exc.response else None
                            if code in (404, 410):
                                print(f"[{now_iso()}] [DROP] push caducada user={user_id}")
                                delete_push_subscription(user_id, sub["endpoint"])
                            elif code == 429:
                                print(f"[{now_iso()}] [RATE] user={user_id} (429)")
                                break
                            else:
                                print(f"[{now_iso()}] [ERR] push user={user_id} code={code}: {exc}")
                        except Exception as exc:
                            print(f"[{now_iso()}] [ERR] push user={user_id}: {exc}")
                    if ok:
                        for it in push_items:
                            mark_push_sent(user_id, alert_id, it[2]["id"], it[2]["level"], "push")
                        push_here += 1

            if chat_id:
                tg_items = [it for it in items if (alert_id, it[2]["id"], it[2]["level"]) not in sent_tg]
                if tg_items:
                    tn, tbody = build_items_text(tg_items, loc["name"])
                    text = f"<b>🔔 {tn} evento{'s' if tn != 1 else ''} cerca de {loc['name']}</b>\n{tbody}"
                    if send_telegram(chat_id, text):
                        for it in tg_items:
                            mark_push_sent(user_id, alert_id, it[2]["id"], it[2]["level"], "telegram")
                        tg_here += 1
                    else:
                        print(f"[{now_iso()}] [SKIP] telegram user={user_id} chat={chat_id}")

        if push_here or tg_here:
            total_push += push_here
            total_tg += tg_here
            print(f"[{now_iso()}] [SEND] user={user_id} push_grupos={push_here} tg_grupos={tg_here}")

    pruned = prune_push_sent(48)
    print(f"[{now_iso()}] [OK] users={len(user_ids)} push_grupos={total_push} tg_grupos={total_tg} pruned={pruned}")


if __name__ == "__main__":
    main()
