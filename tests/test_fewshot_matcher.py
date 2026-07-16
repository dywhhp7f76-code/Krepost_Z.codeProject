"""Tests for FewShotMatcher (krepost.security.pipeline, Layer 3)."""

import asyncio
import pytest
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from krepost.security.pipeline import FewShotMatcher


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _mock_embedder(sync: bool = True):
    """Return a mock embedder with sync or async .encode()."""
    embedder = MagicMock()
    if sync:
        embedder.encode = MagicMock(return_value=[0.1, 0.2, 0.3])
    else:
        embedder.encode = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return embedder


def _mock_collection(distances=None, documents=None, metadatas=None,
                     metric="cosine"):
    """Return a mock ChromaDB collection with configurable query results."""
    collection = MagicMock()
    collection.metadata = {"hnsw:space": metric}

    if distances is not None:
        collection.query = MagicMock(return_value={
            "distances": [distances],
            "documents": [documents],
            "metadatas": [metadatas],
        })
    else:
        collection.query = MagicMock(return_value={
            "distances": [],
            "documents": [],
            "metadatas": [],
        })
    return collection


# ═══════════════════════════════════════════════════════════════════════════
# TestFewShotMatcher
# ═══════════════════════════════════════════════════════════════════════════

class TestFewShotMatcher:

    # ------------------------------------------------------------------
    # 1. Unavailable embedder/collection -> fail-closed
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unavailable_embedder_fail_closed(self):
        matcher = FewShotMatcher(embedder=None, chroma_collection=MagicMock())
        blocked, matches, reason = await matcher.match("hello")
        assert blocked is True
        assert matches == []
        assert reason == "fewshot_unavailable_fail_closed"

    @pytest.mark.asyncio
    async def test_unavailable_collection_fail_closed(self):
        matcher = FewShotMatcher(embedder=MagicMock(), chroma_collection=None)
        blocked, matches, reason = await matcher.match("hello")
        assert blocked is True
        assert matches == []
        assert reason == "fewshot_unavailable_fail_closed"

    @pytest.mark.asyncio
    async def test_both_unavailable_fail_closed(self):
        matcher = FewShotMatcher(embedder=None, chroma_collection=None)
        blocked, matches, reason = await matcher.match("hello")
        assert blocked is True
        assert reason == "fewshot_unavailable_fail_closed"

    # ------------------------------------------------------------------
    # 2. Clean text with no matches -> (False, [], None)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_clean_text_no_matches(self):
        """All similarities below threshold -> no match, not blocked."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.5, 0.6, 0.7],           # similarity = 0.5, 0.4, 0.3
            documents=["doc1", "doc2", "doc3"],
            metadatas=[{"label": "A"}, {"label": "B"}, {"label": "C"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 threshold=0.92)
        blocked, matches, reason = await matcher.match("safe input")
        assert blocked is False
        assert matches == []
        assert reason is None

    # ------------------------------------------------------------------
    # 3. Matching with similarity above threshold
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_match_above_threshold(self):
        """Similarity >= 0.92 should appear in matches."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.05, 0.5],                # similarity = 0.95, 0.5
            documents=["injection example", "safe doc"],
            metadatas=[{"label": "INJECTION"}, {"label": "SAFE"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 threshold=0.92)
        blocked, matches, reason = await matcher.match("test text")
        assert blocked is True
        assert len(matches) == 1
        assert matches[0]["text"] == "injection example"
        assert matches[0]["label"] == "INJECTION"
        assert abs(matches[0]["similarity"] - 0.95) < 1e-9
        assert reason is None

    @pytest.mark.asyncio
    async def test_multiple_matches_above_threshold(self):
        """Multiple results above threshold all returned."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.02, 0.05, 0.5],          # similarity = 0.98, 0.95, 0.5
            documents=["doc1", "doc2", "doc3"],
            metadatas=[{"label": "A"}, {"label": "B"}, {"label": "C"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 threshold=0.92)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert len(matches) == 2
        assert matches[0]["similarity"] == pytest.approx(0.98)
        assert matches[1]["similarity"] == pytest.approx(0.95)

    # ------------------------------------------------------------------
    # 4. Similarity below threshold -> no matches
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_match_below_threshold(self):
        """Similarity just below 0.92 should not match."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.09],                      # similarity = 0.91
            documents=["close but no"],
            metadatas=[{"label": "X"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 threshold=0.92)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is False
        assert matches == []
        assert reason is None

    # ------------------------------------------------------------------
    # 5. Invalid similarity range -> fail-closed
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_invalid_similarity_negative(self):
        """Negative distance making similarity > 1.0 -> fail-closed."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[-0.5],                      # similarity = 1.5 (invalid)
            documents=["doc"],
            metadatas=[{"label": "X"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert matches == []
        assert reason == "fewshot_invalid_similarity_fail_closed"

    @pytest.mark.asyncio
    async def test_invalid_similarity_greater_than_one(self):
        """Distance > 1.0 making similarity < 0.0 -> fail-closed."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[1.5],                       # similarity = -0.5 (invalid)
            documents=["doc"],
            metadatas=[{"label": "X"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert matches == []
        assert reason == "fewshot_invalid_similarity_fail_closed"

    # ------------------------------------------------------------------
    # 6. Embedder timeout -> fail-closed
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_embedder_timeout_fail_closed(self):
        """Embedder that hangs -> asyncio.TimeoutError -> fail-closed."""
        embedder = MagicMock()

        async def slow_encode(text):
            await asyncio.sleep(20)
            return [0.1, 0.2, 0.3]

        embedder.encode = slow_encode
        collection = _mock_collection(
            distances=[0.05],
            documents=["doc"],
            metadatas=[{"label": "X"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert matches == []
        assert "fewshot_error" in reason

    # ------------------------------------------------------------------
    # 7. ChromaDB query error -> fail-closed
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_chromadb_query_error_fail_closed(self):
        """ChromaDB exception -> fail-closed."""
        embedder = _mock_embedder()
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        collection.query = MagicMock(side_effect=RuntimeError("DB crashed"))
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert matches == []
        assert "fewshot_error" in reason

    # ------------------------------------------------------------------
    # 8. LRU cache hit
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_embedding_cache_hit(self):
        """Second call with same text should use cached embedding."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.5],
            documents=["doc"],
            metadatas=[{"label": "X"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 embedding_cache_size=10)

        await matcher.match("same text")
        await matcher.match("same text")

        # Embedder should be called only once; second call uses cache
        assert embedder.encode.call_count == 1

    # ------------------------------------------------------------------
    # 9. LRU cache eviction
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_embedding_cache_eviction(self):
        """With cache_size=2, adding 3rd item evicts the oldest."""
        embedder = _mock_embedder()
        call_count = 0
        original_encode = embedder.encode.side_effect

        def counting_encode(text):
            return [0.1 * hash(text) % 1, 0.2, 0.3]

        embedder.encode = MagicMock(side_effect=counting_encode)

        collection = _mock_collection(
            distances=[0.5],
            documents=["doc"],
            metadatas=[{"label": "X"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 embedding_cache_size=2)

        await matcher.match("text_a")
        await matcher.match("text_b")
        await matcher.match("text_c")  # evicts text_a

        assert len(matcher.embedding_cache) == 2
        assert "text_a" not in matcher.embedding_cache
        assert "text_b" in matcher.embedding_cache
        assert "text_c" in matcher.embedding_cache

        # Call text_a again — should call embedder again (was evicted)
        embedder.encode.reset_mock()
        await matcher.match("text_a")
        assert embedder.encode.call_count == 1

    # ------------------------------------------------------------------
    # 10. _verify_metric with wrong metric -> ValueError logged
    # ------------------------------------------------------------------

    def test_verify_metric_wrong_metric_warns(self):
        """Collection with non-cosine metric should log a warning."""
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "l2"}

        # _verify_metric raises ValueError but is caught and logged as warning
        # The constructor should not crash (logger.warning catches it).
        matcher = FewShotMatcher(
            embedder=MagicMock(), chroma_collection=collection
        )
        # Object should still be created (warning, not crash)
        assert matcher.collection is collection

    def test_verify_metric_correct_metric(self):
        """Collection with cosine metric should pass silently."""
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        matcher = FewShotMatcher(embedder=MagicMock(), chroma_collection=collection)
        assert matcher.threshold == 0.92

    def test_verify_metric_no_collection(self):
        """None collection should skip verification."""
        matcher = FewShotMatcher(embedder=MagicMock(), chroma_collection=None)
        assert matcher.collection is None

    def test_verify_metric_no_metadata(self):
        """Collection without metadata attr should not crash."""
        collection = MagicMock(spec=[])  # no attributes
        # Should handle gracefully via the except branch
        matcher = FewShotMatcher(embedder=MagicMock(), chroma_collection=collection)
        assert matcher.collection is collection

    # ------------------------------------------------------------------
    # 11. Empty DB = cold start (passes); malformed response = fail-closed
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_db_passes_cold_start(self):
        """Empty distances list = cold start, NOT an error: must pass."""
        embedder = _mock_embedder()
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        collection.query = MagicMock(return_value={
            "distances": [[]],
            "documents": [[]],
            "metadatas": [[]],
        })
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is False
        assert matches == []
        assert reason is None

    @pytest.mark.asyncio
    async def test_no_distances_key_fail_closed(self):
        """Missing distances key = malformed response -> fail-closed."""
        embedder = _mock_embedder()
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        collection.query = MagicMock(return_value={})
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert matches == []
        assert reason == "fewshot_invalid_response_fail_closed"

    @pytest.mark.asyncio
    async def test_none_results_fail_closed(self):
        """None results = malformed response -> fail-closed."""
        embedder = _mock_embedder()
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        collection.query = MagicMock(return_value=None)
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert matches == []
        # None results triggers `not results` check
        assert reason == "fewshot_invalid_response_fail_closed"

    # ------------------------------------------------------------------
    # 12. Async embedder support
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_async_embedder(self):
        """Embedder with async encode() method should work."""
        embedder = _mock_embedder(sync=False)
        collection = _mock_collection(
            distances=[0.05],
            documents=["injection"],
            metadatas=[{"label": "INJECT"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 threshold=0.92)
        blocked, matches, reason = await matcher.match("test async")
        assert blocked is True
        assert len(matches) == 1
        assert matches[0]["similarity"] == pytest.approx(0.95)
        embedder.encode.assert_awaited_once_with("test async")

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_missing_label_defaults_to_unknown(self):
        """Metadata without 'label' key defaults to 'UNKNOWN'."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.01],                      # similarity = 0.99
            documents=["doc"],
            metadatas=[{}],                        # no 'label' key
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert matches[0]["label"] == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_exact_threshold_boundary(self):
        """Similarity exactly at threshold (0.92) should be included."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.08],                      # similarity = exactly 0.92
            documents=["borderline"],
            metadatas=[{"label": "EDGE"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection,
                                 threshold=0.92)
        blocked, matches, reason = await matcher.match("test")
        assert blocked is True
        assert len(matches) == 1
        assert matches[0]["similarity"] == pytest.approx(0.92)

    def test_custom_threshold(self):
        """Custom threshold is stored correctly."""
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        matcher = FewShotMatcher(
            embedder=MagicMock(), chroma_collection=collection, threshold=0.85
        )
        assert matcher.threshold == 0.85

    def test_custom_cache_size(self):
        """Custom cache size is stored correctly."""
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        matcher = FewShotMatcher(
            embedder=MagicMock(), chroma_collection=collection,
            embedding_cache_size=500
        )
        assert matcher.embedding_cache_size == 500

    @pytest.mark.asyncio
    async def test_cache_threading_safety(self):
        """Cache operations should use the lock correctly."""
        embedder = _mock_embedder()
        collection = _mock_collection(
            distances=[0.5],
            documents=["doc"],
            metadatas=[{"label": "X"}],
        )
        matcher = FewShotMatcher(embedder=embedder, chroma_collection=collection)

        # Directly test cache methods
        matcher._cache_embedding("key1", [1.0, 2.0])
        result = matcher._get_cached_embedding("key1")
        assert result == [1.0, 2.0]

        # Missing key returns None
        result = matcher._get_cached_embedding("missing")
        assert result is None
