#!/usr/bin/env python3
"""
Крепость Hub — локальный мессенджер для агентов (как Telegram).

Слева — список агентов, справа — чат. Агенты хранятся в chat/data/agents.json.
Каждый агент = свой base URL API (Studio, demo, будущие сервисы).

Запуск:
    python3 chat/server.py
    # или окном без хрома браузера:
    python3 chat/launch.py

Переменные:
    CHAT_HOST / CHAT_PORT — UI (по умолчанию 127.0.0.1:8765)
    KREPOST_URL — куда ходить за API (по умолчанию авто: localhost, потом Tailscale)
    KREPOST_STUDIO_URL — API Крепости в LAN (по умолчанию http://10.0.0.1:8000, UI: /chat)
    HTTP_PROXY / HTTPS_PROXY / ALL_PROXY — для userspace Tailscale
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import uuid
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
AGENTS_FILE = DATA / "agents.json"
DEFAULTS_FILE = ROOT / "agents.defaults.json"
SETTINGS_FILE = DATA / "settings.json"

CHAT_HOST = os.environ.get("CHAT_HOST", "127.0.0.1")
CHAT_PORT = int(os.environ.get("CHAT_PORT", "8765"))
STUDIO_URL = os.environ.get("KREPOST_STUDIO_URL", "http://10.0.0.1:8000").rstrip("/")

DEFAULT_SETTINGS = {
    "api_url": "http://10.0.0.1:8000",
    "chat_url": "http://10.0.0.1:8000/chat",
    "local_url": "http://127.0.0.1:8000",
    "default_target": "studio",  # studio | local | custom
    "apply_to_all_agents": True,
}

AGENT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
# connect timeout короткий — иначе macOS Errno 60 висит минутами
CONNECT_TIMEOUT = float(os.environ.get("KREPOST_CONNECT_TIMEOUT", "8"))
READ_TIMEOUT = float(os.environ.get("KREPOST_READ_TIMEOUT", "300"))

_cached_upstream: str | None = None


def load_defaults() -> dict:
    """7 агентов из репо (Совет + Аналитик + Атакер)."""
    if DEFAULTS_FILE.is_file():
        return json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "agents": [
            {
                "id": "krepost",
                "name": "Крепость",
                "subtitle": "Основной ИИ · Studio",
                "url": "local",
                "defaultMode": "agent",
                "color": "#d4a574",
                "enabled": True,
            }
        ],
    }


DEFAULT_AGENTS = load_defaults()


def _opener() -> urllib.request.OpenerDirector:
    proxies = {}
    for key in ("http", "https"):
        val = os.environ.get(f"{key.upper()}_PROXY") or os.environ.get("ALL_PROXY")
        if val:
            proxies[key] = val
    handlers = []
    if proxies:
        handlers.append(urllib.request.ProxyHandler(proxies))
    handlers.append(urllib.request.HTTPHandler())
    handlers.append(urllib.request.HTTPSHandler())
    return urllib.request.build_opener(*handlers)


OPENER = _opener()


def _probe(base: str, timeout: float = 1.5) -> bool:
    url = base.rstrip("/") + "/health"
    try:
        with OPENER.open(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def load_settings() -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.is_file():
        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            out = dict(DEFAULT_SETTINGS)
            out.update({k: v for k, v in raw.items() if k in DEFAULT_SETTINGS or k in ("api_url", "chat_url", "local_url", "default_target", "apply_to_all_agents")})
            return out
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> dict:
    global STUDIO_URL, _cached_upstream
    DATA.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings or {})
    for key in ("api_url", "chat_url", "local_url"):
        if merged.get(key):
            merged[key] = str(merged[key]).rstrip("/")
    # chat_url всегда UI-путь
    api = merged.get("api_url") or "http://10.0.0.1:8000"
    chat = merged.get("chat_url") or (api + "/chat")
    if not chat.rstrip("/").endswith("/chat"):
        chat = api.rstrip("/") + "/chat"
    merged["api_url"] = api.rstrip("/")
    merged["chat_url"] = chat
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(SETTINGS_FILE)
    target = merged.get("default_target") or "studio"
    if target == "local":
        os.environ["KREPOST_URL"] = merged.get("local_url") or "http://127.0.0.1:8000"
    else:
        os.environ["KREPOST_URL"] = merged["api_url"]
        os.environ["KREPOST_STUDIO_URL"] = merged["api_url"]
    STUDIO_URL = merged["api_url"]
    _cached_upstream = None
    if merged.get("apply_to_all_agents"):
        store = load_store()
        marker = "local" if target == "local" else "studio" if target == "studio" else merged["api_url"]
        for a in store.get("agents", []):
            a["url"] = marker
        save_store(store)
    return merged


def pick_upstream(force: bool = False) -> str:
    """Выбрать API: настройки → env → probe."""
    global _cached_upstream
    if _cached_upstream and not force:
        return _cached_upstream
    settings = load_settings()
    target = settings.get("default_target") or "studio"
    if target == "local":
        cand0 = (settings.get("local_url") or "http://127.0.0.1:8000").rstrip("/")
    else:
        cand0 = (settings.get("api_url") or STUDIO_URL).rstrip("/")
    env = (os.environ.get("KREPOST_URL") or "").strip().rstrip("/")
    ordered = []
    for c in (env, cand0, settings.get("local_url"), "http://127.0.0.1:8000", STUDIO_URL, "http://10.0.0.1:8000"):
        if c and c not in ordered:
            ordered.append(str(c).rstrip("/"))
    for cand in ordered:
        if _probe(cand):
            _cached_upstream = cand
            print(f"Крепость API → {cand}", file=sys.stderr)
            return cand
    _cached_upstream = cand0
    print(f"Крепость API probe fail — использую {cand0}", file=sys.stderr)
    return _cached_upstream


def resolve_agent_url(url: str) -> str:
    u = (url or "").strip()
    if u in ("", "local", "auto", "$KREPOST_URL"):
        return pick_upstream()
    if u in ("studio", "$KREPOST_STUDIO_URL"):
        return STUDIO_URL
    return u.rstrip("/")


def migrate_tailscale_to_local(store: dict) -> bool:
    """Если localhost жив — заменить удалённые URL → local (Errno 60 на Mac)."""
    if not _probe("http://127.0.0.1:8000"):
        return False
    changed = False
    for a in store.get("agents", []):
        u = str(a.get("url") or "")
        if any(x in u for x in ("100.72.72.28", "10.0.0.1")) or u in ("studio", STUDIO_URL):
            a["url"] = "local"
            changed = True
    return changed


def ensure_store() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if not AGENTS_FILE.exists():
        _write_store(load_defaults())
    else:
        try:
            store = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
            if migrate_tailscale_to_local(store):
                _write_store(store)
                print("agents.json: URL переключены на local (localhost API доступен)", file=sys.stderr)
        except Exception:
            pass


def _write_store(store: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = AGENTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(AGENTS_FILE)


def apply_persona(agent: dict, body: bytes | None) -> bytes | None:
    """Подмешивает persona агента в text запроса (роли Совета из репо)."""
    if not body:
        return body
    persona = (agent.get("persona") or "").strip()
    if not persona:
        return body
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return body
    text = str(payload.get("text") or "")
    # не дублируем, если уже обернуто
    marker = f"[РОЛЬ: {agent.get('name', agent.get('id'))}]"
    if text.startswith(marker):
        return body
    wrapped = (
        f"{marker}\n{persona}\n\n"
        f"---\nЗапрос пользователя:\n{text}"
    )
    payload["text"] = wrapped
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def load_store() -> dict:
    ensure_store()
    try:
        return json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(load_defaults()))


def save_store(store: dict) -> None:
    _write_store(store)


def find_agent(store: dict, agent_id: str) -> dict | None:
    for a in store.get("agents", []):
        if a.get("id") == agent_id:
            return a
    return None


def proxy_to(base_url: str, method: str, path: str, body: bytes | None, content_type: str | None):
    url = base_url.rstrip("/") + path
    headers = {"Accept": "application/json", "User-Agent": "krepost-hub/1.0"}
    if body is not None:
        headers["Content-Type"] = content_type or "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    timeout = READ_TIMEOUT if method == "POST" else CONNECT_TIMEOUT
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Content-Type", "application/json"), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "application/json"), e.read()
    except Exception as e:  # noqa: BLE001
        err = str(e)
        hint = (
            "API Крепости недоступен по адресу {base}. "
            "На Mac Studio API обычно слушает только localhost — "
            "нажми «localhost» внизу слева или запусти: "
            "curl -X POST http://127.0.0.1:8765/api/agents/use-local "
            "и проверь: curl http://127.0.0.1:8000/health"
        ).format(base=base_url)
        if "60" in err or "timed out" in err.lower() or "Timeout" in type(e).__name__:
            detail = f"Таймаут связи с {base_url}. {hint}"
        else:
            detail = f"proxy_failed: {type(e).__name__}: {e}. {hint}"
        payload = json.dumps(
            {"status": "error", "detail": detail, "upstream": url},
            ensure_ascii=False,
        ).encode("utf-8")
        return 502, "application/json; charset=utf-8", payload


def _json_bytes(obj, status=200):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return status, "application/json; charset=utf-8", data


class Handler(BaseHTTPRequestHandler):
    server_version = "KrepostHub/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status: int, content_type: str, data: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return None

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length > 0 else b""

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            return self._serve_file(STATIC / "index.html")
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            target = (STATIC / rel).resolve()
            if not str(target).startswith(str(STATIC.resolve())):
                return self._send(403, "text/plain", b"forbidden")
            return self._serve_file(target)

        if path == "/api/agents":
            store = load_store()
            agents = []
            for a in store.get("agents", []):
                row = dict(a)
                row["resolvedUrl"] = resolve_agent_url(a.get("url", "local"))
                agents.append(row)
            return self._send(
                *_json_bytes({"agents": agents, "upstream": pick_upstream()})
            )

        if path == "/api/upstream":
            s = load_settings()
            return self._send(
                *_json_bytes(
                    {
                        "upstream": pick_upstream(force=True),
                        "local_ok": _probe(s.get("local_url") or "http://127.0.0.1:8000"),
                        "studio_ok": _probe(s.get("api_url") or STUDIO_URL),
                        "chat_url": s.get("chat_url"),
                    }
                )
            )

        if path == "/api/settings":
            s = load_settings()
            s = dict(s)
            s["upstream"] = pick_upstream()
            s["local_ok"] = _probe(s.get("local_url") or "http://127.0.0.1:8000")
            s["studio_ok"] = _probe(s.get("api_url") or STUDIO_URL)
            return self._send(*_json_bytes(s))

        m = re.fullmatch(r"/api/agents/([^/]+)/health", path)
        if m:
            return self._agent_proxy(m.group(1), "GET", "/health", None, None)

        m = re.fullmatch(r"/api/agents/([^/]+)/metrics", path)
        if m:
            return self._agent_proxy(m.group(1), "GET", "/metrics", None, None)

        self._send(404, "text/plain; charset=utf-8", b"not found")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/api/agents":
            payload = self._read_json()
            if payload is None:
                return self._send(*_json_bytes({"detail": "invalid_json"}, 400))
            return self._create_agent(payload)

        if path == "/api/settings":
            payload = self._read_json()
            if payload is None:
                return self._send(*_json_bytes({"detail": "invalid_json"}, 400))
            saved = save_settings(payload)
            saved = dict(saved)
            saved["ok"] = True
            saved["upstream"] = pick_upstream(force=True)
            saved["local_ok"] = _probe(saved.get("local_url") or "http://127.0.0.1:8000")
            saved["studio_ok"] = _probe(saved.get("api_url") or STUDIO_URL)
            return self._send(*_json_bytes(saved))

        if path == "/api/settings/test":
            payload = self._read_json() or {}
            url = str(payload.get("url") or pick_upstream()).rstrip("/")
            ok = _probe(url, timeout=3.0)
            return self._send(
                *_json_bytes(
                    {
                        "ok": ok,
                        "url": url,
                        "chat_url": url + "/chat" if not url.endswith("/chat") else url,
                        "detail": "связь есть" if ok else "нет ответа /health",
                    }
                )
            )

        if path == "/api/agents/reset":
            # вернуть 7 агентов из репо (перезаписывает локальный список)
            self._read_body()  # drain
            defaults = load_defaults()
            save_store(defaults)
            pick_upstream(force=True)
            return self._send(
                *_json_bytes({"ok": True, "agents": defaults.get("agents", [])})
            )

        if path == "/api/agents/use-local":
            # все агенты → local (127.0.0.1) — фикс Errno 60 на Studio
            self._read_body()
            store = load_store()
            for a in store.get("agents", []):
                a["url"] = "local"
            save_store(store)
            os.environ["KREPOST_URL"] = "http://127.0.0.1:8000"
            pick_upstream(force=True)
            return self._send(
                *_json_bytes(
                    {
                        "ok": True,
                        "upstream": "http://127.0.0.1:8000",
                        "agents": store.get("agents", []),
                    }
                )
            )

        if path == "/api/agents/use-studio":
            # все агенты → LAN Studio http://10.0.0.1:8000 (чат UI: /chat)
            self._read_body()
            store = load_store()
            for a in store.get("agents", []):
                a["url"] = "studio"
            save_store(store)
            os.environ["KREPOST_URL"] = STUDIO_URL
            pick_upstream(force=True)
            ok = _probe(STUDIO_URL, timeout=3.0)
            return self._send(
                *_json_bytes(
                    {
                        "ok": True,
                        "upstream": STUDIO_URL,
                        "chat_ui": STUDIO_URL + "/chat",
                        "reachable": ok,
                        "hint": None
                        if ok
                        else (
                            f"Крепость по {STUDIO_URL} не отвечает. "
                            f"Проверь в браузере: {STUDIO_URL}/chat и "
                            f"curl -m 3 {STUDIO_URL}/health"
                        ),
                        "agents": store.get("agents", []),
                    }
                )
            )

        m = re.fullmatch(r"/api/agents/([^/]+)/(query|agent)", path)
        if m:
            agent_id, kind = m.group(1), m.group(2)
            upstream = "/v1/query" if kind == "query" else "/v1/agent"
            body = self._read_body()
            return self._agent_proxy(
                agent_id,
                "POST",
                upstream,
                body,
                self.headers.get("Content-Type", "application/json"),
            )

        self._send(404, "text/plain; charset=utf-8", b"not found")

    def do_PATCH(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/agents/([^/]+)", path)
        if not m:
            return self._send(404, "text/plain; charset=utf-8", b"not found")
        payload = self._read_json()
        if payload is None:
            return self._send(*_json_bytes({"detail": "invalid_json"}, 400))
        return self._update_agent(m.group(1), payload)

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/agents/([^/]+)", path)
        if not m:
            return self._send(404, "text/plain; charset=utf-8", b"not found")
        return self._delete_agent(m.group(1))

    def _agent_proxy(self, agent_id, method, upstream_path, body, content_type):
        if not AGENT_ID_RE.match(agent_id):
            return self._send(*_json_bytes({"detail": "bad_agent_id"}, 400))
        store = load_store()
        agent = find_agent(store, agent_id)
        if not agent:
            return self._send(*_json_bytes({"detail": "agent_not_found"}, 404))
        if not agent.get("enabled", True):
            return self._send(*_json_bytes({"detail": "agent_disabled"}, 403))
        if method == "POST" and body is not None:
            body = apply_persona(agent, body)
        base = resolve_agent_url(agent.get("url", "local"))
        status, ctype, data = proxy_to(base, method, upstream_path, body, content_type)
        self._send(status, ctype, data)

    def _create_agent(self, payload: dict) -> None:
        name = str(payload.get("name") or "").strip()
        url = str(payload.get("url") or "").strip().rstrip("/")
        if not name or not url:
            return self._send(*_json_bytes({"detail": "name_and_url_required"}, 400))
        if not (url.startswith("http://") or url.startswith("https://")):
            return self._send(*_json_bytes({"detail": "url_must_be_http"}, 400))

        agent_id = str(payload.get("id") or "").strip() or re.sub(
            r"[^a-z0-9_-]+", "-", name.lower()
        ).strip("-")[:40]
        if not agent_id or not AGENT_ID_RE.match(agent_id):
            agent_id = "agent-" + uuid.uuid4().hex[:8]

        store = load_store()
        if find_agent(store, agent_id):
            agent_id = agent_id + "-" + uuid.uuid4().hex[:4]

        agent = {
            "id": agent_id,
            "name": name[:80],
            "subtitle": str(payload.get("subtitle") or url)[:120],
            "url": url,
            "defaultMode": "agent" if payload.get("defaultMode") == "agent" else "query",
            "color": str(payload.get("color") or "#5288c1")[:20],
            "enabled": True,
        }
        store.setdefault("agents", []).append(agent)
        save_store(store)
        self._send(*_json_bytes({"agent": agent}, 201))

    def _update_agent(self, agent_id: str, payload: dict) -> None:
        store = load_store()
        agent = find_agent(store, agent_id)
        if not agent:
            return self._send(*_json_bytes({"detail": "agent_not_found"}, 404))
        for key in ("name", "subtitle", "url", "defaultMode", "color", "enabled"):
            if key in payload:
                agent[key] = payload[key]
        if "url" in agent:
            agent["url"] = str(agent["url"]).rstrip("/")
        if agent.get("defaultMode") not in ("agent", "query"):
            agent["defaultMode"] = "query"
        save_store(store)
        self._send(*_json_bytes({"agent": agent}))

    def _delete_agent(self, agent_id: str) -> None:
        store = load_store()
        before = len(store.get("agents", []))
        store["agents"] = [a for a in store.get("agents", []) if a.get("id") != agent_id]
        if len(store["agents"]) == before:
            return self._send(*_json_bytes({"detail": "agent_not_found"}, 404))
        save_store(store)
        self._send(*_json_bytes({"ok": True}))

    def _serve_file(self, path: Path) -> None:
        if not path.is_file():
            return self._send(404, "text/plain; charset=utf-8", b"not found")
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype = f"{ctype}; charset=utf-8"
        self._send(200, ctype, data)


def main() -> None:
    ensure_store()
    if not (STATIC / "index.html").is_file():
        print(f"ERROR: нет UI в {STATIC}", file=sys.stderr)
        sys.exit(1)
    httpd = ThreadingHTTPServer((CHAT_HOST, CHAT_PORT), Handler)
    print(f"Крепость Hub → http://{CHAT_HOST}:{CHAT_PORT}")
    print(f"Агенты       → {AGENTS_FILE}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstop")
        httpd.server_close()


if __name__ == "__main__":
    main()
