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
fi
