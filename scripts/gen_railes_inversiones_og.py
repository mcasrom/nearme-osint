from PIL import Image, ImageDraw, ImageFont
W,H=1200,630;bg="#101827";panel="#182235";orange="#ff5a1f";white="#f8fafc";muted="#aab6c8";teal="#3ddc97"
img=Image.new("RGB",(W,H),bg);d=ImageDraw.Draw(img)
def f(sz,bold=False): return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf"%("Bold" if bold else "Regular"),sz)
d.rectangle([0,0,W,10],fill=orange);d.rectangle([54,54,68,98],fill=orange)
d.text((84,54),"RAÍLES",font=f(36,True),fill=white);d.text((84,96),"El Observatorio Ciudadano del Ferrocarril",font=f(20),fill=muted)
d.text((54,170),"Macroinversiones",font=f(64,True),fill=white);d.text((54,246),"ferroviarias",font=f(64,True),fill=white)
d.text((54,342),"Proyectos concretos, importe, estado y fuente.",font=f(28),fill=teal)
d.text((54,410),"No es el total del sistema. Los importes no se suman.",font=f(24),fill="#8ec5ff")
d.text((54,520),"radar.viajeinteligencia.com/railes-inversiones.html",font=f(20,True),fill=white)
d.text((54,566),"Fuente: Ministerio de Transportes · datos abiertos",font=f(18),fill=muted)
img.save("/var/www/radar/railes-inversiones-og.png",optimize=True);print("ok")
