from PIL import Image, ImageDraw, ImageFont
W,H=1200,630;bg="#101827";orange="#ff5a1f";white="#f8fafc";muted="#aab6c8";teal="#3ddc97"
img=Image.new("RGB",(W,H),bg);d=ImageDraw.Draw(img)
def f(sz,bold=False): return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf"%("Bold" if bold else "Regular"),sz)
d.rectangle([0,0,W,10],fill=orange);d.rectangle([54,54,68,98],fill=orange)
d.text((84,54),"RAÍLES",font=f(36,True),fill=white);d.text((84,96),"El Observatorio Ciudadano del Ferrocarril",font=f(20),fill=muted)
d.text((54,180),"About",font=f(86,True),fill=white)
d.text((54,292),"Datos abiertos, fuentes y límites.",font=f(32),fill=white)
d.text((54,350),"Dos dominios: viajeinteligencia.com · pruebapublica.com",font=f(23),fill=teal)
d.text((54,430),"Sin cookies, sin cuentas, sin totales agregados.",font=f(22),fill=muted)
d.text((54,520),"radar.viajeinteligencia.com/railes-about.html",font=f(20,True),fill=white)
img.save("/var/www/radar/railes-about-og.png",optimize=True);print("ok")
