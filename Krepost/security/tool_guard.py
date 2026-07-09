"""
krepost/security/tool_guard.py

Проверка результатов инструментов/MCP перед их подачей обратно в модель.

Дыра, которую это закрывает: пайплайн проверяет ВХОД (Layer 1-3) и финальный
ВЫХОД (Layer 4), но НЕ промежуточные tool-call результаты. Данные, возвращённые
инструментом/MCP-сервером, — это тоже недоверенный внешний контент: сервер
может встроить скрытые инструкции, а модель исполнит их как команды
(см. defense/2026-07-02: mcp-server-fetch обрезал документ и дописал команду;
defense/2026-07-01 Self-Study: фильтрация instruction-подобных спанов роняет
injection-compliance с 88% до 13%).

Двухуровневая реакция:
- HARD-сигналы (известные injection-паттерны, chat-template спуфинг, base64-
  payload) → BLOCK: такой tool-результат вообще не подаём в модель (fail-closed).
- SOFT-сигналы (instruction-подобные строки внутри данных) → SANITIZE: вырезаем
  подозрительную строку, остальные данные отдаём, факт фиксируем для аудита.

Переиспользует RegexFilter (Layer 1) и normalize_for_scanning — не дублирует
их. Проверка синхронная и чисто regex-овая; семантический слой (GuardClassifier
с prompt_template="output") можно навесить отдельно позже.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from krepost.security.normalize import normalize_for_scanning
from krepost.security.pipeline import RegexFilter

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


ToolOutputStatus = Literal["safe", "sanitized", "blocked"]


@dataclass
class ToolOutputVerdict:
    """Результат проверки. `output` пригоден к подаче в модель при status
    safe/sanitized и пуст при blocked."""

    status: ToolOutputStatus
    output: str
    reason: Optional[str] = None
    stripped_spans: List[str] = field(default_factory=list)

    @property
    def safe(self) -> bool:
        """True, если результат можно (хотя бы частично) отдать модели."""
        return self.status != "blocked"


class ToolOutputGuard:
    """Скан tool/MCP-результатов на инъекции-в-данных."""

    # SOFT: строки, где ДАННЫЕ пытаются адресоваться модели как инструкции.
    # То, что уже ловит RegexFilter (ignore previous, you are now, chat-
    # templates, base64), здесь не повторяем — оно идёт в HARD-блок.
    INSTRUCTION_IN_DATA = [
        r"(?i)\b(important|note|attention|reminder)\b\s*[:!].*\b(you|assistant|model|ai|llm|system)\b",
        r"(?i)\bnote to (the )?(ai|assistant|model|llm|system)\b",
        r"(?i)\bdo not (tell|inform|reveal to|mention to|notify) (the )?user\b",
        r"(?i)\bactually,?\s+(ignore|disregard|forget|stop|instead)\b",
        r"(?i)\b(you|the assistant|the model) (should|must|need to|have to) (now|immediately|instead)\b",
        r"(?i)\b(reveal|print|repeat|output|show|leak) (your |the )?(system )?(prompt|instructions?)\b",
        r"(?i)^-{2,}\s*end of (the )?(document|results?|output|tool|context)\b",  # фейковая граница
        r"(?i)<!--.*?-->",  # HTML-комментарий (скрытая инструкция)
        r"(?i)\bplease (ignore|disregard|forget) (everything|all|the) (above|previous|prior)\b",
    ]

    def __init__(self, regex_filter: Optional[RegexFilter] = None):
        self.layer1 = regex_filter or RegexFilter()
        self._instr = [re.compile(p) for p in self.INSTRUCTION_IN_DATA]

    def check(self, tool_output: str, tool_name: str = "") -> ToolOutputVerdict:
        if not tool_output:
            return ToolOutputVerdict("safe", "")

        # Нормализация для скана (гомоглифы, zero-width, control-символы).
        try:
            normalized = normalize_for_scanning(tool_output, soft=False)
        except ValueError:
            # Слишком длинный даже для нормализатора (>200k) — fail-closed.
            logger.warning(f"tool output too long to scan (tool={tool_name!r})")
            return ToolOutputVerdict("blocked", "", reason="tool_output_too_long")

        # ── HARD: известные injection-паттерны (по всему нормализованному тексту,
        #    без 32k-лимита RegexFilter — хвостовые инъекции важны для tool-выхода) ─
        for rx in self.layer1.compiled_patterns:
            if rx.search(normalized):
                return ToolOutputVerdict("blocked", "", reason=f"injection:{rx.pattern}")

        # chat-template спуфинг проверяем на сыром тексте (как в pipeline)
        for rx in self.layer1.chat_template_patterns:
            if rx.search(tool_output):
                return ToolOutputVerdict("blocked", "", reason=f"chat_template:{rx.pattern}")

        is_b64, payload = self.layer1.check_base64_payloads(tool_output)
        if is_b64:
            return ToolOutputVerdict("blocked", "", reason=f"base64:{payload}")

        # ── SOFT: вырезаем instruction-подобные строки, данные сохраняем ──────
        stripped: List[str] = []
        kept: List[str] = []
        for line in tool_output.split("\n"):
            if any(rx.search(line) for rx in self._instr):
                s = line.strip()
                if s:
                    stripped.append(s)
            else:
                kept.append(line)

        if stripped:
            return ToolOutputVerdict(
                "sanitized",
                "\n".join(kept),
                reason="instruction_in_data",
                stripped_spans=stripped,
            )

        return ToolOutputVerdict("safe", tool_output)
