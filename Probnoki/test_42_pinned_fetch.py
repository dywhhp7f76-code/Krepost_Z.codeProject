"""
Пробник #42: connect-time IP pinning после UrlGuard.

- pinned_http_get отвергает private IP даже если их подсунули в resolved_ips
- make_fetch_tool без fetch_fn требует resolved_ips (pin path)
- кастомный fetch_fn сохраняет старое поведение (pin выкл.)
"""
import asyncio
from urllib.parse import urlsplit

import pytest

from krepost.orchestration.tools import make_fetch_tool
from krepost.security.pinned_fetch import pinned_http_get
from krepost.security.url_guard import UrlGuard, UrlVerdict


def test_pinned_rejects_private_ip():
    with pytest.raises(ValueError, match="no_public_resolved_ip"):
        pinned_http_get("http://example.com/", ["127.0.0.1", "10.0.0.1"])


def test_pinned_requires_ips():
    with pytest.raises(ValueError, match="no_resolved_ips"):
        pinned_http_get("http://example.com/", [])


@pytest.mark.asyncio
async def test_make_fetch_tool_custom_fn_unchanged():
    calls = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        return "ok-body"

    tool = make_fetch_tool("fetch", fetch_fn=fake_fetch, url_guard=UrlGuard())
    # example.com литеральный публичный? нет — hostname. без resolve ок
    out = await tool.run({"url": "https://example.com/path"})
    assert out == "ok-body"
    assert calls and "example.com" in calls[0]


@pytest.mark.asyncio
async def test_make_fetch_tool_pin_without_ips_blocked():
    guard = UrlGuard(resolve_dns=False)  # не заполнит resolved_ips для hostname

    # Подмена check → allowed без ips
    def fake_check(url: str) -> UrlVerdict:
        return UrlVerdict(True, url, resolved_ips=[])

    guard.check = fake_check  # type: ignore
    tool = make_fetch_tool("fetch", fetch_fn=None, url_guard=guard, pin_ip=True)
    out = await tool.run({"url": "https://example.com/"})
    assert "no_resolved_ips_for_pinning" in out


@pytest.mark.asyncio
async def test_make_fetch_tool_pin_uses_public_ip(monkeypatch):
    seen = {}

    def fake_pinned(url, ips, timeout=15.0, max_bytes=1_000_000):
        seen["url"] = url
        seen["ips"] = list(ips)
        return "pinned-body"

    monkeypatch.setattr(
        "krepost.security.pinned_fetch.pinned_http_get", fake_pinned
    )
    # Re-import path used inside make_fetch_tool — patch where used after import
    monkeypatch.setattr(
        "krepost.orchestration.tools.pinned_http_get", fake_pinned, raising=False
    )

    # Patch the function used via local import inside _fn
    import krepost.security.pinned_fetch as pf

    monkeypatch.setattr(pf, "pinned_http_get", fake_pinned)

    guard = UrlGuard(resolve_dns=False)

    def fake_check(url: str) -> UrlVerdict:
        return UrlVerdict(True, url, resolved_ips=["93.184.216.34"])

    guard.check = fake_check  # type: ignore
    tool = make_fetch_tool("fetch", fetch_fn=None, url_guard=guard, pin_ip=True)
    out = await tool.run({"url": "https://example.com/"})
    assert out == "pinned-body"
    assert seen["ips"] == ["93.184.216.34"]
