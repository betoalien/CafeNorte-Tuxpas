#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

no_browser=0
for argument in "$@"; do
  case "$argument" in
    --no-browser) no_browser=1 ;;
    *) echo "Unknown option: $argument" >&2; exit 1 ;;
  esac
done
bash "$project_root/scripts/doctor.sh"

env_file="${ENV_FILE:-.env}"

random_port() {
  printf '%s\n' "$((20000 + (RANDOM * 32768 + RANDOM) % 40001))"
}

port_is_free() {
  local port="$1"
  local platform
  platform="$(uname -s)"

  if [[ "$platform" == "Darwin" ]] && command -v lsof >/dev/null 2>&1; then
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      return 1
    fi
    return 0
  fi

  if [[ "$platform" == "Linux" ]] && command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk 'NR > 1 {print $4}' | grep -Eq "(^|:)$port$"; then
      return 1
    fi
    return 0
  fi

  if [[ "$platform" == "Linux" ]] && command -v netstat >/dev/null 2>&1; then
    if netstat -ltn 2>/dev/null | awk 'NR > 2 {print $4}' | grep -Eq "(^|:)$port$"; then
      return 1
    fi
    return 0
  fi

  echo "Cannot check whether port $port is free: install lsof on macOS or ss/netstat on Linux." >&2
  exit 1
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

  local postgres_port="$selected_port"
  selected_port=""
  attempt=1
  while [[ "$attempt" -le 100 ]]; do
    selected_port="$(random_port)"
    if port_is_free "$selected_port"; then break; fi
    selected_port=""
    attempt=$((attempt + 1))
  done
  if [[ -z "$selected_port" ]]; then
    echo "No free Superset port found after 100 attempts." >&2
    exit 1
  fi
  local superset_port="$selected_port"

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
    printf 'SUPERSET_SECRET_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'SUPERSET_ADMIN_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'GERENTE_T001_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'DIRECTOR_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'POSTGRES_PORT=%s\n' "$postgres_port"
    printf 'SUPERSET_PORT=%s\n' "$superset_port"
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

docker compose --env-file "$env_file" up -d postgres redis

attempt=1
while [[ "$attempt" -le 30 ]]; do
  health="$(docker inspect --format='{{.State.Health.Status}}' cafenorte-postgres 2>/dev/null || true)"
  if [[ "$health" == "healthy" ]] && docker compose --env-file "$env_file" exec -T postgres \
    sh -c 'pg_isready --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' >/dev/null 2>&1; then
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
    ingest_output="$(uv run python -m cafenorte.ingest)"
    printf '%s\n' "$ingest_output"
    load_mode="$(printf '%s\n' "$ingest_output" | uv run python -c 'import json,sys; print(json.load(sys.stdin)["load_mode"])')"
    if [[ "$load_mode" != "skipped" ]]; then
      anchor_date="$(docker compose --env-file "$env_file" exec -T postgres sh -c \
        'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -At -c "SELECT LEAST((SELECT max(fecha_hora_normalizada::date) FROM silver.pos_sales), (SELECT max(fecha::date) FROM silver.ecommerce_orders), (SELECT max(fecha) FROM silver.inventory_snapshots));"' \
        | tr -d '\r')"
      [[ "$anchor_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "Could not calculate anchor_date: $anchor_date" >&2; exit 1; }
      echo "anchor_date=$anchor_date"
      uv run dbt build --project-dir dbt --profiles-dir dbt --target-path ../artifacts/evidence/dbt \
        --vars "{\"anchor_date\": \"'$anchor_date'\"}"
      uv run python -m cafenorte.export_answers
    else
      echo "No source changed; dbt build and answer export skipped."
    fi
    docker compose --env-file "$env_file" up -d superset
    superset_attempt=1
    while [[ "$superset_attempt" -le 30 ]]; do
      superset_health="$(docker inspect --format='{{.State.Health.Status}}' cafenorte-superset 2>/dev/null || true)"
      if [[ "$superset_health" == "healthy" ]]; then
        break
      fi
      sleep 2
      superset_attempt=$((superset_attempt + 1))
    done
    [[ "$superset_health" == "healthy" ]] || { docker compose --env-file "$env_file" logs superset; echo "Superset did not become healthy after 60 seconds." >&2; exit 1; }
    bash "$project_root/scripts/status.sh"
    report_args=()
    if [[ "$no_browser" -eq 1 ]]; then report_args+=(--no-browser); fi
    uv run python scripts/run_report.py "${report_args[@]+"${report_args[@]}"}"
    exit 0
  fi
  sleep 2
  attempt=$((attempt + 1))
done

docker compose --env-file "$env_file" logs postgres
echo "PostgreSQL did not become healthy after 60 seconds." >&2
exit 1
