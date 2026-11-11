"""Тесты metrics.py (студент B) — проверяют правила подсчёта без стенда.

Запуск: python -m unittest -v   (или ./run_tests.sh)
"""
import io
import unittest

import metrics


def csv_of(rows):
    """rows: [(t, code, latency_ms), ...] -> файловый объект CSV."""
    buf = io.StringIO()
    buf.write("t,code,latency_ms\n")
    for t, code, lat in rows:
        buf.write(f"{t},{code},{lat}\n")
    buf.seek(0)
    return buf


class MetricsTest(unittest.TestCase):
    def test_slide_example(self):
        """Пример со слайда: 0,30 / 1 эпизод / 360 / 0,70; p50/p95/p99 = 45/1003/1004."""
        m = metrics.compute(metrics.load_rows(metrics.example_csv()))
        self.assertAlmostEqual(m["POFOD"], 0.30)
        self.assertEqual(m["episodes"], 1)
        self.assertAlmostEqual(m["ROCOF_per_h"], 360)
        self.assertAlmostEqual(m["AVAIL"], 0.70)
        self.assertEqual((m["p50"], m["p95"], m["p99"]), (45, 1003, 1004))

    def test_gap_of_two_seconds_starts_new_episode(self):
        """Ошибки в 1,0 и 3,0 с (промежуток ровно 2 с) — это два эпизода."""
        rows = [(0.0, 200, 10), (1.0, 500, 10), (2.0, 200, 10), (3.0, 500, 10)]
        m = metrics.compute(metrics.load_rows(csv_of(rows)))
        self.assertEqual(m["episodes"], 2)

    def test_close_errors_are_one_episode(self):
        rows = [(0.0, 503, 10), (0.5, 0, 1500), (1.9, 500, 10), (3.0, 200, 10)]
        m = metrics.compute(metrics.load_rows(csv_of(rows)))
        self.assertEqual(m["episodes"], 1)

    def test_timeout_code_zero_counts_as_failure(self):
        """Код 0 — клиент не дождался ответа за 1,5 с: это неуспешный запрос."""
        rows = [(0.0, 200, 10), (0.5, 0, 1502)]
        m = metrics.compute(metrics.load_rows(csv_of(rows)))
        self.assertEqual(m["failed"], 1)
        self.assertAlmostEqual(m["POFOD"], 0.5)

    def test_all_ok_run(self):
        rows = [(i * 0.05, 200, 5) for i in range(200)]   # 10 с по 20 запросов/с
        m = metrics.compute(metrics.load_rows(csv_of(rows)))
        self.assertEqual((m["POFOD"], m["episodes"], m["ROCOF_per_h"], m["AVAIL"]), (0, 0, 0, 1.0))

    def test_columns_are_found_by_header_name(self):
        buf = io.StringIO("latency,status,time\n12,200,0.0\n1500,0,0.5\n")
        m = metrics.compute(metrics.load_rows(buf))
        self.assertEqual(m["requests"], 2)
        self.assertEqual(m["failed"], 1)


if __name__ == "__main__":
    unittest.main()
