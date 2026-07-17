"""Probnik #52: EpisodicMemory — add + quarantine (GREEN vs RED/YELLOW)."""
from __future__ import annotations

import asyncio

import numpy as np
import pytest

from krepost.memory.episodic import EpisodicMemory, SecurityVerdict


class FakeProvider:
    """Детерминированный эмбеддер без SentenceTransformer."""

    model_name = "fake-test"
    dim = 8

    def encode_query(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        v[hash(text) % self.dim] = 1.0
        return v

    def encode_passage(self, text: str) -> np.ndarray:
        return self.encode_query(text)


@pytest.fixture
def memory(tmp_path):
    return EpisodicMemory(FakeProvider(), base_dir=tmp_path)


class TestEpisodicQuarantine:
    def test_green_episode_recallable(self, memory):
        async def run():
            eid = await memory.add_episode(
                "hello query",
                "hello response",
                security_verdict=SecurityVerdict.GREEN,
            )
            recalled = await memory.recall("hello query")
            assert len(recalled) == 1
            assert recalled[0].id == eid
            assert recalled[0].quarantine is False

        asyncio.run(run())

    def test_red_episode_quarantined_from_recall(self, memory):
        async def run():
            await memory.add_episode(
                "bad query",
                "bad response",
                security_verdict=SecurityVerdict.RED,
            )
            assert len(await memory.recall("bad query")) == 0
            quarantined = await memory.recall("bad query", include_quarantined=True)
            assert len(quarantined) == 1
            assert quarantined[0].quarantine is True
            assert quarantined[0].security_verdict == SecurityVerdict.RED

        asyncio.run(run())

    def test_yellow_episode_quarantined(self, memory):
        async def run():
            await memory.add_episode(
                "edge query",
                "edge response",
                security_verdict=SecurityVerdict.YELLOW,
            )
            assert len(await memory.recall("edge query")) == 0
            stats = memory.stats()
            assert stats["quarantined"] == 1

        asyncio.run(run())
