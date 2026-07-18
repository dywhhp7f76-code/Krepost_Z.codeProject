#!/usr/bin/env python3
"""
Симбиоз-миграция: дописать metadata.domain в существующий Chroma без re-embed.

Векторы и тексты не трогаем. Берём src/source/doc_id → domain_from_relpath.
После этого MemoryRouter перестаёт уходить в flat fallback на пустых where=domain.

    python scripts/backfill_domain_metadata.py
    python scripts/backfill_domain_metadata.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from krepost.memory.chroma_factory import (
    DEFAULT_MEMORY_COLLECTION,
    env_chroma_dir,
    make_chroma_client,
    make_chroma_collection,
)
from krepost.memory.domains import domain_from_relpath


def _path_from_meta(meta: dict, doc_id_fallback: str = "") -> str:
    for key in ("src", "source", "doc_id"):
        val = (meta or {}).get(key)
        if val:
            return str(val)
    return doc_id_fallback or ""


def backfill(
    *,
    chroma_dir: Path,
    collection_name: str,
    dry_run: bool,
    batch_size: int = 200,
) -> int:
    client = make_chroma_client(chroma_dir)
    col = make_chroma_collection(client, collection_name)
    total = col.count()
    print(f"collection={collection_name} count={total} chroma={chroma_dir}")
    if total == 0:
        return 0

    updated = skipped = already = 0
    offset = 0
    while offset < total:
        # Chroma get pagination via limit/offset
        batch = col.get(
            include=["metadatas"],
            limit=batch_size,
            offset=offset,
        )
        ids = batch.get("ids") or []
        metas = batch.get("metadatas") or []
        if not ids:
            break

        new_ids: list[str] = []
        new_metas: list[dict] = []
        for i, cid in enumerate(ids):
            meta = dict(metas[i] or {})
            path = _path_from_meta(meta, doc_id_fallback=str(meta.get("doc_id") or ""))
            # id вида "01-Energy/foo.md::0"
            if not path and "::" in cid:
                path = cid.split("::", 1)[0]
            domain = domain_from_relpath(path)
            if meta.get("domain") == domain:
                already += 1
                continue
            if meta.get("domain") and meta.get("domain") != domain:
                # уже было другое — перезаписываем по канону path→domain
                pass
            meta["domain"] = domain
            if path and not meta.get("src"):
                meta["src"] = path
            new_ids.append(cid)
            new_metas.append(meta)
            updated += 1

        if new_ids and not dry_run:
            col.update(ids=new_ids, metadatas=new_metas)
        elif new_ids and dry_run:
            skipped += len(new_ids)

        offset += len(ids)
        print(f"  scanned {min(offset, total)}/{total} … pending_updates={updated}")

    mode = "DRY-RUN" if dry_run else "DONE"
    print(
        f"{mode}: would_update_or_updated={updated} already_ok={already} "
        f"dry_pending={skipped if dry_run else 0}"
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill Chroma metadata.domain")
    p.add_argument("--chroma-dir", type=Path, default=None)
    p.add_argument("--collection", default=DEFAULT_MEMORY_COLLECTION)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--batch-size", type=int, default=200)
    args = p.parse_args()
    chroma = args.chroma_dir or env_chroma_dir()
    return backfill(
        chroma_dir=chroma,
        collection_name=args.collection,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    raise SystemExit(main())
