#!/usr/bin/env python3
"""Aviso Telegram mínimo para la revisión mensual de Raíles."""
from __future__ import annotations
import json, sys, urllib.parse, urllib.request
from pathlib import Path
ENV=Path("/home/deploy/hybrid-fimi-radar/.env")
def load_env():
    d={}
    try:
        for ln in ENV.read_text(encoding="utf-8").splitlines():
            ln=ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k,_,v=ln.partition("="); d[k.strip()]=v.strip()
    except OSError as e:
        print("[railes-aviso] no leo .env:",e,file=sys.stderr)
    return d
def send(text):
    e=load_env(); tok=e.get("FIMI_TELEGRAM_BOT_TOKEN",""); chat=e.get("FIMI_OWNER_CHAT","")
    if not tok or not chat:
        print("[railes-aviso] sin token/chat",file=sys.stderr); return False
    data=urllib.parse.urlencode({"chat_id":chat,"text":text,"disable_web_page_preview":"true"}).encode()
    req=urllib.request.Request("https://api.telegram.org/bot%s/sendMessage"%tok,data=data)
    try:
        with urllib.request.urlopen(req,timeout=20) as r: return bool(json.loads(r.read().decode()).get("ok"))
    except Exception as e:
        print("[railes-aviso] fallo Telegram:",e,file=sys.stderr); return False
if __name__=="__main__":
    args=[a for a in sys.argv[1:] if a]
    dry="--dry" in args; args=[a for a in args if a!="--dry"]
    text=" ".join(args).strip() or "Raíles: datos actualizados."
    if dry:
        print(text); sys.exit(0)
    ok=send(text); print("sent" if ok else "failed"); sys.exit(0 if ok else 1)
