# Bloque D3-5

## Regresión macOS/Bash 3.2

Ejecutado con `/bin/bash` en macOS arm64:

```text
start.sh --no-browser: PASS, skipped, reporte generado
start.sh sin --no-browser: PASS, skipped, reporte generado y apertura intentada
restart.sh --no-browser: PASS, skipped
status.sh: PASS; PostgreSQL, Última corrida, Silver (7), Último dbt, Gold (5), Reporte
validate.sh: PASS; dbt 61/61, pytest PASS, RLS PASS
ShellCheck scripts/*.sh docker/postgres/init/*.sh: PASS
ruff check .: PASS
PardoX: soportado (probado)
```

La expansión vacía de `report_args` usa la forma compatible con `set -u` de Bash 3.2. El reporte
se generó en `artifacts/reports/run_report.html`; el archivo está ignorado por Git.

En la ruta full, `validate.sh` ejecutó la ingesta PardoX, pytest, dbt y RLS. En la ruta skipped,
`start.sh` imprimió `No source changed; dbt build and answer export skipped.`
