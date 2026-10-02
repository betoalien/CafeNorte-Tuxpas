#!/usr/bin/env bash
set -euo pipefail
exec uv run cafenorte doctor "$@"
