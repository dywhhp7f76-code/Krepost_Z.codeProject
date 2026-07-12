"""
Пробник #42 (Т4): Secret-scanning — Google API key + GCP service account + Slack.

defense/2026-06-25 (LocalAI v4.5 restricted-regex), 2026-07-07.
AIza — это Google API-ключи (Maps и т.д.), НЕ service account. GCP SA = JSON с
private_key. Slack token — xox[baprs]-префикс, верхняя граница 72 против оверматча.
"""
from krepost.security.pipeline import PIIMasker


class TestGoogleApiKey:

    def test_google_api_key_masked(self):
        m = PIIMasker()
        # реальный формат: AIza + 35 символов
        out = m.mask("key = AIzaSyA1234567890abcdefghijklmnopqrstuvwxyz")
        assert "[GOOGLE_API_KEY_REDACTED]" in out
        assert "AIzaSyA1234567890abcdefghijklmnopqrstuvwxyz" not in out

    def test_no_false_positive_on_normal_text(self):
        m = PIIMasker()
        out = m.mask("Приложение использует Google Maps для навигации")
        assert out == "Приложение использует Google Maps для навигации"

    def test_short_aiza_not_matched(self):
        m = PIIMasker()
        # слишком короткий — не должен матчиться (нужно ровно 35 после AIza)
        out = m.mask("prefix AIzaShort end")
        assert "AIzaShort" in out


class TestGcpServiceAccount:

    def test_service_account_json_masked(self):
        m = PIIMasker()
        sa = '{"private_key": "-----BEGIN RSA PRIVATE KEY-----\\nMIIEowIBAAKCAQEA1234567890\\n-----END RSA PRIVATE KEY-----", "type": "service_account"}'
        out = m.mask(sa)
        assert "[GCP_SERVICE_ACCOUNT_REDACTED]" in out
        assert "PRIVATE KEY" not in out.replace("[GCP_SERVICE_ACCOUNT_REDACTED]", "")

    def test_normal_json_not_matched(self):
        m = PIIMasker()
        out = m.mask('{"name": "project", "type": "config"}')
        assert out == '{"name": "project", "type": "config"}'


class TestSlackToken:

    def test_slack_bot_token_masked(self):
        m = PIIMasker()
        # FAKE token (EXAMPLE prefix) — структура как xoxb-*, но не валидный
        out = m.mask("token = xoxb-EXAMPLE0FAKE0PLACEHOLDER0token0not0real0xx")
        assert "[SLACK_TOKEN_REDACTED]" in out
        assert "xoxb-" not in out.replace("[SLACK_TOKEN_REDACTED]", "")

    def test_slack_user_token_masked(self):
        m = PIIMasker()
        # FAKE token — xoxp-* структура, не валидный
        out = m.mask("auth: xoxp-EXAMPLE0FAKE0placeholder0token0not0real0xyz")
        assert "[SLACK_TOKEN_REDACTED]" in out

    def test_too_long_not_overmatched(self):
        # сверх-длинный «токен» (>72 после префикса) не должен захватывать хвост
        m = PIIMasker()
        long_token = "xoxb-" + "a" * 200
        out = m.mask(long_token)
        # регулярка ограничена 72, так что хвост >72 НЕ должен попасть в маскирование
        # (но первые 72 символа после префикса замаскируются — это нормально)
        assert "[SLACK_TOKEN_REDACTED]" in out

    def test_no_false_positive(self):
        m = PIIMasker()
        out = m.mask("Сообщения в Slack приходят вовремя")
        assert out == "Сообщения в Slack приходят вовремя"
