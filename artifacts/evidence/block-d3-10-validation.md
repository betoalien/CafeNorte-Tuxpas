# Bloque D3-10: validacion final previa a publicacion

Fecha: 2026-10-02 (macOS arm64)

## Parte A

- `grep -rn "noqa" src scripts superset tests`: sin resultados.
- `uv run ruff check .`: PASS.
- `uv run pytest tests/test_cli.py tests/test_run_report.py`: PASS.
- La corrida completa confirma que `anchor_date=2026-03-31` y que el reporte se genera.

## Parte B

- Comando: `uv run --with markdown python scripts/build_proposal_pdf.py`.
- `artifacts/evidence/PROPUESTA_AWS.pdf`: 2 paginas.
- Revision visual de las dos paginas renderizadas: diagrama alineado y tablas completas, sin cortes.

## Parte C

Corrida macOS:

```text
./scripts/start.sh --no-browser
  run_id=8581d9f2-1295-4874-891a-505a44d15933
  load_mode=skipped
./scripts/validate.sh
  dbt PASS=65 WARN=0 ERROR=0 SKIP=0 TOTAL=65
  pytest: 27 passed
  RLS: PASS (manager P3/P4 T001; director 41 canales; dashboard 6 graficas)
  PardoX: PASS (Darwin arm64)
  ruff: PASS
  shellcheck: PASS
  hashes de datos/: PASS
./scripts/start.sh --no-browser
  load_mode=skipped
```

Los artefactos de dbt quedan en `artifacts/evidence/dbt/`; la validacion no reporto errores.

## Seguridad y versionado

- `git ls-files` confirma que no estan versionados `.env`, DOCX, ZIP, `logs/*.jsonl` ni `.prdx`; la unica excepcion PDF es el entregable versionado `artifacts/evidence/PROPUESTA_AWS.pdf`.
- `gitleaks detect --source . --log-opts="--all"`: PASS, 36 commits escaneados, 0 secretos.

## Clon limpio

En `/private/tmp/cafenorte-d310-2E2Y5a/repo` se ejecutaron `uv sync`, `start.sh --no-browser`, `validate.sh` y una segunda `start.sh --no-browser`. La primera corrida fue exitosa con `dbt PASS=65`, `pytest 27 passed` y RLS PASS; la segunda reporto `load_mode=skipped`. El primer intento revelo la colision esperable de los `container_name` fijos; se repitio tras `docker compose down -v`, sin volumenes previos.
