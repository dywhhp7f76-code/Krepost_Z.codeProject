#!/usr/bin/env python3
"""Замер latency OpenAI-совместимого endpoint (LM Studio / vLLM).

    python scripts/probe_latency.py --base-url http://127.0.0.1:1234/v1 \
        --model qwen/qwen3.6-35b-a3b --n 5
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request


def one_call(base_url: str, model: str, api_key: str, prompt: str, timeout: int) -> float:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 64,
        "temperature": 0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()
    return (time.perf_counter() - t0) * 1000


def main() -> int:
    p = argparse.ArgumentParser(description="Probe LLM endpoint latency")
    p.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
    p.add_argument("--model", required=True)
    p.add_argument("--api-key", default="lm-studio")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--prompt", default="Скажи одно слово: ок")
    args = p.parse_args()

    times = []
    for i in range(args.n):
        ms = one_call(args.base_url, args.model, args.api_key, args.prompt, args.timeout)
        times.append(ms)
        print(f"  [{i+1}/{args.n}] {ms:.0f} ms")
    print(
        f"n={args.n} mean={statistics.mean(times):.0f} ms "
        f"p50={statistics.median(times):.0f} ms "
        f"min={min(times):.0f} max={max(times):.0f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
