# Bloque D2-1: validación PardoX real

## APIs y paridad

PardoX `0.3.4` se inspeccionó desde el paquete instalado. Se usaron `read_csv`, `read_parquet`,
`cast`, `validate_contract`, `to_dict` y `to_prdx`. El único fallback fue `inventory.json`, porque
el SDK no ofrece lector JSON anidado.

```text
uv run pytest tests/test_engines.py -q
3 passed (incluye el control negativo de paridad)
```

La prueba compara claves, conteos, sumas y agregados POS contra `silver_pardox`; altera un monto,
confirma que la comparación detecta la diferencia y restaura la fila. La carga PardoX permanece
aislada en `silver_pardox`.

## Benchmark

```text
uv run python -m cafenorte.benchmark
```

Se ejecutaron una corrida fría y cinco calientes por motor, alternando el orden en subprocess.
Cada etapa con filas pasa la guarda de 1 ms; las filas esperadas son sales=86,490,
ecommerce=9,947 y exchange_rates=730. Se midieron lectura, validación, transformación, carga,
total, memoria pico y escritura `.prdx` frente a CSV equivalente.

El resumen está en `artifacts/evidence/benchmark.md`; los JSONL detallados están en `logs/`.
El dataset de 86k filas es pequeño y no generaliza los resultados. La escala x10/x100 queda como
prueba opcional mediante `CAFENORTE_DATA_DIR`.

## Validación oficial

```text
./scripts/validate.sh
pytest: 13 passed
dbt: PASS=60 WARN=0 ERROR=0 SKIP=0 TOTAL=60
shellcheck: 0 warnings
Superset API data queries and RLS: PASS
```
