# Runbook local

## Contrato operativo

### start.sh

Valida prerrequisitos, levanta PostgreSQL y ejecuta la corrida completa Bronze → Silver. La carga
usa Polars, Pydantic, manifiestos SHA-256 y reemplazo transaccional de tablas Silver. PardoX
permanece fuera del Bloque D1. Después de Silver, `start.sh` ejecuta `dbt build`, levanta
Redis/Superset e importa el dashboard versionado de `superset/`, y exporta las cuatro respuestas.

### stop.sh

Detiene servicios sin borrar datos generados, evidencia ni volumenes.

### restart.sh

Compone `stop.sh` y `start.sh`; no replica sus comandos.

### reset.sh

Elimina solo recursos reproducibles del proyecto, incluidos los volúmenes de PostgreSQL, Redis y
metadatos de Superset. Requiere `--yes`, muestra objetivos exactos y preserva `datos/`, documentos y `AI_LOG.md`.

### validate.sh

Ejecuta validaciones del harness sin reescribir evidencia: sintaxis Bash, ShellCheck obligatorio,
`docker compose config`, pytest, existencia de schemas/roles/base PostgreSQL y Ruff.

La ingestión directa se puede repetir con `uv run python -m cafenorte.ingest`; cada ejecución usa
un `run_id`, reemplaza Silver dentro de una transacción y deja su manifiesto en
`artifacts/manifests/<run_id>.json` y `audit.ingestion_manifest`.

### dbt

`profiles.yml` vive en `dbt/` y solo lee variables de entorno. `dbt build` crea staging sobre
Silver, intermediate y marts en `analytics`; guarda `manifest.json` y `run_results.json` en
`artifacts/evidence/dbt/` (ruta `../artifacts/evidence/dbt` relativa al proyecto dbt). Las tablas
analíticas consumen únicamente la última corrida exitosa.

El perfilado reproducible se ejecuta aparte cuando cambian las fuentes o sus reglas:

```bash
uv run python scripts/profile_sources.py
```

Ese comando regenera `artifacts/evidence/profiling.md`; `validate.sh` no debe modificarlo.

### status.sh

Muestra contenedores, healthcheck, último `run_id`, conteos de ejecución, filas Silver, versión dbt
y filas de Gold, URL de Superset y usuarios demo sin mostrar contraseñas.

### Superset

Superset usa `superset_meta` para metadatos, Redis para caché y `superset_ro` para consultar solo
`analytics`. Los artefactos declarativos y el bootstrap idempotente viven en `superset/`. Las
versiones fijadas son `apache/superset:4.1.1` y `redis:7.2.7-alpine3.21`; ambas imágenes incluyen
`linux/arm64`.

## Fallos

- Un contrato invalido bloquea la fuente afectada.
- Un registro invalido conocido va a cuarentena si el contrato permite continuar.
- Una diferencia Polars/PardoX bloquea la promocion de PardoX, no el pipeline de referencia.
- Un test dbt critico bloquea Gold.
- Superset no se declara listo si Gold no tiene una ejecucion valida, falla `psycopg2`, RLS no aisla tiendas o el dashboard no fue importado.

## Recuperacion

El pipeline debe reconstruir Silver y Gold desde Bronze. PostgreSQL no es la unica copia de los datos originales. Toda operacion de recuperacion debe registrar un nuevo `run_id`.
