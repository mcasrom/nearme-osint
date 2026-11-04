from PIL import Image, ImageDraw, ImageFont
W,H=1200,630
bg="#101827"; panel="#182235"; orange="#ff5a1f"; white="#f8fafc"; muted="#aab6c8"; teal="#3ddc97"; blue="#8ec5ff"
img=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(img)
def f(sz,bold=False): return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf"%("Bold" if bold else "Regular"),sz)
d.rectangle([0,0,W,10],fill=orange)
d.rectangle([54,52,68,96],fill=orange)
d.text((84,52),"RAÍLES",font=f(36,True),fill=white)
d.text((84,94),"El Observatorio Ciudadano del Ferrocarril",font=f(19),fill=muted)
d.text((54,154),"Datos abiertos hechos con",font=f(48,True),fill=white)
d.text((54,210),"vibecoding y revisión humana.",font=f(48,True),fill=white)
d.text((54,286),"Red, densidad, uso y seguridad ferroviaria. Sin totales agregados.",font=f(26),fill=teal)
# metrics
cards=[("3.993","km de AV","España"),("7,9","km/1.000 km²","densidad"),("0,27","acc./M tren-km","seguridad ERA")]
x=54
for big,unit,label in cards:
    d.rounded_rectangle([x,354,x+350,474],radius=13,fill=panel,outline="#2b3a52",width=2)
    d.text((x+20,370),big,font=f(42,True),fill=orange)
    d.text((x+20,422),unit,font=f(17,True),fill=white)
    d.text((x+20,446),label,font=f(14),fill=muted)
    x+=364
# CTA
d.text((54,506),"Canal público: t.me/observatorio_amp",font=f(24,True),fill=blue)
d.text((54,552),"radar.viajeinteligencia.com/railes-cifras.html",font=f(19,True),fill=white)
d.text((54,584),"Datos: UIC · Eurostat · Banco Mundial · ERA",font=f(16),fill=muted)
img.save("/var/www/radar/railes-vibecoding-og-v2.png",optimize=True)
img.save("/var/www/radar/railes-vibecoding-og.png",optimize=True)
print("ok")
