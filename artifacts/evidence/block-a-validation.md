# Evidencia de validación — Bloque A

Fecha: 2026-10-01. Entorno: Docker Desktop sobre Windows; se usó `POSTGRES_PORT=15432` porque 5432 estaba ocupado y 55432 pertenecía a un rango reservado del host. No se creó ni versionó `.env`; la prueba utilizó `.env.example` mediante `ENV_FILE`.

## Comandos ejecutados

```text
uv sync
.venv/Scripts/ruff.exe check scripts/profile_sources.py
.venv/Scripts/python.exe scripts/profile_sources.py
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/start.sh
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/status.sh
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/validate.sh
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/start.sh
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/reset.sh
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/reset.sh --yes
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/restart.sh
ENV_FILE=.env.example POSTGRES_PORT=15432 scripts/stop.sh
bash -n scripts/*.sh docker/postgres/init/001_initialize.sh
```

## Resultados observados

- PostgreSQL `16.4-alpine3.20` alcanzó estado `healthy`.
- `start.sh` ejecutado por segunda vez mantuvo el mismo contenedor saludable.
- `validate.sh` encontró schemas `analytics`, `audit`, `intermediate`, `silver`; roles `dbt`, `pipeline`, `superset_meta`, `superset_ro`; y base `superset_meta`.
- Ruff y la comprobación sintáctica Bash terminaron sin errores.
- `reset.sh` sin `--yes` terminó con código 2 y no eliminó recursos.
- `reset.sh --yes` eliminó únicamente contenedor, red y volumen de Compose. La recreación desde cero pasó `start`, `restart` y `validate`.
- El estado final de `cafenorte-postgres` es `Exited (0)`; el volumen se conserva para revisión.

## Integridad de fuentes antes y después de reset

| Archivo | SHA-256 | Preservado |
|---|---|---|
| `sales.csv` | `87628A584D30A353F3BCC9DBE20C2D8F1E55C80A0036ECEE88E76FCE61031276` | Sí |
| `inventory.json` | `2355C6CAB9FF00A707B5505A464A8F7E1A9BF5A2AA6C7A2B6B008F5299C8EADA` | Sí |
| `ecommerce_orders.parquet` | `00C560B39425FE7F0088FBE20C66C2B8861D10C2C7006BA6E7335CDD6DFC856E` | Sí |
| `exchange_rates.csv` | `A0E827EC1E048CF397584ECA3D692CB5B5B1F6B477FB78EFCA2FDBD2F488BDDF` | Sí |
