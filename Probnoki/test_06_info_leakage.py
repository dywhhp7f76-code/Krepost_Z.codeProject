"""
Пробник #6: SEC-004 — Information Leakage через ошибки.

Проверяет:
- GuardClassifier.classify() НЕ раскрывает exception details в reason
- connection_error возвращает generic "connection_error_fail_closed"
- unexpected_error возвращает generic "unexpected_error_fail_closed"
- FewShotMatcher.match() возвращает "fewshot_error_fail_closed"
- Pipeline process() возвращает "pipeline_error_fail_closed"
- Никаких IP-адресов, путей или стектрейсов в reason
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from krepost.security.pipeline import (
    GuardClassifier,
    FewShotMatcher,
    CircuitBreaker,
)


class TestInfoLeakageGuard:

    @pytest.mark.asyncio
    async def test_connection_error_no_details(self):
        """ConnectionError НЕ раскрывает детали в reason."""
        client = MagicMock()
        client.chat = MagicMock(side_effect=ConnectionError("refused at 192.168.1.100:11434"))
        gc = GuardClassifier(client, max_retries=0)
        verdict, conf, reason = await gc.classify("test")
        assert verdict == "RED"
        assert reason == "connection_error_fail_closed"
        assert "192.168" not in reason
        assert "11434" not in reason

    @pytest.mark.asyncio
    async def test_os_error_no_details(self):
        """OSError НЕ раскрывает детали."""
        client = MagicMock()
        client.chat = MagicMock(side_effect=OSError("No route to host /etc/secret"))
        gc = GuardClassifier(client, max_retries=0)
        verdict, conf, reason = await gc.classify("test")
        assert verdict == "RED"
        assert reason == "connection_error_fail_closed"
        assert "/etc" not in reason

    @pytest.mark.asyncio
    async def test_unexpected_error_no_details(self):
        """Неожиданные ошибки НЕ раскрывают стектрейс."""
        client = MagicMock()
        client.chat = MagicMock(side_effect=ValueError("internal state: model_weights_path=/opt/models"))
        gc = GuardClassifier(client, max_retries=0)
        verdict, conf, reason = await gc.classify("test")
        assert verdict == "RED"
        assert reason == "unexpected_error_fail_closed"
        assert "/opt/models" not in reason

    @pytest.mark.asyncio
    async def test_timeout_no_details(self):
        """Timeout не раскрывает ничего лишнего."""
        client = MagicMock()

        async def slow_chat(**kwargs):
            await asyncio.sleep(100)
        client.chat = slow_chat
        gc = GuardClassifier(client, timeout=0.01, max_retries=0)
        verdict, conf, reason = await gc.classify("test")
        assert verdict == "RED"
        assert reason == "timeout_fail_closed"


class TestInfoLeakageFewShot:

    @pytest.mark.asyncio
    async def test_fewshot_error_no_details(self):
        """FewShotMatcher ошибка НЕ раскрывает детали."""
        embedder = MagicMock()
        embedder.encode = MagicMock(side_effect=RuntimeError("GPU memory at /dev/nvidia0"))
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert reason == "fewshot_error_fail_closed"
        assert "GPU" not in reason
        assert "/dev" not in reason
