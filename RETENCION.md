# Políticas de retención del ecosistema

Documento central para evitar errores de limpieza: cada servicio del ecosistema
(Hetzner 178.105.80.193) tiene una política de rotación definida. Antes de
ejecutar cualquier limpieza de datos, consultar esta tabla.

## Tabla de políticas (2026-09-01)

| Servicio | Datos | Política | Cron | Última revisión |
|---|---|---|---|---|
| **nearme-osint** | PostgreSQL `event_history` (snapshots de eventos) | Borra snapshots > **30 días** | `0 3 * * * cleanup_history_retention(30)` | 2026-09-01 |
| **nearme-osint** | PostgreSQL `events` | **NO se borra** — datos de sismos (Granada), incendios, embalses, etc. Intactos | — | 2026-09-01 |
| **myip** | `data/snapshots/fail2ban-*.json` (estado de bloqueos por hora) | Conserva últimos **90 días** | `15 4 * * * find ... -mtime +90 -delete` | 2026-09-01 |
| **lotería-hash** | SQLite participaciones | Anonimiza reparto a los **12 meses** del cierre (conserva agregados) | `0 4 * * 0 /admin/retencion` | 2026-09-01 |
| **logs nginx** | access/error | Diario, **14 rotaciones**, gzip | logrotate | 2026-09-01 |
| **docker** | imágenes/contenedores | Prune semanal (sin borrar volúmenes) | `30 4 * * 0` | 2026-09-01 |
| **intelligence-hub** | `output/*_day_briefing.html` | Conserva **365 días** | `0 4 1 * * find ... -mtime +365 -delete` | 2026-09-01 |
| **intelligence-hub** | `data/news.db` | ⚠️ Sin rotación (148M y crece) — pendiente de definir | — | 2026-09-01 |
| **analisis-pruebapublica** | SQLite likes/comments | Comentarios moderados (pendiente/aprobado) — crecimiento bajo | — | 2026-09-01 |
| **municipal-intel** | SQLite alerts.db | BDs pequeñas, sin rotación (bajo riesgo) | — | 2026-09-01 |

## Reglas de oro

1. **Datos de eventos (`events`) NO se borran**: alimentan gráficos de sismos de
   Granada, nivel de embalses, lluvia/nieve e incendios.
2. **`event_history` SÍ es recortable**: son snapshots internos para trazar la
   evolución de un evento (`get_event_history`, limit=200). No alimentan gráficos.
3. **Nunca borrar volúmenes Docker** sin confirmar: `deploy_uploads` (41M,
   imágenes) y `todo-osint_todo_data` (SQLite) tienen datos.
4. **Lotería**: la anonimización a 12 meses es intencional y conserva los
   agregados (sumas, %, hashes) para la verificación pública.
5. Embalses y meteorología de nearme se **re-consultan de APIs externas**
   (estadoembalses.es, open-meteo.com) — no dependen de la BD local.

## Incidente histórico (2026-09-01)

- `event_history` creció a **24.3M filas (4.4G)** porque el cron usaba 365 días
  (default heredado, inviable para snapshots cada 15 min).
- Corregido: borrado >7 días (16.8M filas), VACUUM FULL, y cron a 30 días.
- Disco pasó de 65% a 58% (16G libres). PostgreSQL de 4.6G a 2.3G.
- Lección: la política de 365 días era de **lotería**; no aplica a snapshots de nearme.
