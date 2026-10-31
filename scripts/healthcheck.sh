#!/usr/bin/env bash
# healthcheck.sh — Verifica API, DB y freshness del pipeline de NearMe
# Alerta por Telegram SOLO en el cambio de estado (down/recovery), no cada ejecucion.
# Uso en cron: */5 * * * * cd /home/deploy/nearme-osint && ./scripts/healthcheck.sh >> logs/healthcheck.log 2>&1
set -e

HEALTH_URL="https://nearme.viajeinteligencia.com/health"
# UA de navegador: el bot-block de nginx corta curl/ → 444 → Cloudflare 520 (falso DOWN)
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CURL_TIMEOUT=10
MAX_AGE_SECONDS=2700  # 45 min (colectores corren cada 15 min)
RETRASOS_PAGE="/var/www/radar/retrasos-renfe-hoy.html"
RETRASOS_ESTACIONES="/var/www/radar/retrasos-renfe-estaciones.html"
RETRASOS_MAX_AGE=2700  # 45 min (generador corre a :02,:17,:32,:47)
GTFS_MAX_AGE=259200  # 72 h (ingesta diaria de referencia)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDIR="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR/..")"
[ -f "$CDIR/.env" ] && source "$CDIR/.env"
STATE_FILE="$CDIR/logs/healthcheck.state"
mkdir -p "$CDIR/logs"

telegram_send() {
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
        return 0
    fi
    if ! curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=$1" \
        -d "disable_web_page_preview=true" \
        --max-time 10 > /dev/null 2>&1; then
        echo "[$(date -u +%FT%TZ)] [WARN] telegram_send fallo (el script continua)" >&2
    fi
}

prev_state=$(cat "$STATE_FILE" 2>/dev/null || echo "up")

HEALTH=$(curl -s -A "$UA" --max-time $CURL_TIMEOUT "$HEALTH_URL" 2>/dev/null || echo "")

if [ -z "$HEALTH" ]; then
    if [ "$prev_state" != "down" ]; then
        echo "[$(date -u +%FT%TZ)] [DOWN] /health no accesible"
        telegram_send "🚨 NearMe DOWN: /health no accesible"
    fi
    echo "down" > "$STATE_FILE"
    exit 1
fi

parse() { echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get(\"$1\",\"\"))" 2>/dev/null || true; }

STATUS=$(parse status)
DB=$(parse database)
LAST_RUN=$(parse last_collector_run)
AGE="?"

NOW_TS=$(date -u +%s)
if [ -n "$LAST_RUN" ]; then
    LAST_TS=$(date -u -d"$LAST_RUN" +%s 2>/dev/null || echo 0)
    AGE=$((NOW_TS - LAST_TS))
fi

REASON=""
if [ "$STATUS" != "ok" ]; then
    REASON="status=$STATUS"
elif [ "$DB" != "connected" ]; then
    REASON="database=$DB"
elif [ -n "$LAST_RUN" ] && [ "$AGE" -gt "$MAX_AGE_SECONDS" ]; then
    REASON="pipeline sin ejecutar hace ${AGE}s (max ${MAX_AGE_SECONDS}s)"
fi

if [ -z "$REASON" ]; then
    GTFS_AGE=$(cd "$CDIR" && PYTHONPATH=. venv/bin/python - <<'PYCODE' 2>/dev/null
import sys
sys.path.insert(0, ".")
from src.db import get_conn
c = get_conn().cursor()
c.execute("SELECT EXTRACT(EPOCH FROM (now() - MAX(updated_at)))::bigint FROM renfe_gtfs_meta")
row = c.fetchone()
print(int(row[0]) if row and row[0] is not None else -1)
PYCODE
) || GTFS_AGE=""
    if [ -n "$GTFS_AGE" ] && [ "$GTFS_AGE" -gt "$GTFS_MAX_AGE" ]; then
        REASON="GTFS estatico sin actualizar hace ${GTFS_AGE}s (max ${GTFS_MAX_AGE}s)"
    fi
fi

if [ -z "$REASON" ]; then
    for page in "$RETRASOS_PAGE" "$RETRASOS_ESTACIONES"; do
        if [ ! -f "$page" ]; then
            REASON="retrasos no generados: $page no existe"
            break
        fi
        MTIME=$(stat -c %Y "$page" 2>/dev/null || echo 0)
        PAGE_AGE=$((NOW_TS - MTIME))
        if [ "$PAGE_AGE" -gt "$RETRASOS_MAX_AGE" ]; then
            REASON="retrasos sin actualizar hace ${PAGE_AGE}s (max ${RETRASOS_MAX_AGE}s): $page"
            break
        fi
    done
fi

if [ -n "$REASON" ]; then
    if [ "$prev_state" != "down" ]; then
        echo "[$(date -u +%FT%TZ)] [DOWN] $REASON"
        telegram_send "🚨 NearMe DOWN: $REASON"
    fi
    echo "down" > "$STATE_FILE"
    exit 1
fi

if [ "$prev_state" = "down" ]; then
    echo "[$(date -u +%FT%TZ)] [RECOVERED] api=$STATUS db=$DB pipeline_age=${AGE}s"
    telegram_send "✅ NearMe OK de nuevo: api=$STATUS db=$DB pipeline_age=${AGE}s"
fi
echo "[$(date -u +%FT%TZ)] [OK] api=$STATUS db=$DB pipeline_age=${AGE}s"
echo "up" > "$STATE_FILE"
