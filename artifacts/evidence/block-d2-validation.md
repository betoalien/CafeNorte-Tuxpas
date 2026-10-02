# Bloque D2: PardoX

## Instalacion macOS arm64

```text
uv sync
Darwin arm64 0.3.4
```

PardoX `0.3.4` quedo fijado en `pyproject.toml` y `uv.lock`. La biblioteca nativa se cargo en
macOS Apple Silicon; su mensaje de GPU indica fallback interno a CPU, que no se oculta.

## Paridad y aislamiento

```text
uv run pytest tests/test_engines.py -q
2 passed in 1.07s
```

La corrida `uv run python -m cafenorte.ingest --engine pardox --force` genero las mismas filas,
suma y agregados comprobados en `silver_pardox`; `silver` no se reemplaza. La salida registro:

```text
engine=pardox
engine_fallback=polars únicamente para inventory.json (JSON anidado)
```

PardoX 0.3.4 ejecutó `read_csv`, `read_parquet`, `cast`, `validate_contract`, `to_dict` y
`to_prdx`; el lector JSON anidado es el único fallback real.

La prueba negativa altera temporalmente un monto en `silver_pardox.pos_sales`, confirma que la
comparación falla y restaura el valor original.

## Benchmark

```text
uv run python -m cafenorte.benchmark
```

Se ejecutaron una corrida fria y cinco calientes por motor en subprocess, alternando el orden.
Cada etapa con filas pasa la guarda de 1 ms y las filas coinciden con sales=86,490,
ecommerce=9,947 y exchange_rates=730. El resumen
versionado esta en `artifacts/evidence/benchmark.md`; los JSONL detallados quedan en `logs/` y
estan ignorados por Git. El dataset es pequeno (86k filas), por lo que los tiempos no se
generalizan. El escalamiento x10/x100 queda documentado como prueba opcional futura mediante
`CAFENORTE_DATA_DIR`.

## Calidad

```text
ruff: All checks passed!
shellcheck scripts/*.sh docker/postgres/init/*.sh: 0 warnings
```
