#!/usr/bin/env bash
# Один прогон эксперимента на локальном стенде Docker.
#   ./experiment.sh off   — без паттерна
#   ./experiment.sh on    — с паттерном Bulkhead
# Таймлайн: 0–30 с норма, 30–60 с dep-a тормозит (FAULT), 60–120 с восстановление.
set -euo pipefail
export MSYS_NO_PATHCONV=1            # Git Bash на Windows: не переписывать пути

MODE=${1:-}
if [[ "$MODE" != "off" && "$MODE" != "on" ]]; then
  echo "Использование: ./experiment.sh off|on" >&2
  exit 1
fi
cd "$(dirname "$0")"
export PATTERN=$MODE MODE
export FAULT=${FAULT:-'{"delay_ms": 4000}'}
mkdir -p results

echo "== Прогон PATTERN=$MODE, FAULT=$FAULT"
docker compose down --remove-orphans >/dev/null 2>&1 || true
docker compose up -d --build --force-recreate dep core

echo "== Ждём, пока core и dep-a поднимутся"
for i in $(seq 1 30); do
  if docker compose exec -T core python -c "import urllib.request as u; u.urlopen('http://localhost:8080/healthz', timeout=1); u.urlopen('http://dep:8081/healthz', timeout=1)" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "== Нагрузка 120 с (20 запросов/с)"
docker compose run --rm -T loadgen

echo "== Метрики"
docker compose run --rm -T tools python metrics.py "results/$MODE.csv" | tee "results/$MODE.metrics.txt"
docker compose logs --no-color core dep > "results/$MODE.stand.log" 2>&1 || true
docker compose down --remove-orphans >/dev/null
echo "== Готово: results/$MODE.csv, results/$MODE.metrics.txt"
