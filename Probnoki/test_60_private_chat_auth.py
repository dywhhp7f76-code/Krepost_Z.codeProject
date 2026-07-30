"""Пробник #60: пароль оператора + ingest личных данных."""
from pathlib import Path

from fastapi.testclient import TestClient

from krepost.api.app import create_app
from krepost.api.auth import AuthGate
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


def _app(tmp_path: Path, password: str = "sekret"):
    pipe = SecurityPipeline(
        guard_client=_GreenGuard(), trust_db_path=tmp_path / "t.db"
    )
    orch = Orchestrator(
        pipe, Router([], default=Route("main", EchoBackend()))
    )
    gate = AuthGate(password=password, require_auth=True, session_ttl_sec=3600)
    return create_app(orch, auth_gate=gate, vault_root=tmp_path / "vault")


def test_query_rejected_without_token(tmp_path):
    with TestClient(_app(tmp_path)) as c:
        r = c.post(
            "/v1/query",
            json={"text": "hi", "session_id": "s1", "use_memory": False},
        )
        assert r.status_code == 401


def test_login_and_query(tmp_path):
    with TestClient(_app(tmp_path)) as c:
        bad = c.post("/v1/login", json={"password": "wrong"})
        assert bad.status_code == 401
        ok = c.post("/v1/login", json={"password": "sekret"})
        assert ok.status_code == 200
        token = ok.json()["token"]
        r = c.post(
            "/v1/query",
            json={"text": "ping", "session_id": "s1", "use_memory": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "blocked", "error") or "output" in r.json()


def test_ingest_personal(tmp_path):
    with TestClient(_app(tmp_path)) as c:
        token = c.post("/v1/login", json={"password": "sekret"}).json()["token"]
        r = c.post(
            "/v1/ingest",
            json={
                "filename": "secret_note.md",
                "content": "личный факт XYZ-7742",
                "private": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "personal/" in body["doc_id"]
        path = Path(body["path"])
        assert path.is_file()
        assert "личный факт XYZ-7742" in path.read_text(encoding="utf-8")
        assert "private: true" in path.read_text(encoding="utf-8")


def test_health_public(tmp_path):
    with TestClient(_app(tmp_path)) as c:
        h = c.get("/health")
        assert h.status_code == 200
        assert h.json().get("auth_required") is True


def test_auth_off_by_default(tmp_path):
    pipe = SecurityPipeline(
        guard_client=_GreenGuard(), trust_db_path=tmp_path / "t.db"
    )
    orch = Orchestrator(
        pipe, Router([], default=Route("main", EchoBackend()))
    )
    gate = AuthGate(password="", require_auth=False)
    with TestClient(create_app(orch, auth_gate=gate, vault_root=tmp_path / "v")) as c:
        r = c.post(
            "/v1/query",
            json={"text": "hi", "session_id": "s1", "use_memory": False},
        )
        assert r.status_code == 200
