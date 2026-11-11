# Вариант 8 — IoT-пожаротушение склада

Паттерн: **Bulkhead — тревоги отдельно** (R = 4 слота для аналитики, таймаут 1 с).
Отказ эксперимента: `dep-a` (облачная аналитика) отвечает на 4000 мс медленнее в окне 30–60 с.

Пошаговая инструкция (Windows, Git Bash, Docker Desktop) — **[INSTRUCTIONS.md](INSTRUCTIONS.md)**.

## Быстрый старт

```bash
./run_tests.sh            # 6 тестов + selftest metrics.py (0,30 / 360 / 0,70)
./experiment.sh off       # прогон без паттерна, ~2,5 мин
./experiment.sh on        # прогон с паттерном
```
Результаты: `results/off.csv`, `results/on.csv`, `results/*.metrics.txt`.

## Состав

| Файл | Что внутри |
| --- | --- |
| `core.py` | Сервис; паттерн в `do_work()`: тревога решается локально, вызовы dep-a — в отсеке `Bulkhead(4)` с таймаутом 1 с |
| `test_core.py` | 6 тестов без кластера и сети |
| `metrics.py` | POFOD, ROCOF, AVAIL, p50/p95/p99 по CSV; `--selftest` |
| `local_stand/dep.py` | dep-a: ломается по команде (`POST /fault`, `POST /clear`) |
| `local_stand/loadgen.py` | 20 запросов/с, ожидание ≤ 1,5 с, сам включает и снимает отказ, пишет CSV |
| `docker-compose.yml`, `Dockerfile` | Локальный стенд (аналог Killercoda) |
| `experiment.sh`, `run_tests.sh` | Прогон эксперимента и тесты в Docker |
| `diagrams/variant8.drawio` | 7 страниц схем для отчёта |
