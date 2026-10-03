# Validación final D3

## Clon limpio

Referencia validada: commit D3-21 (separación de dashboards de red y tienda).

Se ejecutó `docker compose down -v` en el proyecto previo y después un clon temporal sin `.env`,
volúmenes ni entorno virtual previo. `uv sync` instaló desde `uv.lock` incluyendo PardoX 0.3.4.

```text
uv sync                  PASS 14 s
./scripts/start.sh       PASS 53 s
./scripts/validate.sh    PASS 47 s
./scripts/start.sh       PASS 4 s, load_mode=skipped
tiempo total medido     118 s
anchor_date              2026-03-31
dbt                      PASS=75 WARN=0 ERROR=0 SKIP=0
pytest                   35 passed
Superset RLS/API         PASS; dashboard Dirección charts=6; Mi tienda charts=4
Superset dashboard layout PASS (ROOT/GRID, 6/4 charts) para director y gerente_t001
```

La primera ejecución creó `.env` con permisos 600, cuatro fuentes fueron cargadas, y la segunda
ejecución no ejecutó dbt ni exportó respuestas.

## Seguridad

`gitleaks detect --source . --log-opts="--all"` encontró 0 hallazgos en todo el historial. `.env`,
el PDF/DOCX del reto, ZIP, `logs/*.jsonl` y `.prdx` no están versionados. El único PDF versionado
es `artifacts/evidence/PROPUESTA_AWS.pdf`, a propósito. Los CSV versionados
de `artifacts/evidence/answers/` no contienen columnas ni valores de PII de Shopify.

## Estado

`ruff check .`, `shellcheck scripts/*.sh docker/postgres/init/*.sh` y `git status --short` quedan
incluidos en el cierre del commit.
