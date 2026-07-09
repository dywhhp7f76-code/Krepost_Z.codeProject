# Предложение 06: Execution-State Capsules

## Что

Интеграция механизма Execution-State Capsules (graph-bound checkpoint/restore) для snapshot/restore полного состояния исполнения LLM-модели в локальном inference-стеке Крепости. Капсулы снимают слепок ВСЕГО восстановимого состояния (KV-cache, recurrent state, convolution state, MTP state, метаданные), а не только KV-кэша.

Источник: [Execution-State Capsules](https://arxiv.org/abs/2606.20537v1)

## Зачем

### Ограничения текущего подхода

Текущий стек Крепости использует vLLM/PagedAttention для управления KV-cache. Однако:

1. **KV-only недостаточно** -- ablation в paper показывает, что восстановление только KV-cache приводит к расхождению вывода. Recurrent state, conv state критичны для корректности.
2. **Cold prefill при ветвлении** -- агенты Крепости (self-critique, red-team) постоянно ветвятся и откатываются. Каждый откат = cold prefill с нуля.
3. **Высокий TTFT** -- Time-To-First-Token на длинных контекстах (8k-16k) неприемлемо высок для интерактивных сценариев.

### Что дают капсулы

| Метрика | vLLM (текущее) | С капсулами | Выигрыш |
|---|---|---|---|
| Snapshot/restore | Нет (cold prefill) | Sub-millisecond (GPU-resident) | -- |
| TTFT на 2k токенов | Baseline | 3.9x быстрее | **3.9x** |
| TTFT на 8k токенов | Baseline | ~12x быстрее | **~12x** |
| TTFT на 16k токенов | Baseline | 27x быстрее | **27x** |
| Корректность | -- | Byte-exact, token-identical (greedy) | Гарантирована |

### Применение в Крепости

- **Red-teaming** -- fork состояния модели перед атакой, rollback после. Мгновенное ветвление без потери контекста.
- **Self-critique** -- параллельные ветки рассуждений (consensus) из одной контрольной точки.
- **Self-improvement** -- быстрый A/B тест вариантов ответа с восстановлением к checkpoint.
- **Отказоустойчивость** -- snapshot перед каждым шагом пайплайна, restore при сбое.

## Архитектура

### Текстовая диаграмма: интеграция с SecurityPipeline

```
                    ┌─────────────────────────────────────────────┐
                    │           SecurityPipeline v2.2              │
                    │                                             │
                    │  L1 Regex → L2 Guard → L3 FewShot → L4 Out │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       │ verdict=GREEN
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        CapsuleManager                                │
│                                                                      │
│   ┌────────────┐    ┌────────────────┐    ┌──────────────────┐      │
│   │  Capsule    │    │  Capsule        │    │  Capsule          │      │
│   │  Store      │    │  Scheduler      │    │  Fork Engine      │      │
│   │             │    │                 │    │                    │      │
│   │ snapshot()  │    │ auto_checkpoint │    │ fork(capsule_id)  │      │
│   │ restore()   │    │ gc_expired()    │    │ rollback(cap_id)  │      │
│   │ list()      │    │ retention_policy│    │ merge_consensus() │      │
│   └──────┬─────┘    └────────┬────────┘    └────────┬───────────┘      │
│          │                   │                      │                │
│          └───────────────────┼──────────────────────┘                │
│                              │                                       │
│                    ┌─────────▼──────────┐                           │
│                    │   FlashRT Runtime   │                           │
│                    │                     │                           │
│                    │  GPU-resident       │                           │
│                    │  Static buffers     │                           │
│                    │  Graph plans        │                           │
│                    │  Named buffer set   │                           │
│                    └─────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   vLLM / LocalAI    │
                    │   Inference Engine  │
                    └────────────────────┘
```

### Поток данных: fork/rollback для red-teaming

```
Turn N: Агент генерирует ответ
         │
         ├── snapshot(capsule_id="turn_N") ──── [sub-ms, GPU-resident]
         │
         ├── Fork A: red-team атака на ответ
         │     │
         │     ├── Результат: уязвимость найдена
         │     └── rollback(capsule_id="turn_N") ──── [sub-ms]
         │
         ├── Fork B: альтернативная генерация
         │     │
         │     ├── Результат: безопасный вариант
         │     └── сохранить как основную ветку
         │
         └── Fork C: self-critique
               │
               ├── Результат: оценка качества
               └── rollback(capsule_id="turn_N")

Consensus: выбрать лучший результат из Fork A/B/C
```

### Поток данных: checkpoint в SecurityPipeline

```
process() вызов:
  │
  ├── [checkpoint: pre_pipeline]
  │
  ├── Layer 1: RegexFilter
  │     ├── [checkpoint: post_L1]
  │     └── fail → rollback(pre_pipeline), return RED
  │
  ├── Layer 2: GuardClassifier
  │     ├── [checkpoint: post_L2]
  │     └── fail → rollback(post_L1), retry/return RED
  │
  ├── Layer 3: FewShotMatcher
  │     ├── [checkpoint: post_L3]
  │     └── fail → rollback(post_L2), retry/return RED
  │
  ├── Layer 4: OutputFilter
  │     └── fail → rollback(post_L3), regenerate
  │
  └── return GREEN + response
```

## Что добавляется

### Эскиз кода: CapsuleManager

```python
# krepost/inference/capsule_manager.py (эскиз)
"""
Execution-State Capsules для Крепости.
Управление snapshot/restore/fork/rollback полного состояния LLM inference.
"""

from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from loguru import logger


class CapsuleState(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    FORKED = "forked"
    EXPIRED = "expired"


@dataclass
class ExecutionCapsule:
    """Полный snapshot состояния исполнения модели."""
    capsule_id: str
    parent_id: Optional[str]       # None для корневых, capsule_id для форков
    session_id: str
    turn: int
    created_at: float = field(default_factory=time.time)
    state: CapsuleState = CapsuleState.ACTIVE
    token_position: int = 0        # Позиция в последовательности токенов

    # Метаданные буферов (сами буферы — на GPU)
    buffer_names: List[str] = field(default_factory=list)
    total_bytes: int = 0
    includes_kv_cache: bool = True
    includes_recurrent: bool = True
    includes_conv_state: bool = True
    includes_mtp_state: bool = True

    # Верификация
    content_hash: str = ""         # Хеш для проверки byte-exact restore

    @property
    def is_complete(self) -> bool:
        """Все компоненты состояния захвачены."""
        return all([
            self.includes_kv_cache,
            self.includes_recurrent,
            self.includes_conv_state,
            self.includes_mtp_state,
        ])


class CapsuleStore:
    """Хранилище капсул с retention policy."""

    def __init__(self, max_capsules: int = 64, ttl_seconds: float = 3600.0):
        self._capsules: Dict[str, ExecutionCapsule] = {}
        self._max_capsules = max_capsules
        self._ttl = ttl_seconds

    def put(self, capsule: ExecutionCapsule) -> None:
        if len(self._capsules) >= self._max_capsules:
            self._gc()
        self._capsules[capsule.capsule_id] = capsule
        logger.info(f"Capsule stored: {capsule.capsule_id} "
                    f"(turn={capsule.turn}, bytes={capsule.total_bytes})")

    def get(self, capsule_id: str) -> Optional[ExecutionCapsule]:
        cap = self._capsules.get(capsule_id)
        if cap and cap.state == CapsuleState.EXPIRED:
            return None
        return cap

    def list_for_session(self, session_id: str) -> List[ExecutionCapsule]:
        return [c for c in self._capsules.values()
                if c.session_id == session_id and c.state != CapsuleState.EXPIRED]

    def _gc(self) -> None:
        """Garbage collection: удалить expired и самые старые."""
        now = time.time()
        expired = [cid for cid, c in self._capsules.items()
                   if now - c.created_at > self._ttl]
        for cid in expired:
            self._capsules[cid].state = CapsuleState.EXPIRED
            del self._capsules[cid]
            logger.debug(f"Capsule expired: {cid}")

        # Если всё ещё полно — удалить самые старые
        while len(self._capsules) >= self._max_capsules:
            oldest = min(self._capsules.values(), key=lambda c: c.created_at)
            del self._capsules[oldest.capsule_id]
            logger.debug(f"Capsule evicted (oldest): {oldest.capsule_id}")


class CapsuleManager:
    """
    Высокоуровневый API для Execution-State Capsules.

    Интеграция с SecurityPipeline:
        manager = CapsuleManager()

        # Перед inference:
        capsule_id = manager.snapshot(session_id, turn, runtime_handle)

        # Fork для red-team:
        fork_id = manager.fork(capsule_id)

        # После анализа:
        manager.rollback(capsule_id, runtime_handle)
    """

    def __init__(self, max_capsules: int = 64, ttl_seconds: float = 3600.0):
        self._store = CapsuleStore(max_capsules, ttl_seconds)
        self._fork_counter = 0

    def snapshot(
        self,
        session_id: str,
        turn: int,
        runtime_handle,  # FlashRT runtime handle
        parent_id: Optional[str] = None,
    ) -> str:
        """
        Снять snapshot полного состояния исполнения.

        runtime_handle — абстракция над FlashRT/vLLM runtime.
        Реальная реализация вызывает GPU-операции snapshot буферов.
        """
        capsule_id = f"cap_{session_id}_{turn}_{int(time.time() * 1000)}"

        # --- GPU OPERATIONS (заглушка) ---
        # В реальной реализации:
        # buffers = runtime_handle.snapshot_all_buffers()
        # content_hash = runtime_handle.compute_buffer_hash()
        # total_bytes = sum(b.nbytes for b in buffers.values())
        buffer_names = ["kv_cache", "recurrent_state", "conv_state", "mtp_state"]
        content_hash = hashlib.sha256(capsule_id.encode()).hexdigest()[:32]
        total_bytes = 0  # Заглушка
        # --- END GPU OPERATIONS ---

        capsule = ExecutionCapsule(
            capsule_id=capsule_id,
            parent_id=parent_id,
            session_id=session_id,
            turn=turn,
            buffer_names=buffer_names,
            total_bytes=total_bytes,
            content_hash=content_hash,
        )
        self._store.put(capsule)

        logger.info(f"Snapshot created: {capsule_id} (session={session_id}, turn={turn})")
        return capsule_id

    def restore(self, capsule_id: str, runtime_handle) -> bool:
        """
        Восстановить состояние из капсулы.

        Возвращает True при успешном восстановлении.
        """
        capsule = self._store.get(capsule_id)
        if capsule is None:
            logger.error(f"Capsule not found: {capsule_id}")
            return False

        # --- GPU OPERATIONS (заглушка) ---
        # runtime_handle.restore_all_buffers(capsule.buffer_names)
        # assert runtime_handle.compute_buffer_hash() == capsule.content_hash
        # --- END GPU OPERATIONS ---

        logger.info(f"Restored from capsule: {capsule_id} "
                    f"(turn={capsule.turn}, bytes={capsule.total_bytes})")
        return True

    def fork(self, capsule_id: str) -> Optional[str]:
        """
        Создать fork от существующей капсулы.

        Fork = snapshot + новый capsule_id с parent_id → оригинал.
        """
        parent = self._store.get(capsule_id)
        if parent is None:
            logger.error(f"Cannot fork: capsule {capsule_id} not found")
            return None

        self._fork_counter += 1
        fork_id = f"{capsule_id}_fork_{self._fork_counter}"

        fork_capsule = ExecutionCapsule(
            capsule_id=fork_id,
            parent_id=capsule_id,
            session_id=parent.session_id,
            turn=parent.turn,
            state=CapsuleState.FORKED,
            token_position=parent.token_position,
            buffer_names=list(parent.buffer_names),
            total_bytes=parent.total_bytes,
            content_hash=parent.content_hash,
            includes_kv_cache=parent.includes_kv_cache,
            includes_recurrent=parent.includes_recurrent,
            includes_conv_state=parent.includes_conv_state,
            includes_mtp_state=parent.includes_mtp_state,
        )
        self._store.put(fork_capsule)

        parent.state = CapsuleState.ARCHIVED
        logger.info(f"Forked {capsule_id} -> {fork_id}")
        return fork_id

    def rollback(self, capsule_id: str, runtime_handle) -> bool:
        """Rollback = restore + удалить все форки от этой капсулы."""
        if not self.restore(capsule_id, runtime_handle):
            return False

        # Удалить дочерние форки
        children = [c for c in self._store._capsules.values()
                    if c.parent_id == capsule_id]
        for child in children:
            child.state = CapsuleState.EXPIRED
            logger.debug(f"Rolled back fork: {child.capsule_id}")

        return True
```

### Точки интеграции с SecurityPipeline

```python
# Изменения в krepost/security/pipeline.py

class SecurityPipeline:
    def __init__(self, ..., capsule_manager: Optional[CapsuleManager] = None):
        # ... существующая инициализация ...
        self.capsules = capsule_manager

    async def process_with_capsules(
        self,
        text: str,
        session_id: str,
        runtime_handle=None,
    ) -> SecurityContext:
        """
        Обработка с checkpoint/rollback на каждом слое.
        """
        if self.capsules and runtime_handle:
            pre_id = self.capsules.snapshot(session_id, turn=0, runtime_handle=runtime_handle)

        ctx = await self.process(text, session_id)

        if ctx.verdict == "RED" and self.capsules and runtime_handle:
            # Rollback при провале — восстановить чистое состояние
            self.capsules.rollback(pre_id, runtime_handle)

        return ctx

    async def red_team_with_fork(
        self,
        response: str,
        session_id: str,
        capsule_id: str,
        runtime_handle,
        num_branches: int = 3,
    ) -> List[dict]:
        """
        Параллельный red-team через fork капсул.
        Каждая ветка атакует ответ независимо, затем rollback.
        """
        results = []
        for i in range(num_branches):
            fork_id = self.capsules.fork(capsule_id)
            if fork_id is None:
                continue

            # Восстановить состояние в ветке
            self.capsules.restore(fork_id, runtime_handle)

            # Запустить red-team атаку в этой ветке
            attack_result = await self._run_red_team_branch(response, i)
            results.append({
                "branch": i,
                "fork_id": fork_id,
                "result": attack_result,
            })

            # Rollback
            self.capsules.rollback(capsule_id, runtime_handle)

        return results
```

## Зависимости

| Зависимость | Назначение | Статус |
|---|---|---|
| FlashRT runtime | White-box kernel для graph-based inference | Требуется порт/интеграция |
| NVIDIA GPU (CUDA) | GPU-resident буферы для sub-ms snapshot/restore | Mac Studio: MPS/Metal; требуется адаптация |
| vLLM >= 0.22 | Текущий inference engine | Уже развёрнут |
| asyncio | Асинхронные операции | Уже используется |

**Критическое замечание**: FlashRT протестирован на RTX 5090 (CUDA). Для Mac Studio (Apple Silicon / MPS) потребуется адаптация buffer management под Metal API. Альтернатива: использовать CPU-fallback для snapshot/restore (медленнее, но функционально).

## Риски

| Риск | Уровень | Митигация |
|---|---|---|
| FlashRT не поддерживает Apple Silicon / Metal | Высокий | CPU-fallback; мониторинг портирования FlashRT на Metal; рассмотреть отдельный CUDA-узел |
| Потребление GPU-памяти под буферы капсул | Средний | Retention policy: max 64 капсул, TTL 1 час; GC при нехватке памяти |
| Расхождение при non-greedy decode после restore | Низкий | Paper подтверждает byte-exact для greedy; для sampling — ожидаемое поведение |
| Сложность интеграции с vLLM internal state | Высокий | Начать с API-уровня (snapshot/restore через vLLM API); глубокая интеграция — фаза 2 |
| Latency overhead от snapshot на каждом ходу | Низкий | Sub-millisecond на GPU; checkpoint только на границах слоёв пайплайна |

## Этапы внедрения

1. **Фаза 1: Прототип** -- CPU-based capsule store с сериализацией состояния через pickle/safetensors
2. **Фаза 2: GPU интеграция** -- подключение FlashRT или эквивалента для GPU-resident буферов
3. **Фаза 3: Fork/rollback** -- интеграция с SecurityPipeline для red-teaming
4. **Фаза 4: Consensus** -- параллельные ветки с выбором лучшего результата

## Статус: ⏳ Ожидает одобрения
