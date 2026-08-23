"""EndlessDungeon server — FastAPI app.

`GET /health` + `WS /game`. The WS endpoint wires each connection through the
hardened `Connection` gateway (auth, seq, HMAC, rate-limit, generation tracker)
with the shared SQLite session store behind it, so sessions and fights survive
reconnects and restarts.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket

from . import config, ws
from .persistence import SessionStore

import langsmith  # noqa: F401


def _db_path() -> str:
    raw = config.DATABASE_URL
    if raw.startswith("sqlite:///"):
        raw = raw[len("sqlite:///"):]
    path = Path(raw)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


store = SessionStore(_db_path())

app = FastAPI(title="EndlessDungeon", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/game")
async def game(websocket: WebSocket) -> None:
    await ws.Connection(websocket, store=store).run()
