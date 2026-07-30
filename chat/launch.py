#!/usr/bin/env python3
"""
Запуск Крепость Hub окном (не вкладкой браузера).

Поднимает server.py и открывает Chrome/Chromium/Edge в режиме --app.

    python3 chat/launch.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("CHAT_HOST", "127.0.0.1")
PORT = int(os.environ.get("CHAT_PORT", "8765"))
URL = f"http://{HOST}:{PORT}/"


def find_browser() -> list[str] | None:
    env = os.environ.get("KREPOST_BROWSER")
    if env and Path(env).exists():
        return [env]
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "brave-browser",
    ]
    for c in candidates:
        if c.startswith("/") and Path(c).exists():
            return [c]
        found = shutil.which(c)
        if found:
            return [found]
    return None


def wait_ready(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(URL + "api/agents", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def detect_local_api() -> str | None:
    for base in ("http://127.0.0.1:8000", "http://localhost:8000"):
        try:
            with urllib.request.urlopen(base + "/health", timeout=1.5) as r:
                if r.status == 200:
                    return base
        except Exception:
            continue
    return None


def main() -> int:
    env = os.environ.copy()
    # На Studio API почти всегда на localhost — не ходим в Tailscale IP (Errno 60)
    if not env.get("KREPOST_URL"):
        local = detect_local_api()
        if local:
            env["KREPOST_URL"] = local
            print("KREPOST_URL →", local)
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py")],
        cwd=str(ROOT.parent),
        env=env,
    )
    try:
        if not wait_ready():
            print("Сервер не поднялся на", URL, file=sys.stderr)
            return 1
        browser = find_browser()
        if not browser:
            print(f"Браузер не найден. Открой сам: {URL}")
            print("Или задай KREPOST_BROWSER=/path/to/chrome")
            server.wait()
            return 0
        profile = ROOT / "data" / "chrome-profile"
        profile.mkdir(parents=True, exist_ok=True)
        cmd = browser + [
            f"--app={URL}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--disable-extensions",
            f"--window-size=1180,760",
            "--window-position=80,60",
        ]
        print("Крепость Hub →", URL)
        print("Окно:", " ".join(cmd[:2]), "...")
        proc = subprocess.Popen(cmd)
        proc.wait()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
