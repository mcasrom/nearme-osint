#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/deploy/nearme-osint"
JSON="/var/www/radar/datos/railes-cifras.json"
LOG="/home/deploy/scripts/railes_refresh.log"
cd "$ROOT"
stamp(){ date -u +"%Y-%m-%dT%H:%M:%SZ"; }
echo "$(stamp) inicio" >> "$LOG"
before="$(sha256sum "$JSON" | awk '{print $1}')"
/usr/bin/python3 scripts/fetch_railes_cifras.py >/dev/null 2>> "$LOG"
after="$(sha256sum "$JSON" | awk '{print $1}')"
if [ "$before" = "$after" ]; then
  echo "$(stamp) sin cambios de datos; no se regenera" >> "$LOG"
  exit 0
fi
/usr/bin/python3 scripts/gen_railes_cifras.py >> "$LOG" 2>&1
/usr/bin/python3 scripts/gen_railes_seo.py >> "$LOG" 2>&1
/home/deploy/scripts/cf_purge.sh fimi >> "$LOG" 2>&1
msg="Raíles: datos actualizados en la revisión mensual. Cifras y gráficos regenerados, caché purgada. https://radar.viajeinteligencia.com/railes-cifras.html"
/usr/bin/python3 scripts/notify_railes.py "$msg" >> "$LOG" 2>&1 || echo "$(stamp) aviso Telegram fallido" >> "$LOG"
echo "$(stamp) datos cambiados: HTML/SEO regenerados, Cloudflare purgado y aviso enviado" >> "$LOG"
