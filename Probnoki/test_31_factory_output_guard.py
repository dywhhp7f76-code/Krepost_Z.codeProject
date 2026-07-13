"""
Пробник #31 (обновлён): семантический output-guard ОТКЛЮЧЕН, regex-only Layer 4.

ИСТОРИЯ: изначально (BUG-06) пробник проверял что output_guard ВКЛЮЧЕН в обеих
фабриках. Это оказалось ошибкой архитектуры: Qwen3Guard заточен под классификацию
ВХОДОВ (injection-detection); на выходах сваливается в чат-режим → parse_error →
fail-closed блокирует benign. Для air-gapped локалки модерация собственных
ответов не нужна (получатель = оператор). output-guard удалён, Layer 4 теперь
regex-only (PII/leak/secret).

Проверяем:
1. Структурно: обе фабрики дают pipeline БЕЗ output_guard (None).
2. Pipeline с output_guard_client → warning, но не падает (обратная совместимость).
3. Layer 4 regex работает: leak-паттерн блокируется, benign проходит.
4. PII-маскинг работает: карта/email замаскированы на выходе.
"""
import asyncio
import warnings

import pytest

from krepost.orchestration.factory import (build_ollama_orchestrator,
                                            build_ollama_pipeline,
                                            build_openai_pipeline)
from krepost.security.pipeline import SecurityPipeline, SecurityContext

MAIN_MODEL = "qwen3.6:27b"


class _DummyClient:
    """sync-клиент для guard (input → GREEN); main не вызывается в этих тестах."""
    def chat(self, model=None, messages=None, format=None, tools=None, **kwargs):
        return {"message": {"content":
                '{"status":"GREEN","reason":"benign","confidence":0.9}'}}


class TestFactoriesNoOutputGuard:
    """Фабрики НЕ должны собирать семантический output-guard."""

    def test_ollama_pipeline_has_no_output_guard(self, tmp_path):
        pipe, _ = build_ollama_pipeline(
            client=_DummyClient(), trust_db_path=tmp_path / "t.db")
        # OutputFilter больше не имеет атрибута output_guard
        assert not hasattr(pipe.layer4, "output_guard") or \
               getattr(pipe.layer4, "output_guard", None) is None

    def test_openai_pipeline_has_no_output_guard(self, tmp_path):
        pipe, _ = build_openai_pipeline(
            transport=object(), trust_db_path=tmp_path / "t.db")
        assert not hasattr(pipe.layer4, "output_guard") or \
               getattr(pipe.layer4, "output_guard", None) is None

    def test_output_guard_client_ignored_gracefully(self, tmp_path):
        """Передача output_guard_client не валит — pipeline собирается,
        Layer 4 работает regex-only. (warning логируется через loguru,
        отдельно не проверяем — главное что нет исключения и guard=None)."""
        pipe = SecurityPipeline(
            guard_client=None,
            output_guard_client=_DummyClient(),  # должно быть проигнорировано
            trust_db_path=tmp_path / "t.db",
        )
        # pipeline собрался без исключения, Layer 4 — без output_guard
        assert not hasattr(pipe.layer4, "output_guard") or \
               getattr(pipe.layer4, "output_guard", None) is None


class TestLayer4RegexStillWorks:
    """Layer 4 regex-only: leak-паттерны блокируют, benign проходит."""

    @pytest.mark.asyncio
    async def test_leak_pattern_blocked(self, tmp_path):
        pipe = SecurityPipeline(guard_client=None, trust_db_path=tmp_path / "t.db")
        ctx = SecurityContext(session_id="s1", user_input="q",
                              ai_output="my system prompt is: SECRET12345678901234567890")
        out = await pipe.process_output(ctx)
        assert out.is_compromised
        assert out.violation_layer and "Layer4" in out.violation_layer

    @pytest.mark.asyncio
    async def test_benign_output_passes(self, tmp_path):
        pipe = SecurityPipeline(guard_client=None, trust_db_path=tmp_path / "t.db")
        ctx = SecurityContext(session_id="s1", user_input="q",
                              ai_output="The capital of France is Paris.")
        out = await pipe.process_output(ctx)
        assert not out.is_compromised
        assert out.verdict == "GREEN"

    @pytest.mark.asyncio
    async def test_pii_masked_in_output(self, tmp_path):
        pipe = SecurityPipeline(guard_client=None, trust_db_path=tmp_path / "t.db")
        ctx = SecurityContext(session_id="s1", user_input="q",
                              ai_output="my card is 4111111111111111 and email john@example.com")
        out = await pipe.process_output(ctx)
        # не blocked, но PII замаскированы в ai_output
        assert not out.is_compromised
        assert "[CARD_HIDDEN]" in out.ai_output
        assert "[EMAIL_HIDDEN]" in out.ai_output
        assert pipe.metrics["pii_redactions"] >= 1

    @pytest.mark.asyncio
    async def test_secret_redacted_in_output(self, tmp_path):
        pipe = SecurityPipeline(guard_client=None, trust_db_path=tmp_path / "t.db")
        ctx = SecurityContext(session_id="s1", user_input="q",
                              ai_output="the key is sk-" + "a" * 40)
        out = await pipe.process_output(ctx)
        assert not out.is_compromised
        assert pipe.metrics["secret_redactions"] >= 1
