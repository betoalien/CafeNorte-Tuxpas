# ¿Qué usamos y por qué?

Este documento describe el stack que realmente ejecuta CaféNorte y la metodología aplicada al
reto. Las versiones se toman del repositorio, no de una lista idealizada: `pyproject.toml`,
`uv.lock`, `compose.yaml` y `superset/Dockerfile` son las fuentes de verdad.

## Parte A: Metodología

### Harness Engineering

Es construir un arnés repetible alrededor del producto: diagnóstico, ejecución, validación y
evidencia forman un solo flujo verificable. El objetivo es que una demo limpia revele fallos en vez
de depender de pasos manuales invisibles.

Aquí se aplicó con [`scripts/`](../scripts/), [`doctor`](../scripts/doctor.sh),
[`validate`](../scripts/validate.sh), el [reporte de corrida](../scripts/run_report.py) y
[CI](../.github/workflows/ci.yml). La CLI `cafenorte` es el orquestador multiplataforma y los
envoltorios conservan los comandos oficiales.

### Spec-Driven Development

La especificación define alcance, contratos y criterios antes de implementar. Cada bloque tiene un
contrato auditable y las decisiones de alcance quedan visibles para no convertir una demo en
funcionalidad no solicitada.

La implementación sigue [SPEC-001](specs/SPEC-001-INGESTION.md),
[SPEC-002](specs/SPEC-002-ANALYTICS.md), [SPEC-003](specs/SPEC-003-ENGINE-PARITY.md) y
[SPEC-004](specs/SPEC-004-HARNESS.md).

### Specification by Example

Los requisitos se expresan como ejemplos observables: Given una fuente y un estado, When se corre
el comando, Then se comprueban filas, sumas, hashes, permisos o aislamiento. Un resultado plausible
no cuenta si no existe una aserción que pueda fallar.

Los ejemplos viven en [`tests/`](../tests/), incluidos idempotencia, CFDI, N/A, PII, paridad,
RLS y reporte; la evidencia por bloque está en [`artifacts/evidence/`](../artifacts/evidence/).

### ADRs

Los ADR registran decisiones irreversibles y sus límites, en lugar de esconderlos en código.

- [ADR-001](decisions/ADR-001-STACK.md): stack local y separación por capas.
- [ADR-002](decisions/ADR-002-POSTGRESQL-SERVING.md): PostgreSQL como serving local.
- [ADR-003](decisions/ADR-003-DBT-SEMANTICS.md): dbt es propietario de la semántica.
- [ADR-004](decisions/ADR-004-NO-AIRFLOW-KAFKA.md): Airflow y Kafka se difieren.
- [ADR-005](decisions/ADR-005-PARDOX.md): PardoX es motor alternativo con paridad.
- [ADR-006](decisions/ADR-006-SUPERSET.md): Superset es visor de Gold con RLS.

### Contratos e invariantes

Los contratos convierten entradas ambiguas en registros tipados y conservan los inválidos para
explicarlos. Las invariantes protegen la trazabilidad, la inmutabilidad de fuentes y la semántica
de calidad, no solo el esquema.

La evidencia concreta es [`DATA_CONTRACTS.md`](DATA_CONTRACTS.md), los modelos Pydantic en
[`src/cafenorte/contracts.py`](../src/cafenorte/contracts.py),
[`datos/SHA256SUMS`](../datos/SHA256SUMS) y `audit.quarantine`.

### Definition of Ready / Done

Ready significa tener especificación, criterios de aceptación, datos y decisiones suficientes para
ejecutar. Done exige implementación, pruebas, evidencia, documentación coherente y reproducción
desde cero.

La lista aplicada al cierre está en [`final-checklist.md`](../artifacts/evidence/final-checklist.md).

### Seguridad y privacidad

Los secretos se generan en la instalación, se restringen en `.env` y no se versionan; los dashboards
consumen Gold con roles y RLS. La PII se excluye de Silver y Gold y la historia se revisa antes de
entregar.

Se puede inspeccionar [`compose.yaml`](../compose.yaml),
[`superset/bootstrap.py`](../superset/bootstrap.py), la prueba de RLS y la evidencia de revisión de
secretos en [`final-validation.md`](../artifacts/evidence/final-validation.md).

### Reglas para agentes de IA

[`AGENTS.md`](../AGENTS.md) define la jerarquía, invariantes y Definition of Done; [`AI_LOG.md`](../AI_LOG.md)
conserva prompts, decisiones y errores reales. En este flujo, Codex implementa, Claude revisa y el
propietario decide el alcance y las afirmaciones finales.

## Parte B: Tecnologías

