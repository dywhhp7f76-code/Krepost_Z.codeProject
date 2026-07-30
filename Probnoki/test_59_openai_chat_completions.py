"""Пробник #59: OpenAI-compatible /v1/chat/completions → Крепость."""
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from krepost.api.app import create_app
from krepost.api.openai_compat import extract_user_text, resolve_mode
from krepost.orchestration.backends import EchoBackend
from krepost.orchestration.orchestrator import Orchestrator
from krepost.orchestration.router import Route, Router
from krepost.security.pipeline import SecurityPipeline


class _GreenGuard:
    async def chat(self, model=None, messages=None, format=None, **kwargs):
        return {
            "message": {
                "content": '{"status":"GREEN","reason":"ok","confidence":0.9}'
            }
        }


def _client(db_dir: str):
    pipe = SecurityPipeline(
        guard_client=_GreenGuard(),
        trust_db_path=Path(db_dir) / "t.db",
        enable_cache=False,
    )
    orch = Orchestrator(
        pipe,
        Router([], default=Route("general", EchoBackend("general"))),
    )
    return TestClient(create_app(orch))


def test_extract_and_mode():
    assert extract_user_text(
        [{"role": "system", "content": "x"}, {"role": "user", "content": "привет"}]
    ) == "привет"
    assert resolve_mode("krepost") == ("query", True)
    assert resolve_mode("krepost-fast") == ("query", False)
    assert resolve_mode("krepost-agent") == ("agent", True)


def test_models_and_chat():
    with tempfile.TemporaryDirectory() as d:
        c = _client(d)
        r = c.get("/v1/models")
        assert r.status_code == 200
        ids = {m["id"] for m in r.json()["data"]}
        assert "krepost" in ids and "krepost-fast" in ids

        r = c.post(
            "/v1/chat/completions",
            json={
                "model": "krepost",
                "messages": [{"role": "user", "content": "hello world"}],
                "stream": False,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["object"] == "chat.completion"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["choices"][0]["message"]["content"]
        assert body["krepost"]["verdict"] == "GREEN"

        r = c.post(
            "/v1/chat/completions",
            json={
                "model": "krepost-fast",
                "messages": [{"role": "user", "content": "ping"}],
                "stream": True,
            },
        )
        assert r.status_code == 200
        assert "data:" in r.text
        assert "[DONE]" in r.text
