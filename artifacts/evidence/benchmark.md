# Benchmark PardoX vs Polars

| Engine | Stage | Median s | Min s | Difference vs Polars | Peak MB | Call |
|---|---:|---:|---:|---:|---:|---|
| polars | read | 0.003208 | 0.002971 | +0.0% | 152.7 | pl.read_csv / DataFrame.write_database(engine=adbc) |
| pardox | read | 0.144473 | 0.139383 | +4403.0% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| python | read | 0.081486 | 0.080044 | +2439.8% | 171.7 | csv.DictReader / psycopg.executemany |
| polars | validate | 0.001679 | 0.001563 | +0.0% | 152.7 | pl.read_csv / DataFrame.write_database(engine=adbc) |
| pardox | validate | 0.003127 | 0.002958 | +86.2% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| python | validate | 0.017981 | 0.016599 | +970.7% | 171.7 | csv.DictReader / psycopg.executemany |
| polars | transform | 0.001387 | 0.001274 | +0.0% | 152.7 | pl.read_csv / DataFrame.write_database(engine=adbc) |
| pardox | transform | 0.002774 | 0.002468 | +100.0% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| python | transform | 0.011699 | 0.011348 | +743.8% | 171.7 | csv.DictReader / psycopg.executemany |
| polars | aggregate | 0.001387 | 0.001274 | +0.0% | 152.7 | pl.read_csv / DataFrame.write_database(engine=adbc) |
| pardox | aggregate | 0.002774 | 0.002468 | +100.1% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| python | aggregate | 0.011699 | 0.011348 | +743.7% | 171.7 | csv.DictReader / psycopg.executemany |
| polars | load | 0.337634 | 0.258964 | +0.0% | 152.7 | pl.read_csv / DataFrame.write_database(engine=adbc) |
| pardox | load | 0.173667 | 0.164340 | -48.6% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| python | load | 0.804993 | 0.770091 | +138.4% | 171.7 | csv.DictReader / psycopg.executemany |
| polars | write | 0.020818 | 0.017430 | +0.0% | 152.7 | pl.read_csv / DataFrame.write_database(engine=adbc) |
| pardox | write | 0.007895 | 0.007278 | -62.1% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| python | write | 0.091610 | 0.085794 | +340.0% | 171.7 | csv.DictReader / psycopg.executemany |
| pardox | load_prdx | 0.181397 | 0.154731 | +0.0% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| polars | total | 0.396403 | 0.304014 | +0.0% | 152.7 | pl.read_csv / DataFrame.write_database(engine=adbc) |
| pardox | total | 0.563345 | 0.496528 | +42.1% | 140.3 | px.read_csv / df.to_sql / px.write_sql_prdx |
| python | total | 1.052489 | 1.014870 | +165.5% | 171.7 | csv.DictReader / psycopg.executemany |

Guardas: filas esperadas sales=86,490, ecommerce=9,947, exchange_rates=730; no se publican etapas sub-ms con filas.
El dataset de 86k filas es pequeño y no generaliza. Escala opcional: sales x10/x100 en un directorio temporal usando CAFENORTE_DATA_DIR, sin tocar datos/.
Salida serializada: PardoX escribe .prdx y Polars escribe parquet; el tamaño exacto queda en cada línea JSONL de logs/.
Tamaño medido: parquet Polars=897940 bytes; PRDX PardoX=2401320 bytes.
