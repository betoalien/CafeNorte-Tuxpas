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

### Inmutabilidad de fuentes

Los cuatro archivos originales del cliente viven en `datos/` y no se editan. Sus SHA-256 están
versionados en `datos/SHA256SUMS`. Para verificar desde la raíz: en macOS ejecuta
`(cd datos && shasum -a 256 -c SHA256SUMS)`; en Linux usa
`(cd datos && sha256sum -c SHA256SUMS)`. `validate.sh` ejecuta automáticamente el comando apropiado
y falla con `fuente original del cliente modificada` ante cualquier diferencia.

### Portabilidad y PardoX

`start.sh` y `validate.sh` ejecutan primero `scripts/doctor.sh`, que comprueba Docker, Compose v2,
uv, OpenSSL, ShellCheck y la herramienta de puertos del sistema. En WSL el repositorio debe estar
fuera de `/mnt/`, dentro del filesystem Linux. Si la plataforma no tiene binario PardoX, la salida
incluye `PardoX: UNSUPPORTED_PLATFORM (<os>-<arch>)`; se omiten únicamente las pruebas PardoX y el
pipeline Polars conserva exit 0 si el resto pasa. En plataformas soportadas, la paridad es obligatoria.
En macOS arm64 doctor reporta `PardoX: soportado (probado)`; en macOS x86_64 reporta que el binario
está incluido pero no verificado. En Apple Silicon usa el Python arm64 de uv, no Python bajo Rosetta.

Cada arranque genera `artifacts/reports/run_report.html`, un reporte estático ignorado por Git con
run_id, modos, duración, conteos, validación, respuestas, URL de Superset y enlaces de revisión.
Usa `--no-browser` o `CI=true` para imprimir solo la ruta.

La compatibilidad macOS usa Bash 3.2 con `set -u`; los arrays vacíos se expanden con la forma
`${arr[@]+"${arr[@]}"}`. CI usa Bash 5 y por eso el job `bash-compatibility` ejercita argumentos
vacíos explícitamente.

### Datos nuevos

La ingestión registra `skipped`, `incremental` o `full` por fuente en manifest y run log. Sin
cambios, `start.sh` no ejecuta dbt ni exporta respuestas. Con cambios, dbt hace build completo:
a este volumen tarda segundos y no se justifican modelos incrementales de dbt. Para pruebas usa
`CAFENORTE_DATA_DIR=/ruta/a/una/copia`; nunca se modifica `datos/`.

### status.sh

Muestra contenedores, healthcheck, último `run_id`, conteos de ejecución, filas Silver, versión dbt
y filas de Gold, URL de Superset y usuarios demo sin mostrar contraseñas.

### Superset

Superset usa `superset_meta` para metadatos, Redis para caché y `superset_ro` para consultar solo
`analytics`. Los artefactos declarativos y el bootstrap idempotente viven en `superset/`. Las
versiones fijadas son `apache/superset:4.1.1` y `redis:7.2.7-alpine3.21`; ambas imágenes incluyen
`linux/arm64`.

Redis solo está expuesto dentro de la red Compose. Las respuestas CSV se exportan sin `built_at`;
el timestamp sigue disponible en las tablas Gold y la exportación se ejecuta como parte del
harness sin producir cambios por tiempo en Git.

## Fallos

- Un contrato invalido bloquea la fuente afectada.
- Un registro invalido conocido va a cuarentena si el contrato permite continuar.
- Una diferencia Polars/PardoX bloquea la promocion de PardoX, no el pipeline de referencia.
- Un test dbt critico bloquea Gold.
- Superset no se declara listo si Gold no tiene una ejecucion valida, falla `psycopg2`, RLS no aisla tiendas o el dashboard no fue importado.

## Recuperacion

El pipeline debe reconstruir Silver y Gold desde Bronze. PostgreSQL no es la unica copia de los datos originales. Toda operacion de recuperacion debe registrar un nuevo `run_id`.
