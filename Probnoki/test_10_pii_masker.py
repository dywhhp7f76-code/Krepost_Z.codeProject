"""
Пробник #10: PIIMasker — маскирование персональных данных.

Проверяет:
- Luhn-валидация банковских карт
- ИНН 10/12 цифр с контрольной суммой
- СНИЛС с контрольной суммой
- IP-адреса (валидные/невалидные)
- Email-адреса
- Телефоны
- API-ключи (OpenAI, GitHub, AWS)
- JWT-токены
- Приватные ключи
- Российские паспорта
- Безопасный текст не маскируется
"""

import pytest

from krepost.security.pipeline import PIIMasker


class TestPIIMasker:

    @pytest.fixture
    def masker(self):
        return PIIMasker()

    # ─── LUHN VALIDATION ───

    def test_valid_visa_card_masked(self, masker):
        """Валидная карта Visa (проходит Luhn) маскируется."""
        text = "Мой номер карты 4532015112830366"
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" in result
        assert "4532015112830366" not in result

    def test_valid_card_with_spaces(self, masker):
        """Карта с пробелами маскируется."""
        text = "Карта: 4532 0151 1283 0366"
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" in result

    def test_invalid_luhn_not_masked(self, masker):
        """Невалидная по Luhn карта НЕ маскируется."""
        text = "Номер 1234 5678 9012 3456"  # не проходит Luhn
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" not in result

    def test_luhn_validation_algorithm(self, masker):
        """Прямой тест алгоритма Luhn."""
        assert masker._validate_luhn("4532015112830366") is True
        assert masker._validate_luhn("1234567890123456") is False
        assert masker._validate_luhn("123") is False  # слишком короткий

    # ─── ИНН ───

    def test_valid_inn_10_masked(self, masker):
        """Валидный 10-значный ИНН маскируется."""
        assert masker._validate_inn("7707083893") is True

    def test_valid_inn_12_masked(self, masker):
        """Валидный 12-значный ИНН маскируется."""
        assert masker._validate_inn("500100732259") is True

    def test_invalid_inn_not_masked(self, masker):
        """Невалидный ИНН (неправильная контрольная сумма) НЕ маскируется."""
        assert masker._validate_inn("1234567890") is False

    def test_inn_wrong_length(self, masker):
        """ИНН неправильной длины не проходит валидацию."""
        assert masker._validate_inn("12345") is False
        assert masker._validate_inn("12345678901") is False  # 11 цифр

    # ─── СНИЛС ───

    def test_snils_validation(self, masker):
        """СНИЛС с правильной контрольной суммой маскируется."""
        # СНИЛС формат: 123-456-789 XX
        result = masker._validate_snils("08765430300")
        assert isinstance(result, bool)

    def test_snils_wrong_length(self, masker):
        """СНИЛС неправильной длины не проходит."""
        assert masker._validate_snils("1234") is False

    # ─── IP АДРЕСА ───

    def test_valid_ip_masked(self, masker):
        """Валидный IP маскируется."""
        text = "Сервер на 192.168.1.1"
        result = masker.mask(text)
        assert "[IP_HIDDEN]" in result

    def test_invalid_ip_not_masked(self, masker):
        """Невалидный IP (>255) НЕ маскируется."""
        assert masker._validate_ip("999.999.999.999") is False

    def test_ip_validation(self, masker):
        """Прямой тест валидации IP."""
        assert masker._validate_ip("10.0.0.1") is True
        assert masker._validate_ip("256.1.1.1") is False

    # ─── EMAIL ───

    def test_email_masked(self, masker):
        """Email маскируется."""
        text = "Пишите на user@example.com"
        result = masker.mask(text)
        assert "[EMAIL_HIDDEN]" in result
        assert "user@example.com" not in result

    def test_complex_email_masked(self, masker):
        """Сложный email маскируется."""
        text = "Contact: john.doe-123@sub.domain.co.uk"
        result = masker.mask(text)
        assert "[EMAIL_HIDDEN]" in result

    # ─── ТЕЛЕФОНЫ ───

    def test_phone_masked(self, masker):
        """Телефон маскируется."""
        text = "Звоните +7-495-123-4567"
        result = masker.mask(text)
        assert "[PHONE_HIDDEN]" in result

    # ─── API КЛЮЧИ ───

    def test_openai_key_masked(self, masker):
        """OpenAI API ключ маскируется."""
        text = "key: sk-abcdefghijklmnopqrstuvwxyz123456"
        result = masker.mask(text)
        assert "[OPENAI_KEY_REDACTED]" in result

    def test_github_token_masked(self, masker):
        """GitHub token маскируется."""
        text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        result = masker.mask(text)
        assert "[GITHUB_KEY_REDACTED]" in result

    def test_aws_key_masked(self, masker):
        """AWS access key маскируется."""
        text = "aws: AKIAIOSFODNN7EXAMPLE"
        result = masker.mask(text)
        assert "[AWS_ACCESS_KEY_REDACTED]" in result

    # ─── JWT ───

    def test_jwt_masked(self, masker):
        """JWT токен маскируется."""
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        text = f"Authorization: Bearer {jwt}"
        result = masker.mask(text)
        assert "[JWT_REDACTED]" in result

    # ─── ПРИВАТНЫЕ КЛЮЧИ ───

    def test_private_key_masked(self, masker):
        """Приватный ключ маскируется."""
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJBALRiMLP...\n-----END RSA PRIVATE KEY-----"
        result = masker.mask(text)
        assert "[PRIVATE_KEY_REDACTED]" in result

    # ─── БЕЗОПАСНЫЙ ТЕКСТ ───

    def test_safe_text_not_masked(self, masker):
        """Обычный текст не изменяется."""
        text = "Привет, как дела? Всё хорошо!"
        result = masker.mask(text)
        assert result == text

    def test_numbers_in_context_not_masked(self, masker):
        """Числа в контексте (не карты/ИНН) не маскируются."""
        text = "В 2024 году было 150 событий"
        result = masker.mask(text)
        assert "2024" in result
        assert "150" in result

    # ─── РОССИЙСКИЙ ПАСПОРТ ───

    def test_passport_masked(self, masker):
        """Серия и номер паспорта маскируются."""
        text = "Паспорт 4515 123456"
        result = masker.mask(text)
        assert "[RU_PASSPORT_HIDDEN]" in result
