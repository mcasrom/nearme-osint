#!/usr/bin/env python3
"""telegram_bot.py — Bot @nearme_status_bot para alertas de NearMe.

Comandos:
  /start, /help          -> menu de configuracion (teclado inline)
  /menu                  -> abre el menu
  /nearme <CODIGO>       -> vincula tu chat de Telegram con tu cuenta NearMe
  /unlink                -> desvincula el chat
  /estado                -> resumen de tu configuracion

Tambien atiende los comandos del Radar de Emergencias (radar.viajeinteligencia.com):
  /radar <lat> <lon> <radio_km> -> suscribir este chat a una zona
  /zonas                        -> listar zonas suscritas
  /salir                        -> cancelar suscripciones de este chat

Es el UNICO long-poll del token TELEGRAM_BOT_TOKEN. El radar-alerts mantiene su
script en modo solo-alertas (radar_telegram_bot.py) y envia avisos por cron via
sendMessage; sus suscripciones se guardan en /home/deploy/radar-alerts/data/
radar_subs.db, que es la BD que usamos aqui para /radar, /zonas y /salir.

El menu permite configurar (se guarda en telegram_prefs):
  * avisos (tipos de evento), ubicaciones, frecuencia de aviso y solo criticas.

Long-polling con getUpdates (PM2). El healthcheck tambien usa el bot pero solo
hace sendMessage, por lo que no hay conflicto con getUpdates (offset propio).
"""
import html
import os
import socket
import sqlite3
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
    get_user_by_chat,
    get_telegram_prefs,
    set_telegram_prefs,
    get_user_locations,
)

API = "https://api.telegram.org/bot{token}/"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OFFSET_FILE = os.path.join(Path(__file__).parent.parent, "logs", "telegram_bot.offset")

BOT_USERNAME = "nearme_status_bot"

RADAR_DB_PATH = "/home/deploy/radar-alerts/data/radar_subs.db"


