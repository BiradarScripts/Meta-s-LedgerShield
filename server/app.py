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
    from server.certify import build_certify_report
    from server.visualization import build_controlbench_visualization
else:
    from .environment import LedgerShieldEnvironment
    from .certify import build_certify_report
    from .visualization import build_controlbench_visualization


def _load_benchmark_report_module():
    try:
        return importlib.import_module("benchmark_report")
    except ModuleNotFoundError:
        return None


def build_app():
    env = LedgerShieldEnvironment()
    app = create_fastapi_app(env, LedgerShieldAction, LedgerShieldObservation)

    def _latest_report() -> dict[str, Any]:
        benchmark_report = _load_benchmark_report_module()
        if benchmark_report is None:
            return {}
        report_path = benchmark_report.DEFAULT_REPORT_PATH
        if report_path.exists():
            return json.loads(report_path.read_text(encoding="utf-8"))
        return {}

    @app.get("/leaderboard")
    def leaderboard() -> dict[str, Any]:
        benchmark_report = _load_benchmark_report_module()
        if benchmark_report is None:
            return {
                "benchmark": "ledgershield-controlbench-v1",
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
                "benchmark": "ledgershield-controlbench-v1",
                "generated_at": None,
                "note": "benchmark_report.py is unavailable in this runtime image.",
            }
        report_path = benchmark_report.DEFAULT_REPORT_PATH
        if report_path.exists():
            return json.loads(report_path.read_text(encoding="utf-8"))
        return {
            "benchmark": "ledgershield-controlbench-v1",
            "generated_at": None,
            "note": "No benchmark report artifact generated yet. Run benchmark_report.py to create one.",
        }

    @app.post("/certify")
    def certify(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return build_certify_report(
            payload or {},
            benchmark_report=_latest_report(),
            institutional_memory=env.institutional_memory(),
        )

    @app.get("/certify-summary")
    def certify_summary() -> dict[str, Any]:
        return build_certify_report(
            {},
            benchmark_report=_latest_report(),
            institutional_memory=env.institutional_memory(),
        )

    @app.get("/controlbench-visualization")
    def controlbench_visualization() -> dict[str, Any]:
        report = _latest_report()
        if report and isinstance(report.get("controlbench_visualization"), dict):
            return report["controlbench_visualization"]
        return build_controlbench_visualization(report, institutional_memory=env.institutional_memory())

    @app.get("/controlbench-summary")
    def controlbench_summary() -> dict[str, Any]:
        benchmark_report = _load_benchmark_report_module()
        if benchmark_report is not None:
            controlbench_report_path = getattr(benchmark_report, "DEFAULT_CONTROLBENCH_REPORT_PATH", None)
            if isinstance(controlbench_report_path, Path) and controlbench_report_path.exists():
                return json.loads(controlbench_report_path.read_text(encoding="utf-8"))
            report_path = benchmark_report.DEFAULT_REPORT_PATH
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if isinstance(report.get("controlbench_quarter"), dict):
                    return report["controlbench_quarter"]
        memory = env.institutional_memory()
        return {
            "benchmark": "ledgershield-controlbench-v1",
            "note": "No ControlBench report artifact found; returning live institutional memory summary.",
            "controlbench_summary": memory.get("controlbench_summary", {}),
            "loss_surface": (memory.get("loss_ledger", {}) or {}).get("loss_surface", {}),
            "calibration_gate": memory.get("calibration_gate", {}),
        }

    @app.get("/human-baseline-summary")
    def human_baseline_summary() -> dict[str, Any]:
        benchmark_report = _load_benchmark_report_module()
        if benchmark_report is not None:
            report_path = benchmark_report.DEFAULT_REPORT_PATH
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if isinstance(report.get("human_baseline_track"), dict):
                    return report["human_baseline_track"]
        try:
            if __package__ in {None, ""}:
                from server.human_baseline import load_human_baseline_summary
            else:
                from .human_baseline import load_human_baseline_summary
        except ModuleNotFoundError:
            return {
                "track": "human_baseline",
                "note": "Human baseline loader is unavailable in this runtime image.",
            }
        return load_human_baseline_summary()

    @app.get("/institutional-memory")
    def institutional_memory() -> dict[str, Any]:
        return env.institutional_memory()

    @app.post("/institutional-reset")
    def institutional_reset() -> dict[str, Any]:
        return env.reset_institutional_memory()

    return app


app = build_app()


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
