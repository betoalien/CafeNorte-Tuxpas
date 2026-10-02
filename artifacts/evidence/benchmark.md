# Benchmark PardoX vs Polars, D2-4

Imports y conexión quedan fuera de `total`; `import` es informativo. Cada motor mide read, validate,
transform, aggregate, load, write y total.

## 86,490 filas

Medianas en segundos, seis corridas alternadas:

| Engine | Read | Validate | Transform | Aggregate | Load | Write | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Polars | 0.022704 | 0.026756 | 0.006567 | 0.007685 | 0.318785 | 0.027135 | 0.441900 |
| PardoX `to_sql` | 0.010999 | 0.003414 | 0.003418 | 0.003038 | 0.113047 | 0.008054 | 0.173562 |
| PardoX `write_sql_prdx` | 0.006965 | 0.002998 | 0.002466 | 0.002346 | 0.153647 | 0.006718 | 0.245329 |
| Python psycopg | 0.085447 | 0.017431 | 0.034124 | 0.011892 | 0.761095 | 0.123807 | 1.067445 |

Llamadas: Polars `read_csv`, cast/filtros, `str.extract`/`str.slice`, `group_by`, ADBC y
`write_parquet`; PardoX `px.read_csv`, `cast`, `validate_contract`, `str_replace`, `groupby`,
`to_sql` o `to_prdx` + `write_sql_prdx`. Python usa `csv.DictReader` y `executemany`.

## 864,900 filas

Medianas en segundos, seis corridas alternadas. Polars, PardoX `to_sql` y Python conservaron la
paridad:

| Engine | Read | Validate | Transform | Aggregate | Load | Write | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Polars | 0.040232 | 0.002313 | 0.013208 | 0.007033 | 2.032776 | 0.128205 | 2.664857 |
| PardoX `to_sql` | 0.058213 | 0.037149 | 0.030424 | 0.026622 | 1.385163 | 0.092868 | 1.964213 |
| Python psycopg | 0.955383 | 0.442274 | 0.355841 | 0.134486 | 10.385064 | 1.178339 | 13.858283 |

`PardoX write_sql_prdx` queda excluido a x10: produjo 721 grupos tienda x mes frente a 720.
La reproducción está en `pardox-0.3.4-prdx-repro/`. En 0.3.4 la transformación PardoX no
extrae mes ni aplica regex equivalente, por lo que hace menos trabajo que Polars y sus milisegundos
no representan un procesamiento equivalente.

## Interpretación

En 86k PardoX gana en lectura, cómputo y carga nativa; Polars tiene menor total frente a PRDX por el
costo de materializar y recargar. Parquet pesa menos que PRDX; el argumento de PRDX es velocidad de
escritura y recarga, no compresión. La diferencia x10 no se interpreta mientras `write_sql_prdx` no
conserve la granularidad tienda x mes. El JSONL completo está en `logs/`.
