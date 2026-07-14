"""
T8 alerting-infra: webhook-оповещения при pii_filter_healthy=False.

Опциональный KREPOST_ALERT_WEBHOOK. Debounce предотвращает спам при частых
опросах /metrics.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")

AlertSender = Callable[[str, Dict[str, Any]], None]

DEFAULT_DEBOUNCE_SEC = 300.0


class AlertDispatcher:
    """Отправка алертов при деградации PII-фильтра (канарейка fail-open)."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        *,
        debounce_sec: float = DEFAULT_DEBOUNCE_SEC,
        sender: Optional[AlertSender] = None,
    ):
        self.webhook_url = webhook_url or os.environ.get("KREPOST_ALERT_WEBHOOK")
        self.debounce_sec = debounce_sec
        self._sender = sender
        self._last_pii_alert = 0.0
        self._lock = threading.Lock()

    def maybe_alert_pii_unhealthy(self, metrics: Dict[str, Any]) -> bool:
        """Вернуть True, если алерт отправлен (или поставлен в очередь)."""
        if metrics.get("pii_filter_healthy", True):
            return False
        if not self.webhook_url and not self._sender:
            return False

        with self._lock:
            now = time.time()
            if now - self._last_pii_alert < self.debounce_sec:
                return False
            self._last_pii_alert = now

        payload = {
            "event": "pii_filter_unhealthy",
            "total_requests": metrics.get("total_requests", 0),
            "pii_redactions": metrics.get("pii_redactions", 0),
            "secret_redactions": metrics.get("secret_redactions", 0),
        }

        if self._sender:
            self._sender(self.webhook_url or "mock://webhook", payload)
            return True

        self._post_webhook(payload)
        return True

    def _post_webhook(self, payload: Dict[str, Any]) -> None:
        if not self.webhook_url:
            return
        try:
            import httpx

            httpx.post(self.webhook_url, json=payload, timeout=5.0)
        except Exception as e:  # pragma: no cover
            logger.warning(f"alert webhook failed: {type(e).__name__}: {e}")


def format_prometheus_metrics(metrics: Dict[str, Any]) -> str:
    """Текстовый экспорт ключевых метрик (Prometheus-style, без labels)."""
    lines = [
        f"krepost_total_requests {metrics.get('total_requests', 0)}",
        f"krepost_pii_redactions {metrics.get('pii_redactions', 0)}",
        f"krepost_secret_redactions {metrics.get('secret_redactions', 0)}",
        (
            "krepost_pii_filter_healthy "
            f"{1 if metrics.get('pii_filter_healthy') else 0}"
        ),
    ]
    return "\n".join(lines) + "\n"
