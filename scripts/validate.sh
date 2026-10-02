#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

env_file="${ENV_FILE:-.env}"
if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file. Run scripts/start.sh first." >&2
  exit 1
fi

for script in scripts/*.sh docker/postgres/init/*.sh; do
  bash -n "$script"
done

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/*.sh docker/postgres/init/*.sh
else
  echo "shellcheck is required but not installed. Install ShellCheck before running validate.sh." >&2
  exit 1
fi

docker compose --env-file "$env_file" config --quiet
docker compose --env-file "$env_file" exec -T postgres sh -c \
  'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1' <<'SQL'
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('silver', 'audit', 'intermediate', 'analytics')
ORDER BY schema_name;

SELECT rolname
FROM pg_roles
WHERE rolname IN ('pipeline', 'dbt', 'superset_ro', 'superset_meta')
ORDER BY rolname;

SELECT datname FROM pg_database WHERE datname = 'superset_meta';
SQL

superset_health="$(docker inspect --format='{{.State.Health.Status}}' cafenorte-superset 2>/dev/null || true)"
redis_health="$(docker inspect --format='{{.State.Health.Status}}' cafenorte-redis 2>/dev/null || true)"
[[ "$superset_health" == "healthy" ]] || { echo "Superset is not healthy." >&2; exit 1; }
[[ "$redis_health" == "healthy" ]] || { echo "Redis is not healthy." >&2; exit 1; }

set -a
# shellcheck disable=SC1090
. "$env_file"
set +a
UV_CACHE_DIR=/tmp/cafenorte-uv-cache uv run python -m cafenorte.ingest --engine pardox --force
uv run pytest
anchor_date="$(docker compose --env-file "$env_file" exec -T postgres sh -c \
  'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -At -c "SELECT LEAST((SELECT max(fecha_hora_normalizada::date) FROM silver.pos_sales), (SELECT max(fecha::date) FROM silver.ecommerce_orders), (SELECT max(fecha) FROM silver.inventory_snapshots));"' \
  | tr -d '\r')"
[[ "$anchor_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "Could not calculate anchor_date: $anchor_date" >&2; exit 1; }
echo "anchor_date=$anchor_date"
uv run dbt build --project-dir dbt --profiles-dir dbt --target-path ../artifacts/evidence/dbt \
  --vars "{\"anchor_date\": \"'$anchor_date'\"}"
uv run python -m cafenorte.export_answers
uv run ruff check scripts/profile_sources.py
uv run python superset/test_rls.py
