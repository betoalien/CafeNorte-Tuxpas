# Bloque D1-3: validacion

Fecha: 2026-10-01 (macOS, Darwin, bash 3.2)

## Carga temporal

`pytest tests/test_ingestion.py::test_real_incremental_and_full_modes_with_temp_sources -q`

```text
1 passed in 26.98s
```

La prueba usa una copia temporal de `datos/` y contra PostgreSQL real. Verifica: segunda corrida
`skipped` con `run_id` estable; tres ventas nuevas en `incremental` con las filas existentes sin
cambio de `run_id`; monto modificado y fila borrada en `full` solo para `pos_sales`, sin duplicados;
la prueba termina con una corrida `--force` sobre `datos/`.

## Validacion completa

```text
./scripts/validate.sh
anchor_date=2026-03-31
10 passed in 28.29s
dbt: PASS=60 WARN=0 ERROR=0 SKIP=0 TOTAL=60
All checks passed!
manager P3 rows=1 channels=T001
manager P4 rows=1 tienda_id=T001
director P3 rows=41 channels=['ONLINE', 'T001', ... 'T040']
negative control: director without T001 rule sees 41 channels
dashboard charts=5
Superset API data queries and RLS: PASS
```

## Calidad y estado

```text
uv run ruff check src tests scripts/profile_sources.py: All checks passed!
shellcheck scripts/*.sh docker/postgres/init/*.sh: 0 warnings
```

Los artefactos de dbt se regeneraron con el `anchor_date` calculado; no se modificaron Superset,
PardoX ni los archivos originales de `datos/`.
