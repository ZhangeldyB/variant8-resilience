"""loadgen.py — «пользователи» для локального стенда.

20 запросов в секунду к core, каждый ждёт ответа не дольше 1,5 с.
Сам управляет отказом: в FAULT_START включает FAULT на dep-a, в FAULT_END снимает.
Результат — CSV: t (с от старта), code (0 = не дождался), latency_ms.

Запуск: python loadgen.py results/off.csv
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

CORE_URL = os.environ.get("CORE_URL", "http://core:8080/")
DEP_CONTROL = os.environ.get("DEP_CONTROL", "http://dep:8081")
FAULT = os.environ.get("FAULT", '{"delay_ms": 4000}')
RPS = float(os.environ.get("RPS", "20"))
DURATION = float(os.environ.get("DURATION_S", "120"))
FAULT_START = float(os.environ.get("FAULT_START", "30"))
FAULT_END = float(os.environ.get("FAULT_END", "60"))
CLIENT_TIMEOUT = 1.5

rows, lock = [], threading.Lock()


def control(path, body=b""):
    req = urllib.request.Request(DEP_CONTROL + path, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.read().decode()


def one(t_sched):
    start = time.time()
    code = 0
    try:
        with urllib.request.urlopen(CORE_URL, timeout=CLIENT_TIMEOUT) as r:
            r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = 0
    lat = min((time.time() - start) * 1000, CLIENT_TIMEOUT * 1000 + 2)
    with lock:
        rows.append((round(t_sched, 3), code, round(lat, 1)))


def fault_timeline(t0):
    time.sleep(max(0, t0 + FAULT_START - time.time()))
    print(f"[{FAULT_START:>5.1f} s] dep-a: включаем отказ {FAULT} -> {control('/fault', FAULT.encode())}", flush=True)
    time.sleep(max(0, t0 + FAULT_END - time.time()))
    print(f"[{FAULT_END:>5.1f} s] dep-a: снимаем отказ -> {control('/clear')}", flush=True)


def main(out_path):
    control("/clear")
    t0 = time.time()
    threading.Thread(target=fault_timeline, args=(t0,), daemon=True).start()
    threads, i = [], 0
    while True:
        t_sched = i / RPS
        if t_sched >= DURATION:
            break
        delay = t0 + t_sched - time.time()
        if delay > 0:
            time.sleep(delay)
        th = threading.Thread(target=one, args=(t_sched,), daemon=True)
        th.start()
        threads.append(th)
        i += 1
        if i % int(RPS * 10) == 0:
            with lock:
                bad = sum(1 for r in rows if r[1] != 200)
            print(f"[{t_sched:>5.1f} s] отправлено {i}, неуспешных {bad}", flush=True)
    for th in threads:
        th.join(CLIENT_TIMEOUT + 1)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        f.write("t,code,latency_ms\n")
        for r in sorted(rows):
            f.write(f"{r[0]},{r[1]},{r[2]}\n")
    print(f"loadgen: {len(rows)} запросов -> {out_path}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/out.csv")
