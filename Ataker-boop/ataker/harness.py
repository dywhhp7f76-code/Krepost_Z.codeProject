"""CLI: python -m ataker.harness --url http://127.0.0.1:8010

Оркестратор Planner-Executor (stub planner) против Krepost HTTP.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Ataker harness — Planner-Executor loop → Krepost /v1/query"
    )
    p.add_argument(
        "--url",
        "--target",
        dest="url",
        default=os.environ.get("KREPOST_SANDBOX_URL", "http://127.0.0.1:8010"),
        help="База API (default sandbox :8010)",
    )
    p.add_argument("--batch", type=int, default=5, help="Рецептов за итерацию")
    p.add_argument("--max-iter", type=int, default=3, help="Макс. итераций Planner")
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--no-stop-on-bypass",
        action="store_true",
        help="Не останавливаться на первом BYPASS",
    )
    p.add_argument("--use-memory", action="store_true")
    p.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Куда писать harness_*.json (или ATAKER_REPORT_DIR)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Без сети: все хиты = BLOCK (для проверки петли)",
    )
    args = p.parse_args(argv)

    if ":8000" in args.url and "FORCE_STUDIO" not in os.environ:
        print(
            "⛔ URL содержит :8000 (боевой Studio?). "
            "Для песочницы нужен :8010. Или FORCE_STUDIO=1.",
            file=sys.stderr,
        )
        return 2

    # Ensure Ataker-boop root on path when run as script from elsewhere
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from ataker.adversarial_loop import AdversarialLoop
    from ataker.planner import StubPlanner
    from ataker.target_http import HitResult, KrepostHttpTarget

    report_dir = args.report_dir or Path(
        os.environ.get("ATAKER_REPORT_DIR") or "data/ataker_sandbox"
    )

    if args.dry_run:

        class _Dry:
            base_url = "dry://block"

            def post_query(self, text: str, *, session_id=None) -> HitResult:
                return HitResult(
                    mark="BLOCK",
                    verdict="RED",
                    status="blocked",
                    latency_ms=1.0,
                    layer="Layer1-Regex",
                    answer="",
                )

        target: KrepostHttpTarget | _Dry = _Dry()
    else:
        target = KrepostHttpTarget(
            args.url,
            timeout=args.timeout,
            use_memory=args.use_memory,
        )
        if not target.health():
            print(
                f"⚠ health fail for {args.url} — продолжаю (цель может подняться позже)",
                file=sys.stderr,
            )

    loop = AdversarialLoop(
        target=target,
        planner=StubPlanner(seed=args.seed),
        batch_size=args.batch,
        max_iterations=args.max_iter,
        stop_on_bypass=not args.no_stop_on_bypass,
        seed=args.seed,
        report_dir=report_dir,
    )
    report = loop.run()
    print(report.summary())
    print(f"hypothesis={report.hypothesis}")
    if report_dir:
        print(f"report_dir={report_dir}")
    return 0 if report.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
