# Evidencia Bloque B-1: correcciones de Bronze → Silver

Validación macOS Apple Silicon, Bash 3.2.57. No se implementó dbt ni se avanzó de Silver.

## Secuencia operativa

1. `./scripts/reset.sh --yes` creó un volumen PostgreSQL limpio y preservó `datos/`, código,
   documentación y evidencia.
2. `./scripts/start.sh` esperó PostgreSQL healthy y ejecutó la primera corrida completa.
3. `./scripts/validate.sh` ejecutó controles PostgreSQL, pytest y Ruff.
4. Se ejecutó una segunda corrida explícita con `uv run python -m cafenorte.ingest`.

Primer `run_id`: `b0a111a5-5aae-4aef-bbe2-9c49c9d19c2d`.

Segundo `run_id`: `0d36dde0-2ceb-4244-976f-1793115ba0d3`.

## Manifiesto y hashes

La última corrida registró `sha256_before` al inicio, antes de leer las fuentes, y `sha256_after`
después de `load()`. Los cuatro manifests reportaron `hash_equal = true`:

| Fuente | Input | Accepted | Rejected | Hashes iguales |
|---|---:|---:|---:|---|
| `datos/sales.csv` | 86,490 | 86,490 | 0 | Sí |
| `datos/inventory.json` | 230,951 | 230,951 | 0 | Sí |
| `datos/ecommerce_orders.parquet` | 9,947 | 9,947 | 0 | Sí |
| `datos/exchange_rates.csv` | 730 | 730 | 0 | Sí |

La prueba compara cada hash del último manifest con SHA-256 calculado directamente desde `datos/`.
Resultados:

```text
ecommerce_orders.parquet  00c560b39425fe7f0088fbe20c66c2b8861d10c2c7006ba6e7335cdd6dfc856e
exchange_rates.csv        a0e827ec1e048cf397584eca3d692cb5b5b1f6b477fb78efca2fdbd2f488bddf
inventory.json            2355c6cab9ff00a707b5505a464a8f7e1a9bf5a2aa6c7a2b6b008f5299c8eada
sales.csv                 87628a584d30a353f3bcc9dbe20c2d8f1e55c80a0036ecee88e76fce61031276
```

Si una fuente cambia después de la carga, el manifest conserva la diferencia y `audit.run_log`
queda con `status = 'failed'` y `error_message`; la corrida no se reporta como exitosa.

## Idempotencia y calidad

La prueba compara entre corrida 1 y 2 conteos, sumas de unidades, sumas monetarias y el conteo de
`audit.quarantine` para todas las tablas Silver. Los resultados de la última corrida fueron:

| Tabla | Filas | Unidades | Monto |
|---|---:|---:|---:|
| `silver.pos_sales` | 86,490 | 133,383 | 30,947,253.82 MXN |
| `silver.ecommerce_orders` | 9,947 | 13,292 | 2,984,113.06 en moneda original |
| `silver.inventory_snapshots` | 230,776 | | |
| `silver.exchange_rates` | 1,095 | | |

`audit.quarantine` fue 0 en ambas corridas. Duplicados: POS 0, Shopify 0 y snapshots por
`(fecha, tienda_id, sku_erp)` 0. La cuarentena histórica no se borra: se conserva por `run_id`.

## CFDI

| Tipo | Filas | Unidades | Monto |
|---|---:|---:|---:|
| I | 82,518 | 127,241 | 29,503,069.84 |
| E | 3,079 | 4,843 | 1,140,985.33 |
| P | 451 | 692 | 160,501.27 |
| N | 288 | 407 | 100,579.56 |
| T | 154 | 200 | 42,117.82 |
| **Total** | **86,490** | **133,383** | **30,947,253.82** |

Todos los tipos tienen cantidad y monto estrictamente positivos. Silver no altera signo ni inclusión.

## Otros controles

- La transformación unitaria de `N/A` produce `stock_quantity = None`, `stock_raw_value = 'N/A'`
  y `quality_status = 'unknown'`.
- `sales.moneda` solo acepta `MXN`; `ecommerce_orders.currency` solo acepta `MXN`, `USD` o `EUR`.
  Valores fuera del contrato van a cuarentena.
- PII ausente del schema Silver: 0 columnas encontradas.
- EUR=22.0 conserva `fx_quality_flag = 'suspected_truncation'` en 63 filas.
- No se usa `DISABLE TRIGGER ALL` ni `ENABLE TRIGGER ALL`.

## Validación automatizada

```text
9 passed in 11.95s
All checks passed!
```

`shellcheck scripts/*.sh docker/postgres/init/*.sh` terminó sin salida y Ruff terminó con
`All checks passed!`. `status.sh` mostró PostgreSQL `healthy`, el último `run_id`, 328,118 inputs,
328,118 accepted, 0 rejected y los conteos Silver anteriores.
