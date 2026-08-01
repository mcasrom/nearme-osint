#!/usr/bin/env python3
"""telegram_bot.py — Bot @nearme_status_bot para alertas de NearMe.

Comandos:
  /start, /help        -> ayuda
  /nearme <CODIGO>     -> vincula tu chat de Telegram con tu cuenta NearMe
  /unlink              -> desvincula el chat

Long-polling con getUpdates (PM2). El healthcheck tambien usa el bot pero solo
hace sendMessage, por lo que no hay conflicto con getUpdates (offset propio).
"""
import html
import os
import socket
import sys
import time
import urllib3.util.connection
urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(os.path.join(Path(__file__).parent.parent, ".env"), override=True)

import requests

from src.db import (
    consume_telegram_link,
    save_telegram_subscription,
    delete_telegram_subscription_by_chat,
)

API = "https://api.telegram.org/bot{token}/"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OFFSET_FILE = os.path.join(Path(__file__).parent.parent, "logs", "telegram_bot.offset")

BOT_USERNAME = "nearme_status_bot"

HELP = (
    "Hola! Soy el bot de <b>NearMe OSINT</b> 🌍\n\n"
    "Recibiras los avisos de tus alertas (incendios, trafico, AEMET...) cuando "
    "coincidan con tus ubicaciones guardadas, incluso con la app cerrada.\n\n"
    "Para vincular tu cuenta:\n"
    "1. Abre nearme.viajeinteligencia.com y inicia sesion.\n"
    "2. En el panel de alertas pulsa <i>Alertas por Telegram</i>.\n"
    "3. Envia aqui el comando con el codigo que aparece:\n\n"
    "    /nearme CODIGO\n\n"
    "Tambien puedes usar /unlink para desvincularte."
)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tg_call(method: str, **params):
    r = requests.post(API.format(token=TOKEN) + method, json=params, timeout=30)
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text, parse_mode="HTML"):
    tg_call("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode, disable_web_page_preview=True)


def load_offset():
    try:
        with open(OFFSET_FILE) as fh:
            return int(fh.read().strip() or 0)
    except Exception:
        return 0


def save_offset(offset):
    try:
        with open(OFFSET_FILE, "w") as fh:
            fh.write(str(offset))
    except Exception:
        pass


def process_update(update: dict):
    """Procesa un update del bot. Separado para poder testearlo."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or chat.get("type") != "private" or not text:
        return
    from_user = message.get("from") or {}
    tg_username = from_user.get("username", "")

    low = text.lower()
    if low.startswith("/start") or low.startswith("/help"):
        send_message(chat_id, HELP)
        print(f"[{now_iso()}] CMD {chat_id}: {text[:30]}")
        return

    if low.startswith("/nearme"):
        parts = text.split()
        code = parts[1].strip().upper() if len(parts) > 1 else ""
        user_id = consume_telegram_link(code) if code else None
        if user_id:
            save_telegram_subscription(user_id, chat_id, tg_username)
            send_message(chat_id, "✅ <b>Enlazado correctamente.</b>\n\nA partir de ahora recibiras aqui los avisos de tus alertas de NearMe.")
            print(f"[{now_iso()}] LINK ok user={user_id} chat={chat_id}")
        else:
            send_message(chat_id, "❌ Codigo no valido o caducado. Genera uno nuevo en el panel de alertas de NearMe (dura 10 min y es de un solo uso).")
            print(f"[{now_iso()}] LINK fail chat={chat_id} code={code or 'none'}")
        return

    if low.startswith("/unlink"):
        ok = delete_telegram_subscription_by_chat(chat_id)
        send_message(chat_id, "✅ Desvinculado." if ok else "⚠️ No tenias Telegram vinculado.")
        print(f"[{now_iso()}] UNLINK chat={chat_id} ok={ok}")
        return

    send_message(chat_id, "Comando no reconocido. Envia /help para ver las opciones.")


def main():
    if not TOKEN:
        print(f"[{now_iso()}] [FATAL] TELEGRAM_BOT_TOKEN no configurado")
        sys.exit(1)
    offset = load_offset()
    print(f"[{now_iso()}] telegram_bot iniciado (offset={offset})")
    while True:
        try:
            r = tg_call("getUpdates", offset=offset + 1, timeout=30, limit=10)
            for upd in r.get("result", []):
                process_update(upd)
                offset = upd["update_id"]
                save_offset(offset)
            time.sleep(1)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                print(f"[{now_iso()}] [WARN] 409 conflict, reiniciando offset")
                offset = -1
                save_offset(offset)
            elif e.response is not None and e.response.status_code == 401:
                print(f"[{now_iso()}] [FATAL] token invalido")
                sys.exit(1)
            else:
                print(f"[{now_iso()}] [ERR] http {e}")
                time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"[{now_iso()}] [ERR] net: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
