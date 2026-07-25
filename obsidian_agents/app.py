#!/usr/bin/env python3
"""Локальный UI агентов наполнения Obsidian (только Inbox на Air)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from agents.builder import chat_turn
from agents.clipper import clip_url
from agents.common import load_config
from agents.registry import delete_agent, list_agents, run_agent
from agents.topic_note import make_topic_note

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="Obsidian Agents (Air)")


class ClipReq(BaseModel):
    url: str = Field(..., min_length=3, max_length=2000)
    note: str = Field("", max_length=4000)


class TopicReq(BaseModel):
    topic: str = Field(..., min_length=2, max_length=2000)
    extra: str = Field("", max_length=8000)
    use_llm: bool = True


class ChatReq(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    prefer_studio: bool = True


class RunReq(BaseModel):
    text: str = Field("", max_length=8000)
    url: str = Field("", max_length=2000)


@app.get("/")
def ui():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/hub")
def hub():
    """Одна точка входа: Крепость + Agents для группы Safari «Личный»."""
    return FileResponse(STATIC / "hub.html", headers={"Cache-Control": "no-store"})


@app.get("/api/config")
def api_config():
    cfg = load_config()
    return {
        "inbox": str(cfg["_inbox"]),
        "lmstudio_url": cfg.get("lmstudio_url"),
        "krepost_url": cfg.get("krepost_url"),
        "port": cfg.get("port", 8765),
    }


@app.get("/api/inbox")
def api_inbox():
    cfg = load_config()
    inbox: Path = cfg["_inbox"]
    files = sorted(inbox.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = []
    for p in files[:40]:
        items.append(
            {
                "name": p.name,
                "path": str(p),
                "mtime": int(p.stat().st_mtime),
            }
        )
    return {"inbox": str(inbox), "items": items}


@app.post("/api/open-inbox")
def api_open_inbox():
    cfg = load_config()
    inbox: Path = cfg["_inbox"]
    inbox.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["open", str(inbox)])  # Finder на macOS
    return {"ok": True, "inbox": str(inbox)}


@app.post("/api/clip")
def api_clip(req: ClipReq):
    try:
        return clip_url(req.url, note=req.note)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"{type(e).__name__}: {e}"}, status_code=400
        )


@app.post("/api/topic")
def api_topic(req: TopicReq):
    try:
        return make_topic_note(req.topic, extra=req.extra, use_llm=req.use_llm)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"{type(e).__name__}: {e}"}, status_code=400
        )


@app.post("/api/chat")
def api_chat(req: ChatReq):
    return chat_turn(req.message, prefer_studio=req.prefer_studio)


@app.get("/api/agents")
def api_agents():
    return {"agents": list_agents()}


@app.post("/api/agents/{agent_id}/run")
def api_run(agent_id: str, req: RunReq):
    result = run_agent(agent_id, text=req.text, url=req.url)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return result


@app.delete("/api/agents/{agent_id}")
def api_delete(agent_id: str):
    ok = delete_agent(agent_id)
    if not ok:
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
    return {"ok": True}


def main() -> None:
    cfg = load_config()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 8765))
    print(f"Obsidian agents UI → http://{host}:{port}")
    print(f"Inbox → {cfg['_inbox']}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
