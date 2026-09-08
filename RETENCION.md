# Políticas de retención del ecosistema

Documento central para evitar errores de limpieza: cada servicio del ecosistema
(Hetzner 178.105.80.193) tiene una política de rotación definida. Antes de
ejecutar cualquier limpieza de datos, consultar esta tabla.

## Tabla de políticas (2026-09-08)

| Servicio | Datos | Política | Cron | Última revisión |
|---|---|---|---|---|
| **nearme-osint** | PostgreSQL `event_history` (snapshots de eventos) | Borra snapshots > **7 días** | `0 3 * * * cleanup_history_retention(7)` | 2026-09-08 |
| **nearme-osint** | PostgreSQL `events` | **NO se borra** — datos de sismos (Granada), incendios, embalses, etc. Intactos | — | 2026-09-01 |
| **myip** | `data/snapshots/fail2ban-*.json` (estado de bloqueos por hora) | Conserva últimos **90 días** | `15 4 * * * find ... -mtime +90 -delete` | 2026-09-01 |
| **lotería-hash** | SQLite participaciones | Anonimiza reparto a los **12 meses** del cierre (conserva agregados) | `0 4 * * 0 /admin/retencion` | 2026-09-01 |
| **logs nginx** | access/error | Diario, **14 rotaciones**, gzip | logrotate | 2026-09-01 |
| **docker** | imágenes/contenedores | Prune semanal (sin borrar volúmenes) | `30 4 * * 0` | 2026-09-01 |
| **intelligence-hub** | `output/*_day_briefing.html` | Conserva **365 días** | `0 4 1 * * find ... -mtime +365 -delete` | 2026-09-01 |
| **intelligence-hub** | `data/news.db` | ⚠️ Sin rotación (223M y crece) — pendiente de definir | — | 2026-09-08 |
| **analisis-pruebapublica** | SQLite likes/comments | Comentarios moderados (pendiente/aprobado) — crecimiento bajo | — | 2026-09-01 |
| **municipal-intel** | SQLite alerts.db | BDs pequeñas, sin rotación (bajo riesgo) | — | 2026-09-01 |

## Reglas de oro

1. **Datos de eventos (`events`) NO se borran**: alimentan gráficos de sismos de
   Granada, nivel de embalses, lluvia/nieve e incendios.
2. **`event_history` SÍ es recortable**: son snapshots internos para trazar la
   evolución de un evento (`get_event_history`, limit=200). No alimentan gráficos
   ni ninguna página pública (enjambre/retrasos/incendios/calidad del aire/embalses
   leen de `events`, `zone_metrics`, `air_quality_daily` o APIs externas).
3. **Nunca borrar volúmenes Docker** sin confirmar: `deploy_uploads` (41M,
   imágenes) y `todo-osint_todo_data` (SQLite) tienen datos.
4. **Lotería**: la anonimización a 12 meses es intencional y conserva los
   agregados (sumas, %, hashes) para la verificación pública.
5. Embalses y meteorología de nearme se **re-consultan de APIs externas**
   (estadoembalses.es, open-meteo.com) — no dependen de la BD local.

## Incidente histórico (2026-09-01)

- `event_history` creció a **24.3M filas (4.4G)** porque el cron usaba 365 días
  (default heredado, inviable para snapshots cada 15 min).
- Corregido: borrado >30 días, VACUUM FULL, y cron a 30 días.
- Disco pasó de 65% a 58% (16G libres). PostgreSQL de 4.6G a 2.3G.
- Lección: la política de 365 días era de **lotería**; no aplica a snapshots de nearme.

## Incidente (2026-09-08) — 30 días seguía siendo demasiado

- **Síntoma**: disco 58→68% en ~2 días. FIMI descartada (solo ~75M de datos reales).
- **Causa**: `event_history` crecía **~1M filas/día (~180-220 MB/día)** (volumen de
  captura multiplicado). Con retención 30 días y solo 14 días de datos (desde el
  reset del 01/Sep) seguía en rampa hacia ~5-6 GB en equilibrio. El cron borraba 0
  cada noche porque nada superaba 30 días aún — no era fallo, retención laxa.
- **Solución (elección del usuario)**: retención **7 días**. Borrado manual de
  **6.379.593 filas** >7 días + `VACUUM FULL` → tabla 2537 MB → **1239 MB**. Cron
  actualizado a `cleanup_history_retention(7)` (backup en `/tmp/cron_backup.txt`).
- Disco **67% → 60%** (15G libres) tras: event_history (~1.3G) + dump nearme a
  `/var/backups` (417M) + journal vacuum 50M (149M) + apt clean (109M) +
  docker prune (1.8G build cache).
- **Afectados: ninguno**. Verificado por fuente de datos: las páginas públicas de
  sismos/renfe/incendios/calidad del aire/embalses no usan `event_history`.
  Solo el "Patrón temporal" del detalle de un evento en NearMe pasa a 7 días
  (los eventos son efímeros <7d, sin pérdida relevante).
- La tabla se estabilizará en ~7 días (~1.2 GB) con el cron diario.
