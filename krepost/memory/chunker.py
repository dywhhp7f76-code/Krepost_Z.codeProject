"""
krepost/memory/chunker.py

Детерминированное разбиение текста на чанки для векторной БД. Пакует абзацы
(разделённые пустой строкой) в чанки до max_chars; слишком длинный абзац
режется жёстко с перекрытием (overlap) для непрерывности retrieval.
"""
from __future__ import annotations

import re
from typing import List

_PARA_SPLIT = re.compile(r"\n\s*\n")


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    if not text or not text.strip():
        return []
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    overlap = max(0, min(overlap, max_chars - 1))

    paras = [p.strip() for p in _PARA_SPLIT.split(text) if p.strip()]
    chunks: List[str] = []
    cur = ""

    def flush():
        nonlocal cur
        if cur:
            chunks.append(cur)
            cur = ""

    for p in paras:
        if len(p) > max_chars:
            # Длинный абзац: сбрасываем накопленное и режем жёстко с overlap.
            flush()
            step = max_chars - overlap
            for i in range(0, len(p), step):
                chunks.append(p[i:i + max_chars])
                if i + max_chars >= len(p):
                    break
            continue
        if not cur:
            cur = p
        elif len(cur) + 1 + len(p) <= max_chars:
            cur = cur + "\n" + p
        else:
            flush()
            cur = p

    flush()
    return chunks
