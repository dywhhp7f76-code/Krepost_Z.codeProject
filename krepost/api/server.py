"""
krepost/api/server.py

Запуск сервиса. `build_demo_orchestrator()` собирает оркестратор БЕЗ реальных
моделей (EchoBackend + dev-guard), чтобы можно было поднять API локально и
увидеть полный цикл. main() слушает 127.0.0.1 (локальность §5.1), не 0.0.0.0.

    python -m krepost.api.server

⚠️  Демо-сборка НЕ для прода: dev-guard пропускает всё (GREEN). В проде на
    Layer 2 должен стоять реальный Qwen3Guard, а бэкенд — локальная LLM.
"""
from __future__ import annotations

import os
from pathlib import Path

from krepost.api.app import create_app
from krepost.orchestration.backends import EchoBackend
from krepost.orchestration.orchestrator import Orchestrator
from krepost.orchestration.router import Route, Router
from krepost.security.pipeline import SecurityPipeline

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


class _DevAllowGuard:
    """DEV-ONLY: guard-клиент, всегда отдающий GREEN. НИКОГДА не в прод —
    без реального Guard Layer 2 не защищает семантически."""

    async def chat(self, model=None, messages=None, format=None):
        return {"message": {"content":
                '{"status":"GREEN","reason":"dev_allow","confidence":1.0}'}}


_PROD_LIKE_ENVS = {"prod", "production", "staging"}


def build_demo_orchestrator(trust_db_path: Path | None = None) -> Orchestrator:
    # BUG-04-impl: dev-guard пропускает всё (GREEN). Предохранитель, чтобы он
    # не утёк в прод молча — падаем жёстко, а не деградируем защиту.
    env = os.environ.get("KREPOST_ENV", "").strip().lower()
    if env in _PROD_LIKE_ENVS:
        raise RuntimeError(
            f"build_demo_orchestrator() запрещён при KREPOST_ENV={env!r}: "
            "demo dev-guard пропускает всё. В проде используйте "
            "build_ollama_orchestrator()/build_openai_orchestrator() с реальным Guard."
        )
    logger.warning("DEMO orchestrator: dev-guard passes everything — NOT for production")
    pipeline = SecurityPipeline(
        guard_client=_DevAllowGuard(),
        trust_db_path=trust_db_path or Path("data/trust_registry.db"),
        enable_cache=False,
    )
    router = Router(
        routes=[
            Route("code", EchoBackend("code"), keywords=["python", "code", "код", "def "]),
        ],
        default=Route("general", EchoBackend("general")),
    )
    return Orchestrator(pipeline, router)


def main():  # pragma: no cover - точка запуска
    import uvicorn

    host = os.environ.get("KREPOST_API_HOST", "127.0.0.1")
    port = int(os.environ.get("KREPOST_API_PORT", "8000"))
    app = create_app(build_demo_orchestrator())
    logger.info(f"Krepost API (demo) on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    main()
