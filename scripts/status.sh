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
superset_port="$(env_value SUPERSET_PORT)"
health="$(docker inspect --format='{{.State.Health.Status}}' cafenorte-postgres 2>/dev/null || true)"
if [[ -z "$health" ]]; then
  health="not-created"
fi

printf 'PostgreSQL host: 127.0.0.1\n'
printf 'PostgreSQL port: %s\n' "$postgres_port"
printf 'Health: %s\n' "$health"
printf 'Superset URL: http://127.0.0.1:%s\n' "$superset_port"
printf 'Superset users: admin, director, gerente_t001 (passwords are in .env)\n'
docker compose --env-file "$env_file" ps postgres
docker compose --env-file "$env_file" ps redis superset

if [[ "$health" == "healthy" ]]; then
  printf 'Silver:\n'
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
  UNION ALL SELECT 'silver.stores', count(*) FROM silver.stores
  UNION ALL SELECT 'silver.products', count(*) FROM silver.products
  UNION ALL SELECT 'silver.sku_mappings', count(*) FROM silver.sku_mappings
) counts
ORDER BY table_name;
SQL
  if command -v uv >/dev/null 2>&1; then
    uv run dbt --version | sed 's/^Core:/dbt:/' | head -1
  fi
  printf 'Gold (analytics):\n'
  docker compose --env-file "$env_file" exec -T postgres sh -c \
    'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1' <<'SQL'
SELECT table_name, row_count
FROM (
  SELECT 'analytics.mart_inventory_turnover_top10' AS table_name, count(*) AS row_count FROM analytics.mart_inventory_turnover_top10
  UNION ALL SELECT 'analytics.mart_stockouts_over_3_days', count(*) FROM analytics.mart_stockouts_over_3_days
  UNION ALL SELECT 'analytics.mart_monthly_channel_growth', count(*) FROM analytics.mart_monthly_channel_growth
  UNION ALL SELECT 'analytics.mart_negative_margin_products', count(*) FROM analytics.mart_negative_margin_products
  UNION ALL SELECT 'analytics.mart_source_reconciliation', count(*) FROM analytics.mart_source_reconciliation
) gold_counts ORDER BY table_name;
SQL
fi
