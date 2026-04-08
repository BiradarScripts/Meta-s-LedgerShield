from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

import uvicorn

from models import LedgerShieldAction, LedgerShieldObservation
from openenv_compat import create_fastapi_app

if __package__ in {None, ""}:
    import benchmark_report
    from server.environment import LedgerShieldEnvironment
else:
    import benchmark_report
    from .environment import LedgerShieldEnvironment


def build_app():
    env = LedgerShieldEnvironment()
    app = create_fastapi_app(env, LedgerShieldAction, LedgerShieldObservation)

    @app.get("/leaderboard")
    def leaderboard() -> dict[str, Any]:
        return benchmark_report.load_leaderboard_payload()

    @app.get("/benchmark-report")
    def latest_benchmark_report() -> dict[str, Any]:
        report_path = benchmark_report.DEFAULT_REPORT_PATH
        if report_path.exists():
            return json.loads(report_path.read_text(encoding="utf-8"))
        return {
            "benchmark": "ledgershield-v3",
            "generated_at": None,
            "note": "No benchmark report artifact generated yet. Run benchmark_report.py to create one.",
        }

    return app


app = build_app()


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
