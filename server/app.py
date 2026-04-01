from __future__ import annotations

import uvicorn

from models import LedgerShieldAction, LedgerShieldObservation
from openenv_compat import create_fastapi_app
from .environment import LedgerShieldEnvironment


def build_app():
    env = LedgerShieldEnvironment()
    return create_fastapi_app(env, LedgerShieldAction, LedgerShieldObservation)


app = build_app()


def main() -> None:
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()