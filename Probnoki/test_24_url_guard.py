"""
Пробник #24: UrlGuard — защита от SSRF при fetch.

Крепость-клиент ходит в облака; вредоносный URL из недоверенного контента
может увести запрос во внутреннюю сеть. Проверяется ДО fetch
(redteam/2026-07-02: URL Validation Bypass, Concealing payloads in credentials).

Проверяет:
- блок внутренних IP (RFC1918/loopback/link-local), IPv6, IPv4-mapped;
- блок cloud-metadata 169.254.169.254;
- блок обфусцированных числовых хостов (decimal/hex/octal);
- блок не-http схем, credentials, localhost, whitespace;
- allow публичных URL;
- resolve_dns: DNS-rebinding во внутренний IP блокируется;
- allowlist хостов (включая поддомены).
"""

import pytest

from krepost.security.url_guard import UrlGuard, UrlVerdict


@pytest.fixture
def guard():
    return UrlGuard()


class TestBlockInternalIP:

    @pytest.mark.parametrize("url,reason_prefix", [
        ("http://127.0.0.1/admin", "private_ip"),
        ("http://10.0.0.5/", "private_ip"),
        ("http://192.168.1.1/", "private_ip"),
        ("http://172.16.0.1/", "private_ip"),
        ("http://169.254.169.254/latest/meta-data/", "private_ip"),  # cloud metadata
        ("http://[::1]/", "private_ip"),
        ("http://[::ffff:127.0.0.1]/", "private_ip"),  # IPv4-mapped
        ("http://0.0.0.0/", "private_ip"),
    ])
    def test_internal_ip_blocked(self, guard, url, reason_prefix):
        v = guard.check(url)
        assert v.allowed is False
        assert v.reason.startswith(reason_prefix)


class TestBlockObfuscated:

    @pytest.mark.parametrize("url", [
        "http://2130706433/",   # decimal 127.0.0.1
        "http://0x7f000001/",   # hex
        "http://0177.0.0.1/",   # octal label
    ])
    def test_obfuscated_host_blocked(self, guard, url):
        v = guard.check(url)
        assert v.allowed is False
        assert v.reason.startswith("obfuscated_host")


class TestBlockScheme:

    @pytest.mark.parametrize("url", [
        "file:///etc/passwd",
        "gopher://internal/",
        "data:text/html,<script>alert(1)</script>",
        "ftp://host/file",
    ])
    def test_non_http_scheme_blocked(self, guard, url):
        v = guard.check(url)
        assert v.allowed is False
        assert v.reason.startswith("scheme_not_allowed")


class TestBlockMisc:

    def test_credentials_blocked(self, guard):
        assert guard.check("http://user:pass@example.com/").reason == "credentials_in_url"

    def test_localhost_blocked(self, guard):
        assert guard.check("http://localhost:8080/").reason == "localhost"
        assert guard.check("http://foo.localhost/").reason == "localhost"

    def test_internal_whitespace_blocked(self, guard):
        # внутренний пробел/control-символ — обфускация/CRLF-инъекция
        assert guard.check("http://exam ple.com/").reason == "whitespace_in_url"
        assert guard.check("http://a.com/pa\nth").reason == "whitespace_in_url"

    def test_trailing_whitespace_stripped_and_allowed(self, guard):
        # trailing \n (напр. URL из строки файла) — стрипается, URL валиден
        v = guard.check("http://example.com/\n")
        assert v.allowed is True
        assert v.url == "http://example.com/"  # возвращается очищенный

    def test_empty_blocked(self, guard):
        assert guard.check("").reason == "empty_url"
        assert guard.check("   ").reason == "empty_url"

    def test_no_scheme_blocked(self, guard):
        # без схемы urlsplit не выделит host -> scheme_not_allowed
        assert guard.check("example.com/path").allowed is False


class TestAllowPublic:

    @pytest.mark.parametrize("url", [
        "http://example.com/page",
        "https://api.openai.com/v1/chat",
        "https://habr.com/ru/articles/1/",
        "https://8.8.8.8/",  # публичный литеральный IP — разрешён
    ])
    def test_public_url_allowed(self, guard, url):
        v = guard.check(url)
        assert v.allowed is True
        assert v.reason is None


class TestResolveDns:

    def test_rebind_to_private_blocked(self):
        g = UrlGuard(resolve_dns=True, resolver=lambda h: ["10.1.2.3"])
        v = g.check("http://sneaky.com/")
        assert v.allowed is False
        assert v.reason.startswith("resolves_to_private")

    def test_resolve_to_public_allowed(self):
        g = UrlGuard(resolve_dns=True, resolver=lambda h: ["93.184.216.34"])
        v = g.check("http://example.com/")
        assert v.allowed is True
        assert v.resolved_ips == ["93.184.216.34"]

    def test_resolve_failure_fail_closed(self):
        def boom(h):
            raise OSError("dns down")
        g = UrlGuard(resolve_dns=True, resolver=boom)
        assert g.check("http://example.com/").reason == "dns_resolve_failed"

    def test_mixed_ips_one_internal_blocked(self):
        # если хоть один резолвленный IP внутренний — блок
        g = UrlGuard(resolve_dns=True, resolver=lambda h: ["93.184.216.34", "127.0.0.1"])
        assert g.check("http://example.com/").allowed is False


class TestAllowlist:

    def test_allowlist_exact_and_subdomain(self):
        g = UrlGuard(allow_hosts=["openai.com", "habr.com"])
        assert g.check("https://api.openai.com/v1").allowed is True   # поддомен
        assert g.check("https://habr.com/x").allowed is True          # точное
        v = g.check("https://evil.com/")
        assert v.allowed is False
        assert v.reason.startswith("host_not_allowlisted")


class TestVerdictShape:

    def test_verdict_fields(self):
        v = UrlVerdict(True, "http://x.com/", resolved_ips=["1.2.3.4"])
        assert v.allowed is True
        assert v.resolved_ips == ["1.2.3.4"]
