"""
Пробник #46 (Т9): temp=0 в GuardClassifier._call_guard.

redteam/2026-06-28 (judge non-determinism war): guard гонялся с дефолтной
температурой ollama (~0.8) → разброс вердиктов. Фикс: проброс
options={"temperature": 0} в guard_client.chat.

ЖЁСТКИЙ СКОП: только temp=0. Majority vote / instability rate — T9-extended.
temp=0 снижает разброс, но НЕ гарантирует полный детерминизм на LLM
(батчинг/железо сохраняют остаточный шум).
"""
import asyncio
import json

from krepost.security.pipeline import GuardClassifier


class _CapturingClient:
    """Мок guard-клиента, фиксирующий kwargs вызова chat()."""

    def __init__(self, verdict="GREEN", confidence=0.9):
        self.calls = []
        self._response = {"message": {"content": json.dumps(
            {"status": verdict, "confidence": confidence, "reason": "test"}
        )}}

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class TestTemperatureZeroPassed:

    def test_options_temperature_zero_in_kwargs(self):
        client = _CapturingClient()
        guard = GuardClassifier(client, prompt_template="input")
        asyncio.run(guard.classify("some input text"))
        assert len(client.calls) == 1
        kwargs = client.calls[0]
        assert "options" in kwargs
        assert kwargs["options"].get("temperature") == 0

    def test_temperature_zero_on_every_call(self):
        client = _CapturingClient()
        guard = GuardClassifier(client, prompt_template="input")
        for _ in range(5):
            asyncio.run(guard.classify("repeatable input"))
        for call in client.calls:
            assert call["options"]["temperature"] == 0

    def test_output_guard_also_gets_temp_zero(self):
        client = _CapturingClient()
        guard = GuardClassifier(client, prompt_template="output")
        asyncio.run(guard.classify("model output"))
        assert client.calls[0]["options"]["temperature"] == 0


class TestQwen3GuardNativeParser:
    """Парсер нативного формата Qwen3Guard-Gen-4B.

    Модель игнорирует наш JSON-промпт и выводит:
      Safety: Safe|Controversial|Unsafe
      Categories: <список>
    """

    def test_safe_to_green(self):
        guard = GuardClassifier(None)
        v, conf, reason = guard._parse_response(
            {"message": {"content": "Safety: Safe\nCategories: None"}}
        )
        assert v == "GREEN"
        assert "none" in reason.lower()

    def test_unsafe_to_red(self):
        guard = GuardClassifier(None)
        v, conf, reason = guard._parse_response(
            {"message": {"content": "Safety: Unsafe\nCategories: Jailbreak"}}
        )
        assert v == "RED"
        assert "jailbreak" in reason.lower()

    def test_controversial_to_yellow(self):
        guard = GuardClassifier(None)
        v, conf, reason = guard._parse_response(
            {"message": {"content": "Safety: Controversial\nCategories: Jailbreak"}}
        )
        assert v == "YELLOW"

    def test_unknown_safety_fail_closed(self):
        guard = GuardClassifier(None)
        v, conf, reason = guard._parse_response(
            {"message": {"content": "Safety: Explosive\nCategories: Weird"}}
        )
        assert v == "RED"
        assert "unknown_safety" in reason.lower()

    def test_json_still_works(self):
        """Старый JSON-путь не сломан для моделей что слушаются промпт."""
        guard = GuardClassifier(None)
        v, conf, reason = guard._parse_response(
            {"message": {"content": '{"status":"GREEN","reason":"ok","confidence":0.9}'}}
        )
        assert v == "GREEN"
        assert conf == 0.9

    def test_garbage_fail_closed(self):
        guard = GuardClassifier(None)
        v, conf, reason = guard._parse_response(
            {"message": {"content": "I cannot help with that."}}
        )
        assert v == "RED"
        assert "fail_closed" in reason
