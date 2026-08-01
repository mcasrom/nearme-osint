#!/usr/bin/env python3
"""check_telegram_api.py — monitor de latencia/reachability de api.telegram.org (IPv4).

Cron cada 5 min. Escribe una linea por ejecucion en logs/telegram_api.log.
Salida: "OK avg_ttfb=0.12s" o "FAIL fails=3/n". Exit 0 siempre (el log es la fuente).
"""
import os
import socket
import time
import urllib3.util.connection
import requests

urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

URL = "https://api.telegram.org/"
LOG = os.path.join(os.path.dirname(__file__), "..", "logs", "telegram_api.log")


def main():
    ttfb = []
    fails = 0
    for _ in range(3):
        t = time.time()
        try:
            r = requests.get(URL, timeout=8)
            ttfb.append(time.time() - t)
            if r.status_code not in (200, 302):
                fails += 1
        except Exception:
            fails += 1
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if fails == 0 and ttfb:
        line = "%s OK avg_ttfb=%.2fs min=%.2fs max=%.2fs\n" % (
            now, sum(ttfb) / len(ttfb), min(ttfb), max(ttfb))
    else:
        line = "%s FAIL fails=%d/3\n" % (now, fails)
    with open(os.path.normpath(LOG), "a") as f:
        f.write(line)
    print(line.strip())


if __name__ == "__main__":
    main()
