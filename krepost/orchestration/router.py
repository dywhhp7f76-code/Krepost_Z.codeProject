"""
krepost/orchestration/router.py

Маршрутизатор: детерминированно выбирает, какой модели отдать запрос.
Реализует принцип "разделение задач между моделями" (ARCHITECTURE_VISION §5.3):
одна модель — одна функция, оркестратор управляет потоками, малые контексты
вместо одного большого.

Router НЕ вызывает модель и НЕ занимается безопасностью — только выбор Route.
Гарантия детерминизма: при одном и том же вводе выбирается один и тот же Route
(маршруты упорядочены по priority, берётся первый сработавший; при равном
priority — порядок добавления). Default обязателен — маршрут находится всегда.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional, Sequence

from krepost.orchestration.backends import ModelBackend

if TYPE_CHECKING:
    from krepost.security.pipeline import SecurityContext

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


@dataclass
class Route:
    """Именованный маршрут к бэкенду с условиями срабатывания.

    Маршрут срабатывает, если сработал ЛЮБОЙ из заданных матчеров:
    - keyword есть как подстрока в тексте (без учёта регистра);
    - любой regex из patterns нашёл совпадение;
    - predicate(ctx) вернул True.
    Если ни один матчер не задан, маршрут не срабатывает никогда
    (кроме использования его как default в Router).
    """

    name: str
    backend: ModelBackend
    keywords: Sequence[str] = ()
    patterns: Sequence[str] = ()
    predicate: Optional[Callable[["SecurityContext"], bool]] = None
    priority: int = 0
    _compiled: list = field(default_factory=list, repr=False, init=False)

    def __post_init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]
        # Пустые/пробельные keyword'ы отбрасываем: "" как подстрока есть
        # в любом тексте и молча перехватил бы весь трафик на этот маршрут.
        self.keywords = tuple(k.lower() for k in self.keywords if k.strip())

    def matches(self, text_lower: str, ctx: "SecurityContext") -> bool:
        if any(k in text_lower for k in self.keywords):
            return True
        if any(rx.search(text_lower) for rx in self._compiled):
            return True
        if self.predicate is not None:
            try:
                return bool(self.predicate(ctx))
            except Exception as e:  # predicate не должен ронять маршрутизацию
                logger.warning(f"route {self.name!r} predicate raised: {e}")
                return False
        return False


class Router:
    """Выбор маршрута по проверенному контексту."""

    def __init__(self, routes: Sequence[Route], default: Route):
        if default is None:
            raise ValueError("Router requires a default route (fail-safe)")
        # Стабильная сортировка сохраняет порядок добавления при равном priority.
        self.routes = sorted(routes, key=lambda r: -r.priority)
        self.default = default

    def select(self, ctx: "SecurityContext") -> Route:
        text_lower = (ctx.user_input or "").lower()
        for route in self.routes:
            if route.matches(text_lower, ctx):
                return route
        return self.default
