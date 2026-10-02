# Evidencia Bloque D1: Superset local, Redis y RLS

Validación macOS Apple Silicon. PardoX no fue modificado.

## Secuencia ejecutada

```text
./scripts/reset.sh --yes
./scripts/start.sh
./scripts/validate.sh
```

`reset.sh --yes` elimina `cafenorte_postgres_data` y `cafenorte_redis_data`; conserva `datos/` y
el código. `start.sh` genera puertos y secretos en `.env` con permisos 600, levanta PostgreSQL,
Redis y Superset, ejecuta Bronze → Silver → Gold e inicializa el dashboard de forma idempotente.

## Imágenes y healthchecks

```text
apache/superset:4.1.1       base fija, manifest linux/arm64 verificado
redis:7.2.7-alpine3.21      manifest linux/arm64 verificado
PostgreSQL: healthy
Redis: healthy
Superset: healthy
```

## Validación oficial

```text
9 passed
Done. PASS=60 WARN=0 ERROR=0 SKIP=0 TOTAL=60
All checks passed!
Superset API login, dashboard import, and T001 RLS declaration: PASS
```

La API autenticó `director` y `gerente_t001`, confirmó el dashboard `cafenorte-4-respuestas`
para dirección y validó la declaración RLS `tienda_id = 'T001'` para P2/P3/P4. P1 permanece como
indicador de red sin filtro de tienda. La URL y el puerto se muestran con `./scripts/status.sh`;
las contraseñas no se imprimen y permanecen en `.env`.

## Dashboard importado

```text
Superset API login, dashboard import, and T001 RLS declaration: PASS
Dashboard: CaféNorte — 4 respuestas
Charts declarados: P1, P2, P3, P4, Reconciliación
Fuente permitida: analytics (marts y mart_source_reconciliation)
```
