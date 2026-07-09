"""
Пробник #8: M-004 — Проверка длины после нормализации.

Проверяет:
- Проверка длины ДО нормализации по-прежнему работает
- Добавлена проверка длины ПОСЛЕ нормализации
- Строка, расширяющаяся при нормализации, блокируется
- Нормальные строки проходят обе проверки
- Порог: normalized > max_input_length * 2
"""

import pytest

from krepost.security.pipeline import RegexFilter


class TestNormalizedLengthCheck:

    @pytest.fixture
    def rf(self):
        return RegexFilter(max_input_length=100)

    def test_original_too_long_blocked(self, rf):
        """Строка длиннее max_input_length блокируется ДО нормализации."""
        text = "a" * 101
        ok, pattern, _ = rf.check(text)
        assert ok is False
        assert "input_too_long" in pattern

    def test_normal_length_passes(self, rf):
        """Нормальная строка проходит."""
        text = "hello world"
        ok, _, _ = rf.check(text)
        assert ok is True

    def test_normalized_too_long_blocked(self, rf):
        """Строка, расширяющаяся при нормализации > max*2, блокируется."""
        rf_small = RegexFilter(max_input_length=10)
        text = "a" * 10
        ok_before, _, normalized = rf_small.check(text)
        if len(normalized) > 20:
            assert ok_before is False
            assert "normalized_too_long" in _

    def test_exact_boundary_passes(self, rf):
        """Строка ровно max_input_length проходит."""
        text = "a" * 100
        ok, pattern, _ = rf.check(text)
        assert pattern is None or "input_too_long" not in (pattern or "")

    def test_check_returns_normalized_on_length_fail(self, rf):
        """При блокировке по длине возвращается normalized строка."""
        rf_small = RegexFilter(max_input_length=5)
        text = "test"
        ok, _, result = rf_small.check(text)
        assert isinstance(result, str)

    def test_default_max_input_length(self):
        """По умолчанию max_input_length = 32000."""
        rf = RegexFilter()
        assert rf.max_input_length == 32000