def radar_db():
    c = sqlite3.connect(RADAR_DB_PATH)
    c.execute("""
        CREATE TABLE IF NOT EXISTS subs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            radius_km REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.commit()
    return c

EVENTS = [
    ("fire", "🔥 Incendios"),
    ("traffic", "🚧 Tráfico"),
    ("road_incident", "🛣️ Incidencias en vía"),
    ("weather", "🌡️ Meteorología"),
    ("heatwave", "🌡️ Ola de calor"),
    ("flood", "🌊 Inundaciones"),
    ("storm", "⛈️ Tormentas"),
    ("rain", "🌧️ Lluvia"),
    ("earthquake", "🌍 Sismos"),
    ("air", "🌫️ Calidad del aire"),
    ("train", "🚆 Tren"),
    ("uv", "☀️ Índice UV"),
    ("energy", "⚡ Luz"),
    ("beach", "🏖️ Playas"),
    ("wind", "💨 Viento"),
    ("water", "💧 Agua"),
    ("port", "⚓ Puertos"),
    ("telecom", "📡 Telecomunicaciones"),
]

FREQ_LABELS = {
    "inmediato": "⏱️ Al momento",
    "resumen_6h": "🗞️ Resumen cada 6 h",
    "resumen_24h": "📄 Resumen cada 24 h",
    "silencio": "🔕 Silencio",
}
FREQ_DESC = {
    "inmediato": "te aviso al momento de cada aviso que coincida con tus ubicaciones.",
    "resumen_6h": "te envio un unico resumen cada 6 horas con todo lo que coincida.",
    "resumen_24h": "te envio un unico resumen cada 24 horas.",
    "silencio": "no te envio avisos (puedes seguir configurando).",
}

HELP = (
    "Hola! Soy el bot de <b>NearMe OSINT</b> 🌍\n\n"
    "Recibiras los avisos de tus alertas (incendios, trafico, AEMET...) cuando "
    "coincidan con tus ubicaciones guardadas, incluso con la app cerrada.\n\n"
    "Para vincular tu cuenta:\n"
    "1. Abre nearme.viajeinteligencia.com y inicia sesion.\n"
    "2. En el panel de alertas pulsa <i>Alertas por Telegram</i>.\n"
    "3. Envia aqui el comando con el codigo que aparece:\n\n"
    "    /nearme CODIGO\n\n"
    "Con /menu puedes configurar que avisos recibir, desde que ubicaciones, "
    "con que frecuencia y si solo quieres los criticos.\n\n"
    "Tambien puedes usar /unlink para desvincularte.\n\n"
    "🚨 <b>Radar de Emergencias</b>\n"
    "¿Vienes de radar.viajeinteligencia.com? Envía el comando /radar tal cual "
    "te lo da la web para recibir alertas críticas de tu zona:\n\n"
    "    /radar 40.42 -3.70 200\n\n"
    "Usa /zonas y /salir para gestionar tus suscripciones."
)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tg_call(method: str, **params):
    r = requests.post(API.format(token=TOKEN) + method, json=params, timeout=30)
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text, parse_mode="HTML", reply_markup=None):
    params = dict(chat_id=chat_id, text=text, parse_mode=parse_mode, disable_web_page_preview=True)
    if reply_markup is not None:
        params["reply_markup"] = reply_markup
    tg_call("sendMessage", **params)


def edit_message(chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
    params = dict(chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode)
    if reply_markup is not None:
        params["reply_markup"] = reply_markup
    tg_call("editMessageText", **params)


def answer_callback(callback_query_id, text=""):
    try:
        tg_call("answerCallbackQuery", callback_query_id=callback_query_id, text=text)
    except requests.exceptions.RequestException:
        pass


def inline_kb(rows):
    return {"inline_keyboard": [[{"text": t, "callback_data": c} for t, c in row] for row in rows]}


def _fmt_event_types(prefs):
    cur = [t for t, _ in EVENTS if t in (prefs.get("event_types") or "").split(",")]
    if not cur:
        return "todos"
    return ", ".join(lbl for t, lbl in EVENTS if t in cur)


def _fmt_locations(user_id, prefs):
    locs = get_user_locations(user_id)
    sel = [int(x) for x in (prefs.get("locations") or "").split(",") if x.strip()] if prefs.get("locations") else []
    if not sel:
        return "todas"
    return ", ".join(l["name"] for l in locs if l["id"] in sel) or "todas"


def status_text(user_id, prefs):
    freq = prefs.get("frequency", "inmediato")
    crit = "sí (solo críticas)" if prefs.get("critical_only") else "no (todos los niveles)"
    return (
        "📋 <b>Tu configuración</b>\n\n"
        f"📍 <b>Avisos:</b> {html.escape(_fmt_event_types(prefs))}\n"
        f"🗺️ <b>Ubicaciones:</b> {html.escape(_fmt_locations(user_id, prefs))}\n"
        f"⏱️ <b>Frecuencia:</b> {FREQ_LABELS.get(freq, freq)}\n"
        f"🔴 <b>Solo críticas:</b> {crit}\n\n"
        f"<i>Frecuencia actual:</i> {FREQ_DESC.get(freq, '')}"
    )


def main_menu(chat_id, user_id):
    prefs = get_telegram_prefs(user_id)
    crit = "✅ ON" if prefs.get("critical_only") else "OFF"
    kb = inline_kb([
        [("⚙️ Mis avisos", "menu_avisos"), ("🗺️ Ubicaciones", "menu_loc")],
        [("⏱️ Frecuencia de aviso", "menu_freq"), ("🔴 Solo críticas · " + crit, "menu_crit")],
        [("📋 Mi configuración", "menu_status"), ("ℹ️ Ayuda", "menu_help")],
    ])
    send_message(chat_id, status_text(user_id, prefs) + "\n\nElige una opción:", reply_markup=kb)


def avisos_menu(chat_id, message_id, user_id, prefs, edit):
    sel = [t for t, _ in EVENTS if t in (prefs.get("event_types") or "").split(",")]
    rows = []
    for t, lbl in EVENTS:
        rows.append([(("✅ " if t in sel else "") + lbl, f"evt:{t}")])
    rows.append([("🔄 Todos (predeterminado)", "evt:all"), ("🔙 Volver", "menu_main")])
    text = "⚙️ <b>¿Qué avisos quieres recibir?</b>\n\nPulsa para activar o quitar. Si no marcas ninguno, recibes todos.\n\n" + status_text(user_id, prefs)
    if edit:
        edit_message(chat_id, message_id, text, reply_markup=inline_kb(rows))
    else:
        send_message(chat_id, text, reply_markup=inline_kb(rows))


def loc_menu(chat_id, message_id, user_id, prefs, edit):
    locs = get_user_locations(user_id)
    sel = [int(x) for x in (prefs.get("locations") or "").split(",") if x.strip()] if prefs.get("locations") else []
    text = "🗺️ <b>¿Desde qué ubicaciones quieres los avisos?</b>\n\n"
    if not locs:
        text += "No tienes ubicaciones guardadas. Añádelas en nearme.viajeinteligencia.com y vuelve aquí."
        buttons = [[("🔙 Volver", "menu_main")]]
        if edit:
            edit_message(chat_id, message_id, text, reply_markup=inline_kb(buttons))
        else:
            send_message(chat_id, text, reply_markup=inline_kb(buttons))
        return
    rows = []
    for l in locs:
        mark = "✅ " if l["id"] in sel else ""
        rows.append([(mark + l["name"], f"loc:{l['id']}")])
    rows.append([("🔄 Todas (predeterminado)", "loc:all"), ("🔙 Volver", "menu_main")])
    text += "Si no marcas ninguna, usas todas.\n\n" + status_text(user_id, prefs)
    if edit:
        edit_message(chat_id, message_id, text, reply_markup=inline_kb(rows))
    else:
        send_message(chat_id, text, reply_markup=inline_kb(rows))


def freq_menu(chat_id, message_id, user_id, prefs, edit):
    cur = prefs.get("frequency", "inmediato")
    rows = []
    for k, lbl in FREQ_LABELS.items():
        mark = "✅ " if k == cur else ""
        rows.append([(mark + lbl, f"freq:{k}")])
    rows.append([("🔙 Volver", "menu_main")])
    text = "⏱️ <b>Frecuencia de aviso</b>\n\n" + status_text(user_id, prefs)
    if edit:
        edit_message(chat_id, message_id, text, reply_markup=inline_kb(rows))
    else:
        send_message(chat_id, text, reply_markup=inline_kb(rows))


def process_callback(cq: dict):
    chat_id = cq["message"]["chat"]["id"]
    message_id = cq["message"]["message_id"]
    data = cq.get("data", "")
    user_id = get_user_by_chat(chat_id)

    if data == "menu_main":
        answer_callback(cq["id"])
        if user_id:
            main_menu(chat_id, user_id)
        else:
            send_message(chat_id, "⚠️ Primero vincula tu cuenta: envía /nearme CODIGO (genera el código en nearme.viajeinteligencia.com → Alertas por Telegram).")
        return

    if not user_id:
        answer_callback(cq["id"], "Primero vincula tu cuenta con /nearme CODIGO")
        send_message(chat_id, "⚠️ Primero vincula tu cuenta: envía /nearme CODIGO (genera el código en nearme.viajeinteligencia.com → Alertas por Telegram).")
        return

    prefs = get_telegram_prefs(user_id)

    if data.startswith("evt:"):
        t = data[4:]
        cur = [x for x in (prefs.get("event_types") or "").split(",") if x]
        if t == "all":
            cur = []
        elif t in cur:
            cur.remove(t)
        else:
            cur.append(t)
        set_telegram_prefs(user_id, event_types=cur)
        prefs = get_telegram_prefs(user_id)
        answer_callback(cq["id"], "Guardado")
        avisos_menu(chat_id, message_id, user_id, prefs, edit=True)
        return

    if data.startswith("loc:"):
        raw = data[4:]
        cur = [int(x) for x in (prefs.get("locations") or "").split(",") if x.strip()]
        if raw == "all":
            cur = []
        else:
            lid = int(raw)
            if lid in cur:
                cur.remove(lid)
            else:
                cur.append(lid)
        set_telegram_prefs(user_id, locations=cur)
        prefs = get_telegram_prefs(user_id)
        answer_callback(cq["id"], "Guardado")
        loc_menu(chat_id, message_id, user_id, prefs, edit=True)
        return

    if data.startswith("freq:"):
        val = data[5:]
        if val in FREQ_LABELS:
            set_telegram_prefs(user_id, frequency=val)
            answer_callback(cq["id"], "Frecuencia guardada")
        freq_menu(chat_id, message_id, user_id, get_telegram_prefs(user_id), edit=True)
        return

    if data == "menu_crit":
        set_telegram_prefs(user_id, critical_only=not prefs.get("critical_only"))
        prefs = get_telegram_prefs(user_id)
        answer_callback(cq["id"], "Guardado")
        crit = "✅ ON" if prefs.get("critical_only") else "OFF"
        kb = inline_kb([
            [("🔴 Solo críticas · " + crit, "menu_crit")],
            [("🔙 Volver", "menu_main")],
        ])
        edit_message(chat_id, message_id, status_text(user_id, prefs), reply_markup=kb)
        return

    if data == "menu_avisos":
        answer_callback(cq["id"])
        avisos_menu(chat_id, message_id, user_id, prefs, edit=True)
        return

    if data == "menu_loc":
        answer_callback(cq["id"])
        loc_menu(chat_id, message_id, user_id, prefs, edit=True)
        return

    if data == "menu_freq":
        answer_callback(cq["id"])
        freq_menu(chat_id, message_id, user_id, prefs, edit=True)
        return

    if data == "menu_status":
        answer_callback(cq["id"])
        kb = inline_kb([[("⚙️ Configurar", "menu_main")]])
        edit_message(chat_id, message_id, status_text(user_id, prefs), reply_markup=kb)
        return

    if data == "menu_help":
        answer_callback(cq["id"])
        kb = inline_kb([[("🔙 Volver", "menu_main")]])
        edit_message(chat_id, message_id, HELP, reply_markup=kb)
        return

    answer_callback(cq["id"])


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
    if "callback_query" in update:
        process_callback(update["callback_query"])
        return
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
        user_id = get_user_by_chat(chat_id)
        if user_id:
            main_menu(chat_id, user_id)
        else:
            send_message(chat_id, HELP)
        print(f"[{now_iso()}] CMD {chat_id}: {text[:30]}")
        return

    if low.startswith("/menu"):
        user_id = get_user_by_chat(chat_id)
        if user_id:
            main_menu(chat_id, user_id)
        else:
            send_message(chat_id, "⚠️ Primero vincula tu cuenta: envía /nearme CODIGO.")
        print(f"[{now_iso()}] CMD {chat_id}: {text[:30]}")
        return

    if low.startswith("/estado"):
        user_id = get_user_by_chat(chat_id)
        if user_id:
            send_message(chat_id, status_text(user_id, get_telegram_prefs(user_id)))
        else:
            send_message(chat_id, "⚠️ No tienes Telegram vinculado. Envía /nearme CODIGO.")
        print(f"[{now_iso()}] CMD {chat_id}: {text[:30]}")
        return

    if low.startswith("/radar"):
        parts = text.split()
        if len(parts) < 4:
            send_message(chat_id,
                         "Uso: <code>/radar latitud longitud radio_km</code>\n"
                         "Ejemplo: <code>/radar 40.42 -3.70 200</code>")
            return
        try:
            lat, lon, r = float(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            send_message(chat_id, "Coordenadas no válidas. Ejemplo: /radar 40.42 -3.70 200")
            return
        conn = radar_db()
        conn.execute("INSERT INTO subs (chat_id, lat, lon, radius_km) VALUES (?,?,?,?)", (chat_id, lat, lon, r))
        conn.commit()
        conn.close()
        send_message(chat_id, "✅ Zona suscrita: lat %.4f, lon %.4f, radio %d km.\nTe aviso ante eventos críticos de tu zona. Usa /zonas o /salir." % (lat, lon, r))
        print(f"[{now_iso()}] RADAR sub chat={chat_id} lat={lat} lon={lon} r={r}")
        return

    if low.startswith("/zonas"):
        conn = radar_db()
        rows = conn.execute("SELECT id, lat, lon, radius_km FROM subs WHERE chat_id=?", (chat_id,)).fetchall()
        conn.close()
        if not rows:
            send_message(chat_id, "No tienes zonas suscritas al Radar. Usa /radar lat lon radio.")
        else:
            txt = "🗺️ Tus zonas (Radar):\n" + "\n".join(
                "  #%d · %.4f, %.4f · %d km" % (r[0], r[1], r[2], r[3]) for r in rows)
            send_message(chat_id, txt)
        return

    if low.startswith("/salir"):
        conn = radar_db()
        conn.execute("DELETE FROM subs WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()
        send_message(chat_id, "🗑️ Suscripciones del Radar canceladas.")
        print(f"[{now_iso()}] RADAR salir chat={chat_id}")
        return

    if low.startswith("/nearme"):
        parts = text.split()
        code = parts[1].strip().upper() if len(parts) > 1 else ""
        user_id = consume_telegram_link(code) if code else None
        if user_id:
            save_telegram_subscription(user_id, chat_id, tg_username)
            send_message(chat_id, "✅ <b>Enlazado correctamente.</b>\n\nA partir de ahora recibirás aquí los avisos de tus alertas de NearMe. Abre el menú para configurarlos:")
            main_menu(chat_id, user_id)
            print(f"[{now_iso()}] LINK ok user={user_id} chat={chat_id}")
        else:
            send_message(chat_id, "❌ Código no válido o caducado. Genera uno nuevo en el panel de alertas de NearMe (dura 10 min y es de un solo uso).")
            print(f"[{now_iso()}] LINK fail chat={chat_id} code={code or 'none'}")
        return

    if low.startswith("/unlink"):
        ok = delete_telegram_subscription_by_chat(chat_id)
        send_message(chat_id, "✅ Desvinculado." if ok else "⚠️ No tenías Telegram vinculado.")
        print(f"[{now_iso()}] UNLINK chat={chat_id} ok={ok}")
        return

    send_message(chat_id, "Comando no reconocido. Envía /menu para ver las opciones o /help para la ayuda.")


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
