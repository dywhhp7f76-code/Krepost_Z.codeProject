#!/usr/bin/env python3
"""Импорт normalized/attacks.jsonl → Attack Vault.

Пример:
  export FORTRESS_DATA=/fortress_data/attacker
  python Ataker-boop/scripts/import_attacker_base.py \\
      --vault Ataker-boop/vault_data/attacks.db \\
      --limit 5000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ataker.vault import AttackVault  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Import fortress attacker base into Attack Vault")
    p.add_argument(
        "--jsonl",
        default=os.environ.get(
            "ATTACKER_JSONL",
            str(Path(os.environ.get("FORTRESS_DATA", "/fortress_data/attacker")) / "normalized" / "attacks.jsonl"),
        ),
        help="Path to normalized attacks.jsonl",
    )
    p.add_argument(
        "--vault",
        default=str(ROOT / "vault_data" / "attacks.db"),
        help="Attack Vault sqlite path",
    )
    p.add_argument("--source", default="fortress", help="Default source label")
    p.add_argument("--limit", type=int, default=None, help="Max rows to import")
    p.add_argument(
        "--category",
        action="append",
        default=None,
        help="Filter category (repeatable)",
    )
    p.add_argument(
        "--skip-needs-review",
        action="store_true",
        help="Skip rows with raw_meta.needs_review=true",
    )
    args = p.parse_args()

    jsonl = Path(args.jsonl)
    if not jsonl.exists():
        print(f"ERROR: jsonl not found: {jsonl}", file=sys.stderr)
        return 2

    vault_path = Path(args.vault)
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault = AttackVault(db_path=vault_path)
    n = vault.import_from_jsonl(
        jsonl,
        source=args.source,
        limit=args.limit,
        categories=args.category,
        skip_needs_review=args.skip_needs_review,
    )
    stats = vault.get_stats()
    print(json.dumps({"imported": n, "stats": stats}, ensure_ascii=False, indent=2))
    return 0 if n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
