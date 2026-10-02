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
dbt                      PASS=60 WARN=0 ERROR=0 SKIP=0
pytest                   15 passed
Superset RLS/API         PASS; dashboard charts=5
```

La primera ejecución creó `.env` con permisos 600, cuatro fuentes fueron cargadas, y la segunda
ejecución no ejecutó dbt ni exportó respuestas.

## Seguridad

`gitleaks` no estaba instalado; se ejecutó `git log -p --all` con patrones de password, secret,
token, key y API key. Solo aparecieron referencias a variables de entorno y documentación, sin
valores secretos. `.env`, PDF/DOCX, ZIP y `logs/*.jsonl` no están versionados. Los CSV versionados
de `artifacts/evidence/answers/` no contienen columnas ni valores de PII de Shopify.

## Estado

`ruff check .`, `shellcheck scripts/*.sh docker/postgres/init/*.sh` y `git status --short` quedan
incluidos en el cierre del commit.
