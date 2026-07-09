#!/usr/bin/env python3
"""
Сбор threat intelligence из источников для Krepost-V3.
Адаптация github-copilot-expert/scripts/fetch_news.py.

Каждый источник изолирован: ошибка одного НЕ роняет остальные.
Результат -> raw/items.json
Текст санитизируется (обрезка, удаление управляющих символов) ПЕРЕД
отправкой в Claude — базовая защита от prompt-injection через чужой контент.

Krepost-специфичные изменения:
- Добавлены источники: OWASP, NVD, MITRE ATLAS, prompt-injection repos
- Убраны нерелевантные общие AI-источники
- Категории привязаны к слоям Krepost pipeline
- Добавлен приоритет (stars) с учётом security-релевантности
"""
import json, re, sys, time, pathlib, datetime
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "krepost-threat-intel/1.0 (+github actions)"}
TIMEOUT = 20
MAX_PER_SOURCE = 12          # не больше N свежих items с источника
MAX_TEXT = 4000              # обрезка тела одной статьи (символов)

OUT = pathlib.Path("raw"); OUT.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# ИСТОЧНИКИ
# Категории привязаны к слоям Krepost:
#   security  -> Layer 1-3 (RegexFilter, GuardClassifier, FewShotMatcher)
#   defense   -> Layer 2-4 (Guard, OutputFilter, guardrails)
#   redteam   -> Red Team / adversarial testing
#   evolution -> self-improvement, multi-agent, consensus
#   all       -> общий AI/ML контент
# ═══════════════════════════════════════════════════════════════════════════

SOURCES = [
    # --- Krepost-специфичные: Security & Prompt Injection ---
    {"name": "OWASP Top 10 LLM",
     "type": "github_releases",
     "url": "https://api.github.com/repos/OWASP/www-project-top-10-for-large-language-model-applications/releases?per_page=10",
     "cat": "security", "stars": 5},

    {"name": "NVD CVE (AI/ML)",
     "type": "rss",
     "url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss-analyzed.xml",
     "cat": "security", "stars": 5},

    {"name": "MITRE ATLAS",
     "type": "github_releases",
     "url": "https://api.github.com/repos/mitre-atlas/atlas-data/releases?per_page=5",
     "cat": "security", "stars": 5},

    {"name": "JailbreakBench",
     "type": "github_releases",
     "url": "https://api.github.com/repos/JailbreakBench/jailbreakbench/releases?per_page=5",
     "cat": "redteam", "stars": 5},

    {"name": "garak (LLM vuln scanner)",
     "type": "github_releases",
     "url": "https://api.github.com/repos/NVIDIA/garak/releases?per_page=5",
     "cat": "redteam", "stars": 5},

    {"name": "PromptBench",
     "type": "github_releases",
     "url": "https://api.github.com/repos/microsoft/promptbench/releases?per_page=5",
     "cat": "redteam", "stars": 4},

    {"name": "PyRIT",
     "type": "github_releases",
     "url": "https://api.github.com/repos/Azure/PyRIT/releases?per_page=5",
     "cat": "redteam", "stars": 5},

    {"name": "promptfoo",
     "type": "github_releases",
     "url": "https://api.github.com/repos/promptfoo/promptfoo/releases?per_page=5",
     "cat": "redteam", "stars": 4},

    {"name": "Rebuff (prompt injection)",
     "type": "github_releases",
     "url": "https://api.github.com/repos/protectai/rebuff/releases?per_page=5",
     "cat": "defense", "stars": 4},

    {"name": "LLM Guard",
     "type": "github_releases",
     "url": "https://api.github.com/repos/protectai/llm-guard/releases?per_page=5",
     "cat": "defense", "stars": 5},

    {"name": "Guardrails AI",
     "type": "github_releases",
     "url": "https://api.github.com/repos/guardrails-ai/guardrails/releases?per_page=5",
     "cat": "defense", "stars": 4},

    # --- arXiv: Security & Adversarial ML ---
    {"name": "arXiv cs.CR (Crypto/Security)",
     "type": "api_arxiv",
     "url": "http://export.arxiv.org/api/query?search_query=cat:cs.CR+AND+(LLM+OR+prompt+injection+OR+adversarial)&sortBy=submittedDate&sortOrder=descending&max_results=15",
     "cat": "security", "stars": 4},

    {"name": "arXiv cs.AI (AI Safety)",
     "type": "api_arxiv",
     "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+(safety+OR+alignment+OR+guardrail)&sortBy=submittedDate&sortOrder=descending&max_results=15",
     "cat": "defense", "stars": 4},

    {"name": "arXiv cs.LG (Adversarial)",
     "type": "api_arxiv",
     "url": "http://export.arxiv.org/api/query?search_query=cat:cs.LG+AND+(adversarial+OR+robustness+OR+red+team)&sortBy=submittedDate&sortOrder=descending&max_results=15",
     "cat": "redteam", "stars": 3},

    # --- Общие источники (из оригинала, security-фильтрованные) ---
    {"name": "Habr Security",
     "type": "rss",
     "url": "https://habr.com/ru/rss/hub/information_security/",
     "cat": "security", "stars": 4},

    {"name": "Habr AI",
     "type": "rss",
     "url": "https://habr.com/ru/rss/hub/artificial_intelligence/",
     "cat": "all", "stars": 3},

    {"name": "CyberForum AI",
     "type": "rss",
     "url": "https://www.cyberforum.ru/rss/forum-380.html",
     "cat": "security", "stars": 3},

    {"name": "Hacker News",
     "type": "api_hn",
     "url": "https://hacker-news.firebaseio.com/v0/newstories.json",
     "cat": "all", "stars": 2},

    {"name": "r/LocalLLaMA",
     "type": "api_reddit",
     "url": "https://www.reddit.com/r/LocalLLaMA/top.json?t=week&limit=15",
     "cat": "all", "stars": 3},

    # --- Инфраструктура (foundation) ---
    {"name": "LocalAI",
     "type": "github_releases",
     "url": "https://api.github.com/repos/mudler/LocalAI/releases?per_page=5",
     "cat": "foundation", "stars": 3},

    {"name": "vLLM",
     "type": "github_releases",
     "url": "https://api.github.com/repos/vllm-project/vllm/releases?per_page=5",
     "cat": "foundation", "stars": 3},

    {"name": "Ollama",
     "type": "github_releases",
     "url": "https://api.github.com/repos/ollama/ollama/releases?per_page=5",
     "cat": "foundation", "stars": 4},
]


