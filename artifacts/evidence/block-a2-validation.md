# Validación del Bloque A-2

Fecha: 2026-10-01 (America/Monterrey). Host: macOS Apple Silicon.

## Alcance

Solo correcciones previas a Silver. No se implementaron tablas Silver, modelos dbt, ruta PardoX,
Gold ni Superset.

## Entorno

```text
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
Docker Compose v5.1.1
uv 0.10.5
```

`.env` ya existía como archivo local ignorado por Git. Sus valores no se registran; se usa el hash
del archivo para demostrar estabilidad de puerto y credenciales.

```text
stat -f %Lp .env -> 600
POSTGRES_PORT -> 23779
SHA-256 .env -> 1a16078ab868c09d0ad4b4944581a38d91c6fd41d1748d84957bb5f0daf4e19d
```

## Perfilado A-2

Comando ejecutado después de corregir las reglas de mapping:

```bash
uv run python scripts/profile_sources.py
```

Resultado relevante en `artifacts/evidence/profiling.md`:

```text
POS explicit: 74,141 filas / 114,284 unidades / 26,989,097.62 MXN
POS product_number: 6,217 filas / 9,547 unidades / 1,434,008.52 MXN
POS product_number_null_erp: 6,132 filas / 9,552 unidades / 2,524,147.68 MXN
Shopify explicit: 6,959 filas / 9,289 unidades / 2,254,120.66 fuente
Shopify product_number: 1,849 filas / 2,494 unidades / 403,053.27 fuente
Shopify product_number_null_erp: 1,139 filas / 1,509 unidades / 326,939.13 fuente
```

Las cifras esperadas para mappings con `sku_erp` nulo coinciden: POS 6,132 filas /
2,524,147.68 MXN y Shopify 1,139 filas. `CN-00016` tiene `sku_erp = null` y `handle = null` en
`inventory.json`; se reporta así, sin ajustar datos.

`profiling.md` quedó con hash:

```text
61af2f1c133b52dc9d33c85522b6bef75e8ffea422ade44222435e569c55893a
```

## Validación estática

```bash
shellcheck scripts/*.sh docker/postgres/init/*.sh
```

Salida: sin avisos, código 0.

```bash
uv run ruff check scripts/profile_sources.py
```

Salida:

```text
All checks passed!
```

## Harness macOS

### start/status

```bash
./scripts/start.sh
./scripts/status.sh
```

Salida resumida:

```text
PostgreSQL host: 127.0.0.1
PostgreSQL port: 23779
Health: healthy
cafenorte-postgres Up ... (healthy) 127.0.0.1:23779->5432/tcp
/var/run/postgresql:5432 - accepting connections
```

### validate

```bash
./scripts/validate.sh
```

Salida:

```text
schema_name: analytics, audit, intermediate, silver
rolname: dbt, pipeline, superset_meta, superset_ro
datname: superset_meta
All checks passed!
```

`validate.sh` ya no ejecuta `scripts/profile_sources.py`; el hash de `profiling.md` antes y
después de `validate.sh` permaneció igual:

```text
61af2f1c133b52dc9d33c85522b6bef75e8ffea422ade44222435e569c55893a
```

### restart

```bash
./scripts/restart.sh
```

Resultado:

```text
PostgreSQL port: 23779
Health: healthy
/var/run/postgresql:5432 - accepting connections
```

Después de `restart.sh`, `.env` mantuvo el mismo hash:

```text
1a16078ab868c09d0ad4b4944581a38d91c6fd41d1748d84957bb5f0daf4e19d
```

Por tanto, puerto y credenciales locales permanecieron estables sin exponer secretos.

### reset sin confirmación

```bash
./scripts/reset.sh
```

Salida y código:

```text
No changes made. Re-run with --yes to confirm.
exit code 2
```

`./scripts/status.sh` después de ese comando confirmó que PostgreSQL seguía `healthy`.

### reset confirmado

```bash
./scripts/reset.sh --yes
```

Salida resumida:

```text
Container cafenorte-postgres Removed
Network cafenorte_default Removed
Volume cafenorte_postgres_data Removed
```

`docker ps --filter name=cafenorte-postgres` no devolvió contenedores.

## Inmutabilidad de datos

Hashes antes y después de `reset.sh --yes`:

| Archivo | SHA-256 |
|---|---|
| `datos/ecommerce_orders.parquet` | `00c560b39425fe7f0088fbe20c66c2b8861d10c2c7006ba6e7335cdd6dfc856e` |
| `datos/exchange_rates.csv` | `a0e827ec1e048cf397584eca3d692cb5b5b1f6b477fb78efca2fdbd2f488bddf` |
| `datos/inventory.json` | `2355c6cab9ff00a707b5505a464a8f7e1a9bf5a2aa6c7a2b6b008f5299c8eada` |
| `datos/sales.csv` | `87628a584d30a353f3bcc9dbe20c2d8f1e55c80a0036ecee88e76fce61031276` |

## Nota sobre estado Git

Durante la validación A-2 el árbol estaba deliberadamente sucio por las correcciones del bloque y
por el README redactado por Claude que debía incluirse en el commit único. El control específico
del punto 6 fue el hash estable de `profiling.md` antes y después de `validate.sh`.

## Validación posterior al commit

Commit principal: `8bb9161` (`Block A-2: null sku_erp reconciliation, bash-only port, macOS validation`).

Comando ejecutado después del commit:

```bash
./scripts/validate.sh && git status --short
```

Salida relevante:

```text
All checks passed!
```

`git status --short` no imprimió ninguna línea; el árbol quedó limpio.
