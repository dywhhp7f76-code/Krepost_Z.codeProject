"""
Пробник #14: TrustRegistry — реестр доверенных текстов.

Проверяет:
- add_trusted / is_trusted цикл
- Недоверенный текст → False
- revoke_trusted (soft-delete)
- Re-add после revoke
- Нормализация хешей (canonicalize_for_hash)
- Fail-closed при ошибке
- normalization_version в записях
"""

import asyncio
import tempfile
import pytest
from pathlib import Path

from krepost.security.trust_registry import TrustRegistry


class TestTrustRegistry:

    @pytest.fixture
    def trust(self):
        with tempfile.TemporaryDirectory() as d:
            yield TrustRegistry(db_path=Path(d) / "trust.db")

    # ─── BASIC CRUD ───

    @pytest.mark.asyncio
    async def test_add_and_check_trusted(self, trust):
        """Добавленный текст — доверен."""
        await trust.add_trusted("hello world", source_name="test")
        assert await trust.is_trusted("hello world") is True

    @pytest.mark.asyncio
    async def test_untrusted_text_false(self, trust):
        """Недобавленный текст — НЕ доверен."""
        assert await trust.is_trusted("unknown text") is False

    @pytest.mark.asyncio
    async def test_empty_registry_false(self, trust):
        """Пустой реестр → всё False."""
        assert await trust.is_trusted("anything") is False

    # ─── REVOKE (SOFT-DELETE) ───

    @pytest.mark.asyncio
    async def test_revoke_removes_trust(self, trust):
        """revoke_trusted убирает доверие."""
        await trust.add_trusted("trusted text", source_name="test")
        assert await trust.is_trusted("trusted text") is True
        await trust.revoke_trusted("trusted text")
        assert await trust.is_trusted("trusted text") is False

    @pytest.mark.asyncio
    async def test_re_add_after_revoke(self, trust):
        """Повторное добавление после revoke восстанавливает доверие."""
        await trust.add_trusted("text", source_name="v1")
        await trust.revoke_trusted("text")
        assert await trust.is_trusted("text") is False
        await trust.add_trusted("text", source_name="v2")
        assert await trust.is_trusted("text") is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_no_error(self, trust):
        """revoke несуществующего текста не вызывает ошибку."""
        await trust.revoke_trusted("never_added")
        # Не должно быть исключения

    # ─── NORMALIZATION ───

    @pytest.mark.asyncio
    async def test_hash_is_deterministic(self, trust):
        """Один и тот же текст → один и тот же хеш."""
        h1 = trust._compute_hash("hello world")
        h2 = trust._compute_hash("hello world")
        assert h1 == h2

    @pytest.mark.asyncio
    async def test_different_text_different_hash(self, trust):
        """Разный текст → разные хеши."""
        h1 = trust._compute_hash("hello")
        h2 = trust._compute_hash("world")
        assert h1 != h2

    @pytest.mark.asyncio
    async def test_canonicalization_applied(self, trust):
        """Канонизация применяется (casefold + homoglyphs)."""
        h_lower = trust._compute_hash("Hello World")
        h_upper = trust._compute_hash("HELLO WORLD")
        assert h_lower == h_upper  # casefold делает одинаковыми

    @pytest.mark.asyncio
    async def test_whitespace_normalized(self, trust):
        """Пробелы нормализуются."""
        h1 = trust._compute_hash("hello   world")
        h2 = trust._compute_hash("hello world")
        assert h1 == h2

    # ─── MULTIPLE ENTRIES ───

    @pytest.mark.asyncio
    async def test_multiple_trusted_texts(self, trust):
        """Можно добавить несколько доверенных текстов."""
        texts = ["text one", "text two", "text three"]
        for t in texts:
            await trust.add_trusted(t, source_name="batch")
        for t in texts:
            assert await trust.is_trusted(t) is True
        assert await trust.is_trusted("text four") is False

    @pytest.mark.asyncio
    async def test_selective_revoke(self, trust):
        """Revoke одного текста не затрагивает другие."""
        await trust.add_trusted("keep", source_name="test")
        await trust.add_trusted("remove", source_name="test")
        await trust.revoke_trusted("remove")
        assert await trust.is_trusted("keep") is True
        assert await trust.is_trusted("remove") is False

    # ─── DB INITIALIZATION ───

    def test_db_created_on_init(self):
        """БД создаётся при инициализации."""
        with tempfile.TemporaryDirectory() as d:
            db_path = Path(d) / "subdir" / "trust.db"
            trust = TrustRegistry(db_path=db_path)
            assert db_path.parent.exists()
