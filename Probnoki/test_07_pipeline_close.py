"""
Пробник #7: H-004 — pipeline.close() чистит cache и layer3.

Проверяет:
- close() вызывает cache.close() если кэш есть
- close() вызывает layer3.close() если layer3 есть
- close() не падает если cache=None
- close() не падает если layer3=None
- close() не падает если cache.close() выбрасывает ошибку
- close() не падает если layer3.close() выбрасывает ошибку
"""

import asyncio
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from krepost.security.pipeline import SecurityPipeline


class TestPipelineClose:

    @pytest.fixture
    def tmp_path(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    @pytest.mark.asyncio
    async def test_close_without_cache_or_layer3(self, tmp_path):
        """close() работает без cache и layer3."""
        p = SecurityPipeline(trust_db_path=tmp_path / "t.db")
        assert p.cache is None
        assert p.layer3 is None
        await p.close()

    @pytest.mark.asyncio
    async def test_close_calls_cache_close(self, tmp_path):
        """close() вызывает cache.close()."""
        p = SecurityPipeline(trust_db_path=tmp_path / "t.db")
        mock_cache = MagicMock()
        p.cache = mock_cache
        await p.close()
        mock_cache.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_calls_layer3_close(self, tmp_path):
        """close() вызывает layer3.close() если метод есть."""
        p = SecurityPipeline(trust_db_path=tmp_path / "t.db")
        mock_layer3 = MagicMock()
        mock_layer3.close = MagicMock()
        p.layer3 = mock_layer3
        await p.close()
        mock_layer3.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_survives_cache_error(self, tmp_path):
        """close() не падает если cache.close() бросает ошибку."""
        p = SecurityPipeline(trust_db_path=tmp_path / "t.db")
        mock_cache = MagicMock()
        mock_cache.close = MagicMock(side_effect=RuntimeError("DB locked"))
        p.cache = mock_cache
        await p.close()

    @pytest.mark.asyncio
    async def test_close_survives_layer3_error(self, tmp_path):
        """close() не падает если layer3.close() бросает ошибку."""
        p = SecurityPipeline(trust_db_path=tmp_path / "t.db")
        mock_layer3 = MagicMock()
        mock_layer3.close = MagicMock(side_effect=RuntimeError("Connection lost"))
        p.layer3 = mock_layer3
        await p.close()

    @pytest.mark.asyncio
    async def test_closing_flag_set(self, tmp_path):
        """close() устанавливает _closing = True."""
        p = SecurityPipeline(trust_db_path=tmp_path / "t.db")
        await p.close()
        assert p._closing is True
