"""Tests for SMART_CACHE (src/krepost/cache/SMART_CACHE.py).

Mocks sentence_transformers at import level since it is not available
in the test environment.
"""

import sys
import os
import time
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock sentence_transformers BEFORE importing SMART_CACHE
# ---------------------------------------------------------------------------
_mock_st = MagicMock()
sys.modules['sentence_transformers'] = _mock_st

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import tempfile
from pathlib import Path

import pytest

from krepost.cache.SMART_CACHE import (
    _SlidingWindow,
    AnomalyDetector,
    LLMResponseCache,
    CacheEvent,
    CacheEventType,
    CacheLevel,
    CacheStats,
    EventLevel,
    SecurityVerdict,
    L3Entry,
)


# ═══════════════════════════════════════════════════════════════════════════
# _SlidingWindow
# ═══════════════════════════════════════════════════════════════════════════

class TestSlidingWindow:
    def test_add_and_count(self):
        """Events within the window are counted."""
        w = _SlidingWindow(window_seconds=10.0)
        now = 1000.0
        w.add(now - 5)
        w.add(now - 3)
        w.add(now - 1)
        assert w.count(now) == 3

    def test_count_after_expiry(self):
        """Events older than the window are pruned."""
        w = _SlidingWindow(window_seconds=10.0)
        now = 1000.0
        w.add(now - 20)  # expired
        w.add(now - 15)  # expired
        w.add(now - 5)   # within window
        assert w.count(now) == 1

    def test_empty_window(self):
        """Empty window returns 0."""
        w = _SlidingWindow(window_seconds=10.0)
        assert w.count(time.time()) == 0

    def test_all_expired(self):
        """All events expired returns 0."""
        w = _SlidingWindow(window_seconds=5.0)
        now = 1000.0
        w.add(now - 100)
        w.add(now - 50)
        assert w.count(now) == 0

    def test_boundary_event_included(self):
        """Event exactly at the cutoff boundary is included (cutoff uses strict <)."""
        w = _SlidingWindow(window_seconds=10.0)
        now = 1000.0
        # cutoff = 990; event at 990 is NOT < 990, so it stays
        w.add(now - 10)
        assert w.count(now) == 1

    def test_event_just_before_cutoff_excluded(self):
        """Event just before the cutoff is pruned."""
        w = _SlidingWindow(window_seconds=10.0)
        now = 1000.0
        w.add(now - 10.001)  # just before cutoff, excluded
        assert w.count(now) == 0

    def test_boundary_event_just_inside(self):
        """Event just inside the window is included."""
        w = _SlidingWindow(window_seconds=10.0)
        now = 1000.0
        w.add(now - 9.999)
        assert w.count(now) == 1

    def test_progressive_expiry(self):
        """Calling count at different times prunes progressively."""
        w = _SlidingWindow(window_seconds=5.0)
        w.add(100.0)
        w.add(103.0)
        w.add(106.0)
        # cutoff = 105-5 = 100; count prunes < 100, so 100.0 is NOT pruned → 3 kept
        assert w.count(105.0) == 3
        # cutoff = 108-5 = 103; 100 < 103 (pruned); 103 not < 103 (kept), 106 (kept) → 2
        assert w.count(108.0) == 2
        # cutoff = 112-5 = 107; 103 < 107 (pruned), 106 < 107 (pruned) → 0
        assert w.count(112.0) == 0


# ═══════════════════════════════════════════════════════════════════════════
# AnomalyDetector
# ═══════════════════════════════════════════════════════════════════════════

