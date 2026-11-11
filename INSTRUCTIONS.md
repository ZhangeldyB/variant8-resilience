# Инструкция: как всё запустить локально и что куда вставить

Windows + Git Bash + Docker Desktop. Python на компьютере не нужен: всё запускается в контейнерах.
Отчёт: Google Doc «Файнал УПООР». В нём 14 мест вида `[ВСТАВИТЬ СЮДА: ...]` — под каждым уже стоит подпись
*Рисунок N.* … Картинку вставляете вместо строки `[ВСТАВИТЬ СЮДА: ...]`, подпись не трогаете.

---

## 0. Один раз перед началом

1. Запустите **Docker Desktop** и дождитесь зелёного «Engine running».
2. В Git Bash выполните (чтобы Git не портил переводы строк в .sh-файлах):
   ```bash
   git config --global core.autocrlf false
   ```
3. Распакуйте `variant8-resilience.zip`, например в `C:\Users\<вы>\variant8-resilience`.

## 1. Репозиторий на GitHub (нужен для сдачи и для рисунка 14)

```bash
cd ~/variant8-resilience          # путь к распакованной папке
git init -b main
git add .
git commit -m "Вариант 8: стенд, паттерн Bulkhead, тесты, metrics.py"
# создайте пустой репозиторий на github.com, затем:
git remote add origin https://github.com/<логин>/variant8-resilience.git
git push -u origin main
```
Добавьте Аслана в Settings → Collaborators.

## 2. Рисунок 9 — «Подготовка среды»

В Git Bash в папке проекта:
```bash
docker version
docker compose version
git log --oneline -1
ls
```
Сделайте скриншот окна (Win + Shift + S) → вставьте вместо `[ВСТАВИТЬ СЮДА: Git Bash: вывод команд docker version ...]`.

## 3. Рисунок 10 — тесты и самопроверка metrics.py

```bash
./run_tests.sh
```
Первый запуск скачивает образ `python:3.12-slim` и собирает стенд (1–2 мин, нужен интернет).
Ожидаемый конец вывода:
```
Ran 6 tests in 5.0s
OK
example: requests=20 failed=6 POFOD=0.3000 episodes=1 ROCOF=360.0/h AVAIL=0.7000 p50/p95/p99=45/1003/1004 ms
selftest OK: 0,30 / 360 / 0,70; p50/p95/p99 = 45/1003/1004 мс
```
Скриншот → вместо `[ВСТАВИТЬ СЮДА: Git Bash: вывод ./run_tests.sh ...]`.

## 4. Рисунки 11 и 12 — два прогона эксперимента (по ~2,5 мин)

```bash
./experiment.sh off      # без паттерна
./experiment.sh on       # с паттерном
```
Во время прогона видно: на 30-й секунде включается отказ dep-a (+4000 мс), на 60-й снимается.
В конце печатается строка метрик. Скриншот конца вывода `off` → рисунок 11, `on` → рисунок 12.

Что должно получиться (у вас цифры могут отличаться на несколько запросов):

| | POFOD | ROCOF, 1/ч | AVAIL | p50/p95/p99, мс |
|---|---|---|---|---|
| off | 0,2500 | 30 | 0,75 | ~9 / 1502 / 1502 |
| on | 0,0000 | 0 | 1,00 | ~8 / ~16 / ~1004 |

**Если ваши цифры отличаются** — замените их в Google Doc: раздел «Практика», таблица «Результаты»
(колонки PATTERN=off и PATTERN=on), и p95 в первой строке раздела («p95 с 1 502 до 16 мс»).
Ваши строки метрик лежат в `results/off.metrics.txt` и `results/on.metrics.txt`.

## 5. Рисунок 13 — результаты в репозитории

Откройте папку `results` в Проводнике или VS Code (видны `off.csv`, `on.csv`, `*.metrics.txt`,
можно открыть `off.csv`) → скриншот → вместо `[ВСТАВИТЬ СЮДА: Проводник или VS Code: папка results ...]`.
Затем закоммитьте результаты:
```bash
git add results && git commit -m "Результаты прогонов off/on" && git push
```

## 6. Рисунки 1–5, 7, 8 — схемы draw.io

1. Откройте https://app.diagrams.net → **File → Open from → Device** → `diagrams/variant8.drawio`.
2. Внизу вкладки страниц. Для каждой: выберите страницу → **File → Export as → PNG** →
   Zoom 200%, Border 10 → Export → сохраните.
3. В Google Doc выделите строку `[ВСТАВИТЬ СЮДА: ...]` → удалите текст → **Insert → Image → Upload from computer**.

