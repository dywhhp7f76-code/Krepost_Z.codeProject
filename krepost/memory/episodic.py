"""
krepost/memory/episodic.py
Episodic Memory v2.0 — долговременная эпизодическая память.

Хранит query+response пары с двумя эмбеддингами для семантического поиска.
Поддерживает security-флаги, conversation-группировку, exp-decay в ранжировании
и auto-prune старых незначимых эпизодов.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any, Awaitable, Callable, Dict, List, Optional, Protocol, Union,
)

import numpy as np
from pydantic import BaseModel, Field

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


# ═══════════════════════════════════════════════════════════════════════════
# init_logging — вызывается явно
# ═══════════════════════════════════════════════════════════════════════════

def init_logging(log_dir: Path = Path("data/logs")) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "episodic_memory.log",
        rotation="10 MB",
        level="INFO",
        enqueue=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SecurityVerdict — общий с Cache/Ingestion/Triggers
# ═══════════════════════════════════════════════════════════════════════════

class SecurityVerdict(str, Enum):
    GREEN  = "green"
    YELLOW = "yellow"
    RED    = "red"


# ═══════════════════════════════════════════════════════════════════════════
# EmbeddingProvider Protocol (дакт-типизация для DI)
# ═══════════════════════════════════════════════════════════════════════════

class EmbeddingProviderProtocol(Protocol):
    """Контракт embedding-провайдера: encode_query + encode_passage."""
    model_name: str
    dim: int
    def encode_query(self, text: str) -> np.ndarray: ...
    def encode_passage(self, text: str) -> np.ndarray: ...


# ═══════════════════════════════════════════════════════════════════════════
# События для monitoring/Telegram
# ═══════════════════════════════════════════════════════════════════════════

class EpisodicEventLevel(str, Enum):
    GREEN  = "green"
    YELLOW = "yellow"
    RED    = "red"


class EpisodicEventType(str, Enum):
    EPISODE_ADDED         = "episode_added"
    EPISODE_RECALLED      = "episode_recalled"
    EPISODE_FORGOTTEN     = "episode_forgotten"
    ANOMALOUS_GROWTH      = "anomalous_growth"
    LOW_RECALL_RELEVANCE  = "low_recall_relevance"
    STORAGE_FAILURE       = "storage_failure"
    MODEL_MISMATCH_RESET  = "model_mismatch_reset"
    AUTO_PRUNE            = "auto_prune"


@dataclass
class EpisodicEvent:
    level: EpisodicEventLevel
    type: EpisodicEventType
    message: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


def emit_event(event: EpisodicEvent, callback: Optional[Callable[[EpisodicEvent], None]]) -> None:
    msg = f"[{event.level.value.upper()}] {event.type.value}: {event.message}"
    if event.level == EpisodicEventLevel.GREEN:
        logger.debug(msg)
    elif event.level == EpisodicEventLevel.YELLOW:
        logger.warning(msg)
    else:
        logger.error(msg)
    if callback is not None:
        try:
            callback(event)
        except Exception:
            logger.exception("on_event callback failed")


# ═══════════════════════════════════════════════════════════════════════════
# Метаданные памяти (для version-check embedding-модели)
# ═══════════════════════════════════════════════════════════════════════════

class MemoryMetadata(BaseModel):
    embedding_model: str
    embedding_dim: int
    schema_version: str = "2.0"
    created_at: float = Field(default_factory=time.time)


def _read_meta(path: Path) -> Optional[MemoryMetadata]:
    if not path.exists():
        return None
    try:
        return MemoryMetadata(**json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None


def _write_meta(path: Path, meta: MemoryMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# Episode
# ═══════════════════════════════════════════════════════════════════════════

class Episode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    conversation_id: Optional[str] = None
    query: str
    response: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    security_verdict: SecurityVerdict = SecurityVerdict.GREEN
    quarantine: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# EpisodicMemory
# ═══════════════════════════════════════════════════════════════════════════

ImportanceScorer = Callable[[str, str, Dict], float]
LLMCaller = Callable[[str], Union[str, Awaitable[str]]]


class EpisodicMemory:
    """
    Долговременная эпизодическая память для Крепости.

    Использование:
        provider = EmbeddingProvider()  # любой EmbeddingProviderProtocol
        memory = EpisodicMemory(provider, on_event=monitoring_handler)

        # После каждого диалога:
        await memory.add_episode(
            query=user_query,
            response=teacher_response,
            conversation_id="conv_2026_06_07_1",
            importance_score=0.7,
            security_verdict=guard_verdict,
        )

        # Recall похожих эпизодов:
        similar = await memory.recall("предыдущий вопрос про X", top_k=5)

        # Резюме сессии (для триггера session_summary):
        summary = await memory.summarize_via_llm(teacher.call, n=10)
    """

    DEFAULT_BASE_DIR = Path("data/memory")

    DEFAULT_DECAY_DAYS                 = 30
    DEFAULT_PRUNE_IMPORTANCE_THRESHOLD = 0.3
    DEFAULT_PRUNE_AGE_DAYS             = 90
    DEFAULT_AUTO_PRUNE_EVERY_N_ADDS    = 100

    DEFAULT_SIMILARITY_THRESHOLD       = 0.5
    DEFAULT_SIMILARITY_WEIGHT          = 0.7
    DEFAULT_IMPORTANCE_WEIGHT          = 0.3

    DEFAULT_GROWTH_THRESHOLD_PER_MIN   = 100
    DEFAULT_LOW_RELEVANCE_WINDOW       = 50
    DEFAULT_LOW_RELEVANCE_RATIO        = 0.95
    DEFAULT_LOW_RELEVANCE_SCORE        = 0.5

    def __init__(
        self,
        provider: EmbeddingProviderProtocol,
        base_dir: Path = DEFAULT_BASE_DIR,
        importance_scorer: Optional[ImportanceScorer] = None,
        on_event: Optional[Callable[[EpisodicEvent], None]] = None,
        decay_days: float = DEFAULT_DECAY_DAYS,
        prune_importance_threshold: float = DEFAULT_PRUNE_IMPORTANCE_THRESHOLD,
        prune_age_days: float = DEFAULT_PRUNE_AGE_DAYS,
        auto_prune_every_n_adds: int = DEFAULT_AUTO_PRUNE_EVERY_N_ADDS,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        similarity_weight: float = DEFAULT_SIMILARITY_WEIGHT,
        importance_weight: float = DEFAULT_IMPORTANCE_WEIGHT,
        growth_threshold_per_min: int = DEFAULT_GROWTH_THRESHOLD_PER_MIN,
    ):
        self.provider = provider
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.importance_scorer = importance_scorer
        self.on_event = on_event

        self.decay_days = decay_days
        self.prune_importance_threshold = prune_importance_threshold
        self.prune_age_days = prune_age_days
        self.auto_prune_every_n_adds = auto_prune_every_n_adds
        self.similarity_threshold = similarity_threshold
        self.similarity_weight = similarity_weight
        self.importance_weight = importance_weight
        self.growth_threshold_per_min = growth_threshold_per_min

        self._episodes_path = base_dir / "episodes.jsonl"
        self._q_vectors_path = base_dir / "query_vectors.npy"
        self._q_index_path = base_dir / "query_index.json"
        self._r_vectors_path = base_dir / "response_vectors.npy"
        self._r_index_path = base_dir / "response_index.json"
        self._meta_path = base_dir / "meta.json"

        self._episodes: Dict[str, Episode] = {}
        self._q_embeddings: Dict[str, np.ndarray] = {}
        self._r_embeddings: Dict[str, np.ndarray] = {}

        self._add_timestamps: deque = deque(maxlen=500)
        self._recent_max_scores: deque = deque(maxlen=self.DEFAULT_LOW_RELEVANCE_WINDOW)
        self._last_growth_alert: float = 0.0
        self._last_low_relevance_alert: float = 0.0
        self._adds_since_last_prune: int = 0

        self._load()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load(self) -> None:
        # Version check для embedding-модели
        meta = _read_meta(self._meta_path)
        current_meta = MemoryMetadata(
            embedding_model=self.provider.model_name,
            embedding_dim=self.provider.dim,
        )

        if meta is None:
            _write_meta(self._meta_path, current_meta)
        elif (meta.embedding_model != self.provider.model_name
                or meta.embedding_dim != self.provider.dim):
            emit_event(EpisodicEvent(
                level=EpisodicEventLevel.YELLOW,
                type=EpisodicEventType.MODEL_MISMATCH_RESET,
                message="Embedding модель сменилась → embeddings reset, эпизоды сохранены",
                payload={"stored": meta.embedding_model, "current": self.provider.model_name},
            ), self.on_event)
            self._q_vectors_path.unlink(missing_ok=True)
            self._q_index_path.unlink(missing_ok=True)
            self._r_vectors_path.unlink(missing_ok=True)
            self._r_index_path.unlink(missing_ok=True)
            _write_meta(self._meta_path, current_meta)

        if self._episodes_path.exists():
            with open(self._episodes_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ep = Episode(**json.loads(line))
                        self._episodes[ep.id] = ep
                    except Exception as e:
                        logger.warning(f"Skip bad episode: {e}")

        self._load_embeddings(self._q_vectors_path, self._q_index_path, self._q_embeddings)
        self._load_embeddings(self._r_vectors_path, self._r_index_path, self._r_embeddings)

        logger.info(
            f"Memory loaded | episodes={len(self._episodes)} "
            f"q_emb={len(self._q_embeddings)} r_emb={len(self._r_embeddings)}"
        )

        self._auto_prune()

    def _load_embeddings(
        self, vectors_path: Path, index_path: Path, target: Dict[str, np.ndarray],
    ) -> None:
        if not (vectors_path.exists() and index_path.exists()):
            return
        try:
            matrix = np.load(vectors_path)
            index = json.loads(index_path.read_text(encoding="utf-8"))
            for i, ep_id in enumerate(index):
                if ep_id in self._episodes and i < len(matrix):
                    target[ep_id] = matrix[i]
        except Exception as e:
            logger.warning(f"Embeddings load failed for {vectors_path.name}: {e}")

    def _save_episode(self, episode: Episode) -> None:
        try:
            with open(self._episodes_path, "a", encoding="utf-8") as f:
                f.write(episode.model_dump_json() + "\n")
        except OSError as e:
            self._handle_storage_failure(e)

    def _save_embeddings(self) -> None:
        try:
            if self._q_embeddings:
                self._save_embedding_dict(self._q_embeddings, self._q_vectors_path, self._q_index_path)
            if self._r_embeddings:
                self._save_embedding_dict(self._r_embeddings, self._r_vectors_path, self._r_index_path)
        except OSError as e:
            self._handle_storage_failure(e)

    @staticmethod
    def _save_embedding_dict(d: Dict[str, np.ndarray], vec_path: Path, idx_path: Path) -> None:
        ids = list(d.keys())
        matrix = np.array([d[i] for i in ids])
        np.save(vec_path, matrix)
        idx_path.write_text(json.dumps(ids, ensure_ascii=False), encoding="utf-8")

    def _rewrite_episodes(self) -> None:
        try:
            with open(self._episodes_path, "w", encoding="utf-8") as f:
                for ep in self._episodes.values():
                    f.write(ep.model_dump_json() + "\n")
        except OSError as e:
            self._handle_storage_failure(e)

    def _handle_storage_failure(self, e: OSError) -> None:
        msg = str(e)
        disk_full = "No space" in msg or "ENOSPC" in msg
        emit_event(EpisodicEvent(
            level=EpisodicEventLevel.RED,
            type=EpisodicEventType.STORAGE_FAILURE,
            message=f"Storage failure: {msg}",
            payload={"disk_full": disk_full},
        ), self.on_event)
        logger.exception("Memory storage failure")

    # ── Public API ────────────────────────────────────────────────────────

    async def add_episode(
        self,
        query: str,
        response: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: float = 0.5,
        security_verdict: SecurityVerdict = SecurityVerdict.GREEN,
    ) -> str:
        """Добавить эпизод. YELLOW/RED → quarantine=True (по умолчанию
        не появятся в recall)."""
        metadata = metadata or {}

        if self.importance_scorer is not None:
            try:
                scored = float(self.importance_scorer(query, response, metadata))
                importance_score = max(0.0, min(1.0, scored))
            except Exception:
                logger.exception("importance_scorer failed, using passed value")

        quarantine = (security_verdict != SecurityVerdict.GREEN)

        episode = Episode(
            query=query,
            response=response,
            conversation_id=conversation_id,
            metadata=metadata,
            importance_score=importance_score,
            security_verdict=security_verdict,
            quarantine=quarantine,
        )

        # Encode оба embedding'а в отдельном потоке (не блокируем event loop)
        q_emb = await asyncio.to_thread(self.provider.encode_query, query)
        r_emb = await asyncio.to_thread(self.provider.encode_passage, response)

        self._q_embeddings[episode.id] = q_emb
        self._r_embeddings[episode.id] = r_emb
        self._episodes[episode.id] = episode

        self._save_episode(episode)
        self._save_embeddings()

        self._add_timestamps.append(time.time())
        self._check_anomalous_growth()

        self._adds_since_last_prune += 1
        if self._adds_since_last_prune >= self.auto_prune_every_n_adds:
            self._auto_prune()

        emit_event(EpisodicEvent(
            level=EpisodicEventLevel.GREEN,
            type=EpisodicEventType.EPISODE_ADDED,
            message=f"Episode {episode.id[:8]} added (importance={importance_score:.2f}, "
                    f"quarantine={quarantine})",
            payload={"id": episode.id, "quarantine": quarantine,
                     "conversation_id": conversation_id},
        ), self.on_event)

        return episode.id

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        conversation_id: Optional[str] = None,
        include_quarantined: bool = False,
        similarity_threshold: Optional[float] = None,
    ) -> List[Episode]:
        """Поиск похожих эпизодов.

        - max(score_query, score_response) — embedding сходство по двум измерениям
        - final = sim × similarity_weight + (importance × exp(-age/decay)) × importance_weight
        - Фильтры: quarantine, conversation_id, similarity_threshold
        """
        threshold = similarity_threshold if similarity_threshold is not None else self.similarity_threshold

        candidate_ids = [
            ep_id for ep_id, ep in self._episodes.items()
            if (include_quarantined or not ep.quarantine)
            and (conversation_id is None or ep.conversation_id == conversation_id)
            and ep_id in self._q_embeddings
            and ep_id in self._r_embeddings
        ]
        if not candidate_ids:
            return []

        query_emb = await asyncio.to_thread(self.provider.encode_query, query)

        # Нормализованные эмбеддинги (из e5 с normalize_embeddings=True) →
        # cosine similarity = dot product. Чисто NumPy, без torch.
        q_matrix = np.array([self._q_embeddings[i] for i in candidate_ids])
        r_matrix = np.array([self._r_embeddings[i] for i in candidate_ids])
        q_scores = q_matrix @ query_emb
        r_scores = r_matrix @ query_emb
        max_scores = np.maximum(q_scores, r_scores)

        max_sim = float(max_scores.max()) if len(max_scores) else 0.0
        self._recent_max_scores.append(max_sim)
        self._check_low_relevance()

        now = time.time()
        candidates: List[tuple] = []
        for i, ep_id in enumerate(candidate_ids):
            sim_score = float(max_scores[i])
            if sim_score < threshold:
                continue
            ep = self._episodes[ep_id]
            age_days = (now - ep.timestamp) / 86400
            effective_imp = ep.importance_score * math.exp(-age_days / self.decay_days)
            final_score = (
                sim_score * self.similarity_weight
                + effective_imp * self.importance_weight
            )
            candidates.append((ep_id, final_score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        result = [self._episodes[ep_id] for ep_id, _ in candidates[:top_k]]

        emit_event(EpisodicEvent(
            level=EpisodicEventLevel.GREEN,
            type=EpisodicEventType.EPISODE_RECALLED,
            message=f"Recall: {len(result)} episodes (max_sim={max_sim:.3f})",
            payload={"count": len(result), "max_sim": max_sim, "threshold": threshold},
        ), self.on_event)

        return result

    def forget(self, episode_id: str) -> bool:
        if episode_id not in self._episodes:
            return False
        del self._episodes[episode_id]
        self._q_embeddings.pop(episode_id, None)
        self._r_embeddings.pop(episode_id, None)
        self._rewrite_episodes()
        self._save_embeddings()
        emit_event(EpisodicEvent(
            level=EpisodicEventLevel.GREEN,
            type=EpisodicEventType.EPISODE_FORGOTTEN,
            message=f"Episode {episode_id[:8]} forgotten",
            payload={"id": episode_id},
        ), self.on_event)
        return True

    def get_recent(
        self,
        n: int = 10,
        conversation_id: Optional[str] = None,
        include_quarantined: bool = False,
    ) -> List[Episode]:
        """Дешёвый список последних эпизодов без LLM."""
        candidates = [
            ep for ep in self._episodes.values()
            if (include_quarantined or not ep.quarantine)
            and (conversation_id is None or ep.conversation_id == conversation_id)
        ]
        candidates.sort(key=lambda e: e.timestamp, reverse=True)
        return candidates[:n]

    async def summarize_via_llm(
        self,
        llm_caller: LLMCaller,
        n: int = 10,
        conversation_id: Optional[str] = None,
        include_quarantined: bool = False,
    ) -> str:
        """Сгенерировать summary последних эпизодов через LLM.

        llm_caller — функция (sync/async), принимает prompt, возвращает строку.
        Триггер session_summary будет вызывать именно этот метод.
        """
        episodes = self.get_recent(n, conversation_id=conversation_id,
                                   include_quarantined=include_quarantined)
        if not episodes:
            return "Эпизодов нет"

        prompt_lines = [
            "Ниже — последние диалоговые эпизоды.",
            "Составь связное резюме в 3-5 предложениях, без воды.\n",
        ]
        for ep in reversed(episodes):
            dt = datetime.fromtimestamp(ep.timestamp).strftime("%Y-%m-%d %H:%M")
            prompt_lines.append(
                f"[{dt}] Q: {ep.query[:300]}\n→ A: {ep.response[:300]}\n"
            )
        prompt = "\n".join(prompt_lines)

        try:
            result = llm_caller(prompt)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result).strip()
        except Exception:
            logger.exception("LLM summarize failed")
            return "Ошибка генерации summary"

    # ── Auto-prune ────────────────────────────────────────────────────────

    def _auto_prune(self) -> int:
        """Удалить эпизоды с importance < threshold старше age_days."""
        self._adds_since_last_prune = 0
        now = time.time()
        age_seconds = self.prune_age_days * 86400
        to_remove = [
            ep_id for ep_id, ep in self._episodes.items()
            if ep.importance_score < self.prune_importance_threshold
            and now - ep.timestamp > age_seconds
        ]
        if not to_remove:
            return 0
        for ep_id in to_remove:
            del self._episodes[ep_id]
            self._q_embeddings.pop(ep_id, None)
            self._r_embeddings.pop(ep_id, None)
        self._rewrite_episodes()
        self._save_embeddings()
        emit_event(EpisodicEvent(
            level=EpisodicEventLevel.GREEN,
            type=EpisodicEventType.AUTO_PRUNE,
            message=f"Auto-pruned {len(to_remove)} episodes",
            payload={"count": len(to_remove)},
        ), self.on_event)
        return len(to_remove)

    # ── Anomaly detection ─────────────────────────────────────────────────

    def _check_anomalous_growth(self) -> None:
        now = time.time()
        recent = sum(1 for t in self._add_timestamps if now - t < 60)
        if recent < self.growth_threshold_per_min:
            return
        if now - self._last_growth_alert < 600:
            return
        self._last_growth_alert = now
        emit_event(EpisodicEvent(
            level=EpisodicEventLevel.YELLOW,
            type=EpisodicEventType.ANOMALOUS_GROWTH,
            message=f"Memory anomalous growth: {recent} adds/min",
            payload={"rate_per_min": recent, "threshold": self.growth_threshold_per_min},
        ), self.on_event)

    def _check_low_relevance(self) -> None:
        if len(self._recent_max_scores) < self.DEFAULT_LOW_RELEVANCE_WINDOW:
            return
        low_count = sum(1 for s in self._recent_max_scores
                        if s < self.DEFAULT_LOW_RELEVANCE_SCORE)
        ratio = low_count / len(self._recent_max_scores)
        if ratio < self.DEFAULT_LOW_RELEVANCE_RATIO:
            return
        now = time.time()
        if now - self._last_low_relevance_alert < 1800:
            return
        self._last_low_relevance_alert = now
        emit_event(EpisodicEvent(
            level=EpisodicEventLevel.YELLOW,
            type=EpisodicEventType.LOW_RECALL_RELEVANCE,
            message=f"Низкая recall-релевантность: {ratio:.0%} ниже "
                    f"{self.DEFAULT_LOW_RELEVANCE_SCORE}",
            payload={"ratio": ratio, "window": self.DEFAULT_LOW_RELEVANCE_WINDOW},
        ), self.on_event)

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        total = len(self._episodes)
        quarantined = sum(1 for ep in self._episodes.values() if ep.quarantine)
        return {
            "total_episodes": total,
            "quarantined": quarantined,
            "conversations": len({
                ep.conversation_id for ep in self._episodes.values()
                if ep.conversation_id
            }),
            "q_embeddings": len(self._q_embeddings),
            "r_embeddings": len(self._r_embeddings),
        }

    @property
    def size(self) -> int:
        return len(self._episodes)
