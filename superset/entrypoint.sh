#!/usr/bin/env bash
set -euo pipefail

export SUPERSET_CONFIG_PATH=/app/cafenorte_superset/superset_config.py
superset db upgrade
python /app/cafenorte_superset/bootstrap.py
superset init
exec gunicorn --bind 0.0.0.0:8088 --workers 2 --timeout 120 'superset.app:create_app()'
