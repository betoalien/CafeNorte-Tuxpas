# Bloque D2-3: validación

Alcance: únicamente `sales.csv` en `silver_pardox`; no se modifican la ingesta Silver principal,
dbt ni Superset.

## Carga nativa

```text
engine=pardox native_to_sql_rows=86490 accepted_sales=86490
```

PardoX escribió directamente a `silver_pardox.pos_sales_stage` mediante `df.to_sql(..., mode="append")`;
el paso SQL `INSERT ... SELECT` materializó `silver_pardox.pos_sales`. Además, el benchmark validó
`df.to_prdx(...)` seguido de `px.write_sql_prdx(...)`, también con 86,490 filas.

## Paridad SQL y controles negativos

```text
uv run pytest -q tests/test_engines.py
5 passed
```

La suite cubre paridad por `EXCEPT` en ambos sentidos, conteos/sumas/agregados, alteración de monto
con exactamente una diferencia, borrado con exactamente una diferencia, restauración y retorno
`to_sql=86490`.

## Benchmark real

Corrida fría más cinco calientes, subprocess por motor, alternadas. Medianas en segundos:

| Etapa | PardoX | Polars | Python psycopg |
|---|---:|---:|---:|
| read | 0.160276 | 0.004397 | 0.088120 |
| validate | 0.003330 | 0.002139 | 0.018700 |
| transform | 0.002864 | 0.001754 | 0.012615 |
| aggregate | 0.002865 | 0.001754 | 0.012616 |
| load (`to_sql`/ADBC) | 0.173667 | 0.337634 | 0.804993 |
| write (`to_prdx`/Parquet) | 0.007895 | 0.020818 | 0.091610 |
| load PRDX (`write_sql_prdx`) | 0.181397 | n/a | n/a |
| total | 0.563345 | 0.396403 | 1.052489 |

PardoX ganó en `to_sql` y escritura PRDX; Polars ganó claramente en lectura y transformación. Para
86,490 filas, `to_sql` fue ligeramente más rápido que `write_sql_prdx` porque la segunda ruta incluye
la escritura PRDX antes del streaming. El total completo de PardoX fue 0.563345 s frente a 0.396403 s
de Polars; este volumen es pequeño y no generaliza. La salida fue 2,401,320 bytes en `.prdx` frente
a 897,940 bytes en Parquet. La memoria pico medida fue aproximadamente 140.3 MB PardoX, 152.7 MB
Polars y 171.7 MB Python.

Las llamadas exactas y el JSONL completo están en `artifacts/evidence/benchmark.md` y `logs/`.

## Resultado de cierre

```text
ruff: passed
pytest tests/test_engines.py: 5 passed
```
