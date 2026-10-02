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

set -a
# shellcheck disable=SC1090
. "$env_file"
set +a
uv run pytest
uv run dbt build --project-dir dbt --profiles-dir dbt --target-path ../artifacts/evidence/dbt
uv run python -m cafenorte.export_answers
uv run ruff check scripts/profile_sources.py
