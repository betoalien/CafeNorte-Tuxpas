#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

env_file="${ENV_FILE:-.env}"
if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file; Compose status cannot be resolved." >&2
  exit 1
fi

env_value() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$env_file"
}

postgres_port="$(env_value POSTGRES_PORT)"
health="$(docker inspect --format='{{.State.Health.Status}}' cafenorte-postgres 2>/dev/null || true)"
if [[ -z "$health" ]]; then
  health="not-created"
fi

printf 'PostgreSQL host: 127.0.0.1\n'
printf 'PostgreSQL port: %s\n' "$postgres_port"
printf 'Health: %s\n' "$health"
docker compose --env-file "$env_file" ps postgres

if [[ "$health" == "healthy" ]]; then
  docker compose --env-file "$env_file" exec -T postgres sh -c \
    'pg_isready --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"'
  docker compose --env-file "$env_file" exec -T postgres sh -c \
    'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1' <<'SQL'
SELECT run_id, status, input_count, accepted_count, rejected_count
FROM audit.run_log ORDER BY started_at DESC LIMIT 1;
SELECT table_name, row_count
FROM (
  SELECT 'silver.pos_sales' AS table_name, count(*) AS row_count FROM silver.pos_sales
  UNION ALL SELECT 'silver.inventory_snapshots', count(*) FROM silver.inventory_snapshots
  UNION ALL SELECT 'silver.ecommerce_orders', count(*) FROM silver.ecommerce_orders
  UNION ALL SELECT 'silver.exchange_rates', count(*) FROM silver.exchange_rates
) counts
ORDER BY table_name;
SQL
fi
