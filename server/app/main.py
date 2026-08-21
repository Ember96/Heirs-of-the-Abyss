"""EndlessDungeon server — FastAPI app (T1.3).

`GET /health` + `WS /game`. The WS endpoint wires each connection through the
hardened `Connection` gateway (auth, seq, HMAC, rate-limit, generation tracker).
"""

from __future__ import annotations

from fastapi import FastAPI, WebSocket

from . import ws

# LangSmith: tracing auto-initializes from LANGSMITH_API_KEY / LANGSMITH_TRACING env.
import langsmith  # noqa: F401

app = FastAPI(title="EndlessDungeon", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/game")
async def game(websocket: WebSocket) -> None:
    await ws.Connection(websocket).run()
