"""Тесты паттерна Bulkhead (вариант 8) — без кластера и без сети.

Зависимость подменяется функциями, которые ведут себя как urllib с таймаутом:
спят min(delay, timeout) и бросают TimeoutError, если зависимость медленнее таймаута.
Запуск: python -m unittest -v
"""
import threading
import time
import unittest

import core


def make_dep(delay_s, fail=False, counter=None):
    def dep(timeout=core.DEFAULT_DEP_TIMEOUT):
        if counter is not None:
            counter.enter()
        try:
            time.sleep(min(delay_s, timeout))
            if delay_s > timeout:
                raise TimeoutError("dep-a: timed out")
            if fail:
                raise ConnectionError("dep-a: 503")
            return {"confirmed": True}
        finally:
            if counter is not None:
                counter.leave()
    return dep


class Concurrency:
    def __init__(self):
        self.lock = threading.Lock()
        self.now = 0
        self.peak = 0

    def enter(self):
        with self.lock:
            self.now += 1
            self.peak = max(self.peak, self.now)

    def leave(self):
        with self.lock:
            self.now -= 1


class BulkheadTest(unittest.TestCase):
    def setUp(self):
        self._orig_dep = core.call_dep
        self._orig_pattern = core.PATTERN
        core.PATTERN = True
        core.analytics_bulkhead = core.Bulkhead(4)       # R = 4

    def tearDown(self):
        core.call_dep = self._orig_dep
        core.PATTERN = self._orig_pattern

    def test_slow_dep_alarm_answers_fast_and_degraded(self):
        """dep-a тормозит 4 с (отказ эксперимента) → тревога приходит ≤ 1,5 с, не 500."""
        core.call_dep = make_dep(4.0)
        start = time.time()
        r = core.do_work()
        self.assertLess(time.time() - start, 1.5)
        self.assertEqual(r["status"], "degraded")
        self.assertEqual(r["sprinkler"], "open")

    def test_healthy_dep_returns_full_answer(self):
        core.call_dep = make_dep(0.01)
        r = core.do_work()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["analytics"], {"confirmed": True})
        self.assertTrue(r["alarm"])

    def test_full_bulkhead_rejects_instantly_but_alarm_passes(self):
        """Все 4 слота заняты → аналитику не вызываем, тревогу отдаём сразу."""
        calls = []
        core.call_dep = lambda timeout=None: calls.append(1)
        for _ in range(4):
            self.assertTrue(core.analytics_bulkhead.try_enter())
        start = time.time()
        r = core.do_work()
        self.assertLess(time.time() - start, 0.05)
        self.assertEqual(r["analytics"], "rejected")
        self.assertEqual(r["sprinkler"], "open")
        self.assertEqual(calls, [])

    def test_no_more_than_R_concurrent_calls_and_all_fast(self):
        """20 одновременных тревог при медленной dep-a: в аналитике ≤ 4, все ответы ≤ 1,5 с."""
        conc = Concurrency()
        core.call_dep = make_dep(4.0, counter=conc)
        results, durations = [], []

        def worker():
            t0 = time.time()
            results.append(core.do_work())
            durations.append(time.time() - t0)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertLessEqual(conc.peak, 4)
        self.assertLess(max(durations), 1.5)
        self.assertTrue(all(r["sprinkler"] == "open" for r in results))
        self.assertEqual(sum(r["analytics"] == "rejected" for r in results), 16)

    def test_slots_are_released_after_timeouts_and_errors(self):
        core.call_dep = make_dep(4.0)
        for _ in range(3):
            core.do_work()
        core.call_dep = make_dep(0.0, fail=True)
        for _ in range(3):
            core.do_work()
        self.assertEqual(core.analytics_bulkhead.in_use, 0)
        core.call_dep = make_dep(0.0)
        self.assertEqual(core.do_work()["status"], "ok")

    def test_pattern_off_calls_dep_directly(self):
        core.PATTERN = False
        core.call_dep = lambda timeout=core.DEFAULT_DEP_TIMEOUT: {"direct": True}
        self.assertEqual(core.do_work(), {"direct": True})
        core.call_dep = make_dep(0.0, fail=True)
        with self.assertRaises(ConnectionError):
            core.do_work()


if __name__ == "__main__":
    unittest.main()
