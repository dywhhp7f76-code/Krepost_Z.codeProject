"""
Пробник #35 (BUG-03): url_guard.check() в fetch-инструменте не должен
блокировать event loop.

При resolve_dns=True check() зовёт синхронный socket.getaddrinfo, а вызов в
make_fetch_tool._fn был синхронным прямо в корутине → блокировал loop.
Фикс: offload через asyncio.to_thread (без новой зависимости aiodns).

Проверяем детерминированно: резолвер запоминает поток, в котором его вызвали.
До фикса он бы совпал с потоком event loop; после — исполняется в отдельном
потоке (значит check() ушёл с loop'а).
"""
import asyncio
import threading

import pytest

from krepost.orchestration.tools import make_fetch_tool
from krepost.security.url_guard import UrlGuard


class TestUrlCheckOffloaded:

    @pytest.mark.asyncio
    async def test_check_runs_off_event_loop(self):
        loop_thread = threading.get_ident()
        seen = {}

        def resolver(host):
            seen["thread"] = threading.get_ident()
            return ["93.184.216.34"]  # публичный IP — не блокируется

        guard = UrlGuard(resolve_dns=True, resolver=resolver)
        tool = make_fetch_tool("fetch", lambda u: "OK", url_guard=guard)

        result = await tool.run({"url": "http://example.com"})
        assert result == "OK"
        assert "thread" in seen, "резолвер не был вызван"
        assert seen["thread"] != loop_thread, \
            "url_guard.check() исполнился в потоке event loop — блокирует его"

    @pytest.mark.asyncio
    async def test_blocked_url_still_blocks(self):
        # предохранитель не должен ослабнуть: приватный IP по-прежнему режется
        guard = UrlGuard(resolve_dns=False)
        tool = make_fetch_tool("fetch", lambda u: "SHOULD_NOT_RUN", url_guard=guard)
        res = await tool.run({"url": "http://169.254.169.254/latest/meta-data"})
        assert res.startswith("[fetch blocked")
