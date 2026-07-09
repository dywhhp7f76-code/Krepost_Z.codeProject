"""
Пробник #2: C-003 — SessionRateLimiter безопасный cleanup.

Проверяет:
- _cleanup() использует .pop(sid, None) вместо del
- _cleanup() чистит expired сессии всегда (не только при overflow)
- При overflow удаляются самые старые сессии (LRU)
- Нет KeyError при рассинхронизации _sessions и _last_access
- Оба словаря остаются синхронизированными
"""

import time
import pytest

from krepost.security.pipeline import SessionRateLimiter, TokenBucketRateLimiter


class TestSessionRateLimiterCleanup:

    def test_cleanup_removes_expired_always(self):
        """Expired сессии удаляются даже если count <= max_sessions."""
        rl = SessionRateLimiter(rate=10, window=1, max_sessions=100)
        rl.allow("old_session")
        rl._last_access["old_session"] = time.time() - 999
        rl._cleanup()
        assert "old_session" not in rl._sessions
        assert "old_session" not in rl._last_access

    def test_cleanup_no_keyerror_on_missing_session(self):
        """Нет KeyError если session_id есть в _last_access, но нет в _sessions."""
        rl = SessionRateLimiter(rate=10, window=1, max_sessions=100)
        rl._last_access["ghost"] = time.time() - 999
        rl._cleanup()
        assert "ghost" not in rl._last_access

    def test_cleanup_no_keyerror_on_missing_last_access(self):
        """Нет KeyError если session_id есть в _sessions, но нет в _last_access."""
        rl = SessionRateLimiter(rate=10, window=1, max_sessions=100)
        rl._sessions["ghost"] = TokenBucketRateLimiter(10, 1)
        rl._cleanup()
        assert "ghost" in rl._sessions

    def test_lru_eviction_on_overflow(self):
        """При overflow удаляются самые старые сессии."""
        rl = SessionRateLimiter(rate=100, window=60, max_sessions=3)
        rl.allow("s1")
        rl._last_access["s1"] = time.time() - 10
        rl.allow("s2")
        rl._last_access["s2"] = time.time() - 5
        rl.allow("s3")
        rl._last_access["s3"] = time.time() - 1
        rl.allow("s4")
        assert len(rl._sessions) <= 4
        rl._cleanup()
        assert "s1" not in rl._sessions

    def test_dicts_stay_synchronized(self):
        """_sessions и _last_access имеют одинаковые ключи после cleanup."""
        rl = SessionRateLimiter(rate=10, window=1, max_sessions=2)
        for i in range(5):
            rl.allow(f"s{i}")
        rl._cleanup()
        assert set(rl._sessions.keys()) == set(rl._last_access.keys())

    def test_active_sessions_not_removed(self):
        """Активные сессии (недавно использованные) не удаляются."""
        rl = SessionRateLimiter(rate=100, window=60, max_sessions=100)
        rl.allow("active")
        rl._cleanup()
        assert "active" in rl._sessions
        assert "active" in rl._last_access
