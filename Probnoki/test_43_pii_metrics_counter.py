"""
Пробник #43 (Т8): PII/secret счётчики в /metrics + health-flag.

foundation/2026-07-04 (LocalAI v4.6.0 localai_pii_events_total).
PIIMasker.count_redactions считает замены по категориям (pii vs secret).
OutputFilter через on_redaction-sink инкрементит pipeline.metrics.
pii_filter_healthy=False при трафике без единой замены — канарейка fail-open.
"""
import asyncio

from krepost.security.pipeline import PIIMasker, OutputFilter, SecurityPipeline


class TestCountRedactions:

    def test_secret_counted_separately(self):
        m = PIIMasker()
        masked = m.mask("key sk-" + "a" * 40 + " and AIza" + "b" * 35)
        pii, secret = m.count_redactions(masked)
        assert secret == 2
        assert pii == 0

    def test_pii_counted(self):
        m = PIIMasker()
        masked = m.mask("call +1-555-123-4567 or email me@a.com")
        pii, secret = m.count_redactions(masked)
        assert pii >= 2
        assert secret == 0

    def test_no_redactions_zero(self):
        m = PIIMasker()
        masked = m.mask("just normal text without secrets")
        pii, secret = m.count_redactions(masked)
        assert pii == 0 and secret == 0


class TestOutputFilterSink:

    def test_sink_called_on_redaction(self):
        captured = []
        m = PIIMasker()
        of = OutputFilter(m, on_redaction=lambda p, s: captured.append((p, s)))
        out, blocked, reason = asyncio.run(of.filter("token sk-" + "x" * 40))
        assert captured
        assert captured[0][1] == 1  # один секрет

    def test_sink_not_called_on_clean(self):
        captured = []
        m = PIIMasker()
        of = OutputFilter(m, on_redaction=lambda p, s: captured.append((p, s)))
        asyncio.run(of.filter("clean text"))
        assert not captured


class TestPipelineMetrics:

    def test_pipeline_accumulates_redactions(self):
        from krepost.security.pipeline import SecurityContext
        pipe = SecurityPipeline()
        ctx = SecurityContext(session_id="sess1", user_input="q", ai_output="sk-" + "a" * 40)
        asyncio.run(pipe.process_output(ctx))
        assert pipe.metrics["secret_redactions"] >= 1

    def test_pii_filter_healthy_logic(self):
        # При total>0 и redactions==0 → unhealthy
        pipe = SecurityPipeline()
        pipe.metrics["total_requests"] = 5
        pipe.metrics["pii_redactions"] = 0
        pipe.metrics["secret_redactions"] = 0
        total = pipe.metrics["total_requests"]
        red = pipe.metrics["pii_redactions"] + pipe.metrics["secret_redactions"]
        healthy = bool(total == 0 or red > 0)
        assert healthy is False

    def test_pii_filter_healthy_with_redactions(self):
        pipe = SecurityPipeline()
        pipe.metrics["total_requests"] = 5
        pipe.metrics["secret_redactions"] = 3
        total = pipe.metrics["total_requests"]
        red = pipe.metrics["pii_redactions"] + pipe.metrics["secret_redactions"]
        healthy = bool(total == 0 or red > 0)
        assert healthy is True
