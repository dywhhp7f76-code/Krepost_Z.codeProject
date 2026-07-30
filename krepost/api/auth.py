"""Operator auth for Krepost private chat.

Password now; TOTP/key hooks later (KREPOST_TOTP_SECRET reserved).

Env:
  KREPOST_OPERATOR_PASSWORD  — if set, /v1/query|agent|ingest|chat require Bearer token
  KREPOST_REQUIRE_AUTH=1     — fail closed even if password empty (401 until configured)
  KREPOST_SESSION_TTL_SEC    — token lifetime (default 86400)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set


PROTECTED_PREFIXES = (
    "/v1/query",
    "/v1/agent",
    "/v1/ingest",
    "/v1/login",  # login itself is public POST — excluded in middleware
)
PROTECTED_EXACT = {"/metrics", "/metrics/prometheus"}
PUBLIC_EXACT = {"/health", "/v1/login", "/chat", "/"}


@dataclass
class Session:
    token: str
    created_at: float
    expires_at: float


class AuthGate:
    def __init__(
        self,
        password: str = "",
        *,
        require_auth: bool = False,
        session_ttl_sec: int = 86400,
        totp_secret: str = "",  # reserved — enable later
    ):
        self._password = password
        self.require_auth = require_auth or bool(password)
        self.session_ttl_sec = max(60, session_ttl_sec)
        self.totp_secret = totp_secret  # unused until TOTP phase
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "AuthGate":
        pw = os.environ.get("KREPOST_OPERATOR_PASSWORD", "")
        require = os.environ.get("KREPOST_REQUIRE_AUTH", "0").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        ttl = int(os.environ.get("KREPOST_SESSION_TTL_SEC", "86400"))
        totp = os.environ.get("KREPOST_TOTP_SECRET", "")
        return cls(password=pw, require_auth=require, session_ttl_sec=ttl, totp_secret=totp)

    @property
    def enabled(self) -> bool:
        return self.require_auth

    @property
    def configured(self) -> bool:
        return bool(self._password)

    def verify_password(self, password: str, totp_code: str = "") -> bool:
        if not self._password:
            return False
        ok = hmac.compare_digest(
            hashlib.sha256(password.encode("utf-8")).digest(),
            hashlib.sha256(self._password.encode("utf-8")).digest(),
        )
        # TOTP later: if self.totp_secret — verify totp_code
        if self.totp_secret and totp_code:
            # Placeholder: reject until pyotp wired (operator said TOTP later)
            pass
        return ok

    def issue_token(self) -> Session:
        token = secrets.token_urlsafe(32)
        now = time.time()
        sess = Session(
            token=token,
            created_at=now,
            expires_at=now + self.session_ttl_sec,
        )
        with self._lock:
            self._sessions[token] = sess
        return sess

    def revoke(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def valid_token(self, token: str) -> bool:
        if not token:
            return False
        with self._lock:
            sess = self._sessions.get(token)
            if sess is None:
                return False
            if time.time() > sess.expires_at:
                self._sessions.pop(token, None)
                return False
            return True

    def needs_auth(self, path: str, method: str) -> bool:
        if not self.enabled:
            return False
        if path in PUBLIC_EXACT:
            return False
        if path == "/v1/login" and method.upper() == "POST":
            return False
        if path in PROTECTED_EXACT:
            return True
        for p in ("/v1/query", "/v1/agent", "/v1/ingest", "/v1/logout"):
            if path == p or path.startswith(p + "/"):
                return True
        return False

    def extract_bearer(self, authorization: Optional[str]) -> str:
        if not authorization:
            return ""
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return ""