class TestAnomalyDetector:

    def test_no_events_when_on_event_none(self):
        """With on_event=None, _check should do nothing (no crash)."""
        detector = AnomalyDetector(
            growth_threshold_per_min=5,
            window_seconds=60.0,
            on_event=None,
        )
        # Force check
        detector._last_check_time = 0
        for _ in range(100):
            detector.record_put()
        # No exception means success

    def test_growth_anomaly_long_window(self):
        """With window >= 60s, growth is normalised to per-minute rate."""
        events = []
        detector = AnomalyDetector(
            growth_threshold_per_min=10,
            miss_rate_threshold=0.90,
            window_seconds=60.0,
            on_event=events.append,
        )
        detector._check_interval = 0  # disable gating

        now = time.time()
        # Add 15 puts in the window (15/min > threshold of 10)
        for i in range(15):
            detector._put_timestamps.add(now - i)
        detector._last_check_time = 0
        detector.record_put()  # triggers check

        growth_events = [e for e in events if e.type == CacheEventType.GROWTH_ANOMALY]
        assert len(growth_events) >= 1
        assert growth_events[0].level == EventLevel.YELLOW

    def test_no_growth_anomaly_below_threshold(self):
        """Puts below threshold should not fire."""
        events = []
        detector = AnomalyDetector(
            growth_threshold_per_min=100,
            window_seconds=60.0,
            on_event=events.append,
        )
        detector._check_interval = 0

        now = time.time()
        for i in range(5):
            detector._put_timestamps.add(now - i)
        detector._last_check_time = 0
        detector.record_put()

        growth_events = [e for e in events if e.type == CacheEventType.GROWTH_ANOMALY]
        assert len(growth_events) == 0

    def test_growth_anomaly_short_window_fix3(self):
        """FIX-3: with window < 60s, absolute count is used (no extrapolation)."""
        events = []
        detector = AnomalyDetector(
            growth_threshold_per_min=10,  # used as absolute threshold for short windows
            window_seconds=5.0,           # short window
            on_event=events.append,
        )
        detector._check_interval = 0

        now = time.time()
        # Add 15 puts in a 5s window. Without FIX-3, this would be
        # extrapolated to 180/min. With FIX-3, compared as absolute 15 > 10.
        for i in range(15):
            detector._put_timestamps.add(now - i * 0.1)
        detector._last_check_time = 0
        detector.record_put()

        growth_events = [e for e in events if e.type == CacheEventType.GROWTH_ANOMALY]
        assert len(growth_events) >= 1

    def test_short_window_no_false_positive_fix3(self):
        """FIX-3: few puts in short window should NOT trigger anomaly."""
        events = []
        detector = AnomalyDetector(
            growth_threshold_per_min=60,
            window_seconds=0.5,           # very short window
            on_event=events.append,
        )
        detector._check_interval = 0

        now = time.time()
        # 5 puts in 0.5s. Without FIX-3: 5/0.00833 = 600/min (false positive!).
        # With FIX-3: absolute 5 < 60 threshold → no anomaly.
        for i in range(5):
            detector._put_timestamps.add(now - i * 0.1)
        detector._last_check_time = 0
        detector.record_put()

        growth_events = [e for e in events if e.type == CacheEventType.GROWTH_ANOMALY]
        assert len(growth_events) == 0

    def test_miss_rate_high(self):
        """Miss rate above threshold fires MISS_RATE_HIGH event."""
        events = []
        detector = AnomalyDetector(
            growth_threshold_per_min=1000,
            miss_rate_threshold=0.80,
            window_seconds=300.0,
            on_event=events.append,
        )
        detector._check_interval = 0

        now = time.time()
        # 2 hits, 18 misses -> miss_rate = 0.9 > 0.8
        for _ in range(2):
            detector._hit_timestamps.add(now)
        for _ in range(18):
            detector._miss_timestamps.add(now)
        detector._last_check_time = 0
        detector.record_miss()

        miss_events = [e for e in events if e.type == CacheEventType.MISS_RATE_HIGH]
        assert len(miss_events) >= 1
        assert miss_events[0].payload["miss_rate"] > 0.8

    def test_miss_rate_not_triggered_below_minimum(self):
        """Miss rate check requires >= 10 total events."""
        events = []
        detector = AnomalyDetector(
            growth_threshold_per_min=1000,
            miss_rate_threshold=0.50,
            window_seconds=300.0,
            on_event=events.append,
        )
        detector._check_interval = 0

        now = time.time()
        # 1 hit + 7 misses = 8 total, then record_miss adds 1 more = 9 total (< 10 minimum)
        detector._hit_timestamps.add(now)
        for _ in range(7):
            detector._miss_timestamps.add(now)
        detector._last_check_time = 0
        detector.record_miss()

        miss_events = [e for e in events if e.type == CacheEventType.MISS_RATE_HIGH]
        assert len(miss_events) == 0

    def test_check_interval_gating(self):
        """Events within check_interval should not trigger _check."""
        events = []
        detector = AnomalyDetector(
            growth_threshold_per_min=1,
            window_seconds=60.0,
            on_event=events.append,
        )
        detector._check_interval = 9999  # very long interval
        detector._last_check_time = time.time()

        # These should all be gated
        for _ in range(100):
            detector.record_put()

        # No events because check_interval not exceeded
        assert len(events) == 0

    def test_stats_dict(self):
        """stats_dict() returns correct structure."""
        detector = AnomalyDetector(window_seconds=60.0, on_event=None)
        now = time.time()
        detector._hit_timestamps.add(now)
        detector._miss_timestamps.add(now)
        detector._put_timestamps.add(now)

        stats = detector.stats_dict()
        assert "window_seconds" in stats
        assert "hits_in_window" in stats
        assert "misses_in_window" in stats
        assert "miss_rate" in stats
        assert "puts_in_window" in stats
        assert stats["window_seconds"] == 60.0


