"""
Пробник #12: SecurityContext — контекст безопасности и freeze.

Проверяет:
- Все поля SecurityContext инициализируются корректно
- freeze() запрещает дальнейшую модификацию
- Замороженный контекст выбрасывает RuntimeError
- Значения по умолчанию корректны
- Метаданные (dict) работают до freeze
- policy_version и normalization_version присутствуют
"""

import pytest
from datetime import datetime, timezone

from krepost.security.pipeline import SecurityContext, POLICY_VERSION
from krepost.security.normalize import NORMALIZATION_VERSION


class TestSecurityContext:

    def test_default_values(self):
        """Значения по умолчанию корректны."""
        ctx = SecurityContext(session_id="test", user_input="hello")
        assert ctx.session_id == "test"
        assert ctx.user_input == "hello"
        assert ctx.verdict == "GREEN"
        assert ctx.confidence == 1.0
        assert ctx.is_compromised is False
        assert ctx.normalized_input == ""
        assert ctx.processed_input == ""
        assert ctx.ai_output == ""
        assert ctx.violation_layer is None
        assert ctx.attack_vector is None
        assert ctx.kv_cache_dirty is False
        assert ctx.audit_hash is None
        assert ctx.trace_hash is None

    def test_metadata_default_empty_dict(self):
        """metadata по умолчанию — пустой dict."""
        ctx = SecurityContext(session_id="s", user_input="t")
        assert isinstance(ctx.metadata, dict)
        assert len(ctx.metadata) == 0

    def test_metadata_independent_per_instance(self):
        """Каждый SecurityContext имеет свой dict metadata."""
        ctx1 = SecurityContext(session_id="s1", user_input="t1")
        ctx2 = SecurityContext(session_id="s2", user_input="t2")
        ctx1.metadata["key"] = "value1"
        assert "key" not in ctx2.metadata

    def test_policy_version(self):
        """policy_version совпадает с глобальной константой."""
        ctx = SecurityContext(session_id="s", user_input="t")
        assert ctx.policy_version == POLICY_VERSION

    def test_normalization_version(self):
        """normalization_version совпадает с normalize.py."""
        ctx = SecurityContext(session_id="s", user_input="t")
        assert ctx.normalization_version == NORMALIZATION_VERSION

    def test_timestamp_is_utc(self):
        """timestamp — datetime в UTC."""
        ctx = SecurityContext(session_id="s", user_input="t")
        assert isinstance(ctx.timestamp, datetime)
        assert ctx.timestamp.tzinfo is not None

    # ─── FREEZE BEHAVIOR ───

    def test_freeze_prevents_modification(self):
        """freeze() запрещает изменение полей."""
        ctx = SecurityContext(session_id="s", user_input="t")
        ctx.verdict = "RED"
        ctx.freeze()
        with pytest.raises(RuntimeError, match="Cannot modify frozen"):
            ctx.verdict = "GREEN"

    def test_freeze_prevents_all_fields(self):
        """freeze() запрещает изменение любого поля."""
        ctx = SecurityContext(session_id="s", user_input="t")
        ctx.freeze()
        with pytest.raises(RuntimeError):
            ctx.session_id = "new"
        with pytest.raises(RuntimeError):
            ctx.is_compromised = True
        with pytest.raises(RuntimeError):
            ctx.confidence = 0.5

    def test_freeze_allows_read(self):
        """Замороженный контекст можно читать."""
        ctx = SecurityContext(session_id="s", user_input="t")
        ctx.verdict = "RED"
        ctx.freeze()
        assert ctx.verdict == "RED"
        assert ctx.session_id == "s"

    def test_not_frozen_by_default(self):
        """По умолчанию контекст НЕ заморожен."""
        ctx = SecurityContext(session_id="s", user_input="t")
        ctx.verdict = "RED"  # не должно вызвать ошибку
        ctx.verdict = "GREEN"  # и это тоже
        assert ctx.verdict == "GREEN"

    def test_modification_before_freeze(self):
        """До freeze можно свободно менять все поля."""
        ctx = SecurityContext(session_id="s", user_input="t")
        ctx.verdict = "RED"
        ctx.is_compromised = True
        ctx.violation_layer = "Layer1"
        ctx.metadata["test"] = True
        assert ctx.verdict == "RED"
        assert ctx.is_compromised is True
        assert ctx.violation_layer == "Layer1"
        assert ctx.metadata["test"] is True

    def test_freeze_is_permanent(self):
        """freeze() нельзя отменить — _frozen=False обходит проверку, но повторный freeze сохраняет состояние."""
        ctx = SecurityContext(session_id="s", user_input="t")
        ctx.freeze()
        # _frozen — special case в __setattr__ (name != '_frozen' guard),
        # но даже если сбросить, freeze() можно вызвать снова
        ctx._frozen = False  # разрешено по дизайну
        ctx.verdict = "RED"  # теперь можно менять
        ctx.freeze()  # снова заморозить
        with pytest.raises(RuntimeError):
            ctx.verdict = "GREEN"

    def test_frozen_field_name_in_error(self):
        """RuntimeError содержит имя поля."""
        ctx = SecurityContext(session_id="s", user_input="t")
        ctx.freeze()
        try:
            ctx.verdict = "GREEN"
        except RuntimeError as e:
            assert "verdict" in str(e)
