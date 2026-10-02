# Validación final D3

## Clon limpio

Se ejecutó `docker compose down -v` en el proyecto previo y después un clon temporal sin `.env`,
volúmenes ni entorno virtual previo. `uv sync` instaló desde `uv.lock` incluyendo PardoX 0.3.4.

```text
./scripts/start.sh       PASS 35 s
./scripts/validate.sh    PASS 41 s
./scripts/start.sh       PASS 3 s, load_mode=skipped
tiempo total medido     79 s
anchor_date              2026-03-31
dbt                      PASS=67 WARN=0 ERROR=0 SKIP=0
pytest                   28 passed
Superset RLS/API         PASS; dashboard charts=6
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
