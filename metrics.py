"""metrics.py — POFOD, ROCOF, AVAIL, p50/p95/p99 по CSV от loadgen.py.

Использование:
    python metrics.py results/off.csv [results/on.csv ...]
    python metrics.py --selftest        # пример из 20 запросов: 0,30 / 360 / 0,70

Формат CSV: по строке на запрос; столбцы времени, кода ответа и задержки
распознаются по заголовку (t|time|ts|timestamp, code|status, latency_ms|latency|ms).
Код ответа 0 или пустой (клиент не дождался ответа за 1,5 с) — неуспешный запрос.

Правила (слайд «metrics.py на маленьком примере»):
  POFOD   = неуспешных / всего запросов
  эпизод  = серия ошибок, где промежуток между соседними ошибками < 2 с
  ROCOF   = эпизодов / длительность прогона в часах
  AVAIL   = доля секунд, в которых был хотя бы один ответ 200
  pXX     = элемент № ceil(p * n) в отсортированном списке задержек (все запросы)
"""
import csv
import io
import math
import sys

EPISODE_GAP_S = 2.0
TIME_KEYS = ("t", "time", "ts", "timestamp", "time_s", "t_s")
CODE_KEYS = ("code", "status", "status_code", "http_code")
LAT_KEYS = ("latency_ms", "latency", "ms", "lat_ms", "duration_ms")


def _pick(header, keys):
    low = [h.strip().lower() for h in header]
    for k in keys:
        if k in low:
            return low.index(k)
    raise ValueError(f"нет столбца из {keys} в заголовке {header}")


def load_rows(f):
    reader = csv.reader(f)
    header = next(reader)
    it, ic, il = _pick(header, TIME_KEYS), _pick(header, CODE_KEYS), _pick(header, LAT_KEYS)
    rows = []
    for rec in reader:
        if not rec:
            continue
        code = rec[ic].strip()
        rows.append((float(rec[it]), int(float(code)) if code else 0, float(rec[il])))
    rows.sort(key=lambda r: r[0])
    return rows


def percentile(sorted_vals, p):
    idx = max(1, math.ceil(p * len(sorted_vals)))      # номер элемента, с 1
    return sorted_vals[idx - 1]


def compute(rows):
    if not rows:
        raise ValueError("пустой CSV")
    n = len(rows)
    t0 = rows[0][0]
    fails = [t for t, code, _ in rows if code != 200]

    episodes, last = 0, None
    for t in fails:
        if last is None or t - last >= EPISODE_GAP_S:
            episodes += 1
        last = t

    n_seconds = int(math.floor(rows[-1][0] - t0)) + 1   # секунды окна прогона
    ok_seconds = {int(math.floor(t - t0)) for t, code, _ in rows if code == 200}
    lat = sorted(l for _, _, l in rows)

    return {
        "requests": n,
        "failed": len(fails),
        "POFOD": len(fails) / n,
        "episodes": episodes,
        "duration_s": n_seconds,
        "ROCOF_per_h": episodes / (n_seconds / 3600),
        "AVAIL": len(ok_seconds) / n_seconds,
        "p50": percentile(lat, 0.50),
        "p95": percentile(lat, 0.95),
        "p99": percentile(lat, 0.99),
    }


def fmt(name, m):
    return (f"{name}: requests={m['requests']} failed={m['failed']} "
            f"POFOD={m['POFOD']:.4f} episodes={m['episodes']} "
            f"ROCOF={m['ROCOF_per_h']:.1f}/h AVAIL={m['AVAIL']:.4f} "
            f"p50/p95/p99={m['p50']:.0f}/{m['p95']:.0f}/{m['p99']:.0f} ms")


# Пример со слайда: 20 запросов за 10 с, по 2 в секунду
EXAMPLE_CODES = [200, 200, 200, 200, 200, 200, 200, 200, 500, 500,
                 500, 503, 503, 500, 200, 200, 200, 200, 200, 200]
EXAMPLE_LAT = [38, 39, 39, 40, 40, 41, 42, 43, 1000, 1001,
               1001, 1002, 1003, 1004, 44, 45, 46, 47, 51, 180]


def example_csv():
    out = io.StringIO()
    out.write("t,code,latency_ms\n")
    for i, (c, l) in enumerate(zip(EXAMPLE_CODES, EXAMPLE_LAT)):
        out.write(f"{i * 0.5:.1f},{c},{l}\n")
    out.seek(0)
    return out


def selftest():
    m = compute(load_rows(example_csv()))
    assert abs(m["POFOD"] - 0.30) < 1e-9, m
    assert m["episodes"] == 1, m
    assert abs(m["ROCOF_per_h"] - 360) < 1e-9, m
    assert abs(m["AVAIL"] - 0.70) < 1e-9, m
    assert (m["p50"], m["p95"], m["p99"]) == (45, 1003, 1004), m
    print(fmt("example", m))
    print("selftest OK: 0,30 / 360 / 0,70; p50/p95/p99 = 45/1003/1004 мс")


def main(argv):
    if not argv or argv[0] == "--selftest":
        selftest()
        return
    for path in argv:
        with open(path, newline="") as f:
            print(fmt(path, compute(load_rows(f))))


if __name__ == "__main__":
    main(sys.argv[1:])
