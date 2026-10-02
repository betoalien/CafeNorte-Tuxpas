# Evidencia Bloque D1-2: modos de carga

No se modificaron Superset, PardoX ni la ingesta de datos original. `datos/` permaneció intacto.

## Segunda corrida `start.sh`

```text
{"run_id": "3b1ceaa7-d22e-474d-9bdd-3bb7f50ce9cc", "load_mode": "skipped"}
No source changed; dbt build and answer export skipped.
```

Silver conservó 86,490 filas POS, 230,776 snapshots y 9,947 órdenes; Gold conservó sus conteos.

## Carga forzada y validación

```text
uv run python -m cafenorte.ingest --force
load_mode: full
anchor_date: 2026-03-31
pytest: 9 passed
dbt: PASS=60 WARN=0 ERROR=0 SKIP=0
shellcheck: PASS
ruff: PASS
Superset API RLS: PASS
```

La columna `row_hash` existe en las siete tablas Silver y `load_mode` en manifest/run_log. Las
ventanas dbt consumen `var('anchor_date')`; con las fuentes actuales el ancla común es
`2026-03-31` y los conteos de answers permanecen 10, 3, 492 y 120. Los CSV se exportan sin
`built_at`, evitando cambios por timestamps durante `validate.sh`.

Los modos se seleccionan así: SHA iguales => `skipped`; solo claves nuevas sin cambios existentes
=> `incremental`; modificación de una clave o desaparición => `full`. `--force` fuerza `full`.
