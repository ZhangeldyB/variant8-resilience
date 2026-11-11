#!/usr/bin/env bash
# Тесты паттерна и самопроверка metrics.py внутри Docker (Python на Windows не нужен).
set -euo pipefail
export MSYS_NO_PATHCONV=1
export FAULT=${FAULT:-"{}"} PATTERN=${PATTERN:-off} MODE=${MODE:-off}
cd "$(dirname "$0")"
docker compose build tools
docker compose run --rm -T tools python -m unittest -v
docker compose run --rm -T tools python metrics.py --selftest