# ═══════════════════════════════════════════════════════════════════════════
# LLMResponseCache (L3)
# ═══════════════════════════════════════════════════════════════════════════

class TestLLMResponseCache:

    @pytest.fixture
    def cache_dir(self, tmp_path):
        """Provide a temporary directory for cache files."""
        return tmp_path

    @pytest.fixture
    def cache(self, cache_dir):
        """Create a fresh LLMResponseCache."""
        return LLMResponseCache(
            cache_dir=cache_dir,
            max_entries=100,
            default_ttl=3600.0,
            prompt_version="v1",
        )

    # -- _make_key --

    def test_make_key_deterministic(self, cache):
        """Same inputs produce same key."""
        k1 = cache._make_key("hello", "ctx123", "gpt-4")
        k2 = cache._make_key("hello", "ctx123", "gpt-4")
        assert k1 == k2

    def test_make_key_different_inputs(self, cache):
        """Different inputs produce different keys."""
        k1 = cache._make_key("hello", "ctx123", "gpt-4")
        k2 = cache._make_key("world", "ctx123", "gpt-4")
        k3 = cache._make_key("hello", "ctx456", "gpt-4")
        k4 = cache._make_key("hello", "ctx123", "gpt-3.5")
        assert len({k1, k2, k3, k4}) == 4

    def test_make_key_includes_prompt_version(self, cache_dir):
        """Changing prompt_version changes the key."""
        c1 = LLMResponseCache(cache_dir=cache_dir, prompt_version="v1")
        c2 = LLMResponseCache(cache_dir=cache_dir, prompt_version="v2")
        k1 = c1._make_key("q", "ctx", "m")
        k2 = c2._make_key("q", "ctx", "m")
        assert k1 != k2

    # -- put with GREEN verdict --

    def test_put_green_verdict(self, cache):
        """GREEN verdict should store the entry."""
        key = cache.put(
            query="What is X?",
            response="X is Y.",
            context_hash="abc",
            model="gpt-4",
            source_notes=["note1.md"],
            verdict=SecurityVerdict.GREEN,
        )
        assert key is not None
        assert len(cache._entries) == 1

    # -- put with RED verdict (no-op) --

    def test_put_red_verdict_noop(self, cache):
        """RED verdict should not store anything."""
        key = cache.put(
            query="malicious",
            response="blocked",
            context_hash="abc",
            model="gpt-4",
            source_notes=["note.md"],
            verdict=SecurityVerdict.RED,
        )
        assert key is None
        assert len(cache._entries) == 0

    def test_put_yellow_verdict_noop(self, cache):
        """YELLOW verdict should not store anything."""
        key = cache.put(
            query="suspicious",
            response="maybe",
            context_hash="abc",
            model="gpt-4",
            source_notes=[],
            verdict=SecurityVerdict.YELLOW,
        )
        assert key is None
        assert len(cache._entries) == 0

    # -- get existing entry --

    def test_get_existing_entry(self, cache):
        """Get should return stored entry."""
        cache.put("q1", "response1", "ctx1", "m1", ["n.md"], SecurityVerdict.GREEN)
        entry = cache.get("q1", "ctx1", "m1")
        assert entry is not None
        assert entry.response == "response1"
        assert entry.hits == 1

    def test_get_missing_entry(self, cache):
        """Get for non-existent key returns None."""
        entry = cache.get("nonexistent", "ctx", "model")
        assert entry is None
        assert cache._misses == 1

    # -- get expired entry --

    def test_get_expired_entry(self, cache):
        """Expired entries should be removed and return None."""
        cache.put("q1", "r1", "ctx1", "m1", [], SecurityVerdict.GREEN, ttl=0.0)
        # Entry is instantly expired (ttl=0)
        # Need a tiny sleep or manual timestamp manipulation
        time.sleep(0.01)
        entry = cache.get("q1", "ctx1", "m1")
        assert entry is None
        assert cache._misses >= 1

    # -- TTL expiration --

    def test_ttl_expiration(self, cache_dir):
        """Custom TTL works correctly."""
        cache = LLMResponseCache(cache_dir=cache_dir, default_ttl=0.1)
        cache.put("q", "r", "c", "m", [], SecurityVerdict.GREEN)
        # Should exist immediately
        assert cache.get("q", "c", "m") is not None
        # Wait for TTL
        time.sleep(0.15)
        assert cache.get("q", "c", "m") is None

    # -- invalidate_by_note cascade --

    def test_invalidate_by_note(self, cache):
        """Invalidation removes entries associated with the note."""
        cache.put("q1", "r1", "c1", "m1", ["note_a.md"], SecurityVerdict.GREEN)
        cache.put("q2", "r2", "c2", "m2", ["note_a.md", "note_b.md"], SecurityVerdict.GREEN)
        cache.put("q3", "r3", "c3", "m3", ["note_b.md"], SecurityVerdict.GREEN)

        removed = cache.invalidate_by_note("note_a.md")
        assert removed == 2
        assert len(cache._entries) == 1
        # q3 should still be present
        assert cache.get("q3", "c3", "m3") is not None

    def test_invalidate_by_note_no_match(self, cache):
        """Invalidation of non-existent note returns 0."""
        cache.put("q1", "r1", "c1", "m1", ["other.md"], SecurityVerdict.GREEN)
        removed = cache.invalidate_by_note("nonexistent.md")
        assert removed == 0
        assert len(cache._entries) == 1

    # -- eviction at max_entries --

    def test_eviction_at_max_entries(self, cache_dir):
        """When max_entries is reached, oldest entries are evicted."""
        cache = LLMResponseCache(
            cache_dir=cache_dir,
            max_entries=3,
            default_ttl=3600.0,
        )
        for i in range(5):
            cache.put(f"q{i}", f"r{i}", f"c{i}", "m", [], SecurityVerdict.GREEN)
            time.sleep(0.01)  # ensure different timestamps

        # Should have at most 3 entries
        assert len(cache._entries) <= 3

    # -- prompt_version filtering --

    def test_prompt_version_filtering(self, cache_dir):
        """Entries with different prompt_version are filtered on load."""
        cache_v1 = LLMResponseCache(
            cache_dir=cache_dir,
            prompt_version="v1",
            default_ttl=3600.0,
        )
        cache_v1.put("q1", "r1", "c1", "m1", [], SecurityVerdict.GREEN)
        cache_v1.close()

        # Load with different prompt_version
        cache_v2 = LLMResponseCache(
            cache_dir=cache_dir,
            prompt_version="v2",
            default_ttl=3600.0,
        )
        # v1 entries should be filtered out
        assert len(cache_v2._entries) == 0

    # -- duplicate put returns existing key --

    def test_put_duplicate_returns_existing(self, cache):
        """Putting the same query again returns the existing key without duplicating."""
        k1 = cache.put("q1", "r1", "c1", "m1", [], SecurityVerdict.GREEN)
        k2 = cache.put("q1", "r1", "c1", "m1", [], SecurityVerdict.GREEN)
        assert k1 == k2
        assert len(cache._entries) == 1

    # -- stats --

    def test_stats(self, cache):
        """stats() returns valid CacheStats."""
        cache.put("q1", "r1", "c1", "m1", [], SecurityVerdict.GREEN)
        cache.get("q1", "c1", "m1")
        cache.get("missing", "c", "m")

        st = cache.stats()
        assert st.layer == CacheLevel.L3_LLM
        assert st.entries == 1
        assert st.hits == 1
        assert st.misses == 1
        assert st.hit_rate == 0.5

    # -- close --

    def test_close_rewrites_file(self, cache):
        """close() should persist entries."""
        cache.put("q1", "r1", "c1", "m1", [], SecurityVerdict.GREEN)
        cache.close()
        assert cache._jsonl_path.exists()


