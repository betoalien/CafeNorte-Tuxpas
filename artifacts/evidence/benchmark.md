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

La copia temporal tuvo 864,900 filas y venta_id único. La guarda obligatoria falló en
`write_sql_prdx`: Polars/Python produjeron 720 grupos tienda x mes y PRDX produjo 721. Los totales
globales PRDX sí coincidieron: `864900`, `1333830`, `309472538.20`. El benchmark termina con error y
no publica tiempos x10 como resultados certificados.

## Interpretación

En 86k PardoX gana en lectura, cómputo y carga nativa; Polars tiene menor total frente a PRDX por el
costo de materializar y recargar. Parquet pesa menos que PRDX; el argumento de PRDX es velocidad de
escritura y recarga, no compresión. La diferencia x10 no se interpreta mientras `write_sql_prdx` no
conserve la granularidad tienda x mes. El JSONL completo está en `logs/`.
