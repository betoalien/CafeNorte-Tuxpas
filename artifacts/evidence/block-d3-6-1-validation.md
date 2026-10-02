# Evidencia D3-6-1

Fecha: 2026-10-02. Plataforma: macOS arm64.

## Corrida completa

Secuencia ejecutada:

```text
./scripts/stop.sh
./scripts/reset.sh --yes
./scripts/start.sh --no-browser
```

La primera reconstrucción de Gold falló por el quoting de `anchor_date` del refactor. Se corrigió
la CLI para pasar `{"anchor_date": "'2026-03-31'"}` como hacía Bash y se repitió el flujo. La
ejecución completa posterior terminó con:

```text
anchor_date=2026-03-31
Done. PASS=61 WARN=0 ERROR=0 SKIP=0 TOTAL=61
Superset API data queries and RLS: PASS
```

La repetición final de `./scripts/start.sh --no-browser` produjo `anchor_date=2026-03-31`,
`PASS=61` y el bloque `Superset listo`. La validación final mediante `uv run cafenorte validate`
produjo `PardoX: soportado (probado)`, `PASS=61`, `Superset API data queries and RLS: PASS` y
`All checks passed!`.

## Validación y skipped

```text
./scripts/status.sh
./scripts/validate.sh
./scripts/start.sh --no-browser
uv run cafenorte status
uv run cafenorte start --no-browser
```

Resumen de ambas rutas:

```text
script start: load_mode=skipped; No source changed; dbt build and answer export skipped.
cli start:    load_mode=skipped; No source changed; dbt build and answer export skipped.
script status: Silver consulta 7 tablas; Gold consulta 5 marts; reporte presente.
cli status:    Silver consulta 7 tablas; Gold consulta 5 marts; reporte presente.
```

La salida de validación incluyó el esquema `audit`, `silver`, `intermediate`, `analytics`, los
roles `pipeline`, `dbt`, `superset_ro`, `superset_meta`, la base `superset_meta`, PardoX soportado
en `Darwin-arm64`, dbt `PASS=61` y RLS `PASS`.

## Pruebas

```text
uv run pytest
23 passed in 32.33s
uv run pytest tests/test_cli_parity.py tests/test_cli.py tests/test_tech_stack_doc.py -q
6 passed
```

La prueba `tests/test_cli_parity.py` compara los ocho subcomandos contra el plan derivado de
`8add93f` y reporta el nombre de cada paso faltante. No se incluyen credenciales en esta evidencia.
