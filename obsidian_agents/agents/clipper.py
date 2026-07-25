"""Агент 1: URL → чистая markdown-заметка в Inbox."""
from __future__ import annotations

import re
from typing import Any, Dict
from urllib.parse import urlparse

import html2text
import requests
from bs4 import BeautifulSoup

from agents.common import load_config, write_note

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) ObsidianClipper/1.0"
}


def _fetch(url: str, timeout: int = 25) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def _extract(html: str, url: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "aside", "iframe"]):
        tag.decompose()
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = title or h1.get_text(strip=True)
    article = soup.find("article") or soup.find("main") or soup.body or soup
    conv = html2text.HTML2Text()
    conv.ignore_links = False
    conv.ignore_images = True
    conv.body_width = 0
    md = conv.handle(str(article))
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    if len(md) > 12000:
        md = md[:12000] + "\n\n…[обрезано]"
    if not title:
        title = urlparse(url).netloc or "clip"
    return title, md


def clip_url(url: str, *, note: str = "") -> Dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    html = _fetch(url)
    title, body = _extract(html, url)
    if note.strip():
        body = f"**Заметка оператора:** {note.strip()}\n\n---\n\n{body}"
    cfg = load_config()
    path = write_note(
        cfg["_inbox"],
        title=title,
        body=body,
        tags=["inbox", "clip", "from_web"],
        source=url,
        agent="clipper",
    )
    return {
        "ok": True,
        "agent": "clipper",
        "title": title,
        "path": str(path),
        "preview": body[:400],
    }
