# Evidencia Bloque C: dbt → Gold y cuatro respuestas

Validación macOS Apple Silicon. No se implementaron PardoX ni Superset.

## Secuencia

Se ejecutó `./scripts/reset.sh --yes`, después `./scripts/start.sh`, que realizó Bronze → Silver,
`dbt build` y la exportación de respuestas. Se ejecutó `./scripts/validate.sh` y posteriormente
una segunda corrida de `uv run python -m cafenorte.ingest`; se volvió a construir dbt y exportar.

La última corrida exitosa de ingestión fue filtrada por staging desde `audit.run_log`.

## dbt

Artefactos generados por SPEC-002:

- `artifacts/evidence/dbt/manifest.json`
- `artifacts/evidence/dbt/run_results.json`

Resultado final:

```text
Found 22 models, 36 data tests, 10 sources
Done. PASS=58 WARN=0 ERROR=0 SKIP=0 TOTAL=58
```

El build incluye fuentes Silver/Audit, staging, intermediate, dimensiones, hechos y marts en
`analytics`.

## Identidad y semántica

La prueba singular de identidad coincidió con profiling:

| Fuente | explicit | product_number | product_number_null_erp |
|---|---:|---:|---:|
| POS | 74,141 | 6,217 | 6,132 |
| Shopify | 6,959 | 1,849 | 1,139 |

FX usa la tasa de la fecha; EUR=22.0 conserva `suspected_truncation`. El costo efectivo usa la
última vigencia no posterior a la venta. Silver conserva la hora local POS y dbt mantiene la zona
IANA de `dim_store` disponible para conversión semántica.

## Respuestas exportadas

Cada resultado tiene CSV y consulta SQL en `artifacts/evidence/answers/`:

| Mart | Filas exportadas |
|---|---:|
| `mart_inventory_turnover_top10` | 10 |
| `mart_stockouts_over_3_days` | 3 |
| `mart_monthly_channel_growth` | 492 |
| `mart_negative_margin_products` | 120 |

P1 usa únicamente POS para `units_sold`, excluye productos sin match del ranking y muestra
`coverage`. P2 usa 2026-01-01—2026-03-31, rompe rachas con N/A/días faltantes y marca
`starts_before_window`. P3 incluye cada tienda y `ONLINE`, con abril 2025 sin base. P4 separa
tiendas POS y `ONLINE` y solo conserva margen total negativo.

## Reconciliación

`analytics.mart_source_reconciliation` contiene 40,940 filas por fuente, periodo, producto y
`match_method`, con `certified_rows`, `excluded_rows`, `unmatched_rows`, `no_fx_rows` y
`no_cost_rows`. El test `test_source_reconciliation_balances` verifica:

```text
input_rows = certified_rows + excluded_rows
```

sin diferencias.

## Consultas de revisión

```sql
select source_name, match_method, count(*)
from intermediate.int_product_identity
group by 1, 2;

select count(*) from analytics.mart_inventory_turnover_top10;
select count(*) from analytics.mart_stockouts_over_3_days;
select count(*) from analytics.mart_monthly_channel_growth;
select count(*) from analytics.mart_negative_margin_products;
```

`status.sh` mostró PostgreSQL healthy, el último `run_id`, conteos Silver y conteos Gold. El árbol
Git quedó limpio después del commit.
