#!/usr/bin/env bash
# healthcheck.sh — Verifica API, DB y freshness del pipeline de NearMe
# Uso en cron: */5 * * * * cd /home/deploy/nearme-osint && ./scripts/healthcheck.sh >> logs/healthcheck.log 2>&1
set -e

HEALTH_URL="https://nearme.viajeinteligencia.com/health"
CURL_TIMEOUT=10
MAX_AGE_SECONDS=2700  # 45 min (colectores corren cada 15 min)
CDIR="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$CDIR/.env" ] && source "$CDIR/.env"

alert() {
    local msg="$1"
    echo "[$(date -u +%FT%TZ)] [ALERT] $msg"
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=🚨 NearMe DOWN: $msg" \
            --max-time 10 > /dev/null 2>&1
    fi
}

HEALTH=$(curl -s --max-time $CURL_TIMEOUT "$HEALTH_URL" 2>/dev/null || echo "")

if [ -z "$HEALTH" ]; then
    alert "/health no accesible"
    exit 1
fi

parse() { echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get(\"$1\",\"\"))" 2>/dev/null; }

STATUS=$(parse status)
DB=$(parse database)
LAST_RUN=$(parse last_collector_run)

if [ "$STATUS" != "ok" ]; then
    alert "status=$STATUS"
    exit 1
fi
if [ "$DB" != "connected" ]; then
    alert "database=$DB"
    exit 1
fi

if [ -n "$LAST_RUN" ]; then
    NOW_TS=$(date -u +%s)
    LAST_TS=$(date -u -d"$LAST_RUN" +%s 2>/dev/null || echo 0)
    AGE=$((NOW_TS - LAST_TS))
    if [ "$AGE" -gt "$MAX_AGE_SECONDS" ]; then
        alert "pipeline sin ejecutar hace ${AGE}s"
        exit 1
    fi
    echo "[$(date -u +%FT%TZ)] [OK] api=$STATUS db=$DB pipeline_age=${AGE}s"
else
    echo "[$(date -u +%FT%TZ)] [OK] api=$STATUS db=$DB (sin last_collector_run)"
fi
