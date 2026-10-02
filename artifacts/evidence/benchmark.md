# Benchmark PardoX vs Polars

| Engine | Stage | Median s | Min s | Difference vs Polars |
|---|---:|---:|---:|---:|
| polars | reading | 0.000002 | 0.000000 | +0.0% |
| polars | total | 0.000002 | 0.000000 | +0.0% |
| pardox | reading | 0.006858 | 0.006795 | +450789.9% |
| pardox | total | 0.006858 | 0.006795 | +361633.4% |

PardoX fue más lento en esta corrida pequeña; no se generaliza a cargas mayores.
Escalamiento opcional: generar sales x10 y x100 en un directorio temporal con CAFENORTE_DATA_DIR, sin modificar datos/.
