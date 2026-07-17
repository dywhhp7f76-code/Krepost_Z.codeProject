"""
Пробник #54: OCC-RAG reader scaffold (context-faithful поверх retrieve).
"""
from __future__ import annotations

import pytest

from krepost.memory.occ_reader import OccReader, OccAnswer
from krepost.memory.store import RetrievalResult, RetrievedChunk
from krepost.prompts.assistant import NO_DATA_TOKEN


class _FakeBackend:
    def __init__(self, text: str = "ответ из контекста [src: a.md]"):
        self.text = text
        self.last_messages = None

    async def generate(self, prompt, ctx, **kwargs):
        self.last_messages = kwargs.get("messages")
        return self.text


@pytest.mark.asyncio
async def test_occ_reader_uses_context_messages():
    chunks = [
        RetrievedChunk("solar battery facts", 0.9, "a", {"src": "a.md"}),
    ]
    retrieval = RetrievalResult("q", chunks, 0.9, True)
    be = _FakeBackend()
    reader = OccReader(be)
    ans = await reader.answer("что про battery?", retrieval)
    assert ans.used_reader
    assert "CONTEXT" in be.last_messages[1]["content"]
    assert "solar battery" in be.last_messages[1]["content"]
    assert ans.text.startswith("ответ")


@pytest.mark.asyncio
async def test_occ_reader_empty_retrieval():
    retrieval = RetrievalResult("q", [], 0.0, False)
    ans = await OccReader(_FakeBackend()).answer("q", retrieval)
    assert ans.no_data
    assert NO_DATA_TOKEN in ans.text


@pytest.mark.asyncio
async def test_occ_reader_fail_open_on_backend_error():
    class Boom:
        async def generate(self, *a, **k):
            raise RuntimeError("down")

    chunks = [RetrievedChunk("x", 0.8, "1", {"src": "x.md"})]
    retrieval = RetrievalResult("q", chunks, 0.8, True)
    ans = await OccReader(Boom()).answer("q", retrieval)
    assert ans.used_reader is False
    assert ans.error == "RuntimeError"


@pytest.mark.asyncio
async def test_orchestrator_prefers_occ_reader(tmp_path):
    from krepost.orchestration import Orchestrator, Route, Router
    from krepost.orchestration.backends import EchoBackend
    from krepost.security.pipeline import SecurityPipeline

    class _GreenGuard:
        async def chat(self, model=None, messages=None, format=None, **kwargs):
            return {"message": {"content":
                    '{"status":"GREEN","reason":"ok","confidence":0.95}'}}

    class _Mem:
        async def retrieve(self, text, k=5):
            return RetrievalResult(
                text,
                [RetrievedChunk("fact about krepost", 0.95, "d", {"src": "d.md"})],
                0.95,
                True,
            )

        def _source_label(self, meta, doc_id):
            return meta.get("src", doc_id)

    class _Occ:
        async def answer(self, q, retrieval, ctx=None):
            return OccAnswer("OCC SAYS HI", used_reader=True)

    pipe = SecurityPipeline(
        guard_client=_GreenGuard(), trust_db_path=tmp_path / "t.db",
    )
    echo = EchoBackend()
    orch = Orchestrator(
        pipe,
        Router([], default=Route("main", echo)),
        memory_store=_Mem(),
        occ_reader=_Occ(),
    )
    result = await orch.handle("что такое krepost?", "s1")
    assert result.ok
    assert "OCC SAYS HI" in result.output
    assert result.metadata.get("occ_reader") is True
