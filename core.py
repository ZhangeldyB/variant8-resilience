"""core.py — вариант 8 «IoT-пожаротушение склада».

Ключевая функция: «датчик → спринклер» (RTO — секунды, RPO — 0).
Зависимость dep-a — облачная аналитика (видеоподтверждение очага).
Паттерн варианта: Bulkhead — тревоги отдельно.

  * Тревога (решение открыть клапан) считается локально и НИКОГДА не ждёт dep-a.
  * Вызовы аналитики изолированы в своём «отсеке»: не больше BULKHEAD_SIZE (R = 4)
    одновременных вызовов, каждый не дольше TIMEOUT_S (1 с).
  * Отсек полон или аналитика не ответила вовремя → ответ 200 с решением по
    тревоге и пометкой "analytics": "rejected" / "timeout" (деградированный режим).

Каркас сервера (PATTERN, call_dep, обработчик HTTP) соответствует выданному core.py;
паттерн целиком находится в do_work() и вспомогательных функциях над ним.
Готовые библиотеки устойчивости не используются — только стандартная библиотека.
"""
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATTERN = os.environ.get("PATTERN", "off").lower() in ("on", "1", "true", "yes")
DEP_URL = os.environ.get("DEP_URL", "http://dep-a:8080/work")
PORT = int(os.environ.get("PORT", "8080"))
DEFAULT_DEP_TIMEOUT = 10.0          # без паттерна ждём зависимость до 10 с

# --- параметры паттерна варианта 8 ----------------------------------------
BULKHEAD_SIZE = int(os.environ.get("BULKHEAD_SIZE", "4"))   # R = 4 слота для аналитики
TIMEOUT = float(os.environ.get("TIMEOUT_S", "1.0"))         # не дольше 1 с на вызов аналитики


def call_dep(timeout=DEFAULT_DEP_TIMEOUT):
    """Вызов зависимости dep-a (облачная аналитика). Дан готовым в каркасе."""
    with urllib.request.urlopen(DEP_URL, timeout=timeout) as resp:
        return json.loads(resp.read().decode() or "{}")


# --- Bulkhead: отдельный отсек для аналитики --------------------------------
class Bulkhead:
    """Ограничивает число одновременных вызовов зависимости.

    Не ставит запросы в очередь: если свободного слота нет, вызов сразу
    отклоняется. Так поток тревоги не может застрять за медленной аналитикой.
    """

    def __init__(self, size):
        self.size = size
        self._slots = threading.BoundedSemaphore(size)
        self._lock = threading.Lock()
        self.in_use = 0          # для метрики saturation и тестов
        self.max_in_use = 0
        self.rejected = 0

    def try_enter(self):
        if not self._slots.acquire(blocking=False):
            with self._lock:
                self.rejected += 1
            return False
        with self._lock:
            self.in_use += 1
            self.max_in_use = max(self.max_in_use, self.in_use)
        return True

    def leave(self):
        with self._lock:
            self.in_use -= 1
        self._slots.release()


analytics_bulkhead = Bulkhead(BULKHEAD_SIZE)


def local_alarm_decision():
    """Отсек тревог: решение по локальному правилу «2 датчика из 2 в секции».

    Работает только на данных контроллера, без сети, за микросекунды.
    В стенде показания датчиков не передаются, поэтому решение фиксированное:
    клапан секции открыть.
    """
    return {"alarm": True, "sprinkler": "open", "rule": "2oo2-local"}


def do_work():
    if not PATTERN:
        return call_dep()                      # тревога ждёт аналитику до 10 с

    decision = local_alarm_decision()          # 1. тревога — сразу, без dep-a

    if not analytics_bulkhead.try_enter():     # 2. отсек аналитики полон
        return {**decision, "status": "degraded", "analytics": "rejected"}
    try:
        result = call_dep(timeout=TIMEOUT)     # 3. аналитика — не дольше 1 с
        return {**decision, "status": "ok", "analytics": result}
    except Exception:
        return {**decision, "status": "degraded", "analytics": "timeout"}
    finally:
        analytics_bulkhead.leave()             # слот освобождается всегда


# --- HTTP-сервер (каркас) ---------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/healthz"):
            # readiness/liveness: только процесс, без проверки dep-a
            return self._send(200, {"status": "up"})
        try:
            body, code = do_work(), 200
        except Exception as exc:               # без паттерна ошибка зависимости = отказ
            body, code = {"error": str(exc)}, 503
        self._send(code, body)

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass                               # клиент уже ушёл по таймауту

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"core: PATTERN={'on' if PATTERN else 'off'} BULKHEAD_SIZE={BULKHEAD_SIZE} "
          f"TIMEOUT_S={TIMEOUT} DEP_URL={DEP_URL}", flush=True)
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
