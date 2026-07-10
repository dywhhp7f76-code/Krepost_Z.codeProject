"""
krepost/security/url_guard.py

Валидация URL перед сетевым запросом — защита от SSRF.

Крепость в роли КЛИЕНТА ходит в облака (разведчик, tool-fetch, будущие
источники). Вредоносный источник или инъекция в контенте может подсунуть
URL, который уведёт запрос во внутреннюю сеть (SSRF) или на нестандартную
схему. Это недоверенные данные — URL проверяется ДО fetch.

Покрывает (defense/redteam digest 2026-07-02: URL Validation Bypass Cheat
Sheet, Concealing payloads in URL credentials):
- схема только из белого списка (http/https) — режет file://, gopher://,
  data:, ftp:// и пр.;
- запрет credentials в URL (user:pass@host) — скрытие payload/обход;
- запрет литеральных внутренних IP (RFC1918, loopback, link-local,
  reserved, multicast, unspecified) — IPv4 и IPv6, включая IPv4-mapped;
- запрет обфусцированных числовых хостов (decimal/hex/octal IP);
- запрет localhost;
- опционально: резолв DNS и проверка КАЖДОГО полученного IP.

Компонент чистый и детерминированный (по умолчанию без сети). resolve_dns
включает резолвинг; резолвер можно внедрить (тесты, кастомная логика).

ВНИМАНИЕ (TOCTOU / DNS rebinding): резолв на этапе валидации не защищает от
подмены DNS между проверкой и коннектом. Полная защита — пинить проверенный
IP и коннектиться именно к нему. Этот guard — необходимый, но не достаточный
слой; connect-time pinning остаётся за fetch-клиентом.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence
from urllib.parse import urlsplit

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


Resolver = Callable[[str], Sequence[str]]

_OCTAL_LABEL = re.compile(r"^0[0-7]+$")
_ALL_DIGITS = re.compile(r"^\d+$")


@dataclass
class UrlVerdict:
    allowed: bool
    url: str
    reason: Optional[str] = None
    resolved_ips: List[str] = field(default_factory=list)


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Внутренний/спец-диапазон, куда SSRF не должен ходить."""
    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
        return True
    # IPv4-mapped IPv6 (::ffff:127.0.0.1) — проверяем вложенный IPv4
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None and _is_blocked_ip(mapped):
        return True
    return False


def _default_resolver(host: str) -> List[str]:
    infos = socket.getaddrinfo(host, None)
    return [info[4][0] for info in infos]


class UrlGuard:
    """Проверка URL перед fetch."""

    def __init__(
        self,
        allowed_schemes: Sequence[str] = ("http", "https"),
        allow_hosts: Optional[Sequence[str]] = None,
        allowed_ports: Optional[Sequence[int]] = None,
        block_private: bool = True,
        resolve_dns: bool = False,
        resolver: Optional[Resolver] = None,
    ):
        self.allowed_schemes = tuple(s.lower() for s in allowed_schemes)
        self.allow_hosts = set(h.lower() for h in allow_hosts) if allow_hosts else None
        self.allowed_ports = set(allowed_ports) if allowed_ports else None
        self.block_private = block_private
        self.resolve_dns = resolve_dns
        self._resolver = resolver or _default_resolver

    def check(self, url: str) -> UrlVerdict:
        if not url or not url.strip():
            return UrlVerdict(False, url, reason="empty_url")

        # Пробелы/control-символы внутри URL — признак обфускации.
        if any(ord(c) < 0x21 for c in url.strip()):
            return UrlVerdict(False, url, reason="whitespace_in_url")

        url = url.strip()

        try:
            parts = urlsplit(url)
        except ValueError as e:
            return UrlVerdict(False, url, reason=f"malformed_url:{e}")

        scheme = parts.scheme.lower()
        if scheme not in self.allowed_schemes:
            return UrlVerdict(False, url, reason=f"scheme_not_allowed:{scheme or '(none)'}")

        if parts.username or parts.password:
            return UrlVerdict(False, url, reason="credentials_in_url")

        host = parts.hostname
        if not host:
            return UrlVerdict(False, url, reason="no_host")
        host = host.lower()

        try:
            port = parts.port
        except ValueError:
            return UrlVerdict(False, url, reason="invalid_port")
        if self.allowed_ports is not None and port is not None and port not in self.allowed_ports:
            return UrlVerdict(False, url, reason=f"port_not_allowed:{port}")

        # 1. Литеральный IP?
        try:
            ip = ipaddress.ip_address(host)
            if self.block_private and _is_blocked_ip(ip):
                return UrlVerdict(False, url, reason=f"private_ip:{host}")
            return UrlVerdict(True, url, resolved_ips=[str(ip)])
        except ValueError:
            pass  # не литеральный IP — идём дальше

        # 2. Обфусцированный числовой хост (decimal/hex/octal IP)?
        if self._is_obfuscated_host(host):
            return UrlVerdict(False, url, reason=f"obfuscated_host:{host}")

        # 3. localhost и его варианты
        if host == "localhost" or host.endswith(".localhost"):
            return UrlVerdict(False, url, reason="localhost")

        # 4. Allowlist хостов (если задан)
        if self.allow_hosts is not None and not self._host_allowed(host):
            return UrlVerdict(False, url, reason=f"host_not_allowlisted:{host}")

        # 5. Опциональный резолв DNS + проверка каждого IP
        if self.resolve_dns:
            try:
                ips = list(self._resolver(host))
            except Exception as e:
                logger.warning(f"DNS resolve failed for {host!r}: {e}")
                return UrlVerdict(False, url, reason="dns_resolve_failed")
            if not ips:
                return UrlVerdict(False, url, reason="dns_no_records")
            for raw in ips:
                try:
                    ip = ipaddress.ip_address(raw)
                except ValueError:
                    return UrlVerdict(False, url, reason=f"bad_resolved_ip:{raw}")
                if self.block_private and _is_blocked_ip(ip):
                    return UrlVerdict(False, url, reason=f"resolves_to_private:{raw}")
            return UrlVerdict(True, url, resolved_ips=[str(i) for i in ips])

        return UrlVerdict(True, url)

    def _host_allowed(self, host: str) -> bool:
        if host in self.allow_hosts:
            return True
        # поддомен разрешённого хоста
        return any(host.endswith("." + h) for h in self.allow_hosts)

    @staticmethod
    def _is_obfuscated_host(host: str) -> bool:
        # hex-обфускация вида 0x7f000001
        if "0x" in host:
            return True
        # чистое десятичное число (2130706433 == 127.0.0.1)
        if _ALL_DIGITS.match(host):
            return True
        # октальные лейблы (0177.0.0.1)
        if any(_OCTAL_LABEL.match(label) for label in host.split(".")):
            return True
        return False
