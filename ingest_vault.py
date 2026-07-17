#!/usr/bin/env python3
"""
ingest_vault.py — индексация vault/ в persistent Chroma (BGE-M3, cosine).

Перед записью каждый файл проходит ToolOutputGuard (ingest-guard).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

from krepost.memory.chroma_factory import env_chroma_dir, make_memory_stack
from krepost.memory.domains import domain_from_relpath

VAULT = Path(__file__).resolve().parent / "vault"
TEXT_SUFFIXES = {".md", ".txt", ".markdown"}


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_files(vault: Path):
    for path in sorted(vault.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.name == "00-INDEX.md":
            continue
        yield path


async def ingest(
    vault: Path,
    *,
    chroma_dir: Path,
    dry_run: bool = False,
) -> int:
    if not vault.is_dir():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 1

    files = list(_iter_files(vault))
    if dry_run:
        for f in files:
            print(f"  would ingest: {f.relative_to(vault)}")
        print(f"total: {len(files)} files")
        return 0

    _, _, store = make_memory_stack(chroma_dir=chroma_dir)
    added = blocked = 0
    for path in files:
        rel = path.relative_to(vault).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            continue
        doc_id = rel
        meta = {
            "src": rel,
            "source": rel,
            "file_hash": _file_hash(path),
            "domain": domain_from_relpath(rel),
        }
        result = await store.add(doc_id, text, metadata=meta)
        if result.blocked:
            blocked += 1
            print(f"  BLOCKED {rel}: {result.reason}")
        elif result.added:
            added += result.added
            print(f"  + {rel} ({result.added} chunks)")

    print(f"done: {len(files)} files, {added} chunks, {blocked} blocked")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Ingest Krepost vault into ChromaDB")
    p.add_argument("--vault", type=Path, default=VAULT, help="Path to vault/")
    p.add_argument("--chroma-dir", type=Path, default=None, help="Chroma persist dir")
    p.add_argument("--dry-run", action="store_true", help="List files only")
    args = p.parse_args()
    chroma = args.chroma_dir or env_chroma_dir()
    return asyncio.run(ingest(args.vault, chroma_dir=chroma, dry_run=args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
