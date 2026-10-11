#!/usr/bin/env python3
"""gen_nieve_og.py — tarjeta OG 1200x630 para nivel-nieve.html (radar)."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
NAVY = (11, 18, 32)
SNOW = (56, 189, 248)
WHITE = (237, 242, 247)
DIM = (148, 163, 184)
OUT = "/var/www/radar/nivel-nieve-og.png"
FB = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
FR = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"


def f(path, size):
    return ImageFont.truetype(path, size)


img = Image.new("RGB", (W, H), NAVY)
d = ImageDraw.Draw(img)

for i in range(H):
    t = i / H
    d.line([(0, i), (W, i)], fill=(int(11 + 10 * t), int(18 + 16 * t), int(32 + 26 * t)))

d.rectangle([0, 0, W, 10], fill=SNOW)

d.text((60, 60), "OBSERVATORIO · RADAR DE ESPAÑA", font=f(FB, 24), fill=SNOW)

d.text((60, 150), "Nieve en las", font=f(FB, 92), fill=WHITE)
d.text((60, 250), "estaciones de esquí", font=f(FB, 92), fill=WHITE)

d.text((62, 380), "Manto de nieve y nevadas previstas por estación (24 h)",
       font=f(FR, 34), fill=DIM)
d.text((62, 428), "30 estaciones de España · datos abiertos, sin parte oficial",
       font=f(FR, 34), fill=DIM)

d.text((62, 500), "Fuente: Open-Meteo · NearMe · Actualizado 2 veces al día",
       font=f(FR, 28), fill=DIM)

d.text((60, 555), "radar.viajeinteligencia.com/nivel-nieve.html",
       font=f(FB, 30), fill=SNOW)

img.save(OUT, "PNG", optimize=True)
print("OK", OUT, img.size)
