from __future__ import annotations

import json
import os
from pathlib import Path
import importlib
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
    from server.environment import LedgerShieldEnvironment
else:
    from .environment import LedgerShieldEnvironment


def _load_benchmark_report_module():
    try:
        return importlib.import_module("benchmark_report")
    except ModuleNotFoundError:
        return None


def build_app():
    env = LedgerShieldEnvironment()
    app = create_fastapi_app(env, LedgerShieldAction, LedgerShieldObservation)

    @app.get("/leaderboard")
    def leaderboard() -> dict[str, Any]:
        benchmark_report = _load_benchmark_report_module()
        if benchmark_report is None:
            return {
                "benchmark": "ledgershield-v3",
                "generated_at": None,
                "note": "benchmark_report.py is unavailable in this runtime image.",
                "entries": [],
            }
        return benchmark_report.load_leaderboard_payload()

    @app.get("/benchmark-report")
    def latest_benchmark_report() -> dict[str, Any]:
        benchmark_report = _load_benchmark_report_module()
        if benchmark_report is None:
            return {
                "benchmark": "ledgershield-v3",
                "generated_at": None,
                "note": "benchmark_report.py is unavailable in this runtime image.",
            }
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
