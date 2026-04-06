from __future__ import annotations

import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

import uvicorn

from models import LedgerShieldAction, LedgerShieldObservation
from openenv_compat import create_fastapi_app

if __package__ in {None, ""}:
    from server.environment import LedgerShieldEnvironment
else:
    from .environment import LedgerShieldEnvironment


def build_app():
    env = LedgerShieldEnvironment()
    return create_fastapi_app(env, LedgerShieldAction, LedgerShieldObservation)


app = build_app()


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