def clean(text: str) -> str:
    """Санитизация текста от HTML и управляющих символов."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)          # убрать html-теги
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)  # управляющие
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_TEXT]


def get(url):
    """HTTP GET с User-Agent и таймаутом."""
    return requests.get(url, headers=UA, timeout=TIMEOUT)


def fetch(src):
    """Извлечь items из одного источника. Поддерживаемые типы:
    rss, api_devto, api_arxiv, api_hn, api_reddit, github_releases, html
    """
    t = src["type"]; items = []

    if t == "rss":
        d = feedparser.parse(src["url"])
        for e in d.entries[:MAX_PER_SOURCE]:
            items.append({
                "title": clean(e.get("title", "")),
                "url": e.get("link", ""),
                "text": clean(e.get("summary", "") or e.get("description", ""))
            })

    elif t == "api_devto":
        for a in get(src["url"]).json()[:MAX_PER_SOURCE]:
            items.append({
                "title": clean(a.get("title", "")),
                "url": a.get("url", ""),
                "text": clean(a.get("description", ""))
            })

    elif t == "api_arxiv":
        d = feedparser.parse(get(src["url"]).text)
        for e in d.entries[:MAX_PER_SOURCE]:
            items.append({
                "title": clean(e.get("title", "")),
                "url": e.get("link", ""),
                "text": clean(e.get("summary", ""))
            })

    elif t == "api_hn":
        ids = get(src["url"]).json()[:MAX_PER_SOURCE]
        for i in ids:
            it = get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json").json() or {}
            if it.get("title"):
                items.append({
                    "title": clean(it.get("title", "")),
                    "url": it.get("url", f"https://news.ycombinator.com/item?id={i}"),
                    "text": clean(it.get("text", ""))
                })

    elif t == "api_reddit":
        for c in get(src["url"]).json().get("data", {}).get("children", [])[:MAX_PER_SOURCE]:
            p = c.get("data", {})
            items.append({
                "title": clean(p.get("title", "")),
                "url": "https://reddit.com" + p.get("permalink", ""),
                "text": clean(p.get("selftext", ""))
            })

    elif t == "github_releases":
        for r in get(src["url"]).json()[:MAX_PER_SOURCE]:
            items.append({
                "title": clean(r.get("name") or r.get("tag_name", "")),
                "url": r.get("html_url", ""),
                "text": clean(r.get("body", ""))
            })

    elif t == "html":
        soup = BeautifulSoup(get(src["url"]).text, "lxml")
        for a in soup.select("a")[:60]:
            title = clean(a.get_text())
            href = a.get("href", "")
            if len(title) > 30 and href.startswith("http"):
                items.append({"title": title, "url": href, "text": ""})
        items = items[:MAX_PER_SOURCE]

    # Пометить каждый item источником и категорией
    for it in items:
        it["source"] = src["name"]
        it["cat"] = src["cat"]
        it["stars"] = src["stars"]

    return items


def main():
    all_items, log = [], []
    for src in SOURCES:
        try:
            got = fetch(src)
            all_items.extend(got)
            log.append(f"OK   {src['name']}: {len(got)}")
        except Exception as e:
            log.append(f"SKIP {src['name']}: {type(e).__name__} {e}")
        time.sleep(1)   # вежливый троттлинг между источниками

    print("\n".join(log), file=sys.stderr)

    (OUT / "items.json").write_text(json.dumps({
        "generated": datetime.datetime.utcnow().isoformat() + "Z",
        "count": len(all_items),
        "sources_total": len(SOURCES),
        "sources_security": sum(1 for s in SOURCES if s["cat"] == "security"),
        "sources_redteam": sum(1 for s in SOURCES if s["cat"] == "redteam"),
        "items": all_items
    }, ensure_ascii=False, indent=2))

    print(f"Collected {len(all_items)} items from {len(SOURCES)} sources "
          f"({sum(1 for s in SOURCES if s['stars'] >= 4)} high-priority).")


if __name__ == "__main__":
    main()
