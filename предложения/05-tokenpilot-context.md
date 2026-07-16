# Предложение 05: Интеграция TokenPilot в SMART_CACHE

**Статус:** ✅ ОДОБРЕНО (2026-07-16) — оператор одобрил к реализации; интеграция в ContextWindowManager запланирована после стабилизации RAG.

## Что

Интеграция подхода TokenPilot (Cache-Efficient Context Management) в слой SMART_CACHE Крепости для оптимизации управления контекстом долгоживущих LLM-агентов. Два ключевых механизма:

1. **Ingestion-Aware Compaction** -- стабилизация prompt-префиксов для максимального переиспользования KV-cache
2. **Lifecycle-Aware Eviction** -- отслеживание остаточной полезности сегментов контекста с выгрузкой по batch-turn расписанию

Источник: [TokenPilot: Cache-Efficient Context Management for LLM Agents](https://arxiv.org/abs/2606.17016v1)

## Зачем

### Проблема

Текущий SMART_CACHE (v2.1) оперирует тремя слоями (L1 embedding, L2 RAG, L3 LLM) и кэширует результаты по хешам/эмбеддингам. Однако он **не управляет контекстным окном** самой модели:

- Накопление контекста в длинных агентских сессиях раздувает стоимость инференса (квадратичная зависимость attention)
- Наивная обрезка контекста (text pruning, sliding window) **ломает prompt prefix** -> cache invalidation в vLLM/PagedAttention -> cold prefill -> деградация TTFT
- Eviction без учёта lifecycle задачи удаляет релевантные сегменты и сохраняет мусорные

### Решение TokenPilot

| Метрика | До TokenPilot | После TokenPilot |
|---|---|---|
| Стоимость токенов | Baseline | **-61% до -87%** |
| Cache hit rate (KV) | Деградирует при росте контекста | Стабилизирован через prefix alignment |
| Качество ответов | Baseline | Сопоставимо (без деградации) |

### Критичность для Крепости

- **VRAM-экономия** -- Mac Studio с ограниченной GPU-памятью; стабильные KV-cache prefix = меньше перевычислений
- **Длинные агентские сессии** -- агенты self-critique, red-team, self-improvement работают десятки ходов; контекст растёт экспоненциально
- **Локальный инференс** -- каждый сэкономленный токен = реальная экономия ресурсов (нет внешнего API)

## Что добавляется

### Архитектура изменений

```
┌──────────────────────────────────────────────────────────┐
│                     CacheLayer (v2.2)                     │
│                                                          │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │  L1 Embedding    │  │  НОВОЕ: ContextWindowManager │  │
│  │  L2 RAG Results  │  │  ┌────────────────────────┐  │  │
│  │  L3 LLM Response │  │  │ IngestionCompactor     │  │  │
│  │                   │  │  │  - prefix stabilizer   │  │  │
│  │  (существующее)   │  │  │  - noise gate          │  │  │
│  │                   │  │  ├────────────────────────┤  │  │
│  │                   │  │  │ LifecycleEvictor       │  │  │
│  │                   │  │  │  - segment tracker     │  │  │
│  │                   │  │  │  - utility scorer      │  │  │
│  │                   │  │  │  - batch-turn eviction │  │  │
│  └─────────────────┘  │  └────────────────────────┘  │  │
│                        └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Эскиз кода: ContextWindowManager

```python
# krepost/cache/context_window.py (эскиз)
"""
TokenPilot-style контекст-менеджер для интеграции в SMART_CACHE.
Стабилизирует prompt-prefix и управляет lifecycle сегментов контекста.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict

from loguru import logger


class SegmentRole(str, Enum):
    """Роль сегмента в контексте."""
    SYSTEM = "system"           # Системный промпт (никогда не evict)
    INSTRUCTION = "instruction" # Инструкция текущей задачи
    HISTORY = "history"         # История диалога
    TOOL_RESULT = "tool_result" # Результат вызова инструмента
    SCRATCH = "scratch"         # Временные рассуждения (первый кандидат на eviction)


@dataclass
class ContextSegment:
    """Отслеживаемый сегмент контекста с метаданными lifecycle."""
    segment_id: str
    role: SegmentRole
    content: str
    token_count: int
    created_at_turn: int
    last_referenced_turn: int
    reference_count: int = 0
    utility_score: float = 1.0  # [0.0, 1.0] — остаточная полезность

    @property
    def age_turns(self) -> int:
        """Сколько ходов назад сегмент был создан (относительно last_referenced_turn)."""
        return self.last_referenced_turn - self.created_at_turn

    @property
    def prefix_hash(self) -> str:
        """Хеш для стабилизации prefix."""
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]


class IngestionCompactor:
    """
    Ingestion-Aware Compaction: стабилизация prompt-prefix.

    Гарантирует, что начало промпта (system + instruction) остаётся
    идентичным между ходами → KV-cache prefix reuse в vLLM/PagedAttention.
    """

    def __init__(self, noise_threshold: float = 0.15):
        self._stable_prefix: Optional[str] = None
        self._prefix_hash: Optional[str] = None
        self._noise_threshold = noise_threshold  # доля "шумовых" токенов

    def stabilize_prefix(
        self, segments: List[ContextSegment]
    ) -> Tuple[List[ContextSegment], str]:
        """
        Упорядочить сегменты так, чтобы prefix оставался стабильным.

        Возвращает (упорядоченные сегменты, prefix_hash).
        """
        # Стабильная часть: SYSTEM + INSTRUCTION всегда в начале, неизменны
        stable = [s for s in segments if s.role in (SegmentRole.SYSTEM, SegmentRole.INSTRUCTION)]
        dynamic = [s for s in segments if s.role not in (SegmentRole.SYSTEM, SegmentRole.INSTRUCTION)]

        # Noise gate: отфильтровать сегменты с низкой информативностью
        dynamic_filtered = []
        for seg in dynamic:
            if seg.role == SegmentRole.SCRATCH and seg.utility_score < self._noise_threshold:
                logger.debug(f"Noise gate: отброшен scratch-сегмент {seg.segment_id} "
                             f"(utility={seg.utility_score:.2f})")
                continue
            dynamic_filtered.append(seg)

        ordered = stable + dynamic_filtered
        prefix_content = "".join(s.content for s in stable)
        prefix_hash = hashlib.sha256(prefix_content.encode()).hexdigest()[:16]

        if self._prefix_hash and self._prefix_hash != prefix_hash:
            logger.warning(f"Prefix changed: {self._prefix_hash} -> {prefix_hash} "
                           f"(KV-cache invalidation!)")

        self._prefix_hash = prefix_hash
        return ordered, prefix_hash


class LifecycleEvictor:
    """
    Lifecycle-Aware Eviction: выгрузка сегментов по остаточной полезности.

    Не выгружает сегменты сразу при превышении лимита — ждёт batch-turn
    границы, чтобы минимизировать нарушение prefix alignment.
    """

    def __init__(
        self,
        max_context_tokens: int = 8192,
        eviction_batch_turns: int = 3,
        min_utility: float = 0.1,
        decay_rate: float = 0.15,
    ):
        self.max_context_tokens = max_context_tokens
        self.eviction_batch_turns = eviction_batch_turns
        self.min_utility = min_utility
        self.decay_rate = decay_rate
        self._current_turn = 0
        self._last_eviction_turn = 0

    def update_turn(self, turn: int):
        self._current_turn = turn

    def decay_utilities(self, segments: List[ContextSegment]) -> None:
        """Обновить utility_score на основе возраста и обращений."""
        for seg in segments:
            if seg.role == SegmentRole.SYSTEM:
                seg.utility_score = 1.0  # Системные сегменты не деградируют
                continue

            turns_since_ref = self._current_turn - seg.last_referenced_turn
            # Экспоненциальный decay с учётом количества обращений
            recency_factor = max(0.0, 1.0 - self.decay_rate * turns_since_ref)
            frequency_bonus = min(0.3, seg.reference_count * 0.05)
            seg.utility_score = min(1.0, recency_factor + frequency_bonus)

    def should_evict(self, segments: List[ContextSegment]) -> bool:
        """Проверить, нужна ли eviction."""
        total_tokens = sum(s.token_count for s in segments)
        turns_since_eviction = self._current_turn - self._last_eviction_turn
        return (
            total_tokens > self.max_context_tokens
            and turns_since_eviction >= self.eviction_batch_turns
        )

    def evict(self, segments: List[ContextSegment]) -> Tuple[List[ContextSegment], List[ContextSegment]]:
        """
        Выгрузить сегменты с наименьшей полезностью.

        Возвращает (оставшиеся, выгруженные).
        """
        if not self.should_evict(segments):
            return segments, []

        self.decay_utilities(segments)

        # Сортировка кандидатов: SYSTEM/INSTRUCTION не трогаем
        evictable = [s for s in segments if s.role not in (SegmentRole.SYSTEM, SegmentRole.INSTRUCTION)]
        protected = [s for s in segments if s.role in (SegmentRole.SYSTEM, SegmentRole.INSTRUCTION)]

        evictable.sort(key=lambda s: s.utility_score)

        total_tokens = sum(s.token_count for s in segments)
        evicted = []
        while total_tokens > self.max_context_tokens and evictable:
            candidate = evictable[0]
            if candidate.utility_score > self.min_utility:
                break  # Не выгружать полезные сегменты
            evicted.append(evictable.pop(0))
            total_tokens -= candidate.token_count
            logger.info(f"Evicted segment {candidate.segment_id} "
                        f"(role={candidate.role.value}, utility={candidate.utility_score:.2f}, "
                        f"tokens={candidate.token_count})")

        self._last_eviction_turn = self._current_turn
        return protected + evictable, evicted


class ContextWindowManager:
    """
    Главный менеджер контекстного окна. Интегрируется в CacheLayer.

    Использование:
        cwm = ContextWindowManager(max_tokens=8192)
        cwm.add_segment("sys", SegmentRole.SYSTEM, system_prompt, token_count=200)
        cwm.add_segment("q1", SegmentRole.HISTORY, user_query, token_count=50)

        # На каждом ходе агента:
        optimized, prefix_hash = cwm.optimize(current_turn=5)
    """

    def __init__(self, max_tokens: int = 8192, eviction_batch_turns: int = 3):
        self._segments: OrderedDict[str, ContextSegment] = OrderedDict()
        self._compactor = IngestionCompactor()
        self._evictor = LifecycleEvictor(
            max_context_tokens=max_tokens,
            eviction_batch_turns=eviction_batch_turns,
        )
        self._eviction_log: List[dict] = []

    def add_segment(
        self,
        segment_id: str,
        role: SegmentRole,
        content: str,
        token_count: int,
        turn: int = 0,
    ) -> None:
        """Добавить или обновить сегмент контекста."""
        if segment_id in self._segments:
            seg = self._segments[segment_id]
            seg.last_referenced_turn = turn
            seg.reference_count += 1
            return

        self._segments[segment_id] = ContextSegment(
            segment_id=segment_id,
            role=role,
            content=content,
            token_count=token_count,
            created_at_turn=turn,
            last_referenced_turn=turn,
        )

    def reference(self, segment_id: str, turn: int) -> None:
        """Пометить сегмент как использованный на данном ходу."""
        if segment_id in self._segments:
            seg = self._segments[segment_id]
            seg.last_referenced_turn = turn
            seg.reference_count += 1

    def optimize(self, current_turn: int) -> Tuple[List[ContextSegment], str]:
        """
        Оптимизировать контекстное окно: compaction + eviction.

        Возвращает (оптимизированные сегменты, prefix_hash).
        """
        self._evictor.update_turn(current_turn)
        segments = list(self._segments.values())

        # 1. Lifecycle-Aware Eviction
        remaining, evicted = self._evictor.evict(segments)
        for seg in evicted:
            self._eviction_log.append({
                "segment_id": seg.segment_id,
                "role": seg.role.value,
                "turn": current_turn,
                "utility": seg.utility_score,
                "tokens_freed": seg.token_count,
            })
            del self._segments[seg.segment_id]

        # 2. Ingestion-Aware Compaction (стабилизация prefix)
        ordered, prefix_hash = self._compactor.stabilize_prefix(remaining)

        return ordered, prefix_hash

    @property
    def total_tokens(self) -> int:
        return sum(s.token_count for s in self._segments.values())

    @property
    def stats(self) -> dict:
        return {
            "total_segments": len(self._segments),
            "total_tokens": self.total_tokens,
            "eviction_events": len(self._eviction_log),
            "tokens_evicted_total": sum(e["tokens_freed"] for e in self._eviction_log),
            "segments_by_role": {
                role.value: sum(1 for s in self._segments.values() if s.role == role)
                for role in SegmentRole
            },
        }
```

### Интеграция в CacheLayer

Изменения в `krepost/cache/SMART_CACHE.py`:

```python
# В классе CacheLayer.__init__:
from krepost.cache.context_window import ContextWindowManager, SegmentRole

class CacheLayer:
    def __init__(self, ...):
        # ... существующая инициализация L1/L2/L3 ...

        # НОВОЕ: TokenPilot context management
        self._context_managers: Dict[str, ContextWindowManager] = {}

    def _get_context_manager(self, session_id: str) -> ContextWindowManager:
        """Получить или создать ContextWindowManager для сессии."""
        if session_id not in self._context_managers:
            self._context_managers[session_id] = ContextWindowManager(
                max_tokens=8192,
                eviction_batch_turns=3,
            )
        return self._context_managers[session_id]

    async def process_with_context(
        self, query: str, session_id: str, turn: int, token_count: int
    ) -> Tuple[Optional[str], str]:
        """
        Обработать запрос с учётом контекстного окна.

        Возвращает (cached_response | None, prefix_hash).
        """
        cwm = self._get_context_manager(session_id)

        # Добавить текущий запрос как сегмент
        seg_id = f"turn_{turn}_query"
        cwm.add_segment(seg_id, SegmentRole.HISTORY, query, token_count, turn)

        # Оптимизировать окно
        segments, prefix_hash = cwm.optimize(turn)

        # Стандартный cache lookup (L1 -> L2 -> L3)
        cached = await self.get(query)

        return cached, prefix_hash
```

## Зависимости

| Зависимость | Назначение |
|---|---|
| SMART_CACHE v2.1+ | Базовый слой для интеграции |
| vLLM/PagedAttention | KV-cache, для которого стабилизируется prefix |
| sentence-transformers | Уже используется в L1/L2 |
| loguru | Уже используется |

Новых внешних зависимостей **не требуется**.

## Риски

| Риск | Уровень | Митигация |
|---|---|---|
| Неверная оценка utility ведёт к потере важного контекста | Средний | Консервативный min_utility=0.1; SYSTEM/INSTRUCTION никогда не выгружаются; лог eviction для отладки |
| Overhead ContextWindowManager на каждом ходу | Низкий | O(n) по сегментам; типичная сессия <100 сегментов |
| Рассогласование prefix_hash с реальным KV-cache vLLM | Средний | Требуется интеграционное тестирование с vLLM; prefix_hash — индикатор, а не гарантия |
| Утечка памяти в _context_managers для завершённых сессий | Низкий | Добавить TTL/cleanup для неактивных сессий |

## Ожидаемые результаты

По данным TokenPilot paper:
- **-61%** снижение стоимости токенов при умеренных агентских сессиях (10-30 ходов)
- **-87%** снижение стоимости при длинных сессиях (50+ ходов) с большим накоплением контекста
- **0% деградация качества** -- компакция и eviction сохраняют релевантные сегменты
- **Стабильный KV-cache hit rate** -- prefix alignment предотвращает cache invalidation

## Статус: ⏳ Ожидает одобрения
