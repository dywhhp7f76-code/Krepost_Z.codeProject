"""
Connect-time IP pinning для fetch после UrlGuard.

UrlGuard резолвит DNS на этапе check(); между проверкой и коннектом DNS
может смениться (rebinding). Этот модуль коннектится к УЖЕ проверенному IP
из UrlVerdict.resolved_ips, а Host/SNI оставляет оригинальным.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from typing import Sequence
from urllib.parse import urlsplit

from krepost.security.url_guard import _is_blocked_ip


def _pick_public_ip(resolved_ips: Sequence[str]) -> str:
    for raw in resolved_ips:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            continue
        return str(ip)
    raise ValueError("no_public_resolved_ip")


def pinned_http_get(
    url: str,
    resolved_ips: Sequence[str],
    *,
    timeout: float = 15.0,
    max_bytes: int = 1_000_000,
) -> str:
    """GET url, TCP/TLS к pinned IP; Host и SNI — оригинальный hostname."""
    if not resolved_ips:
        raise ValueError("no_resolved_ips_for_pinning")

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"scheme_not_allowed:{parts.scheme}")
    host = parts.hostname
    if not host:
        raise ValueError("no_host")

    safe_ip = _pick_public_ip(resolved_ips)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"

    raw_sock = socket.create_connection((safe_ip, port), timeout=timeout)
    try:
        if parts.scheme == "https":
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(raw_sock, server_hostname=host)
            raw_sock = None  # ownership moved
        else:
            sock = raw_sock
            raw_sock = None

        # HTTPConnection к IP; Host-заголовок — оригинальный hostname.
        conn = http.client.HTTPConnection(safe_ip, port=port, timeout=timeout)
        conn.sock = sock
        try:
            conn.request(
                "GET",
                path,
                headers={"Host": host, "User-Agent": "KrepostUrlGuard/1.0"},
            )
            resp = conn.getresponse()
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError("response_too_large")
            charset = "utf-8"
            ctype = resp.getheader("Content-Type", "") or ""
            if "charset=" in ctype.lower():
                charset = ctype.lower().split("charset=")[-1].split(";")[0].strip() or "utf-8"
            return data.decode(charset, errors="replace")
        finally:
            conn.close()
    finally:
        if raw_sock is not None:
            raw_sock.close()
