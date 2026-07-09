"""
Пробник #32 (BUG-02): CircuitBreaker HALF_OPEN должен пускать ОДИН probe.

Заявление аудита: can_execute() в HALF_OPEN возвращает True для ВСЕХ запросов
вместо одного пробного → при восстановлении Guard все конкурентные запросы
разом бьют по ещё не оправившемуся сервису.

Каноническая семантика circuit breaker:
- в HALF_OPEN проходит РОВНО один probe, остальные получают False;
- probe успешен → CLOSED; probe неуспешен → сразу OPEN (окно ожидания
  перезапускается).
"""
import threading

from krepost.security.pipeline import CircuitBreaker


class TestHalfOpenSingleProbe:

    def test_only_one_probe_passes(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        cb.state = "HALF_OPEN"
        assert cb.can_execute() is True   # probe
        assert cb.can_execute() is False  # остальные — стоп
        assert cb.can_execute() is False

    def test_probe_failure_reopens_immediately(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is True   # OPEN→HALF_OPEN, это и есть probe
        assert cb.state == "HALF_OPEN"
        cb.record_failure()               # probe провалился
        assert cb.state == "OPEN"         # сразу OPEN, без накопления до threshold

    def test_probe_success_closes_and_allows(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        cb.state = "HALF_OPEN"
        assert cb.can_execute() is True
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.can_execute() is True   # после закрытия снова пускает всех

    def test_concurrent_probe_exactly_one(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        cb.state = "HALF_OPEN"
        results = []
        lock = threading.Lock()

        def worker():
            r = cb.can_execute()
            with lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sum(1 for r in results if r) == 1, \
            f"ожидали ровно 1 probe, прошло {sum(1 for r in results if r)}"
