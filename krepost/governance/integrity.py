"""
krepost/governance/integrity.py

Prompt-integrity diff — контроль целостности system-prompt + скриптов между
итерациями эволюции (redteam/2026-07-07, arXiv 2602.15654).

После каждого шага эволюции хэшируем артефакт (набор файлов) и сравниваем с
предыдущим чекпойнтом. Появление новых инструкций не из разрешённого множества
→ блок (self-reinforcing injection). Сочетается с audit_hash/trace_hash.

Алгоритм хеширования устойчив к перемещению байта между файлами: каждый файл
хешируется отдельно, потом хеш от упорядоченной JSON-структуры {путь: хеш}
(с путями в ключах). Простой SHA256 от конкатенации содержимого — НЕ годится:
байт, переехавший с конца файла A в начало B, даёт тот же хеш.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

PathLike = Union[str, Path]


def hash_file(path: PathLike) -> str:
    """SHA256 от содержимого одного файла."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_path(p: PathLike) -> str:
    """Стабильный ключ-путь (str, нормализованные разделители)."""
    return str(Path(p)).replace("\\", "/")


def hash_artifact(paths: List[PathLike]) -> str:
    """Составной хеш набора файлов.

    Каждый файл хешируется ОТДЕЛЬНО (hash_file), собирается в упорядоченный
    dict {нормализованный_путь: file_hash}, сериализуется json.dumps(sort_keys),
    от результата — SHA256. Пути в ключах + отдельные хеши → перемещение байта
    между файлами A и B меняет оба file_hash и итоговый хеш."""
    structure: Dict[str, str] = {}
    for p in paths:
        key = _norm_path(p)
        structure[key] = hash_file(p)
    payload = json.dumps(structure, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def artifact_fingerprints(paths: List[PathLike]) -> Dict[str, str]:
    """Словарь {путь: file_hash} — для точечного diff."""
    return {_norm_path(p): hash_file(p) for p in paths}


@dataclass
class IntegrityDiff:
    """Результат сравнения двух чекпойнтов целостности."""
    changed: List[str] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (self.changed or self.added or self.removed)

    def __bool__(self) -> bool:
        return not self.clean


def diff_checkpoint(
    prev: Dict[str, str],
    curr_paths: List[PathLike],
) -> IntegrityDiff:
    """Сравнить предыдущие отпечатки {путь: хеш} с текущим набором файлов.

    Возвращает IntegrityDiff: changed (хеш поменялся), added (новый файл),
    removed (файл исчез)."""
    curr = artifact_fingerprints(curr_paths)
    prev_keys = set(prev)
    curr_keys = set(curr)
    return IntegrityDiff(
        changed=[k for k in (prev_keys & curr_keys) if prev[k] != curr[k]],
        added=sorted(curr_keys - prev_keys),
        removed=sorted(prev_keys - curr_keys),
    )


@dataclass
class Checkpoint:
    """Сохранённый чекпойнт целостности артефакта."""
    artifact_hash: str
    fingerprints: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_paths(cls, paths: List[PathLike]) -> "Checkpoint":
        fps = artifact_fingerprints(paths)
        payload = json.dumps(fps, sort_keys=True, ensure_ascii=False)
        return cls(
            artifact_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            fingerprints=fps,
        )

    def diff_against(self, paths: List[PathLike]) -> IntegrityDiff:
        return diff_checkpoint(self.fingerprints, paths)

    def to_json(self) -> str:
        return json.dumps(
            {"artifact_hash": self.artifact_hash, "fingerprints": self.fingerprints},
            sort_keys=True, ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, data: str) -> "Checkpoint":
        obj = json.loads(data)
        return cls(artifact_hash=obj["artifact_hash"], fingerprints=obj.get("fingerprints", {}))


def verify_against_checkpoint(
    checkpoint: Checkpoint,
    paths: List[PathLike],
    *,
    allow_add: bool = False,
    allow_remove: bool = False,
) -> Optional[IntegrityDiff]:
    """Верифицировать что артефакт соответствует чекпойнту.

    Возвращает IntegrityDiff если есть расхождения (None если чисто).
    allow_add/allow_remove смягчают: новые/удалённые файлы не считаются
    нарушением (но changed — всегда нарушение)."""
    diff = checkpoint.diff_against(paths)
    if diff.changed:
        return diff
    if diff.added and not allow_add:
        return diff
    if diff.removed and not allow_remove:
        return diff
    return None
