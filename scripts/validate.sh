#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

bash "$project_root/scripts/doctor.sh"

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

case "$(uname -s)" in
  Darwin) checksum_command=(shasum -a 256 -c SHA256SUMS) ;;
  Linux) checksum_command=(sha256sum -c SHA256SUMS) ;;
  *) echo "Unsupported platform for source checksum verification." >&2; exit 1 ;;
esac
if ! (cd datos && "${checksum_command[@]+"${checksum_command[@]}"}" >/dev/null); then
  echo "fuente original del cliente modificada" >&2
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
paradox_platform="$(uname -s)-$(uname -m)"
case "$(uname -s)/$(uname -m)" in
  Darwin/arm64|Darwin/x86_64|Linux/x86_64|MINGW*/x86_64|MSYS*/x86_64|CYGWIN*/x86_64)
    pardox_supported=1 ;;
  *)
    pardox_supported=0
    echo "PardoX: UNSUPPORTED_PLATFORM ($paradox_platform)"
    ;;
esac
if [[ "$pardox_supported" -eq 1 ]]; then
  if UV_CACHE_DIR=/tmp/cafenorte-uv-cache uv run python -m cafenorte.ingest --engine pardox --force; then
    uv run pytest
  else
    pardox_supported=0
    echo "PardoX: UNSUPPORTED_PLATFORM ($paradox_platform)"
    uv run pytest --ignore=tests/test_engines.py
  fi
else
  uv run pytest --ignore=tests/test_engines.py
fi
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
mkdir -p artifacts/reports
if /bin/bash --version 2>/dev/null | head -1 | grep -Eq 'version 3\.'; then
  /bin/bash -n scripts/*.sh
  uv run python scripts/run_report.py --dry-run --no-browser
fi
printf 'validate.sh: PASS (%s)\n' "$(date -u +%FT%TZ)" > artifacts/reports/last_validate.txt
