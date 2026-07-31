#!/usr/bin/env bash
set -euo pipefail

LOG_DIR=/var/log/nginx
FILTERED=/home/deploy/nearme-osint/analytics/nearme-filtered.log
OUT=/home/deploy/nearme-osint/analytics/index.html

zcat "$LOG_DIR"/access.log.*.gz 2>/dev/null | cat "$LOG_DIR"/access.log "$LOG_DIR"/access.log.1 - |
    grep -E "nearme\.viajeinteligencia\.com| /api/ | /admin| /health|/sw\.js|/manifest\.json|/icon\.svg|/icon-256\.png|/og-image|/static/|/favicon\.png" > "$FILTERED"

goaccess -f "$FILTERED" --log-format=COMBINED -o "$OUT" --no-global-config 2>/dev/null || exit 1

chmod 644 "$OUT"
