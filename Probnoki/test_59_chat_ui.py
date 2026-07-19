"""Пробник #59: чат UI отдаётся с API."""
from pathlib import Path

from fastapi.testclient import TestClient

from krepost.api.app import create_app
from krepost.orchestration import Orchestrator, Route, Router
from krepost.orchestration.backends import EchoBackend
from krepost.security.pipeline import SecurityPipeline


class _GreenGuard:
    async def chat(self, model=None, messages=None, format=None, **kwargs):
        return {
            "message": {
                "content": '{"status":"GREEN","reason":"ok","confidence":0.95}'
            }
        }


def test_chat_page_served(tmp_path):
    pipe = SecurityPipeline(
        guard_client=_GreenGuard(), trust_db_path=tmp_path / "t.db"
    )
    orch = Orchestrator(
        pipe, Router([], default=Route("main", EchoBackend()))
    )
    with TestClient(create_app(orch)) as c:
        r = c.get("/chat")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "Крепость" in r.text
        r2 = c.get("/")
        assert r2.status_code == 200
        h = c.get("/health")
        assert h.json().get("chat") == "/chat"


def test_chat_html_on_disk():
    p = Path(__file__).resolve().parents[1] / "krepost" / "api" / "static" / "chat.html"
    assert p.is_file()
    assert "Крепость" in p.read_text(encoding="utf-8")