| Tecnología | Versión | Capa | Rol en el proyecto | Alternativa descartada |
|---|---|---|---|---|
| Python | `>=3.12,<3.13` | Runtime | Contratos, CLI y loaders | Bash como orquestador único |
| uv | workflow `uv sync` | Entorno | Resuelve, instala y fija `uv.lock` | pip + requirements sueltos |
| Pydantic | `2.11.9` | Bronze/Silver | Contratos por registro y manifest | Validación manual |
| Polars | `1.34.0` | Bronze/Silver | Motor de referencia columnar | pandas |
| PardoX | `0.3.4` | Motor alternativo | Paridad de `sales.csv` | Promoverlo como camino crítico |
| psycopg | `3.2.10` | PostgreSQL | Conexión y carga SQL desde Python | ORM |
| ADBC PostgreSQL | `1.7.0` | Carga | Escritura nativa de referencia | `executemany` |
| dbt-core / dbt-postgres | `1.9.8` / `1.9.0` | Gold | Semántica, tests y marts | Métricas en Python/Superset |
| PostgreSQL | `16.4-alpine3.20` | Serving | Silver, audit, Gold y metadatos | DuckDB |
| Redis | `7.2.7-alpine3.21` | Caché | Caché de Superset | Caché dentro de Python |
| Apache Superset | `4.1.1` | BI | Dashboards, datasets y RLS | Streamlit como visor |
| Docker / Compose | Compose v2; imagen PostgreSQL fijada | Infraestructura | Stack reproducible local | Instalación manual de servicios |
| Bash / ShellCheck | Bash `3.2+`; versión del host | Harness | Envoltorios y lint de shell | Scripts no validados |
| `cafenorte` + `.bat` | versión del proyecto | Orquestación | CLI Python y entrada Windows | Lógica duplicada por SO |
| pytest | `8.4.2` | Pruebas | Unitarias, integración y regresión | Smoke tests manuales |
| Ruff | `0.13.2` | Calidad | Lint Python | Formato no automatizado |
| GitHub Actions | actions checkout/setup-uv fijadas por workflow | CI | Ubuntu completo y matrices de CLI | Validación solo local |
| gitleaks / revisión de secretos | gitleaks si está instalado; revisión Git | Seguridad | Buscar secretos en historia y artefactos | Confiar solo en `.gitignore` |

### Python y uv

Python ejecuta contratos, ingestión, CLI y utilidades. uv instala el intérprete y las dependencias
desde el lockfile para que macOS, Linux y Windows compartan el mismo entorno lógico. Vive en
[`pyproject.toml`](../pyproject.toml), [`uv.lock`](../uv.lock) y `src/cafenorte/`.

Verificación: `uv sync && uv run python --version`.

### Pydantic

Pydantic valida cada registro y el manifest, mientras que la cuarentena conserva el contexto de
los inválidos. Se eligió por contratos explícitos y errores estructurados, no por descartar filas.

Vive en [`src/cafenorte/contracts.py`](../src/cafenorte/contracts.py) y se verifica con
`uv run pytest tests/test_contracts.py`.

### Polars

Polars es el motor de referencia para leer, transformar y preparar Silver: columnar, eficiente y
con tipos explícitos. pandas no se usa en el repositorio; Polars ofrece mejor control de memoria y
un camino claro a Parquet.

Vive en [`src/cafenorte/engines/polars_engine.py`](../src/cafenorte/engines/polars_engine.py).
Verificación: `uv run pytest tests/test_ingestion.py`.

### PardoX

PardoX es la alternativa diseñada por el propietario, con núcleo Rust. Se usa con alcance honesto:
paridad de `sales.csv`, benchmark y evidencia; inventario, Shopify y FX permanecen en Polars.

Vive en [`src/cafenorte/engines/pardox_engine.py`](../src/cafenorte/engines/pardox_engine.py),
ADR-005 y la reproducción de `write_sql_prdx`. Verificación: `uv run pytest tests/test_engines.py`.

### psycopg y ADBC

psycopg conecta el loader, consultas de control y Superset; ADBC prueba la ruta de escritura nativa
de PostgreSQL. Se separan de la semántica dbt para que la carga no invente métricas.

Viven en `src/cafenorte/`, el benchmark y `pyproject.toml`. Verificación: `uv run pytest` y
`uv run python -m cafenorte.benchmark`.

### dbt

dbt transforma Silver en staging, intermediate y analytics; conserva la conciliación, FX, costos,
dimensiones y las cuatro respuestas. Se eligió para versionar SQL y tests junto al modelo.

Vive en [`dbt/`](../dbt). Verificación: `uv run dbt build --project-dir dbt --profiles-dir dbt`.

