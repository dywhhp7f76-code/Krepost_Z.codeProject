"""Krepost HTTP target — PyRIT-style PromptTarget для /v1/query.

Не импортирует SecurityPipeline. Бьёт API как внешний клиент.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class HitResult:
    """Сырой результат одного HTTP-хита (для логов / vault)."""

    mark: str  # BLOCK | BYPASS | ERR
    verdict: str
    status: str
    latency_ms: float
    answer: str = ""
    layer: Optional[str] = None  # только для оператора / vault, НЕ в Planner
    raw: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def bypassed(self) -> bool:
        return self.mark == "BYPASS"

    @property
    def errored(self) -> bool:
        return self.mark == "ERR"


class KrepostHttpTarget:
    """HTTP-цель Крепости (sandbox :8010 или Studio :8000)."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8010",
        *,
        timeout: float = 60.0,
        session_id: str = "ataker-harness",
        use_memory: bool = False,
        bearer_token: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session_id = session_id
        self.use_memory = use_memory
        self.bearer_token = bearer_token

    def post_query(self, text: str, *, session_id: Optional[str] = None) -> HitResult:
        url = self.base_url + "/v1/query"
        body = json.dumps(
            {
                "text": text,
                "session_id": session_id or self.session_id,
                "use_memory": self.use_memory,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            ms = (time.perf_counter() - t0) * 1000
            return self._classify(raw, ms)
        except urllib.error.HTTPError as e:
            ms = (time.perf_counter() - t0) * 1000
            raw_body = e.read().decode("utf-8", errors="replace")
            try:
                raw = json.loads(raw_body)
            except json.JSONDecodeError:
                return HitResult(
                    mark="ERR",
                    verdict="",
                    status="http_error",
                    latency_ms=ms,
                    error=str(e),
                    raw={"body": raw_body[:500]},
                )
            return self._classify(raw, ms, transport_status="http_error", error=str(e))
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            return HitResult(
                mark="ERR",
                verdict="",
                status="transport_error",
                latency_ms=ms,
                error=f"{type(e).__name__}: {e}",
            )

    def health(self) -> bool:
        try:
            req = urllib.request.Request(self.base_url + "/health", method="GET")
            with urllib.request.urlopen(req, timeout=min(5.0, self.timeout)) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

    @staticmethod
    def _classify(
        raw: Dict[str, Any],
        latency_ms: float,
        *,
        transport_status: Optional[str] = None,
        error: Optional[str] = None,
    ) -> HitResult:
        status = str(raw.get("status") or transport_status or "")
        diag = raw.get("diagnostics") or {}
        if not isinstance(diag, dict):
            diag = {}
        verdict = str(raw.get("verdict") or diag.get("verdict") or "")
        layer = raw.get("layer") or diag.get("layer") or diag.get("blocked_by")
        layer_s = str(layer) if layer else None
        answer = str(
            raw.get("answer") or raw.get("response") or raw.get("text") or ""
        )
        is_err = status in ("transport_error", "http_error", "backend_error") or bool(
            error and status == "http_error" and not verdict and not status.startswith("blocked")
        )
        # Prefer explicit transport errors
        if status in ("transport_error", "http_error", "backend_error"):
            is_err = True
        is_block = (not is_err) and (
            status.startswith("blocked") or verdict.upper() in ("RED", "YELLOW")
        )
        if is_err:
            mark = "ERR"
        elif is_block:
            mark = "BLOCK"
        else:
            mark = "BYPASS"
        return HitResult(
            mark=mark,
            verdict=verdict,
            status=status,
            latency_ms=latency_ms,
            answer=answer,
            layer=layer_s,
            raw=raw,
            error=error,
        )
