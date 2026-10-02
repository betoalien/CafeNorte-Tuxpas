# Benchmark PardoX vs Polars

| Engine | Stage | Median s | Min s | Difference vs Polars | Peak MB |
|---|---:|---:|---:|---:|---:|
| polars | read | 0.123739 | 0.108079 | +0.0% | 354752.0 |
| pardox | read | 0.010651 | 0.009973 | -91.4% | 325808.0 |
| polars | validate | 0.082210 | 0.070351 | +0.0% | 354752.0 |
| pardox | validate | 0.003022 | 0.002943 | -96.3% | 325808.0 |
| polars | transform | 0.067648 | 0.066453 | +0.0% | 354752.0 |
| pardox | transform | 0.155624 | 0.140176 | +130.1% | 325808.0 |
| polars | load | 0.063663 | 0.060319 | +0.0% | 354752.0 |
| pardox | load | 0.120671 | 0.115445 | +89.5% | 325808.0 |
| pardox | to_prdx | 0.006546 | 0.005714 | +0.0% | 325808.0 |
| polars | total | 0.337786 | 0.312948 | +0.0% | 354752.0 |
| pardox | total | 0.306142 | 0.279080 | -9.4% | 325808.0 |

Guardas: filas esperadas sales=86,490, ecommerce=9,947, exchange_rates=730; no se publican etapas sub-ms con filas.
El dataset de 86k filas es pequeño y no generaliza. Escala opcional: sales x10/x100 en un directorio temporal usando CAFENORTE_DATA_DIR, sin tocar datos/.
Salida serializada: PardoX escribe .prdx y Polars escribe CSV equivalente; el tamaño exacto queda en cada línea JSONL de logs/.
Tamaño medido: CSV Polars=5078843 bytes; PRDX PardoX=2401320 bytes.
