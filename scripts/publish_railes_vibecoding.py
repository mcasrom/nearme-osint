#!/usr/bin/env python3
import json, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path
SP="/home/deploy/social-poster"; ENV=Path("/home/deploy/hybrid-fimi-radar/.env")
IMG="https://radar.viajeinteligencia.com/railes-vibecoding-og-v2.png"
BASE="https://radar.viajeinteligencia.com/railes-cifras.html"
um=BASE+"?utm_source=mastodon&utm_medium=social&utm_campaign=railes_vibecoding"
ub=BASE+"?utm_source=bluesky&utm_medium=social&utm_campaign=railes_vibecoding"
ux=BASE+"?utm_source=x&utm_medium=social&utm_campaign=railes_vibecoding"
ut=BASE+"?utm_source=telegram&utm_medium=social&utm_campaign=railes_vibecoding"
mast=f"""He publicado Raíles: un observatorio ferroviario de datos abiertos hecho con #vibecoding y revisión humana.

3.993 km de AV · 7,9 km/1.000 km² · 82,6 km/M hab. · 0,27 accidentes significativos/M tren-km.

Con fuente, fecha y límites. Sin totales agregados ni cifras inventadas.

Ver: {um}
Canal: https://t.me/observatorio_amp"""
bsky=f"""Raíles: datos ferroviarios abiertos hechos con #vibecoding y revisión humana. 3.993 km de AV, densidad, uso y seguridad, con fuente y límites. Sin totales agregados.

{ub}"""
x=f"""Raíles: datos ferroviarios abiertos hechos con #vibecoding y revisión humana. 3.993 km de AV, densidad, uso y seguridad, con fuente y límites. Sin totales agregados.

{ux}"""
tg=f"""🚆 Raíles · datos abiertos hechos con #vibecoding y revisión humana.

3.993 km de AV · 7,9 km/1.000 km² · 82,6 km/M hab. · 0,27 accidentes significativos/M tren-km.

Con fuente, fecha y límites. Sin totales agregados ni cifras inventadas.

Cifras y gráficos: {ut}

Canal: https://t.me/observatorio_amp"""
li=f"""He publicado Raíles, un observatorio ferroviario de datos abiertos construido con #vibecoding y revisión humana.

3.993 km de alta velocidad en España · 7,9 km por 1.000 km² · 82,6 km por millón de habitantes · 0,27 accidentes significativos por millón de tren-km.

La página separa UIC (alta velocidad), Eurostat (ferrocarril total), Banco Mundial (población y superficie) y ERA (seguridad). Declara lo que no se sabe y no publica totales agregados.

Ver: {BASE}?utm_source=linkedin&utm_medium=social&utm_campaign=railes_vibecoding
Canal: https://t.me/observatorio_amp"""
alt="Raíles: 3.993 km de alta velocidad, 7,9 km por 1.000 km², 82,6 km por millón de habitantes y 0,27 accidentes por millón de tren-km. Hecho con vibecoding y revisión humana."
def env():
    d={}
    for ln in ENV.read_text(encoding="utf-8").splitlines():
        ln=ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k,_,v=ln.partition("="); d[k.strip()]=v.strip()
    return d
def send_photo(chat, caption):
    e=env(); tok=e.get("FIMI_TELEGRAM_BOT_TOKEN","")
    data=urllib.parse.urlencode({"chat_id":chat,"photo":IMG,"caption":caption}).encode()
    req=urllib.request.Request("https://api.telegram.org/bot%s/sendPhoto"%tok,data=data)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
def send_msg(chat,text):
    e=env(); tok=e.get("FIMI_TELEGRAM_BOT_TOKEN","")
    data=urllib.parse.urlencode({"chat_id":chat,"text":text,"disable_web_page_preview":"true"}).encode()
    req=urllib.request.Request("https://api.telegram.org/bot%s/sendMessage"%tok,data=data)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
def run(args):
    r=subprocess.run(["/usr/bin/python3"]+args,cwd=SP,capture_output=True,text=True,timeout=300)
    print("$", " ".join(args[:2]), "rc=",r.returncode, (r.stdout+r.stderr).strip()[:600])
    return r
print("mast",len(mast),"bsky",len(bsky),"x",len(x.replace(ux,"x"*23)),"tg",len(tg),"li",len(li))
if "--dry" in sys.argv:
    print("DRY: no se publica"); sys.exit(0)
m=run(["publish_mastodon.py",mast,IMG,"--alt",alt])
b=run(["publish_bluesky.py","-t",bsky,"-s",IMG,"--alt",alt,"--langs","es"])
e=env(); canal=e.get("TELEGRAM_CANAL") or e.get("FIMI_CANAL") or ""
owner=e.get("FIMI_OWNER_CHAT") or e.get("FIMI_TELEGRAM_CHAT_ID") or ""
if canal:
    try: print("TG canal ok=",send_photo(canal,tg).get("ok"))
    except Exception as ex: print("TG canal fallo",ex)
else: print("TG canal: sin TELEGRAM_CANAL")
if owner:
    try: print("TG bot/X ok=",send_msg(owner,"Texto para X (manual):\n\n"+x+"\n\nTexto para LinkedIn:\n\n"+li).get("ok"))
    except Exception as ex: print("TG bot/X fallo",ex)
else: print("TG bot: sin owner chat")
out=(m.stdout+m.stderr+"\n"+b.stdout+b.stderr)
Path("/home/deploy/social-poster/railes_vibecoding_20261104.posted").write_text(out,encoding="utf-8")
print("log escrito")
