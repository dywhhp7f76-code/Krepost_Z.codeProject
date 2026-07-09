"""
krepost.prompts — инженерные системные промпты для моделей Крепости.

- assistant.py — RAG-промпт основной модели (Qwen3.6-27B): context-faithful,
  цитаты-источники, протокол отказа, граница контекста через nonce-маркеры.

Guard-промпты (Layer 2/4) живут в pipeline.py рядом с классификатором.
"""
from krepost.prompts.assistant import (
    NO_DATA_TOKEN,
    build_assistant_system_prompt,
    build_rag_messages,
)

__all__ = [
    "build_assistant_system_prompt",
    "build_rag_messages",
    "NO_DATA_TOKEN",
]