# ═══════════════════════════════════════════════════════════════════════════
# CacheEvent / CacheStats dataclass construction
# ═══════════════════════════════════════════════════════════════════════════

class TestCacheEvent:
    def test_cache_event_construction(self):
        """CacheEvent should be constructable with all fields."""
        evt = CacheEvent(
            level=EventLevel.GREEN,
            type=CacheEventType.HIT,
            layer=CacheLevel.L1_EMBEDDING,
            message="test event",
            payload={"key": "value"},
        )
        assert evt.level == EventLevel.GREEN
        assert evt.type == CacheEventType.HIT
        assert evt.layer == CacheLevel.L1_EMBEDDING
        assert evt.message == "test event"
        assert evt.payload == {"key": "value"}
        assert evt.timestamp > 0

    def test_cache_event_default_payload(self):
        """CacheEvent without payload defaults to empty dict."""
        evt = CacheEvent(
            level=EventLevel.YELLOW,
            type=CacheEventType.MISS,
            layer=CacheLevel.L2_RAG,
            message="miss",
        )
        assert evt.payload == {}

    def test_cache_event_timestamp_auto(self):
        """Timestamp is auto-generated."""
        before = time.time()
        evt = CacheEvent(
            level=EventLevel.RED,
            type=CacheEventType.GROWTH_ANOMALY,
            layer=CacheLevel.L3_LLM,
            message="anomaly",
        )
        after = time.time()
        assert before <= evt.timestamp <= after


class TestCacheStats:
    def test_cache_stats_construction(self):
        """CacheStats should be constructable with required fields."""
        st = CacheStats(
            layer=CacheLevel.L1_EMBEDDING,
            entries=10,
            hits=5,
            misses=3,
            hit_rate=0.625,
        )
        assert st.layer == CacheLevel.L1_EMBEDDING
        assert st.entries == 10
        assert st.hits == 5
        assert st.misses == 3
        assert st.hit_rate == 0.625
        assert st.last_event_at_iso is None

    def test_cache_stats_with_timestamp(self):
        """CacheStats with last_event_at_iso."""
        st = CacheStats(
            layer=CacheLevel.L3_LLM,
            entries=0,
            hits=0,
            misses=0,
            hit_rate=0.0,
            last_event_at_iso="2024-01-01T00:00:00+00:00",
        )
        assert st.last_event_at_iso == "2024-01-01T00:00:00+00:00"
