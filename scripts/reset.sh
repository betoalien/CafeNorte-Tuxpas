#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

echo "Reset targets:"
echo "  - Docker Compose containers and network for project cafenorte"
echo "  - Docker volume cafenorte_postgres_data"
echo "Preserved: datos/, docs/, AI_LOG.md, source code, and evidence."

if [[ "${1:-}" != "--yes" ]]; then
  echo "No changes made. Re-run with --yes to confirm." >&2
  exit 2
fi

env_file="${ENV_FILE:-.env}"
if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file; refusing to resolve Compose resources." >&2
  exit 1
fi

docker compose --env-file "$env_file" down --volumes --remove-orphans
