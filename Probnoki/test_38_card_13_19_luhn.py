"""
Пробник #38 (P2 #10): маскирование карт длиной 13–19 цифр (Luhn), не только 16.

Regex ловил лишь 16-значный формат 4-4-4-4, хотя _validate_luhn уже рассчитан
на 13–19 цифр. Значит Amex(15) и 13/19-значные карты УТЕКАЛИ (fail-open PII).
Расширяем regex до 13–19 цифр с опциональными разделителями; Luhn по-прежнему
отсеивает случайные числа (нет ложных срабатываний). Порог ≥13 цифр исключает
телефон/ИНН/СНИЛС/паспорт (все ≤12 цифр или иной формат).
"""
import pytest

from krepost.security.pipeline import PIIMasker


class TestCard13to19:

    @pytest.fixture
    def masker(self):
        return PIIMasker()

    def test_amex_15_digits_masked(self, masker):
        # 378282246310005 — стандартный тестовый Amex, проходит Luhn
        text = "Карта Amex 378282246310005 к оплате"
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" in result
        assert "378282246310005" not in result

    def test_visa_13_digits_masked(self, masker):
        # 4222222222222 — тестовый 13-значный Visa, проходит Luhn
        text = "Старый Visa 4222222222222"
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" in result
        assert "4222222222222" not in result

    def test_amex_with_spaces_masked(self, masker):
        text = "Amex: 3782 822463 10005"
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" in result

    def test_16_digit_still_masked(self, masker):
        # регресс: прежний формат работает
        text = "Карта 4532015112830366"
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" in result

    def test_invalid_luhn_15_not_masked(self, masker):
        # 15 цифр, но Luhn не проходит — не карта
        text = "Число 123456789012345"
        result = masker.mask(text)
        assert "[CARD_HIDDEN]" not in result

    def test_phone_not_treated_as_card_leak(self, masker):
        # телефон (11 цифр) < 13 → не карта; но PII всё равно замаскирована
        text = "Звоните +7-495-123-4567"
        result = masker.mask(text)
        assert "123-4567" not in result  # цифры не утекли

    def test_short_numbers_untouched(self, masker):
        text = "В 2024 году было 150 событий"
        result = masker.mask(text)
        assert "2024" in result and "150" in result
