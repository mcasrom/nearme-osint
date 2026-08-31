# Informe de viabilidad del ecosistema — 31/08/2026

## Contexto
Análisis de los accesos de la última semana (98.317 peticiones nginx, todos los vhosts).
Objetivo: determinar viabilidad por proyecto y decidir dónde concentrar recursos.

## Veredicto global
**SÍ hay viabilidad.** 29.645 peticiones humanas reales/semana ≈ **4.235/día ≈ 176/hora**
(30.3% del total; el resto son bots monitor/SEO/scanners).

## Clasificación por proyecto

### 🟢 SÓLIDOS — prioridad de inversión (78% del tráfico humano)
| Proyecto | Humano/sem | % humano | Dominio |
|---|---|---|---|
| country.viajeinteligencia.com | 8.549 | 66% | país a país |
| municipal.viajeinteligencia.com | 7.876 | 45% | datos municipales |
| nearme.viajeinteligencia.com | 4.609 | 28.5% | OSINT cercano |
| www.viajeinteligencia.com | 2.245 | 15.4% | hub principal |

### 🟡 VIABLES — mantener, sin foco principal
| Proyecto | Humano/sem | % humano |
|---|---|---|
| radar.viajeinteligencia.com | 1.163 | 68% |
| aegis.viajeinteligencia.com | 951 | 91% |
| 178.105.80.193 (directo) | 931 | 43% |
| news.viajeinteligencia.com | 614 | 9% |
| status.viajeinteligencia.com | 220 | 55% |
| fimi.viajeinteligencia.com | 72 | 36% (recién lanzado) |

### 🔴 ZOMBIES — mantenimiento mínimo o descomisión (a evaluar)
| Proyecto | Humano/sem | % humano | Razón |
|---|---|---|---|
| eclipse.viajeinteligencia.com | 559 | 13.5% | sobre todo bots |
| myip.viajeinteligencia.com | 306 | 3% | casi solo bots |
| security.viajeinteligencia.com | 337 | 10% | auth-basic limita |
| operacion-puzzle.viajeinteligencia.com | 161 | 5% | bots dominan |
| wiki.viajeinteligencia.com | 141 | 12% | privado, esperable |
| libro-colaborativo | 368 | 50% | bajo volumen |
| jobs.viajeinteligencia.com | 188 | 28.5% | bajo |

### ⚫ DESCOMISIONADOS (ya no son proyectos)
| Proyecto | Estado real | Detalle |
|---|---|---|
| tools.viajeinteligencia.com | Descomisionado 08-Ago-2026 | Redirige 301 al dominio raíz |
| alquimetria.viajeinteligencia.com | Descomisionado | Redirige 301 a www.viajeinteligencia.com |

> **Nota:** tools y alquimetria NO son proyectos activos. Su tráfico residual
> (tools 46, alquimetria 5 humanos/sem) son las redirecciones 301 al principal.
> No requieren inversión ni mantenimiento; solo deben seguir redirigiendo.

## Estrategia acordada (31/08/2026)
**CONSOLIDAR LOS SÓLIDOS:**
1. **country** — el más usado por humanos (66%). Prioridad 1: SEO, contenido, actualización.
2. **municipal** — 45% humano, segundo mayor volumen. Ya endurecido contra bots (31/08). Invertir en contenido/datos.
3. **nearme** — 28.5%, motor OSINT. Mantener pipeline + visibilidad.
4. **www (hub)** — 15.4% pero es la puerta de entrada. Mantener como distribuidor de tráfico.

**ZOMBIES (mantenimiento mínimo):** myip, wiki, operacion-puzzle, eclipse, security,
jobs, libro-colaborativo. No invertir más. Dejar funcionando sin coste; descomisión
si dejan de ser mantenibles.

**YA DESCOMISIONADOS (no proyectos):** tools, alquimetria. Solo siguen redirigiendo 301 al principal.

## Acciones derivadas (relacionadas con este informe)
- **Hardening accesos (31/08)**: bloqueados scanners (feroxbuster, l9scan, censys, curl)
  en block_bots.conf unificado + rate-limit en municipal. Tráfico humano intacto.
- Los healthchecks/Uptime-Kuma (~24%) son legítimos y quedan aislados.

## Nota
La config de nginx no está versionada en repos (es del sistema). Los cambios de
hardening se documentan en WAYAHEAD.md de nearme para trazabilidad.
