# Bloque D2-5

## Diagnóstico

- macOS arm64; PardoX `0.3.4`.
- x10: `864,900` filas, `720` grupos esperados.
- Polars y PardoX `to_sql`: `720` grupos.
- PardoX `write_sql_prdx`: `721` grupos; conteo `864,900`, unidades `1,333,830` y monto
  `309,472,538.20` globales coincidentes.
- x2 pasa; x5 y x10 fallan de forma determinista en cinco repeticiones.
- `load_prdx` presenta la discrepancia antes de escribir a PostgreSQL; el fallo queda aislado a
  la serialización/lectura PRDX.

La reproducción y la comparación por posición están en
`artifacts/evidence/pardox-0.3.4-prdx-repro/`. El patrón afecta columnas UTF-8 y cruza bloques;
las columnas numéricas conservan los totales.

## Verificación

```text
ruff check .: PASS
pytest: 15 passed
dbt build: 60/60 PASS
shellcheck scripts/*.sh docker/postgres/init/*.sh: PASS
git status --short: vacío
```

No se modificó PardoX, su instalación, la ingesta, dbt ni Superset. El cambio de código restante
fue solo formato para eliminar E501 en los dos archivos Superset solicitados.
