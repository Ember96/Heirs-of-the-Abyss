"""Standalone protocol server for client dev — no LLM, no game engine (T2+).

Run:  uv run python scripts/mock_server.py
      (equivalent to: uv run uvicorn app.main:app --host 127.0.0.1 --port 8000)
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
