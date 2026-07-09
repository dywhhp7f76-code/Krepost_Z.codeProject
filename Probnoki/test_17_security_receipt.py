"""
Пробник #17: SecurityReceipt — аудит и хеширование.

Проверяет:
- compute_audit_hash() детерминистичен
- compute_trace_hash() зависит от audit_hash
- Разные входы → разные хеши
- Одинаковые входы → одинаковые хеши
- Формат хеша (SHA-256, 64 hex chars)
- policy_version и normalization_version включены
"""

import pytest
from datetime import datetime, timezone

from krepost.security.pipeline import SecurityReceipt, POLICY_VERSION
from krepost.security.normalize import NORMALIZATION_VERSION


class TestSecurityReceipt:

    @pytest.fixture
    def receipt(self):
        return SecurityReceipt(
            session_id="session1",
            query="hello world",
            verdict="GREEN",
            confidence=0.95,
            layer_verdicts=[{"layer": "Layer1-Regex", "passed": True}],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=42.5,
        )

    # ─── AUDIT HASH ───

    def test_audit_hash_is_sha256(self, receipt):
        """audit_hash — SHA-256 (64 hex chars)."""
        h = receipt.compute_audit_hash()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_audit_hash_deterministic(self, receipt):
        """Одинаковые входы → одинаковый audit_hash."""
        h1 = receipt.compute_audit_hash()
        h2 = receipt.compute_audit_hash()
        assert h1 == h2

    def test_audit_hash_different_query(self):
        """Разные запросы → разные audit_hash."""
        r1 = SecurityReceipt(
            session_id="s", query="hello", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        r2 = SecurityReceipt(
            session_id="s", query="world", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        assert r1.compute_audit_hash() != r2.compute_audit_hash()

    def test_audit_hash_different_verdict(self):
        """Разные вердикты → разные audit_hash."""
        r1 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        r2 = SecurityReceipt(
            session_id="s", query="test", verdict="RED",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        assert r1.compute_audit_hash() != r2.compute_audit_hash()

    def test_audit_hash_includes_session(self):
        """Разные session_id → разные audit_hash."""
        r1 = SecurityReceipt(
            session_id="s1", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        r2 = SecurityReceipt(
            session_id="s2", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        assert r1.compute_audit_hash() != r2.compute_audit_hash()

    def test_audit_hash_ignores_timestamp(self):
        """audit_hash НЕ зависит от timestamp."""
        r1 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        r2 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2025, 6, 15, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        assert r1.compute_audit_hash() == r2.compute_audit_hash()

    def test_audit_hash_ignores_latency(self):
        """audit_hash НЕ зависит от latency_ms."""
        r1 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        r2 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=999.0,
        )
        assert r1.compute_audit_hash() == r2.compute_audit_hash()

    # ─── TRACE HASH ───

    def test_trace_hash_is_sha256(self, receipt):
        """trace_hash — SHA-256 (64 hex chars)."""
        h = receipt.compute_trace_hash()
        assert len(h) == 64

    def test_trace_hash_depends_on_timestamp(self):
        """trace_hash ЗАВИСИТ от timestamp (runtime data)."""
        r1 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        r2 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2025, 6, 15, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        assert r1.compute_trace_hash() != r2.compute_trace_hash()

    def test_trace_hash_depends_on_latency(self):
        """trace_hash ЗАВИСИТ от latency_ms."""
        r1 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=10.0,
        )
        r2 = SecurityReceipt(
            session_id="s", query="test", verdict="GREEN",
            confidence=1.0, layer_verdicts=[],
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            latency_ms=999.0,
        )
        assert r1.compute_trace_hash() != r2.compute_trace_hash()

    # ─── VERSION FIELDS ───

    def test_policy_version_default(self, receipt):
        """policy_version по умолчанию = POLICY_VERSION."""
        assert receipt.policy_version == POLICY_VERSION

    def test_normalization_version_default(self, receipt):
        """normalization_version по умолчанию = NORMALIZATION_VERSION."""
        assert receipt.normalization_version == NORMALIZATION_VERSION
