#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

env_file="${ENV_FILE:-.env}"
if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file; nothing was stopped." >&2
  exit 1
fi

docker compose --env-file "$env_file" stop postgres
