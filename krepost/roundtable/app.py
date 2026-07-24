"""Round Table HTTP app — Air only (default :8011)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from krepost.roundtable.broker import RedactionError
from krepost.roundtable.mode import ModeGate
from krepost.roundtable.schemas import (
    AttackReceipt,
    DefenseReceipt,
    Speaker,
)
from krepost.roundtable.session import RoundTable

_STATIC = Path(__file__).resolve().parent / "static" / "roundtable.html"


class PostBody(BaseModel):
    speaker: Speaker
    body: str = Field(..., min_length=1, max_length=4000)
    cites: List[str] = Field(default_factory=list)


class ModeBody(BaseModel):
    attack_locked: Optional[bool] = None
    poison_marker: Optional[str] = None


def create_roundtable_app(
    table: Optional[RoundTable] = None,
    *,
    poison_marker: Optional[str] = None,
    attack_locked: Optional[bool] = None,
) -> FastAPI:
    marker = poison_marker
    if marker is None:
        marker = os.environ.get("ROUNDTABLE_POISON_MARKER", "")
    locked_env = os.environ.get("ROUNDTABLE_ATTACK_LOCKED", "1").strip() not in (
        "0",
        "false",
        "False",
        "no",
    )
    if attack_locked is None:
        attack_locked = locked_env

    gate = ModeGate(
        poison_marker=marker or None,
        attack_locked=bool(attack_locked),
    )
    rt = table or RoundTable(gate=gate)

    app = FastAPI(title="RoundTable", version="0.1.0")
    app.state.roundtable = rt  # type: ignore[attr-defined]

    @app.get("/health")
    def health():
        snap = rt.mode()
        return {
            "status": "ok",
            "service": "RoundTable",
            "mode": snap.mode.value,
            "live_allowed": snap.live_allowed,
            "poison_present": snap.poison_present,
            "attack_locked": snap.attack_locked,
            "reason": snap.reason,
            "ui": "/roundtable",
        }

    @app.get("/")
    @app.get("/roundtable")
    def ui():
        if not _STATIC.is_file():
            raise HTTPException(500, "roundtable.html missing")
        return FileResponse(
            _STATIC,
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/v1/roundtable/mode")
    def get_mode():
        snap = rt.mode()
        return {
            "mode": snap.mode.value,
            "live_allowed": snap.live_allowed,
            "poison_present": snap.poison_present,
            "attack_locked": snap.attack_locked,
            "reason": snap.reason,
        }

    @app.post("/v1/roundtable/mode")
    def set_mode(body: ModeBody):
        if body.attack_locked is not None:
            rt.gate.set_attack_locked(body.attack_locked)
        if body.poison_marker is not None:
            rt.gate.set_poison_marker(body.poison_marker or None)
        return get_mode()

    @app.get("/v1/roundtable/feed")
    def feed(limit: int = 200):
        items = rt.feed(limit=min(max(limit, 1), 500))
        return {"items": [u.model_dump(mode="json") for u in items]}

    @app.get("/v1/roundtable/receipts")
    def receipts():
        return rt.receipts()

    @app.post("/v1/roundtable/receipts/attack")
    def post_attack(receipt: AttackReceipt):
        rt.add_attack_receipt(receipt)
        return {"ok": True, "attack_id": receipt.attack_id}

    @app.post("/v1/roundtable/receipts/defense")
    def post_defense(receipt: DefenseReceipt):
        rt.add_defense_receipt(receipt)
        return {"ok": True, "defense_id": receipt.defense_id}

    @app.post("/v1/roundtable/post")
    def post_utt(body: PostBody):
        try:
            utt = rt.post(body.speaker, body.body, body.cites)
        except RedactionError as e:
            raise HTTPException(
                status_code=403,
                detail={"reason_code": e.reason_code, "detail": e.detail or ""},
            ) from e
        return utt.model_dump(mode="json")

    return app


def main() -> None:
    import uvicorn

    host = os.environ.get("ROUNDTABLE_HOST", "127.0.0.1")
    port = int(os.environ.get("ROUNDTABLE_PORT", "8011"))
    uvicorn.run(
        "krepost.roundtable.app:create_roundtable_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