| Рисунок в отчёте | Страница draw.io |
|---|---|
| Рисунок 1 (задание 2) | 1. Архитектура как есть (SPOF) |
| Рисунок 2 (задание 2) | 2. Архитектура после (резервирование + Bulkhead) |
| Рисунок 3 (задание 3) | 4. Матрица рисков 5x5 |
| Рисунок 4 (задание 4) | 3. RBD: доступность A-B-C |
| Рисунок 5 (задание 4) | 5. Fault → Error → Failure |
| Рисунок 7 (задание 7) | 6. План Kubernetes |
| Рисунок 8 (практика) | 7. Стенд Killercoda |

## 7. Рисунок 6 — DFD в OWASP Threat Dragon (задание 6)

1. Откройте https://www.threatdragon.com/ (или desktop-версию) → **New model** → название «Вариант 8».
2. Add diagram → тип **STRIDE**.
3. Нарисуйте элементы из раздела «DFD в OWASP Threat Dragon» отчёта:
   - External entity (actor): Датчик, Оператор, Облачная аналитика C, ПЦН / 101;
   - Process: Контроллер склада A, Сервис правил B;
   - Store: Конфигурация правил, Журнал событий;
   - Data flow: датчик → A (MQTT), A → клапан, A ↔ C (HTTPS), оператор → B, B → A, A → ПЦН;
   - Trust boundary: между складом и интернетом (пересекает потоки A ↔ C и A → ПЦН).
4. На каждом элементе из таблицы «Угрозы STRIDE» добавьте угрозу (кнопка + в панели Threats):
   тип S/T/R/I/D/E, описание и меру — из таблицы отчёта.
5. Скриншот диаграммы → вместо `[ВСТАВИТЬ СЮДА: скриншот диаграммы в Threat Dragon ...]`.
   Модель сохраните (Save → JSON) и положите в репозиторий как `diagrams/threat-model.json`.

## 8. Рисунок 14 — проверка кода через pull request

Задание требует, чтобы каждый проверил код партнёра:
```bash
# Жангельды
git checkout -b feature/bulkhead
git commit --allow-empty -m "Bulkhead: тревоги отдельно (review)"   # или реальная правка в core.py
git push -u origin feature/bulkhead
```
На GitHub → **Compare & pull request** → Аслан открывает PR → Files changed → **Review changes → Approve** → Merge.
Аналогично Аслан делает ветку `feature/metrics` для `metrics.py`, а Жангельды апрувит.
Скриншот страницы PR с Approve → вместо `[ВСТАВИТЬ СЮДА: GitHub: страница pull request ...]`.

## 9. Финиш

1. Первая страница документа — «титульны лист»: замените своим титульным листом (всё после неё начинается с новой страницы).
2. Проверьте шрифт после вставки картинок: выделить всё (Ctrl + A) → Times New Roman, 12 — уже стоит, но если
   что-то вставляли из буфера, повторите.
3. Номера страниц: **Insert → Page numbers**. Содержание (если нужно): **Insert → Table of contents**.
4. Сдача: **File → Download → PDF** + ссылка на репозиторий (core.py, test_core.py, metrics.py, results/*.csv).

## Если что-то не работает

| Проблема | Решение |
|---|---|
| `$'\r': command not found` | Файлы получили CRLF. `git config --global core.autocrlf false`, заново распакуйте zip или `sed -i 's/\r$//' *.sh` |
| `Cannot connect to the Docker daemon` | Docker Desktop не запущен |
| `port is already allocated` (8080) | В `docker-compose.yml` у сервиса core замените `"8080:8080"` на `"18080:8080"` |
| `permission denied: ./experiment.sh` | `chmod +x experiment.sh run_tests.sh` или запуск через `bash experiment.sh off` |
| Первый прогон очень медленный | Docker собирает образ; второй и следующие идут быстро |
| Хотите прогнать в Killercoda | Возьмите выданный каркас, перенесите из нашего `core.py` класс `Bulkhead`, `local_alarm_decision()` и `do_work()`; `metrics.py` и `test_core.py` работают без изменений |

## Что лежит в папке

| Файл | Кто писал (по отчёту) | Зачем |
|---|---|---|
| `core.py` | студент A | сервис + паттерн Bulkhead в `do_work()` |
| `test_core.py` | студент A | 6 тестов без кластера |
| `metrics.py` | студент B | POFOD, ROCOF, AVAIL, перцентили по CSV |
| `local_stand/dep.py`, `local_stand/loadgen.py` | стенд | зависимость, которая ломается по команде, и «пользователи» |
| `docker-compose.yml`, `Dockerfile` | стенд | локальная замена Killercoda |
| `experiment.sh`, `run_tests.sh` | стенд | один прогон / тесты |
| `diagrams/variant8.drawio` | — | 7 схем для отчёта |
