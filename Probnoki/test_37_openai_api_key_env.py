"""
Пробник #37 (P2 #16): api_key для OpenAI-совместимого стека берётся из env.

Хардкод api_key="lm-studio" молча даёт 401 на реальном OpenAI-совместимом
сервере с авторизацией. Резолвим ключ из KREPOST_OPENAI_API_KEY; явный
аргумент имеет приоритет; фолбэк "lm-studio" для локального LM Studio.
"""
from krepost.orchestration.factory import _resolve_openai_api_key


class TestResolveApiKey:

    def test_explicit_wins(self, monkeypatch):
        monkeypatch.setenv("KREPOST_OPENAI_API_KEY", "from-env")
        assert _resolve_openai_api_key("explicit") == "explicit"

    def test_env_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("KREPOST_OPENAI_API_KEY", "from-env")
        assert _resolve_openai_api_key(None) == "from-env"

    def test_fallback_local_when_nothing(self, monkeypatch):
        monkeypatch.delenv("KREPOST_OPENAI_API_KEY", raising=False)
        assert _resolve_openai_api_key(None) == "lm-studio"
