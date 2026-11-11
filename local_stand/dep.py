"""dep.py — зависимость dep-a (облачная аналитика) для локального стенда.

GET  /work   — «работа» зависимости (~5 мс).
POST /fault  — включить отказ; тело — JSON, как в FAULT:
               {"delay_ms": 4000}       задержка ответа
               {"error_rate": 0.3}      доля ответов 500
               {"unavailable": true}    все ответы 503
POST /clear  — снять отказ.
GET  /healthz — проверка, что сервис поднялся.
"""
import json
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8081"))
_fault = {}
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/healthz"):
            return self._send(200, {"status": "up", "fault": _fault})
        with _lock:
            fault = dict(_fault)
        time.sleep(0.005 + fault.get("delay_ms", 0) / 1000)
        if fault.get("unavailable"):
            return self._send(503, {"error": "unavailable"})
        if random.random() < fault.get("error_rate", 0):
            return self._send(500, {"error": "injected"})
        self._send(200, {"confirmed": True})

    def do_POST(self):
        global _fault
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else ""
        with _lock:
            if self.path.startswith("/fault"):
                _fault = json.loads(body or "{}")
            elif self.path.startswith("/clear"):
                _fault = {}
            else:
                return self._send(404, {"error": "unknown"})
            current = dict(_fault)
        print(f"dep-a: fault = {current}", flush=True)
        self._send(200, {"fault": current})

    def _send(self, code, body):
        data = json.dumps(body).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"dep-a listening on :{PORT}", flush=True)
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
