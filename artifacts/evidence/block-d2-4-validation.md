# Bloque D2-4: validación

## Alcance

Solo se corrigió el benchmark. No se tocaron paridad, ingesta principal, dbt ni Superset.

## Escala base: 86,490 filas

Medianas en segundos, seis corridas alternadas por variante:

| Motor | Read | Validate | Transform | Aggregate | Load | Write | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Polars | 0.022704 | 0.026756 | 0.006567 | 0.007685 | 0.318785 | 0.027135 | 0.441900 |
| PardoX to_sql | 0.010999 | 0.003414 | 0.003418 | 0.003038 | 0.113047 | 0.008054 | 0.173562 |
| PardoX write_sql_prdx | 0.006965 | 0.002998 | 0.002466 | 0.002346 | 0.153647 | 0.006718 | 0.245329 |
| Python psycopg | 0.085447 | 0.017431 | 0.034124 | 0.011892 | 0.761095 | 0.123807 | 1.067445 |

Los imports quedan fuera del total y se reportan como etapa informativa. Tamaños sin favorecer ningún
formato: Parquet 0.90 MB y PRDX 2.40 MB.

## Escala x10: 864,900 filas

La fuente temporal realmente alcanzó 864,900 filas y los totales globales de PRDX fueron:

```text
count=864900, sum(cantidad)=1333830, sum(monto)=309472538.20
```

La guarda de agregados falló deliberadamente: Polars/Python produjeron 720 grupos tienda x mes;
`write_sql_prdx` produjo 721 grupos, aunque sus totales globales coincidieron. Por ello no se publica
una tabla de tiempos x10 como resultado certificado. El benchmark devuelve error en este caso, como
exige el contrato, en vez de publicar una comparación sin paridad.

## Validaciones

```text
pytest completo: 15 passed in 34.73s
dbt build: PASS=60 WARN=0 ERROR=0 SKIP=0
shellcheck scripts/*.sh docker/postgres/init/*.sh: PASS
ruff benchmark.py: PASS
ruff completo: FAIL por avisos E501 preexistentes en superset/bootstrap.py y superset/test_rls.py;
no se modificó Superset por alcance.
benchmark x10: FAIL deliberado por discrepancia de agregados write_sql_prdx.
```
