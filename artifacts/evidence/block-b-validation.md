# Evidencia Bloque B: Bronze → Silver

Fecha de validación: 2026-10-01, macOS Apple Silicon, Bash 3.2.57.

## Corrida limpia

Se ejecutó `./scripts/reset.sh --yes` y después `./scripts/start.sh`. El reset preservó
`datos/`, documentación, código y evidencia; el arranque creó el volumen nuevo, esperó PostgreSQL
healthy y ejecutó `uv run python -m cafenorte.ingest`.

Primer `run_id`: `05337a0d-6b09-4c17-abba-baf2fb8a8d69`.

La corrida terminó `succeeded` con cuatro manifiestos en `audit.ingestion_manifest` y archivos
JSON en `artifacts/manifests/`. Contrato: `silver.v1`.

## Segunda corrida e idempotencia

Se ejecutó de nuevo `uv run python -m cafenorte.ingest` con las mismas fuentes.

Segundo `run_id`: `0e978bd9-bfc5-4b55-845b-3338de6575e6`.

Conteos por archivo en la segunda corrida:

| Fuente | Input | Accepted | Rejected |
|---|---:|---:|---:|
| `datos/sales.csv` | 86,490 | 86,490 | 0 |
| `datos/inventory.json` | 230,951 | 230,951 | 0 |
| `datos/ecommerce_orders.parquet` | 9,947 | 9,947 | 0 |
| `datos/exchange_rates.csv` | 730 | 730 | 0 |

Conteos reconciliados en Silver:

| Tabla | Filas | Unidades | Monto |
|---|---:|---:|---:|
| `silver.pos_sales` | 86,490 | 133,383 | 30,947,253.82 MXN |
| `silver.ecommerce_orders` | 9,947 | 13,292 | monedas originales |
| `silver.inventory_snapshots` | 230,776 | | |
| `silver.exchange_rates` | 1,095 | | |

La segunda corrida reemplaza las tablas dentro de la transacción y no dejó duplicados: POS 0,
Shopify 0 y snapshots `(fecha, tienda_id, sku_erp)` 0. `audit.run_log` reportó `input_count`
328,118, `accepted_count` 328,118 y `rejected_count` 0.

## Calidad, privacidad y contratos

- `N/A` se cargó como `stock_quantity = null` y `stock_raw_value = 'N/A'`; no se convirtió a cero.
- Los cinco mappings con `sku_erp` nulo se conservaron como `NULL`; Silver expone columnas técnicas,
  no calcula `match_method`.
- EUR=22.0 quedó marcado como `fx_quality_flag = 'suspected_truncation'` en 63 registros.
- La consulta de columnas PII (`customer_name`, `customer_email`, `customer_rfc`,
  `shipping_address`, `shipping_city`) en `information_schema.columns` devolvió 0 filas para Silver.
- Las categorías CFDI se cargan sin cambiar signo ni inclusión; `silver.pos_sales` conserva 86,490 filas.

## Inmutabilidad

Hashes SHA-256 observados antes y después de las corridas:

| Archivo | SHA-256 |
|---|---|
| `datos/ecommerce_orders.parquet` | `00c560b39425fe7f0088fbe20c66c2b8861d10c2c7006ba6e7335cdd6dfc856e` |
| `datos/exchange_rates.csv` | `a0e827ec1e048cf397584eca3d692cb5b5b1f6b477fb78efca2fdbd2f488bddf` |
| `datos/inventory.json` | `2355c6cab9ff00a707b5505a464a8f7e1a9bf5a2aa6c7a2b6b008f5299c8eada` |
| `datos/sales.csv` | `87628a584d30a353f3bcc9dbe20c2d8f1e55c80a0036ecee88e76fce61031276` |

Cada manifest registró el mismo hash en `sha256_before` y `sha256_after`.

## Automatización

`./scripts/validate.sh` terminó con:

```text
7 passed in 12.53s
All checks passed!
```

Además pasaron `shellcheck scripts/*.sh docker/postgres/init/*.sh` sin salida y
`uv run ruff check src tests scripts/profile_sources.py` con `All checks passed!`.

`./scripts/status.sh` mostró PostgreSQL `healthy`, el segundo `run_id` y conteos de Silver. No se
implementaron dbt, Gold, PardoX ni Superset.
