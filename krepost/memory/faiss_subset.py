"""L2: инкрементальный subset-индекс (FAISS если есть, иначе numpy).

Не заменяет Chroma Phase 3/4 — Air/ops tool для отфильтрованного подмножества
(candidates.json или одна папка domain).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

META_NAME = "meta.json"
VEC_NAME = "vectors.npy"
FAISS_NAME = "index.faiss"


@dataclass
class SearchHit:
    path: str
    score: float
    preview: str


def _file_sig(path: Path) -> str:
    st = path.stat()
    raw = f"{path.as_posix()}|{st.st_mtime_ns}|{st.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _read_preview(path: Path, n: int = 400) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:n]
    except OSError:
        return ""


class SubsetIndex:
    """Персистентный cosine/IP индекс по списку файлов vault."""

    def __init__(self, index_dir: Path, dim: int = 0):
        self.index_dir = Path(index_dir)
        self.dim = dim
        self.paths: List[str] = []
        self.sigs: List[str] = []
        self.vectors: Optional[np.ndarray] = None
        self._faiss = None

    @property
    def meta_path(self) -> Path:
        return self.index_dir / META_NAME

    def load(self) -> bool:
        if not self.meta_path.is_file():
            return False
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        self.dim = int(meta.get("dim") or 0)
        self.paths = list(meta.get("paths") or [])
        self.sigs = list(meta.get("sigs") or [])
        vec_path = self.index_dir / VEC_NAME
        if vec_path.is_file():
            self.vectors = np.load(vec_path)
        faiss_path = self.index_dir / FAISS_NAME
        if faiss_path.is_file():
            try:
                import faiss  # type: ignore

                self._faiss = faiss.read_index(str(faiss_path))
            except Exception:
                self._faiss = None
        return True

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "dim": self.dim,
            "paths": self.paths,
            "sigs": self.sigs,
            "n": len(self.paths),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if self.vectors is not None:
            np.save(self.index_dir / VEC_NAME, self.vectors.astype(np.float32))
        if self._faiss is not None:
            try:
                import faiss  # type: ignore

                faiss.write_index(self._faiss, str(self.index_dir / FAISS_NAME))
            except Exception:
                pass

    def _rebuild_faiss(self) -> None:
        if self.vectors is None or self.vectors.size == 0:
            self._faiss = None
            return
        try:
            import faiss  # type: ignore

            index = faiss.IndexFlatIP(self.dim)
            index.add(self.vectors.astype(np.float32))
            self._faiss = index
        except Exception:
            self._faiss = None

    def upsert(
        self,
        vault: Path,
        rel_paths: Sequence[str],
        encode_fn,
        *,
        max_chars: int = 6000,
    ) -> Dict[str, int]:
        """Инкрементально добавить/обновить/удалить пути. encode_fn(list[str])->ndarray."""
        vault = Path(vault)
        wanted = [p.replace("\\", "/") for p in rel_paths]
        wanted_set = set(wanted)
        by_path = {p: i for i, p in enumerate(self.paths)}

        keep_idx: List[int] = []
        for i, p in enumerate(self.paths):
            if p not in wanted_set:
                continue
            abs_p = vault / p
            if not abs_p.is_file():
                continue
            if i < len(self.sigs) and self.sigs[i] == _file_sig(abs_p):
                keep_idx.append(i)

        kept_paths = [self.paths[i] for i in keep_idx]
        kept_sigs = [self.sigs[i] for i in keep_idx]
        kept_vecs = (
            self.vectors[keep_idx]
            if self.vectors is not None and keep_idx
            else np.zeros((0, self.dim or 1), dtype=np.float32)
        )

        stale = [p for p in wanted if p not in set(kept_paths)]
        added = 0
        if stale:
            texts: List[str] = []
            new_paths: List[str] = []
            new_sigs: List[str] = []
            for p in stale:
                abs_p = vault / p
                if not abs_p.is_file():
                    continue
                texts.append(
                    abs_p.read_text(encoding="utf-8", errors="replace")[:max_chars]
                )
                new_paths.append(p)
                new_sigs.append(_file_sig(abs_p))
            if texts:
                emb = np.asarray(encode_fn(texts), dtype=np.float32)
                if emb.ndim == 1:
                    emb = emb.reshape(1, -1)
                # L2-normalize for IP = cosine
                norms = np.linalg.norm(emb, axis=1, keepdims=True)
                norms = np.clip(norms, 1e-12, None)
                emb = emb / norms
                if self.dim and emb.shape[1] != self.dim:
                    raise ValueError(
                        f"dim mismatch: index={self.dim} emb={emb.shape[1]}"
                    )
                self.dim = int(emb.shape[1])
                if kept_vecs.size == 0 or kept_vecs.shape[1] != self.dim:
                    kept_vecs = np.zeros((0, self.dim), dtype=np.float32)
                kept_vecs = np.vstack([kept_vecs, emb])
                kept_paths.extend(new_paths)
                kept_sigs.extend(new_sigs)
                added = len(new_paths)

        removed = len(self.paths) - len(keep_idx)
        self.paths = kept_paths
        self.sigs = kept_sigs
        self.vectors = kept_vecs.astype(np.float32) if len(kept_paths) else None
        if self.vectors is not None and self.dim == 0:
            self.dim = int(self.vectors.shape[1])
        self._rebuild_faiss()
        self.save()
        return {"kept": len(keep_idx), "added": added, "removed": max(0, removed)}

    def search(
        self,
        query_vec: np.ndarray,
        *,
        top_k: int = 8,
        vault: Optional[Path] = None,
    ) -> List[SearchHit]:
        if self.vectors is None or len(self.paths) == 0:
            return []
        q = np.asarray(query_vec, dtype=np.float32).reshape(1, -1)
        q = q / np.clip(np.linalg.norm(q, axis=1, keepdims=True), 1e-12, None)
        k = min(top_k, len(self.paths))
        if self._faiss is not None:
            D, I = self._faiss.search(q, k)
            scores = D[0]
            idxs = I[0]
        else:
            sims = (self.vectors @ q.T).ravel()
            idxs = np.argsort(-sims)[:k]
            scores = sims[idxs]
        hits: List[SearchHit] = []
        for i, sc in zip(idxs, scores):
            if int(i) < 0:
                continue
            p = self.paths[int(i)]
            preview = ""
            if vault is not None:
                preview = _read_preview(Path(vault) / p)
            hits.append(SearchHit(path=p, score=float(sc), preview=preview))
        return hits


def default_encode_fn(model_name: str = "BAAI/bge-m3"):
    """Ленивый SentenceTransformer encode (MPS/CPU)."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    def _encode(texts: List[str]):
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return _encode
