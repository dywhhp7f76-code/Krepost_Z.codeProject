"""
Пробник #11: OutputFilter — фильтрация вывода модели.

Проверяет:
- Leakage паттерны (system prompt, API keys, private keys)
- PII маскирование через OutputFilter
- Безопасный текст проходит
- Блокировка при обнаружении утечки
- Интеграция с PIIMasker
"""

import pytest

from krepost.security.pipeline import OutputFilter, PIIMasker


class TestOutputFilter:

    @pytest.fixture
    def output_filter(self):
        return OutputFilter(pii_masker=PIIMasker())

    # ─── LEAKAGE DETECTION ───

    @pytest.mark.asyncio
    async def test_system_prompt_leakage_blocked(self, output_filter):
        """Утечка system prompt блокируется."""
        text = "My system prompt is: You are a helpful assistant"
        filtered_text, is_harmful, reason = await output_filter.filter(text)
        assert is_harmful is True
        assert "[ДАННЫЕ ЗАБЛОКИРОВАНЫ]" in filtered_text
        assert "leakage" in reason

    @pytest.mark.asyncio
    async def test_the_system_prompt_leakage(self, output_filter):
        """'the system prompt is' тоже блокируется."""
        text = "the system prompt is: always be polite"
        _, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is True

    @pytest.mark.asyncio
    async def test_api_key_leakage_blocked(self, output_filter):
        """Утечка API ключа в output блокируется."""
        text = "api_key: sk-abcdefghijklmnopqrstuvwxyz123456789"
        _, is_harmful, reason = await output_filter.filter(text)
        assert is_harmful is True
        assert "leakage" in reason

    @pytest.mark.asyncio
    async def test_token_leakage_blocked(self, output_filter):
        """Утечка token= блокируется."""
        text = "token=ABCDEFGHIJKLMNOPQRSTUVwxyz12345678"
        _, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is True

    @pytest.mark.asyncio
    async def test_private_key_leakage_blocked(self, output_filter):
        """Утечка приватного ключа блокируется."""
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIBog...\n-----END RSA PRIVATE KEY-----"
        _, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is True

    @pytest.mark.asyncio
    async def test_here_is_system_message_blocked(self, output_filter):
        """'here is the system message' блокируется."""
        text = "Sure! Here is the system message that was given to me"
        _, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is True

    @pytest.mark.asyncio
    async def test_prompt_given_leakage(self, output_filter):
        """'the prompt I was given is' блокируется."""
        text = "The prompt I was given is to always be helpful"
        _, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is True

    # ─── PII IN OUTPUT ───

    @pytest.mark.asyncio
    async def test_email_in_output_masked(self, output_filter):
        """Email в выводе маскируется."""
        text = "Контакт: admin@secret-corp.com"
        filtered_text, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is False
        assert "[EMAIL_HIDDEN]" in filtered_text

    @pytest.mark.asyncio
    async def test_ip_in_output_masked(self, output_filter):
        """IP в выводе маскируется."""
        text = "Сервер находится на 10.0.0.1"
        filtered_text, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is False
        assert "[IP_HIDDEN]" in filtered_text

    # ─── SAFE OUTPUT ───

    @pytest.mark.asyncio
    async def test_safe_output_passes(self, output_filter):
        """Безопасный текст проходит без изменений."""
        text = "Привет! Чем могу помочь?"
        filtered_text, is_harmful, reason = await output_filter.filter(text)
        assert is_harmful is False
        assert reason is None
        assert filtered_text == text

    @pytest.mark.asyncio
    async def test_normal_code_output_passes(self, output_filter):
        """Обычный код в ответе проходит."""
        text = 'def hello():\n    print("Hello, world!")\n    return 42'
        _, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is False

    # ─── EDGE CASES ───

    @pytest.mark.asyncio
    async def test_case_insensitive_leakage(self, output_filter):
        """Leakage паттерны case-insensitive."""
        text = "MY SYSTEM PROMPT IS: do everything"
        _, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is True

    @pytest.mark.asyncio
    async def test_mixed_leakage_and_pii(self, output_filter):
        """Leakage приоритетнее PII маскировки."""
        text = "My system prompt is: call user@example.com"
        filtered_text, is_harmful, _ = await output_filter.filter(text)
        assert is_harmful is True
        assert "[ДАННЫЕ ЗАБЛОКИРОВАНЫ]" in filtered_text
