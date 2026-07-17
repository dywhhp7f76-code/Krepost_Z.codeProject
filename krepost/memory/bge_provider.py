"""Адаптер SentenceTransformer (BGE-M3) → EmbeddingProviderProtocol для EpisodicMemory."""
from __future__ import annotations

from typing import Any

import numpy as np


class BGEProvider:
    """Обёртка над уже загруженным SentenceTransformer — без второй загрузки модели."""

    def __init__(self, model: Any, model_name: str = "BAAI/bge-m3"):
        self._model = model
        self.model_name = model_name
        probe = self.encode_query("dim-probe")
        self.dim = int(probe.shape[-1])

    def encode_query(self, text: str) -> np.ndarray:
        vec = self._model.encode(text, normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32).reshape(-1)

    def encode_passage(self, text: str) -> np.ndarray:
        return self.encode_query(text)
