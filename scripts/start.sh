#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

env_file="${ENV_FILE:-.env}"

run_python() {
  if command -v python3 >/dev/null 2>&1 && python3 -c 'pass' >/dev/null 2>&1; then
    python3 "$@"
  elif command -v python >/dev/null 2>&1 && python -c 'pass' >/dev/null 2>&1; then
    python "$@"
  elif command -v py >/dev/null 2>&1 && py -3 -c 'pass' >/dev/null 2>&1; then
    py -3 "$@"
  else
    return 1
  fi
}

random_port() {
  run_python -c 'import secrets; print(20000 + secrets.randbelow(40001))' || {
    echo "Python is required to select a random PostgreSQL port." >&2
    return 1
  }
}

port_is_free() {
  local port="$1"
  local platform
  platform="$(uname -s)"

  if [[ "$platform" == "Darwin" ]] && command -v lsof >/dev/null 2>&1; then
    ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi

  if [[ "$platform" == "Linux" ]] && command -v ss >/dev/null 2>&1; then
    ! ss -ltn | awk 'NR > 1 {print $4}' | grep -Eq "(^|:)$port$"
    return
  fi

  if [[ "$platform" == "Linux" ]] && command -v netstat >/dev/null 2>&1; then
    ! netstat -ltn 2>/dev/null | awk 'NR > 2 {print $4}' | grep -Eq "(^|:)$port$"
    return
  fi

  if ! run_python - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        raise SystemExit(1)
PY
  then
    return 1
  fi
}

create_env_file() {
  local selected_port=""
  local attempt=1
  local temp_file

  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to generate local credentials." >&2
    exit 1
  fi

  while [[ "$attempt" -le 100 ]]; do
    selected_port="$(random_port)"
    if port_is_free "$selected_port"; then
      break
    fi
    selected_port=""
    attempt=$((attempt + 1))
  done

  if [[ -z "$selected_port" ]]; then
    echo "No free PostgreSQL port found after 100 attempts." >&2
    exit 1
  fi

  umask 077
  temp_file="${env_file}.tmp.$$"
  trap 'rm -f "${temp_file:-}"' EXIT HUP INT TERM
  {
    printf 'POSTGRES_DB=cafenorte\n'
    printf 'POSTGRES_USER=cafenorte_admin\n'
    printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'PIPELINE_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'DBT_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'SUPERSET_RO_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'SUPERSET_META_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'POSTGRES_PORT=%s\n' "$selected_port"
  } >"$temp_file"
  chmod 600 "$temp_file"
  mv "$temp_file" "$env_file"
  chmod 600 "$env_file"
  trap - EXIT HUP INT TERM
  echo "Generated $env_file with PostgreSQL port $selected_port."
}

if [[ ! -f "$env_file" ]]; then
  if [[ "$env_file" != ".env" ]]; then
    echo "Missing $env_file; automatic generation is limited to .env." >&2
    exit 1
  fi
  create_env_file
fi

if grep -q 'replace_with' "$env_file"; then
  echo "$env_file contains replace_with placeholders; refusing to start." >&2
  exit 1
fi

if grep -Eq '^POSTGRES_PORT=auto([[:space:]]|$)' "$env_file"; then
  echo "$env_file contains POSTGRES_PORT=auto. Remove it and run start.sh to generate a stable port." >&2
  exit 1
fi

docker compose --env-file "$env_file" up -d postgres

attempt=1
while [[ "$attempt" -le 30 ]]; do
  health="$(docker inspect --format='{{.State.Health.Status}}' cafenorte-postgres 2>/dev/null || true)"
  if [[ "$health" == "healthy" ]] && docker compose --env-file "$env_file" exec -T postgres \
    sh -c 'pg_isready --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' >/dev/null 2>&1; then
    bash "$project_root/scripts/status.sh"
    exit 0
  fi
  sleep 2
  attempt=$((attempt + 1))
done

docker compose --env-file "$env_file" logs postgres
echo "PostgreSQL did not become healthy after 60 seconds." >&2
exit 1
