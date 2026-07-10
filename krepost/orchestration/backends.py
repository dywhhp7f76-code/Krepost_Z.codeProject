"""
krepost/orchestration/backends.py

Абстракция модели-исполнителя. Оркестратор не знает, что за модель стоит
за бэкендом — Ollama, MLX, vLLM или мок. Это прямое следствие принципа
"архитектура важнее модели" (ARCHITECTURE_VISION §5.2): ни один компонент
не завязан на конкретную модель сильнее, чем необходимо.

ModelBackend — это Protocol (структурная типизация): бэкендом считается
что угодно с атрибутом `name` и async-методом `generate`. Никакого
наследования не требуется.
"""
from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Protocol, Union, runtime_checkable

if TYPE_CHECKING:
    from krepost.security.pipeline import SecurityContext

try:
    from loguru import logger
except ImportError:  # pragma: no cover - fallback без loguru
    import logging

    logger = logging.getLogger("Krepost")


@runtime_checkable
class ModelBackend(Protocol):
    """Контракт исполнителя. Бэкенд получает уже проверенный (GREEN) ввод.

    ВАЖНО: на вход генерации подаётся исходный текст пользователя, а НЕ
    нормализованная форма — нормализация (гомоглифы, схлопывание пробелов)
    предназначена только для сканирования и искажает смысл для генерации.
    Контекст `ctx` доступен как read-only источник метаданных.
    """

    name: str

    async def generate(self, prompt: str, ctx: "SecurityContext") -> str: ...


GenerateFn = Union[
    Callable[[str, "SecurityContext"], str],
    Callable[[str, "SecurityContext"], Awaitable[str]],
]


class CallableBackend:
    """Бэкенд-обёртка над произвольной функцией (sync или async).

    Sync-функция исполняется через asyncio.to_thread, чтобы не блокировать
    event loop — тот же приём, что и во всём пайплайне.
    """

    def __init__(self, name: str, fn: GenerateFn):
        self.name = name
        self._fn = fn
        # Ловим и async-функции, и объекты с async __call__ (напр. partial
        # уже покрыт iscoroutinefunction, но callable-класс с async __call__
        # — нет; иначе он ушёл бы в to_thread и вернул корутину).
        self._is_async = inspect.iscoroutinefunction(fn) or inspect.iscoroutinefunction(
            getattr(fn, "__call__", None)
        )

    async def generate(self, prompt: str, ctx: "SecurityContext") -> str:
        if self._is_async:
            result = await self._fn(prompt, ctx)  # type: ignore[misc]
        else:
            result = await asyncio.to_thread(self._fn, prompt, ctx)
        if not isinstance(result, str):
            # Бэкенд обязан вернуть строку; иначе это ошибка бэкенда,
            # а не молчаливое приведение к str (маскирует баги).
            raise TypeError(
                f"backend {self.name!r} returned {type(result).__name__}, expected str"
            )
        return result


class EchoBackend:
    """Тривиальный бэкенд для разработки и тестов: возвращает фиксированный
    ответ (по умолчанию — эхо ввода с префиксом имени)."""

    def __init__(self, name: str = "echo", reply: Any = None):
        self.name = name
        self._reply = reply

    async def generate(self, prompt: str, ctx: "SecurityContext") -> str:
        if self._reply is not None:
            return str(self._reply)
        return f"[{self.name}] {prompt}"
