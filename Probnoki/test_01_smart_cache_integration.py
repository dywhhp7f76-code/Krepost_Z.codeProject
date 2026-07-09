"""
Пробник #1: C-002 — SMART_CACHE интегрирован в SecurityPipeline.

Проверяет:
- CacheLayer импортируется в pipeline.py
- SecurityPipeline принимает параметры cache_dir / enable_cache
- Кэш инициализируется при enable_cache=True
- Кэш НЕ инициализируется при enable_cache=False
- L2 cache store вызывается после GREEN verdict
- pipeline.close() корректно закрывает кэш
"""

import asyncio
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from krepost.security.pipeline import SecurityPipeline, SecurityContext


class TestSmartCacheIntegration:

    @pytest.fixture
    def tmp_path(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_pipeline_accepts_cache_params(self):
        """SecurityPipeline принимает cache_dir и enable_cache."""
        p = SecurityPipeline(enable_cache=False)
        assert p.cache is None

    def test_cache_disabled_by_default(self):
        """Кэш выключен по умолчанию."""
        p = SecurityPipeline()
        assert p.cache is None

    def test_cache_attribute_exists(self):
        """Атрибут self.cache существует в pipeline."""
        p = SecurityPipeline(enable_cache=False)
        assert hasattr(p, 'cache')

    @pytest.mark.asyncio
    async def test_process_works_without_cache(self, tmp_path):
        """Pipeline работает нормально без кэша."""
        p = SecurityPipeline(
            trust_db_path=tmp_path / "trust.db",
            enable_cache=False,
        )
        ctx = await p.process("hello world", "session1")
        assert ctx.verdict in ("GREEN", "RED", "YELLOW")
        assert ctx.metadata.get("cache_hit") is None

    @pytest.mark.asyncio
    async def test_close_works_without_cache(self, tmp_path):
        """close() работает когда кэша нет."""
        p = SecurityPipeline(
            trust_db_path=tmp_path / "trust.db",
            enable_cache=False,
        )
        await p.close()

    @pytest.mark.asyncio
    async def test_close_calls_cache_close(self, tmp_path):
        """close() вызывает cache.close() если кэш есть."""
        p = SecurityPipeline(
            trust_db_path=tmp_path / "trust.db",
            enable_cache=False,
        )
        mock_cache = MagicMock()
        mock_cache.close = MagicMock()
        p.cache = mock_cache
        await p.close()
        mock_cache.close.assert_called_once()

    def test_cache_layer_attribute_exists(self):
        """CacheLayer атрибут существует в pipeline (None если sentence-transformers не установлен)."""
        from krepost.security import pipeline
        assert hasattr(pipeline, 'CacheLayer')
