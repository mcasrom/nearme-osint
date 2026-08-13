#!/usr/bin/env bash
# check_stats_health.sh — Vigilancia semanal de la salud de los datos estadísticos
# Verifica que cada fuente haya generado métricas RECIENTES en daily_stats
# (detecta fuentes "atascadas" como el bug de embalses: última métrica vieja).
# Alerta por Telegram si alguna fuente lleva > N días sin métrica nueva.
#
# Uso en cron (semanal, p.ej. lunes 09:00):
#   0 9 * * 1 cd /home/deploy/nearme-osint && ./scripts/check_stats_health.sh >> logs/stats_health.log 2>&1
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDIR="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR/..")"
[ -f "$CDIR/.env" ] && source "$CDIR/.env"
mkdir -p "$CDIR/logs"

# Umbral de frescura por fuente (días máximos sin métrica nueva)
# embalses: usa GREATEST(created_at, updated_at), debe actualizarse a diario
declare -A MAX_AGE_DAYS=(
  ["embalses"]=3
  ["renfe"]=3
  ["nasa_firms"]=3
  ["miteco"]=3
)

telegram_send() {
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
        return 0
    fi
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=$1" \
        -d "disable_web_page_preview=true" \
        --max-time 10 > /dev/null 2>&1 || echo "[WARN] telegram_send fallo" >&2
}

LOG="[$(date -u +%FT%TZ)]"
STALE=""

# Para cada fuente vigilada, obtener la última métrica y su fecha
for src in "${!MAX_AGE_DAYS[@]}"; do
  max_days=${MAX_AGE_DAYS[$src]}
  result=$(cd "$CDIR" && venv/bin/python3 - "$src" "$max_days" <<'PYEOF'
import sys, datetime
sys.path.insert(0, ".")
from src.db import get_conn
source = sys.argv[1]
max_days = int(sys.argv[2])
conn = get_conn(); cur = conn.cursor()
cur.execute(
    "SELECT MAX(stat_date), COUNT(DISTINCT metric) FROM daily_stats WHERE source=%s",
    (source,))
row = cur.fetchone()
last = row[0]
nmetrics = row[1]
cur.close(); conn.close()
if last is None:
    print(f"NONE|{nmetrics}")
else:
    age = (datetime.date.today() - last).days
    print(f"{last}|{age}|{nmetrics}")
PYEOF
)
  IFS='|' read -r last_date age nmetrics <<< "$result"
  if [ "$last_date" = "NONE" ]; then
    STALE="$STAGE $src(sin datos)"
    echo "$LOG [STALE] $src: SIN métricas en daily_stats"
  elif [ "$age" -gt "$max_days" ]; then
    STALE="$STALE $src(última $last_date, $age días)"
    echo "$LOG [STALE] $src: última métrica $last_date, $age días (max $max_days)"
  else
    echo "$LOG [OK] $src: última $last_date, $age días, $nmetrics métricas"
  fi
done

if [ -n "$STALE" ]; then
  telegram_send "⚠️ ESTADÍSTICAS DESACTUALIZADAS:$STALE"
  echo "$LOG [ALERT]$STALE"
else
  echo "$LOG [OK] Todas las fuentes estadísticas frescas"
fi
exit 0
