"""
Пробник #48 (T8 alerting-infra): webhook + Prometheus при pii_filter_unhealthy.

foundation/2026-07-04: канарейка pii_filter_healthy уже в /metrics.
Добавлен AlertDispatcher (KREPOST_ALERT_WEBHOOK) с debounce и /metrics/prometheus.
"""
import tempfile
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from krepost.api.alerts import AlertDispatcher, format_prometheus_metrics  # noqa: E402
from krepost.api.app import create_app  # noqa: E402
from krepost.orchestration.backends import EchoBackend  # noqa: E402
from krepost.orchestration.orchestrator import Orchestrator  # noqa: E402
from krepost.orchestration.router import Route, Router  # noqa: E402
from krepost.security.pipeline import SecurityPipeline  # noqa: E402


class _GreenGuard:
    async def chat(self, model=None, messages=None, format=None, **kwargs):
        return {"message": {"content":
                '{"status":"GREEN","reason":"ok","confidence":0.9}'}}


def _pipeline(db_dir):
    return SecurityPipeline(
        guard_client=_GreenGuard(),
        trust_db_path=Path(db_dir) / "t.db",
        enable_cache=False,
    )


def _orch(db_dir):
    router = Router(
        [Route("general", EchoBackend("general"))],
        default=Route("general", EchoBackend("general")),
    )
    return Orchestrator(_pipeline(db_dir), router)


class TestAlertDispatcher:

    def test_healthy_no_alert(self):
        sent = []
        d = AlertDispatcher(
            webhook_url="http://example/hook",
            sender=lambda url, p: sent.append((url, p)),
            debounce_sec=0,
        )
        assert d.maybe_alert_pii_unhealthy({"pii_filter_healthy": True}) is False
        assert sent == []

    def test_unhealthy_sends_alert(self):
        sent = []
        d = AlertDispatcher(
            webhook_url="http://example/hook",
            sender=lambda url, p: sent.append((url, p)),
            debounce_sec=0,
        )
        metrics = {
            "pii_filter_healthy": False,
            "total_requests": 10,
            "pii_redactions": 0,
            "secret_redactions": 0,
        }
        assert d.maybe_alert_pii_unhealthy(metrics) is True
        assert len(sent) == 1
        url, payload = sent[0]
        assert url == "http://example/hook"
        assert payload["event"] == "pii_filter_unhealthy"
        assert payload["total_requests"] == 10

    def test_debounce_suppresses_repeat(self):
        sent = []
        d = AlertDispatcher(
            webhook_url="http://example/hook",
            sender=lambda url, p: sent.append((url, p)),
            debounce_sec=60,
        )
        bad = {"pii_filter_healthy": False, "total_requests": 5}
        assert d.maybe_alert_pii_unhealthy(bad) is True
        assert d.maybe_alert_pii_unhealthy(bad) is False
        assert len(sent) == 1

    def test_no_webhook_no_send(self):
        sent = []
        d = AlertDispatcher(sender=None, debounce_sec=0)
        assert d.maybe_alert_pii_unhealthy({"pii_filter_healthy": False}) is False


class TestPrometheusFormat:

    def test_format_includes_gauge(self):
        text = format_prometheus_metrics({
            "total_requests": 3,
            "pii_redactions": 0,
            "secret_redactions": 0,
            "pii_filter_healthy": False,
        })
        assert "krepost_pii_filter_healthy 0" in text
        assert "krepost_total_requests 3" in text


class TestApiAlertIntegration:

    @pytest.fixture
    def db_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_metrics_triggers_mock_webhook(self, db_dir):
        sent = []
        alerts = AlertDispatcher(
            webhook_url="http://mock/hook",
            sender=lambda url, p: sent.append((url, p)),
            debounce_sec=0,
        )
        pipe = _pipeline(db_dir)
        pipe.metrics["total_requests"] = 7
        pipe.metrics["pii_redactions"] = 0
        pipe.metrics["secret_redactions"] = 0
        orch = Orchestrator(pipe, Router([], default=Route("g", EchoBackend("g"))))
        with TestClient(create_app(orch, alert_dispatcher=alerts)) as client:
            r = client.get("/metrics")
            assert r.status_code == 200
            assert r.json()["pii_filter_healthy"] is False
            assert len(sent) == 1

    def test_prometheus_endpoint(self, db_dir):
        alerts = AlertDispatcher(debounce_sec=0)
        with TestClient(create_app(_orch(db_dir), alert_dispatcher=alerts)) as client:
            r = client.get("/metrics/prometheus")
            assert r.status_code == 200
            assert "krepost_pii_filter_healthy" in r.text
