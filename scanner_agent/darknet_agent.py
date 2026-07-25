#!/usr/bin/env python3
"""WebScannerAgent — сканер clearnet/.onion. Пишет ТОЛЬКО в ./results."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"


def _safe_results_path(name: str) -> Path:
    path = (RESULTS_DIR / name).resolve()
    root = RESULTS_DIR.resolve()
    if path != root and not str(path).startswith(str(root) + os.sep):
        raise ValueError(f"Отказ: путь вне results/: {path}")
    return path


class WebScannerAgent:
    def __init__(self):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.tor_proxies = {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050",
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.scan_results: list[dict] = []
        self.keywords: list[str] = []
        self.results_txt = _safe_results_path("results.txt")
        self.scan_log = _safe_results_path("scan_log.jsonl")

    def is_onion(self, url: str) -> bool:
        return ".onion" in url.lower()

    def set_keywords(self, words: list[str]) -> None:
        self.keywords = [w.strip().lower() for w in words if w.strip()]
        if self.keywords:
            print(f"🔑 Фильтр слов: {', '.join(self.keywords)}")
        else:
            print("🔑 Фильтр слов сброшен")

    def load_urls_from_file(self, filename: str = "urls.txt") -> list[str]:
        filepath = PROJECT_ROOT / filename
        if not filepath.is_file():
            print(f"❌ Файл {filename} не найден")
            return []
        urls = [
            line.strip()
            for line in filepath.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        print(f"📂 Загружено {len(urls)} URL из {filename}")
        return urls

    def _append_log(self, result: dict) -> None:
        with open(self.scan_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        status = "OK" if result.get("success") else "FAIL"
        line = (
            f"[{result.get('timestamp')}] {status} {result.get('url')} "
            f"status={result.get('status')} title={result.get('title')!r} "
            f"keywords={result.get('matched_keywords')} "
            f"error={result.get('error')}\n"
        )
        with open(self.results_txt, "a", encoding="utf-8") as f:
            f.write(line)

    def save_results(self) -> None:
        if not self.scan_results:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = _safe_results_path(f"scan_{timestamp}.json")
        path.write_text(
            json.dumps(self.scan_results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n💾 Результаты: {path}")

    def scan(self, url: str, timeout: int = 30) -> dict | None:
        url = url.strip()
        if not url:
            return None
        if not url.startswith("http"):
            url = "http://" + url

        print(f"\n[+] Сканирование: {url}")
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "status": None,
            "title": None,
            "preview": None,
            "matched_keywords": [],
            "keyword_filter_active": bool(self.keywords),
            "kept": True,
            "error": None,
        }

        try:
            proxies = self.tor_proxies if self.is_onion(url) else None
            response = requests.get(
                url,
                proxies=proxies,
                headers=self.headers,
                timeout=timeout,
                verify=False,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            title = (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else "Без заголовка"
            )
            text_preview = soup.get_text(separator=" ", strip=True)[:500]
            blob = f"{title}\n{text_preview}".lower()
            matched = [k for k in self.keywords if k in blob] if self.keywords else []

            result.update(
                {
                    "success": True,
                    "status": response.status_code,
                    "title": title,
                    "preview": text_preview,
                    "matched_keywords": matched,
                }
            )

            if self.keywords and not matched:
                result["kept"] = False
                print(f"⏭ Пропуск (нет слов {self.keywords}): {title}")
                self._append_log(result)
                return result

            print(f"✅ Статус: {response.status_code}")
            print(f"📌 Заголовок: {title}")
            if matched:
                print(f"🔑 Совпало: {matched}")

        except requests.exceptions.ProxyError:
            result["error"] = "Tor не запущен на 127.0.0.1:9050"
            print("❌ Tor не запущен (SOCKS 9050)")
        except requests.exceptions.Timeout:
            result["error"] = "Таймаут"
            print("❌ Таймаут")
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Ошибка: {e}")

        if result.get("kept", True):
            self.scan_results.append(result)
        self._append_log(result)
        return result


def _print_help() -> None:
    print(
        """
Команды:
  URL                  — сканировать (для .onion нужен Tor :9050)
  file urls.txt        — массовый скан из файла
  kw слово1,слово2     — фильтр по словам
  kw                   — сбросить фильтр
  help                 — справка
  exit / quit / выход  — сохранить и выйти

CLI:
  python darknet_agent.py
  python darknet_agent.py file urls.txt
  python darknet_agent.py kw bitcoin -- file urls.txt
""".strip()
    )


def _parse_cli(argv: list[str]) -> tuple[list[str], str | None]:
    keywords: list[str] = []
    file_arg: str | None = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "kw" and i + 1 < len(argv):
            keywords = [x.strip() for x in argv[i + 1].split(",") if x.strip()]
            i += 2
            continue
        if a == "file" and i + 1 < len(argv):
            file_arg = argv[i + 1]
            i += 2
            continue
        if a in ("help", "-h", "--help"):
            _print_help()
            sys.exit(0)
        i += 1
    return keywords, file_arg


def main() -> None:
    agent = WebScannerAgent()
    print("Darknet Agent v2.1")
    print("=" * 50)
    _print_help()

    keywords, file_arg = _parse_cli(sys.argv[1:])
    if keywords:
        agent.set_keywords(keywords)

    if file_arg:
        urls = agent.load_urls_from_file(file_arg)
        for i, url in enumerate(urls, 1):
            print(f"\n--- [{i}/{len(urls)}] ---")
            agent.scan(url)
    else:
        default = PROJECT_ROOT / "urls.txt"
        default_urls = agent.load_urls_from_file("urls.txt") if default.is_file() else []
        if default_urls:
            print(f"🚀 Массовый скан urls.txt ({len(default_urls)})…")
            for i, url in enumerate(default_urls, 1):
                print(f"\n--- [{i}/{len(default_urls)}] ---")
                agent.scan(url)
        else:
            print("Интерактив. Введи URL или команду (help).")
            while True:
                try:
                    target = input("\n> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if not target:
                    continue
                low = target.lower()
                if low in ("exit", "quit", "выход"):
                    break
                if low in ("help", "?"):
                    _print_help()
                    continue
                if low == "kw" or low.startswith("kw "):
                    rest = target[2:].strip()
                    if not rest:
                        agent.set_keywords([])
                    else:
                        agent.set_keywords([x.strip() for x in rest.split(",")])
                    continue
                if low.startswith("file "):
                    urls = agent.load_urls_from_file(target.split(None, 1)[1].strip())
                    for i, url in enumerate(urls, 1):
                        print(f"\n--- [{i}/{len(urls)}] ---")
                        agent.scan(url)
                    continue
                agent.scan(target)

    if agent.scan_results:
        agent.save_results()
        ok = sum(1 for r in agent.scan_results if r.get("success"))
        print(f"\n📊 Итог: {ok}/{len(agent.scan_results)} успешных")
    print("👋 Готово!")


if __name__ == "__main__":
    main()
