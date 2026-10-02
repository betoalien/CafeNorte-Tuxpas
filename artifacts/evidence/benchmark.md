# Benchmark PardoX vs Polars

| Engine | Stage | Median s | Min s | Difference vs Polars | Peak MB |
|---|---:|---:|---:|---:|---:|
| polars | read | 0.003709 | 0.003293 | +0.0% | 229536.0 |
| pardox | read | 0.007257 | 0.006854 | +95.6% | 412976.0 |
| polars | validate | 0.076693 | 0.061854 | +0.0% | 229536.0 |
| pardox | validate | 0.003010 | 0.002858 | -96.1% | 412976.0 |
| polars | transform | 0.680376 | 0.614562 | +0.0% | 229536.0 |
| pardox | transform | 0.716756 | 0.693878 | +5.3% | 412976.0 |
| polars | load | 1.050422 | 0.917029 | +0.0% | 229536.0 |
| pardox | load | 0.952201 | 0.838870 | -9.4% | 412976.0 |
| pardox | to_prdx | 0.006762 | 0.005496 | +0.0% | 412976.0 |
| polars | total | 1.957812 | 1.791404 | +0.0% | 229536.0 |
| pardox | total | 2.125367 | 1.994081 | +8.6% | 412976.0 |

Guardas: filas esperadas sales=86,490, ecommerce=9,947, exchange_rates=730; no se publican etapas sub-ms con filas.
El dataset de 86k filas es pequeño y no generaliza. Escala opcional: sales x10/x100 en un directorio temporal usando CAFENORTE_DATA_DIR, sin tocar datos/.
Salida serializada: PardoX escribe .prdx y Polars escribe CSV equivalente; el tamaño exacto queda en cada línea JSONL de logs/.
Tamaño medido: CSV Polars=5078843 bytes; PRDX PardoX=2401320 bytes.