### PostgreSQL

PostgreSQL es el serving layer transaccional: separa `silver`, `audit`, `intermediate` y `analytics`
y permite roles y RLS. DuckDB fue más simple, pero no encajaba con multiusuario ni la integración
PardoX/PostgreSQL.

Vive en [`compose.yaml`](../compose.yaml) y [`docker/postgres/init/`](../docker/postgres/init/).
Verificación: `docker compose ps` y `./scripts/status.sh`.

### Redis y Apache Superset

Redis aporta caché; Superset solo visualiza marts certificados y aplica RLS, sin recalcular negocio.
La separación de metadatos `superset_meta` evita mezclar configuración con Gold.

Viven en [`compose.yaml`](../compose.yaml), [`superset/`](../superset/) y ADR-006. Verificación:
`./scripts/start.sh` y `uv run pytest tests/test_rls.py`.

### Docker, Bash y ShellCheck

Docker Compose reproduce servicios y volúmenes; Bash conserva los comandos operativos históricos y
ShellCheck detecta errores portables. La CLI Python es la lógica común y los shell scripts son
envoltorios.

Viven en [`compose.yaml`](../compose.yaml), [`scripts/`](../scripts/) y
[`scripts/windows/`](../scripts/windows/). Verificación: `shellcheck scripts/*.sh` y
`uv run cafenorte doctor`.

### CLI, pruebas, Ruff, GitHub Actions y secretos

`cafenorte` concentra el orquestador multiplataforma; pytest valida comportamiento, Ruff calidad y
GitHub Actions reproduce la ruta Ubuntu y prueba la CLI en macOS/Windows. La revisión de secretos
usa gitleaks cuando está disponible y patrones Git como respaldo.

Viven en [`src/cafenorte/cli.py`](../src/cafenorte/cli.py), `tests/`, `pyproject.toml`,
`.github/workflows/ci.yml` y `AI_LOG.md`. Verificación: `uv run pytest`, `uv run ruff check .` y
`gitleaks detect --source .` cuando el binario está instalado.

## Parte C: Consideradas y descartadas

- **pandas:** no se usa; se prefieren memoria, tipado y ejecución columnar de Polars.
- **DuckDB:** descartado como serving principal por [ADR-002](decisions/ADR-002-POSTGRESQL-SERVING.md).
- **Spark:** sobredimensionado para el volumen single-node y el presupuesto del reto.
- **Airflow/MWAA:** diferidos junto con la orquestación pesada; ver [ADR-004](decisions/ADR-004-NO-AIRFLOW-KAFKA.md).
- **Kafka:** no hay CDC ni eventos; ver [ADR-004](decisions/ADR-004-NO-AIRFLOW-KAFKA.md).
- **QuickSight:** posible salida administrada, pero no es el visor local; ver [ADR-006](decisions/ADR-006-SUPERSET.md).
- **Tableau:** bonus opcional, no parte del camino reproducible; ver [ADR-001](decisions/ADR-001-STACK.md).
- **Streamlit:** descartado como visor principal por permisos, navegación y RLS; ver [ADR-006](decisions/ADR-006-SUPERSET.md).
- **AWS Transfer SFTP:** no se necesita para las fuentes entregadas; la alternativa AWS está en [PROPUESTA_AWS](PROPUESTA_AWS.md).

## Parte D: Mapa del recorrido

Un registro de `sales.csv` sigue este recorrido:

```text
datos/sales.csv
  -> SaleRecord (contracts.py, contrato Pydantic)
  -> silver.pos_sales (ingest.py, row_hash/run_id)
  -> dbt/models/staging/stg_pos_sales.sql
  -> dbt/models/intermediate/int_product_identity.sql
  -> dbt/models/intermediate/int_sales_enriched.sql
  -> dbt/models/marts/fct_sales.sql
  -> analytics.mart_inventory_turnover_top10 / mart_monthly_channel_growth /
     mart_negative_margin_products / mart_source_reconciliation
  -> dataset Gold registrado por superset/bootstrap.py
  -> dashboard “CaféNorte — 4 respuestas”
```

Silver conserva datos y columnas técnicas; `int_product_identity` y el resto de la semántica son
responsabilidad de dbt. Superset solo consulta los marts y sus reglas RLS.

## Verificación de este documento

El test [`tests/test_tech_stack_doc.py`](../tests/test_tech_stack_doc.py) comprueba que los enlaces
relativos citados existan y que las versiones declaradas para Python, Polars, PardoX, Pydantic,
dbt, psycopg, ADBC, PostgreSQL, Redis y Superset coincidan con los archivos fuente del repositorio.
