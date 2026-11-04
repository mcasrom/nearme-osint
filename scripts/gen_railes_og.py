from PIL import Image, ImageDraw, ImageFont
W,H=1200,630
bg="#101827"; panel="#182235"; orange="#ff5a1f"; white="#f8fafc"; muted="#aab6c8"; teal="#3ddc97"
img=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(img)
def f(sz,bold=False): return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf"%("Bold" if bold else "Regular"),sz)
d.rectangle([0,0,W,10],fill=orange)
d.rectangle([54,54,68,98],fill=orange)
d.text((84,54),"RAÍLES",font=f(36,True),fill=white)
d.text((84,96),"El Observatorio Ciudadano del Ferrocarril",font=f(20),fill=muted)
d.text((54,160),"Cifras de alta velocidad",font=f(56,True),fill=white)
d.text((54,230),"3.993 km",font=f(96,True),fill=orange)
d.text((58,340),"red en servicio · España · 2024 · series y seguridad",font=f(24),fill=white)
cards=[("7,9","km/1.000 km²","densidad"),("82,6","km/M hab.","por habitante"),("3,8","M pkm/km","intensidad de uso"),("0,27","acc./M tren-km","seguridad ERA 2024")]
x=54
for big,unit,label in cards:
    d.rounded_rectangle([x,404,x+272,546],radius=14,fill=panel,outline="#2b3a52",width=2)
    d.text((x+18,424),big,font=f(44,True),fill=teal)
    d.text((x+18,480),unit,font=f(17,True),fill=white)
    d.text((x+18,508),label,font=f(14),fill=muted)
    x+=284
d.text((54,576),"Solo países comparables · sin totales agregados · UIC, Eurostat, Banco Mundial, ERA",font=f(18),fill=muted)
d.text((54,602),"radar.viajeinteligencia.com/railes-cifras.html",font=f(18,True),fill=white)
img.save("/var/www/radar/railes-cifras-og.png",optimize=True)
print("ok")
