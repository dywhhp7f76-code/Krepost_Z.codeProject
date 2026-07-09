"""
Пробник #15: normalize.py — функции нормализации.

Проверяет:
- canonicalize_for_hash(): полная каноникализация
- normalize_for_scanning(): для сканирования правилами
- Zero-width символы удаляются
- Casefold работает
- Homoglyph mapping (кириллица→латиница, цифры→буквы)
- NFKC нормализация
- soft=True сохраняет кириллицу
- Пустая строка
"""

import pytest

from krepost.security.normalize import (
    canonicalize_for_hash,
    normalize_for_scanning,
    NORMALIZATION_VERSION,
    _HOMOGLYPH_MAP,
    _ZERO_WIDTH,
)


class TestCanonicalizeForHash:

    def test_empty_string(self):
        """Пустая строка → пустая строка."""
        assert canonicalize_for_hash("") == ""

    def test_casefold(self):
        """Casefold приводит к нижнему регистру."""
        result = canonicalize_for_hash("HELLO World")
        assert "H" not in result
        assert "W" not in result

    def test_whitespace_collapse(self):
        """Множественные пробелы → один."""
        result = canonicalize_for_hash("hello   world")
        assert "   " not in result
        assert result == "hello world"

    def test_strip(self):
        """Пробелы по краям удаляются."""
        result = canonicalize_for_hash("  hello  ")
        assert result == "hello"

    def test_zero_width_removal(self):
        """Zero-width символы удаляются."""
        text = "he​llo"  # zero-width space
        result = canonicalize_for_hash(text)
        assert "​" not in result
        assert "hello" in result

    def test_bom_removed(self):
        """BOM удаляется."""
        text = "﻿hello"
        result = canonicalize_for_hash(text)
        assert "﻿" not in result

    def test_bidi_marks_removed(self):
        """BiDi marks удаляются."""
        text = "hel‎lo"  # left-to-right mark
        result = canonicalize_for_hash(text)
        assert "‎" not in result

    def test_nbsp_removed(self):
        """NBSP (non-breaking space) удаляется."""
        text = "hello world"
        result = canonicalize_for_hash(text)
        assert " " not in result

    def test_nfkc_normalization(self):
        """NFKC нормализация (ﬁ → fi)."""
        text = "ﬁle"  # fi-ligature
        result = canonicalize_for_hash(text)
        assert "fi" in result or "file" in result

    def test_cyrillic_homoglyphs(self):
        """Кириллические гомоглифы → латиница."""
        result = canonicalize_for_hash("а")  # Cyrillic а
        assert result == "a"  # Latin a

    def test_digit_homoglyphs(self):
        """Цифры-гомоглифы: 0→o, 1→i, 5→s."""
        assert "o" in canonicalize_for_hash("0")
        assert "i" in canonicalize_for_hash("1")
        assert "s" in canonicalize_for_hash("5")

    def test_deterministic(self):
        """Канонизация детерминистична."""
        text = "Hello World 123"
        r1 = canonicalize_for_hash(text)
        r2 = canonicalize_for_hash(text)
        assert r1 == r2

    def test_pipe_to_i(self):
        """|→i."""
        result = canonicalize_for_hash("|")
        assert result == "i"


class TestNormalizeForScanning:

    def test_empty_string(self):
        """Пустая строка → пустая."""
        assert normalize_for_scanning("") == ""

    def test_casefold(self):
        """Casefold работает."""
        result = normalize_for_scanning("HELLO")
        assert result == "hello"

    def test_soft_mode_preserves_homoglyphs(self):
        """soft=True НЕ применяет HOMOGLYPH_MAP."""
        text = "тест 0 1 5"
        result_soft = normalize_for_scanning(text, soft=True)
        result_hard = normalize_for_scanning(text, soft=False)
        assert "0" in result_soft  # цифры сохранены в soft
        assert "0" not in result_hard  # цифры заменены в hard

    def test_hard_mode_replaces_digits(self):
        """soft=False заменяет цифры."""
        result = normalize_for_scanning("0 1 5", soft=False)
        assert "0" not in result
        assert "1" not in result
        assert "5" not in result

    def test_zero_width_removed_in_both_modes(self):
        """Zero-width удаляется в обоих режимах."""
        text = "he​llo"
        assert "​" not in normalize_for_scanning(text, soft=True)
        assert "​" not in normalize_for_scanning(text, soft=False)


class TestNormalizationVersion:

    def test_version_exists(self):
        """NORMALIZATION_VERSION существует и непустая."""
        assert NORMALIZATION_VERSION is not None
        assert len(NORMALIZATION_VERSION) > 0

    def test_version_format(self):
        """NORMALIZATION_VERSION в формате X.Y.Z."""
        parts = NORMALIZATION_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()


class TestHomoglyphMap:

    def test_map_exists(self):
        """_HOMOGLYPH_MAP существует."""
        assert _HOMOGLYPH_MAP is not None

    def test_cyrillic_a_mapped(self):
        """Кириллическая 'а' маппится."""
        result = "а".translate(_HOMOGLYPH_MAP)
        assert result == "a"

    def test_greek_alpha_mapped(self):
        """Греческая α маппится."""
        result = "α".translate(_HOMOGLYPH_MAP)
        assert result == "a"


class TestZeroWidthMap:

    def test_zero_width_space(self):
        """Zero-width space в карте."""
        assert 0x200b in _ZERO_WIDTH

    def test_bom_in_map(self):
        """BOM в карте."""
        assert 0xfeff in _ZERO_WIDTH

    def test_nbsp_in_map(self):
        """NBSP в карте."""
        assert 0x00a0 in _ZERO_WIDTH
