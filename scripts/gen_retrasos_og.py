#!/usr/bin/env python3
"""gen_retrasos_og.py — og-preview 1200x630 para la página de retrasos RENFE.

Estilo dark del ecosistema (fondo oscuro + acento rojo), KPIs del día. Se usa en
X/Bluesky/Mastodon cuando se comparte la página. Regenera con cada cron.
Salida: /var/www/radar/retrasos-renfe-og.png
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path.home() / "nearme-osint"
sys.path.insert(0, str(BASE))
from src.db import get_conn  # noqa: E402

OUT = Path("/var/www/radar/retrasos-renfe-og.png")
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BI = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def gradient(w, h, top, bot):
    img = Image.new("RGB", (w, h))
    dd = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        dd.line([(0, y), (w, y)],
                fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return img


def main():
    cur = get_conn().cursor()
    cur.execute("""
        SELECT title, subtype, created_at
        FROM events WHERE source='renfe' AND event_type='train_delay'
          AND created_at >= date_trunc('day', now())
    """)
    rows = cur.fetchall()
    eventos = []
    for title, subtype, created_at in rows:
        m = re.search(r": \+(\d+)min \((.*)\)", title or "")
        if not m:
            continue
        eventos.append({"delay": int(m.group(1)), "tipo": subtype or "",
                        "est": m.group(2)})
    if not eventos:
        print("sin datos"); sys.exit(1)

    total = len(eventos)
    av = sum(1 for e in eventos if e["tipo"] == "alta_velocidad")
    cer = total - av
    media = sum(e["delay"] for e in eventos) / total
    est_n = defaultdict(int)
    for e in eventos:
        s = e["est"].replace("Ŕ", "À").replace("Ń", "Ñ")
        est_n[s] += 1
    top = max(est_n, key=lambda s: est_n[s])

    W, H = 1200, 630
    img = gradient(W, H, (20, 20, 32), (48, 16, 24))
    d = ImageDraw.Draw(img)
    fb = ImageFont.truetype(FONT_B, 44)
    fb2 = ImageFont.truetype(FONT_B, 62)
    fr = ImageFont.truetype(FONT_R, 30)
    fs = ImageFont.truetype(FONT_R, 26)

    d.text((48, 40), "RETRASOS DEL TREN EN ESPAÑA", font=ImageFont.truetype(FONT_B, 26), fill=(220, 120, 120))
    d.text((48, 96), "Hoy en la red", font=fb2, fill=(255, 255, 255))

    # KPI principal
    d.text((48, 200), str(total), font=ImageFont.truetype(FONT_B, 130), fill=(248, 113, 113))
    d.text((48 + 200, 268), "retrasos detectados", font=fs, fill=(200, 200, 210))

    # fila secundaria
    y2 = 420
    d.text((48, y2), f"AVE / larga distancia   {av}", font=fb, fill=(255, 255, 255))
    d.text((48, y2 + 56), f"Cercanías              {cer}", font=fb, fill=(255, 255, 255))
    d.text((520, y2), f"Media  +{media:.0f} min", font=fb, fill=(251, 191, 36))
    d.text((520, y2 + 56), f"Estación con más:  {top[:30]}", font=fr, fill=(200, 200, 210))

    d.text((48, H - 46), "radar.viajeinteligencia.com  ·  datos oficiales RENFE (GTFS-RT) vía NearMe",
           font=ImageFont.truetype(FONT_R, 20), fill=(140, 140, 155))

    img.save(OUT)
    print(f"OK: {OUT} — {total} retrasos (AV {av}, cer {cer}, media +{media:.0f})")


if __name__ == "__main__":
    main()
