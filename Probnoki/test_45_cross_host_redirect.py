"""
Пробник #45 (Т6): refuse cross-host redirects + cap.

foundation/2026-06-16 (LocalAI v4.3.6, GHSA-3mj3-57v2-4636): редирект на
чужой хост утекает credentials/token. validate_redirect решает, можно ли
следовать с from_url на to_url. follow_redirects_safely — обёртка с ручным
следованием, max_redirects cap защищает от same-host цикла.
"""
import pytest

from krepost.security.url_guard import UrlGuard, follow_redirects_safely


class TestValidateRedirect:

    def test_same_host_allowed(self):
        g = UrlGuard()
        v = g.validate_redirect(
            "https://example.com/page1",
            "https://example.com/page2",
        )
        assert v.allowed

    def test_cross_host_blocked(self):
        g = UrlGuard()
        v = g.validate_redirect(
            "https://example.com/page",
            "https://evil.com/page",
        )
        assert not v.allowed
        assert "cross_host_redirect" in (v.reason or "")

    def test_ssrf_in_location_blocked(self):
        g = UrlGuard()
        v = g.validate_redirect(
            "https://example.com/page",
            "https://169.254.169.254/latest/meta-data/",
        )
        assert not v.allowed
        # reason от основного check() — private_ip
        assert "private_ip" in (v.reason or "")

    def test_redirect_to_loopback_blocked(self):
        g = UrlGuard()
        v = g.validate_redirect(
            "https://example.com/page",
            "http://127.0.0.1:8080/admin",
        )
        assert not v.allowed

    def test_path_redirect_relative_rejected_by_check(self):
        # Относительный URL (/b) не имеет схемы → check() его режет.
        # Разрешение относительных редиректов — обязанность HTTP-клиента
        # (urljoin относительно base); guard видит только абсолютные URL.
        g = UrlGuard()
        v = g.validate_redirect("https://example.com/a", "/b")
        assert not v.allowed
        assert "scheme" in (v.reason or "")


class _FakeResp:
    def __init__(self, status, text="", headers=None):
        self.status_code = status
        self.text = text
        self.headers = headers or {}


class TestFollowRedirectsSafely:

    def test_no_redirect_returns_text(self):
        g = UrlGuard()
        calls = []

        def fetch(url, **kw):
            calls.append(url)
            return _FakeResp(200, text="hello")

        text, visited = follow_redirects_safely(fetch, "https://example.com/a", g)
        assert text == "hello"
        assert visited == ["https://example.com/a"]

    def test_same_host_chain_followed(self):
        g = UrlGuard()
        responses = {
            "https://example.com/a": _FakeResp(302, headers={"Location": "https://example.com/b"}),
            "https://example.com/b": _FakeResp(200, text="final"),
        }

        def fetch(url, **kw):
            return responses[url]

        text, visited = follow_redirects_safely(fetch, "https://example.com/a", g)
        assert text == "final"
        assert len(visited) == 2

    def test_cross_host_blocked_raises(self):
        g = UrlGuard()

        def fetch(url, **kw):
            return _FakeResp(302, headers={"Location": "https://evil.com/x"})

        with pytest.raises(ValueError, match="cross_host_redirect"):
            follow_redirects_safely(fetch, "https://example.com/a", g)

    def test_cap_on_same_host_cycle(self):
        """РЕГРЕССИЯ: same-host цикл должен быть ограничен cap."""
        g = UrlGuard()

        def fetch(url, **kw):
            # бесконечный same-host редирект A→A
            return _FakeResp(302, headers={"Location": "https://example.com/a"})

        with pytest.raises(ValueError, match="max_redirects_exceeded"):
            follow_redirects_safely(fetch, "https://example.com/a", g, max_redirects=3)

    def test_custom_max_redirects(self):
        g = UrlGuard()
        responses = {
            "https://example.com/0": _FakeResp(302, headers={"Location": "https://example.com/1"}),
            "https://example.com/1": _FakeResp(302, headers={"Location": "https://example.com/2"}),
            "https://example.com/2": _FakeResp(200, text="done"),
        }

        def fetch(url, **kw):
            return responses[url]

        text, _ = follow_redirects_safely(fetch, "https://example.com/0", g, max_redirects=5)
        assert text == "done"
