# Bloque D2-2: PardoX punta a punta en sales

## Paridad

```text
uv run pytest tests/test_engines.py -q
3 passed in 1.51s
```

`build_pos_sales_pardox()` produce las tuplas que se cargan exclusivamente en
`silver_pardox.pos_sales`; las demás fuentes no se presentan como PardoX. `check_parity()` compara
venta_id, row_hash, monto, conteos, sumas y agregados tienda-mes/tipo_comprobante. El control
negativo alteró una fila, obtuvo exactamente una diferencia, y luego restauró el valor.

## Tiempos reales

Corrida final: una fría y cinco calientes por motor, alternadas, en subprocess, con INSERT real a
tabla temporal PostgreSQL y guardas de 86,490 filas.

| Etapa | Polars mediana (s) | PardoX mediana (s) | Diferencia |
|---|---:|---:|---:|
| read | 0.003709 | 0.007257 | +95.6% |
| validate | 0.076693 | 0.003010 | -96.1% |
| transform | 0.680376 | 0.716756 | +5.3% |
| load | 1.050422 | 0.952201 | -9.4% |
| total | 1.957812 | 2.125367 | +8.6% |

PardoX fue más lento en el total de este dataset, aunque ganó en validación y carga. La conclusión
no se generaliza: 86,490 filas es una muestra pequeña. `.prdx` midió 2,401,320 bytes frente a la
salida serializada Polars de 5,078,843 bytes. El escalamiento x10/x100 queda como prueba opcional
con `CAFENORTE_DATA_DIR`.

## Validación

```text
validate.sh: pytest 13 passed
dbt: PASS=60 WARN=0 ERROR=0 SKIP=0 TOTAL=60
shellcheck: 0 warnings
RLS: PASS
```
