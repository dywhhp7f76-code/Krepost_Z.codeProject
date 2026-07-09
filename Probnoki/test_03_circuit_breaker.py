"""
Пробник #3: C-004 — CircuitBreaker сброс failure_count при HALF_OPEN.

Проверяет:
- failure_count сбрасывается при переходе OPEN → HALF_OPEN
- Одна ошибка в HALF_OPEN не наследует старый счётчик
- Успешный запрос в HALF_OPEN закрывает circuit
- Полный цикл: CLOSED → OPEN → HALF_OPEN → CLOSED
- Полный цикл: CLOSED → OPEN → HALF_OPEN → OPEN (при ошибке)
"""

import pytest

from krepost.security.pipeline import CircuitBreaker


class TestCircuitBreakerHalfOpenReset:

    def test_failure_count_reset_on_half_open(self):
        """failure_count == 0 при переходе в HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.failure_count == 3
        assert cb.can_execute() is True
        assert cb.state == "HALF_OPEN"
        assert cb.failure_count == 0

    def test_single_failure_in_half_open_goes_back_to_open(self):
        """Одна ошибка в HALF_OPEN -> сразу OPEN (BUG-02: канон circuit breaker;
        раньше код накапливал до threshold и ассерт был ослаблен)."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        for _ in range(3):
            cb.record_failure()
        cb.can_execute()
        assert cb.failure_count == 0
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == "OPEN"

    def test_success_in_half_open_closes(self):
        """Успех в HALF_OPEN → CLOSED."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        for _ in range(3):
            cb.record_failure()
        cb.can_execute()
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_full_cycle_to_closed(self):
        """CLOSED → OPEN → HALF_OPEN → CLOSED."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
        assert cb.state == "CLOSED"
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        cb.can_execute()
        assert cb.state == "HALF_OPEN"
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.can_execute() is True

    def test_full_cycle_back_to_open(self):
        """CLOSED → OPEN → HALF_OPEN → OPEN (при threshold=2 и двух ошибках)."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        cb.can_execute()
        assert cb.state == "HALF_OPEN"
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

    def test_no_infinite_accumulation(self):
        """failure_count не накапливается бесконечно через циклы."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        for cycle in range(5):
            for _ in range(3):
                cb.record_failure()
            assert cb.state == "OPEN"
            cb.can_execute()
            assert cb.failure_count == 0
